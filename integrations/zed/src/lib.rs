use zed_extension_api::settings::ContextServerSettings;
use zed_extension_api::ContextServerConfiguration;
use zed_extension_api::{
    self as zed, Command, ContextServerId, DownloadedFileType, Os, Project, Result,
};

/// Version of the bootstrap script to download from GitHub Releases.
const BOOTSTRAP_VERSION: &str = "0.2.0";

/// GitHub asset name (fixed, as published in every release).
const BOOTSTRAP_ASSET_NAME: &str = "mcp_memento_bootstrap.py";

/// GitHub Releases base URL for the bootstrap script.
/// Tag convention: bootstrap-v{BOOTSTRAP_VERSION}
/// Asset: mcp_memento_bootstrap.py
const BOOTSTRAP_BASE_URL: &str = "https://github.com/annibale-x/mcp-memento/releases/download";

struct MementoExtension {
    cached_script: Option<String>,
}

impl MementoExtension {
    /// Downloads the bootstrap script into the extension working directory
    /// if it is not already present, then returns its filename.
    /// Zed sets the extension working directory as the cwd for child processes,
    /// so the bare filename is enough for Python to find the script.
    fn ensure_bootstrap_script(&mut self, version: &str) -> Result<String> {
        // If we already resolved it during this session, skip everything.
        if let Some(ref cached) = self.cached_script {
            return Ok(cached.clone());
        }

        // Embed the version in the local filename so that upgrading BOOTSTRAP_VERSION
        // always triggers a fresh download (zed::download_file never overwrites).
        let local_name = format!("mcp_memento_bootstrap_v{}.py", version);

        // Check if the versioned file already exists on disk — if so, skip the
        // network call entirely.  zed::download_file returns an error when the
        // destination file already exists, which would cause context_server_command
        // to fail and Zed to report "Context server stopped running".
        let file_exists = std::fs::metadata(&local_name).is_ok();

        if !file_exists {
            let url = format!(
                "{}/bootstrap-v{}/{}",
                BOOTSTRAP_BASE_URL, version, BOOTSTRAP_ASSET_NAME
            );

            zed::download_file(&url, &local_name, DownloadedFileType::Uncompressed)
                .map_err(|e| format!("Failed to download mcp-memento bootstrap: {e}"))?;
        }

        self.cached_script = Some(local_name.clone());

        Ok(local_name)
    }

    /// Returns ordered Python executable candidates for the current platform.
    /// The caller will try them in order; Zed uses the first `command` string
    /// directly, so we just return the best single candidate we can determine
    /// without a live `which()` call.
    fn default_python_candidates(os: Os) -> Vec<&'static str> {
        match os {
            Os::Windows => vec!["py", "python", "python3"],
            Os::Mac | Os::Linux => vec!["python3", "python"],
        }
    }
}

impl zed::Extension for MementoExtension {
    fn new() -> Self {
        Self {
            cached_script: None,
        }
    }

    fn context_server_command(
        &mut self,
        context_server_id: &ContextServerId,
        project: &Project,
    ) -> Result<Command> {
        let (os, _arch) = zed::current_platform();

        // --- Read settings ---
        let mut python_command: Option<String> = None;
        let mut bootstrap_version = BOOTSTRAP_VERSION.to_string();
        let mut env_vars = vec![("PYTHONUNBUFFERED".to_string(), "1".to_string())];

        if let Ok(settings) =
            ContextServerSettings::for_project(context_server_id.as_ref(), project)
        {
            if let Some(zed_extension_api::serde_json::Value::Object(map)) = settings.settings {
                if let Some(cmd) = map.get("PYTHON_COMMAND").and_then(|v| v.as_str()) {
                    if !cmd.is_empty() && cmd != "auto" {
                        python_command = Some(cmd.to_string());
                    }
                }

                if let Some(ver) = map.get("BOOTSTRAP_VERSION").and_then(|v| v.as_str()) {
                    if !ver.is_empty() {
                        bootstrap_version = ver.to_string();
                    }
                }

                if let Some(path) = map.get("MEMENTO_SQLITE_PATH").and_then(|v| v.as_str()) {
                    env_vars.push(("MEMENTO_SQLITE_PATH".to_string(), path.to_string()));
                }

                if let Some(profile) = map.get("MEMENTO_TOOL_PROFILE").and_then(|v| v.as_str()) {
                    env_vars.push(("MEMENTO_TOOL_PROFILE".to_string(), profile.to_string()));
                }
            }
        }

        // --- Resolve Python executable ---
        // If the user provided an explicit command, honour it.
        // Otherwise pick the best default for the current OS.
        let python_bin = match python_command {
            Some(cmd) => cmd,

            None => {
                let candidates = Self::default_python_candidates(os);
                // We cannot call `which()` here (no Worktree handle), so we
                // return the first/best candidate and let Zed (and the OS)
                // resolve it via the process PATH at spawn time.
                candidates
                    .first()
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| "python".to_string())
            }
        };

        // --- Ensure bootstrap script is present ---
        let script_name = self.ensure_bootstrap_script(&bootstrap_version)?;

        Ok(Command {
            command: python_bin,
            args: vec!["-u".to_string(), script_name],
            env: env_vars,
        })
    }

    fn context_server_configuration(
        &mut self,
        _context_server_id: &ContextServerId,
        _project: &Project,
    ) -> Result<Option<ContextServerConfiguration>> {
        let settings_schema = zed_extension_api::serde_json::json!({
            "type": "object",
            "properties": {
                "MEMENTO_SQLITE_PATH": {
                    "type": "string",
                    "description": "Path to the Memento SQLite database file.",
                    "default": "~/.mcp-memento/context.db"
                },
                "MEMENTO_TOOL_PROFILE": {
                    "type": "string",
                    "description": "Tool profile to load (core, extended, advanced).",
                    "enum": ["core", "extended", "advanced"],
                    "default": "core"
                },
                "PYTHON_COMMAND": {
                    "type": "string",
                    "description": "Python executable to use. Set to 'auto' (or leave empty) for OS-based defaults, or specify an absolute path (e.g. C:\\Python312\\python.exe).",
                    "default": "auto"
                },
                "BOOTSTRAP_VERSION": {
                    "type": "string",
                    "description": "Version of the mcp-memento bootstrap script to download.",
                    "default": "0.1.0"
                }
            }
        });

        let default_settings = concat!(
            "{\n",
            "  \"MEMENTO_SQLITE_PATH\": \"~/.mcp-memento/context.db\",\n",
            "  \"MEMENTO_TOOL_PROFILE\": \"core\",\n",
            "  \"PYTHON_COMMAND\": \"auto\",\n",
            "  \"BOOTSTRAP_VERSION\": \"0.2.0\"\n",
            "}"
        );

        Ok(Some(ContextServerConfiguration {
            installation_instructions: concat!(
                "Memento requires Python 3.8+ installed on your system.\n\n",
                "On first use the extension downloads a small bootstrap script from GitHub\n",
                "Releases and installs mcp-memento via pip automatically.\n\n",
                "If Python is not found automatically, set PYTHON_COMMAND to the full\n",
                "path of your Python executable\n",
                "(e.g. \"C:\\\\Users\\\\you\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\python.exe\")."
            )
            .to_string(),
            settings_schema: settings_schema.to_string(),
            default_settings: default_settings.to_string(),
        }))
    }
}

zed::register_extension!(MementoExtension);
