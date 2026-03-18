use zed_extension_api::settings::ContextServerSettings;
use zed_extension_api::ContextServerConfiguration;
use zed_extension_api::{
    self as zed, Command, ContextServerId, DownloadedFileType, Os, Project, Result,
};

/// Version of the native stub binary to download from GitHub Releases.
const STUB_VERSION: &str = "0.1.0";

/// GitHub Releases base URL for the stub binary.
/// Tag convention: stub-v{STUB_VERSION}
const STUB_BASE_URL: &str = "https://github.com/annibale-x/mcp-memento/releases/download";

struct MementoExtension {
    cached_stub: Option<String>,
}

impl MementoExtension {
    /// Returns the platform-specific asset name for the stub binary.
    fn stub_asset_name(os: Os, arch: zed_extension_api::Architecture) -> &'static str {
        match (os, arch) {
            (Os::Windows, _) => "memento-stub-x86_64-pc-windows-msvc.exe",
            (Os::Mac, zed_extension_api::Architecture::Aarch64) => {
                "memento-stub-aarch64-apple-darwin"
            }
            (Os::Mac, _) => "memento-stub-x86_64-apple-darwin",
            (Os::Linux, zed_extension_api::Architecture::Aarch64) => {
                "memento-stub-aarch64-unknown-linux-gnu"
            }
            (Os::Linux, _) => "memento-stub-x86_64-unknown-linux-gnu",
        }
    }

    /// Returns the local filename for the versioned stub binary.
    /// Embedding the version ensures a fresh download whenever STUB_VERSION changes.
    fn stub_local_name(os: Os, arch: zed_extension_api::Architecture, version: &str) -> String {
        let asset = Self::stub_asset_name(os, arch);

        // Strip the extension suffix so we can insert the version cleanly,
        // then re-attach it.
        if let Some(stem) = asset.strip_suffix(".exe") {
            format!("{}-v{}.exe", stem, version)
        } else {
            format!("{}-v{}", asset, version)
        }
    }

    /// Downloads the stub binary into the extension working directory if not
    /// already present, marks it executable on Unix, and returns its absolute path.
    fn ensure_stub(
        &mut self,
        os: Os,
        arch: zed_extension_api::Architecture,
        version: &str,
    ) -> Result<String> {
        if let Some(ref cached) = self.cached_stub {
            return Ok(cached.clone());
        }

        let local_name = Self::stub_local_name(os, arch, version);
        let asset_name = Self::stub_asset_name(os, arch);

        // Skip the network call if the file is already on disk.
        let already_exists = std::fs::metadata(&local_name).is_ok();

        if !already_exists {
            let url = format!("{}/stub-v{}/{}", STUB_BASE_URL, version, asset_name);

            zed::download_file(&url, &local_name, DownloadedFileType::Uncompressed)
                .map_err(|e| format!("Failed to download memento stub: {e}"))?;
        }

        // On Unix the file must be executable.
        zed::make_file_executable(&local_name)
            .map_err(|e| format!("Failed to make stub executable: {e}"))?;

        // Build an absolute path using the WASM working directory ($PWD).
        // Passing an absolute path avoids problems when Zed's ShellBuilder
        // changes the CWD before spawning the process.
        let abs_path = std::env::current_dir()
            .map(|cwd| cwd.join(&local_name).to_string_lossy().into_owned())
            .unwrap_or(local_name.clone());

        self.cached_stub = Some(abs_path.clone());

        Ok(abs_path)
    }
}

impl zed::Extension for MementoExtension {
    fn new() -> Self {
        Self { cached_stub: None }
    }

    fn context_server_command(
        &mut self,
        context_server_id: &ContextServerId,
        project: &Project,
    ) -> Result<Command> {
        let (os, arch) = zed::current_platform();

        // --- Read settings ---
        let mut stub_version = STUB_VERSION.to_string();
        let mut env_vars = vec![("PYTHONUNBUFFERED".to_string(), "1".to_string())];

        if let Ok(settings) =
            ContextServerSettings::for_project(context_server_id.as_ref(), project)
        {
            if let Some(zed_extension_api::serde_json::Value::Object(map)) = settings.settings {
                if let Some(ver) = map.get("STUB_VERSION").and_then(|v| v.as_str()) {
                    if !ver.is_empty() {
                        stub_version = ver.to_string();
                    }
                }

                if let Some(cmd) = map.get("PYTHON_COMMAND").and_then(|v| v.as_str()) {
                    if !cmd.is_empty() && cmd != "auto" {
                        env_vars.push(("PYTHON_COMMAND".to_string(), cmd.to_string()));
                    }
                }

                if let Some(path) = map.get("MEMENTO_DB_PATH").and_then(|v| v.as_str()) {
                    env_vars.push(("MEMENTO_DB_PATH".to_string(), path.to_string()));
                }

                if let Some(profile) = map.get("MEMENTO_PROFILE").and_then(|v| v.as_str()) {
                    env_vars.push(("MEMENTO_PROFILE".to_string(), profile.to_string()));
                }
            }
        }

        // --- Ensure stub binary is present ---
        let stub_path = self.ensure_stub(os, arch, &stub_version)?;

        Ok(Command {
            command: stub_path,
            args: vec![],
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
                "MEMENTO_DB_PATH": {
                    "type": "string",
                    "description": "Path to the Memento SQLite database file.",
                    "default": "~/.mcp-memento/context.db"
                },
                "MEMENTO_PROFILE": {
                    "type": "string",
                    "description": "Tool profile to load (core, extended, advanced).",
                    "enum": ["core", "extended", "advanced"],
                    "default": "core"
                },
                "PYTHON_COMMAND": {
                    "type": "string",
                    "description": "Python executable override. Leave empty for automatic discovery, or set to an absolute path (e.g. C:\\Python312\\python.exe).",
                    "default": "auto"
                },
                "STUB_VERSION": {
                    "type": "string",
                    "description": "Version of the memento-stub binary to download.",
                    "default": "0.1.0"
                }
            }
        });

        let default_settings = concat!(
            "{\n",
            "  \"MEMENTO_DB_PATH\": \"~/.mcp-memento/context.db\",\n",
            "  \"MEMENTO_PROFILE\": \"core\",\n",
            "  \"PYTHON_COMMAND\": \"auto\",\n",
            "  \"STUB_VERSION\": \"0.1.0\"\n",
            "}"
        );

        Ok(Some(ContextServerConfiguration {
            installation_instructions: concat!(
                "Memento requires Python 3.8+ installed on your system.\n\n",
                "The extension downloads a small native launcher (memento-stub) from\n",
                "GitHub Releases. The launcher discovers Python automatically and starts\n",
                "the mcp-memento server.\n\n",
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
