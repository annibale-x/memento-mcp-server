use zed_extension_api::ContextServerConfiguration;
use zed_extension_api::settings::ContextServerSettings;
use zed_extension_api::{
    self as zed, Command, ContextServerId, DownloadedFileType, Os, Project, Result,
};

// ---------------------------------------------------------------------------
// Release naming convention
//
// GitHub releases for this repo follow the scheme:
//
//   v{python_version}-ext.{N}
//
// where:
//   - python_version  is the mcp-memento Python package version (e.g. 0.2.6)
//   - N               is a monotonically increasing extension release counter
//
// Example: "v0.2.6-ext.1"
//
// This keeps Python package releases and extension releases clearly separated
// while tying each extension release to the Python version it ships with.
//
// The STUB_EXT_RELEASE constant below encodes the full tag.  Changing it
// forces all clients to re-download the stub binary on the next launch.
// ---------------------------------------------------------------------------

/// Full GitHub release tag for the current stub binaries.
/// Format: "v{python_version}-ext.{N}"
const STUB_EXT_RELEASE: &str = "v0.2.6-ext.1";

/// GitHub repository (owner/name) hosting the releases.
const REPO: &str = "annibale-x/mcp-memento";

/// Subdirectory inside the extension working directory where bundled stub
/// binaries are stored (committed to the repository under integrations/zed/).
const BUNDLED_BIN_DIR: &str = "stub/bin";

// ---------------------------------------------------------------------------

struct MementoExtension {
    cached_stub: Option<String>,
}

impl MementoExtension {
    /// Platform-specific asset filename for the stub binary.
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

    /// Local filename used when caching a downloaded stub binary.
    /// Embeds the release tag so a tag change triggers a fresh download.
    fn stub_download_name(os: Os, arch: zed_extension_api::Architecture) -> String {
        let asset = Self::stub_asset_name(os, arch);
        // Sanitise the release tag for use in a filename (replace '.' and '+').
        let safe_tag = STUB_EXT_RELEASE.replace(['.', '+'], "-");

        if let Some(stem) = asset.strip_suffix(".exe") {
            format!("{}-{}.exe", stem, safe_tag)
        } else {
            format!("{}-{}", asset, safe_tag)
        }
    }

    /// Resolves the stub binary path using a "bundle-first" strategy:
    ///
    /// 1. Look for the binary pre-committed in `stub/bin/` (present in both
    ///    dev extensions and marketplace installs where Zed clones the full
    ///    submodule including static assets).
    /// 2. Look for a previously downloaded binary in the working directory
    ///    (cached download from a previous run).
    /// 3. Download from the GitHub release and cache it locally.
    ///
    /// Returns the **absolute** path to the binary so that Zed's ShellBuilder
    /// does not lose track of the file when it adjusts the working directory.
    fn ensure_stub(&mut self, os: Os, arch: zed_extension_api::Architecture) -> Result<String> {
        if let Some(ref cached) = self.cached_stub {
            return Ok(cached.clone());
        }

        let asset_name = Self::stub_asset_name(os, arch);

        // ------------------------------------------------------------------
        // Step 1: bundled binary committed to the repository.
        // ------------------------------------------------------------------
        let bundled_path = format!("{}/{}", BUNDLED_BIN_DIR, asset_name);

        if std::fs::metadata(&bundled_path).is_ok() {
            zed::make_file_executable(&bundled_path)
                .map_err(|e| format!("Failed to make bundled stub executable: {e}"))?;

            let abs = self.to_abs_path(&bundled_path);
            self.cached_stub = Some(abs.clone());
            return Ok(abs);
        }

        // ------------------------------------------------------------------
        // Step 2 + 3: cached download or fresh download.
        // ------------------------------------------------------------------
        let download_name = Self::stub_download_name(os, arch);

        if std::fs::metadata(&download_name).is_err() {
            // Not cached — download from the GitHub release.
            let url = format!(
                "https://github.com/{}/releases/download/{}/{}",
                REPO, STUB_EXT_RELEASE, asset_name,
            );

            zed::download_file(&url, &download_name, DownloadedFileType::Uncompressed)
                .map_err(|e| format!("Failed to download memento stub from {url}: {e}"))?;
        }

        zed::make_file_executable(&download_name)
            .map_err(|e| format!("Failed to make downloaded stub executable: {e}"))?;

        let abs = self.to_abs_path(&download_name);
        self.cached_stub = Some(abs.clone());
        Ok(abs)
    }

    /// Builds an absolute path from a relative one using the WASM working
    /// directory.  Falls back to the relative path if `current_dir` fails.
    fn to_abs_path(&self, relative: &str) -> String {
        std::env::current_dir()
            .map(|cwd| cwd.join(relative).to_string_lossy().into_owned())
            .unwrap_or_else(|_| relative.to_owned())
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

        // --- Read user settings ---
        let mut env_vars = vec![("PYTHONUNBUFFERED".to_string(), "1".to_string())];

        if let Ok(settings) =
            ContextServerSettings::for_project(context_server_id.as_ref(), project)
        {
            if let Some(zed_extension_api::serde_json::Value::Object(map)) = settings.settings {
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

        // --- Resolve stub binary (bundle-first) ---
        let stub_path = self.ensure_stub(os, arch)?;

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
                }
            }
        });

        let default_settings = concat!(
            "{\n",
            "  \"MEMENTO_DB_PATH\": \"~/.mcp-memento/context.db\",\n",
            "  \"MEMENTO_PROFILE\": \"core\",\n",
            "  \"PYTHON_COMMAND\": \"auto\"\n",
            "}"
        );

        Ok(Some(ContextServerConfiguration {
            installation_instructions: concat!(
                "Memento requires Python 3.8+ installed on your system.\n\n",
                "The extension includes a small native launcher (memento-stub) that\n",
                "discovers Python automatically and starts the mcp-memento server.\n",
                "If the bundled launcher is not available for your platform it will\n",
                "be downloaded automatically from the GitHub release.\n\n",
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
