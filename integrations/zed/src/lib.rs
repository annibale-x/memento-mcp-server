use zed_extension_api::ContextServerConfiguration;
use zed_extension_api::settings::ContextServerSettings;
use zed_extension_api::{
    self as zed, Command, ContextServerId, DownloadedFileType, Os, Project, Result,
};

// ---------------------------------------------------------------------------
// The STUB_EXT_RELEASE constant is the GitHub release tag from which the
// stub binary is downloaded as a fallback (steps 2-3 of bundle-first).
//
// It tracks the mcp-memento Python package version: every Python release
// publishes the stub binaries as assets on the same release tag (vX.Y.Z).
//
// Changing this value forces all clients that lack a bundled binary to
// re-download the stub on the next launch.
// ---------------------------------------------------------------------------

/// GitHub release tag for the current stub binaries (matches Python version tag).
const STUB_EXT_RELEASE: &str = "v0.2.16";

/// Distribution channel: "prod" downloads from the vX.Y.Z GitHub Release;
/// "dev" downloads from the rolling pre-release tag "dev-latest".
/// Set automatically by scripts/deploy.py during a version bump.
const STUB_CHANNEL: &str = "prod";

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
        // Step 1: bundled binary in the Zed extension work directory.
        //
        // Zed uses  <data>/extensions/work/<ext-id>/  as the WASM sandbox CWD.
        // It does NOT copy repo source files there.  The binary is placed here
        // by running:  python scripts/deploy.py dev-stub
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
            // Not cached — download from the appropriate GitHub release.
            // "prod"  → versioned release  vX.Y.Z  (stable, official)
            // "dev"   → rolling pre-release dev-latest (updated on every dev bump)
            let release_tag = match STUB_CHANNEL {
                "prod" => STUB_EXT_RELEASE.to_string(),
                _ => "dev-latest".to_string(),
            };

            let url = format!(
                "https://github.com/{}/releases/download/{}/{}",
                REPO, release_tag, asset_name,
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
                    if !cmd.is_empty() && cmd != "default" {
                        env_vars.push(("PYTHON_COMMAND".to_string(), cmd.to_string()));
                    }
                }

                if let Some(path) = map.get("MEMENTO_DB_PATH").and_then(|v| v.as_str()) {
                    if !path.is_empty() && path != "default" {
                        env_vars.push(("MEMENTO_DB_PATH".to_string(), path.to_string()));
                    }
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
        let (os, _arch) = zed::current_platform();

        let db_path_default_hint = match os {
            Os::Windows => "%USERPROFILE%\\.mcp-memento\\context.db",
            _ => "~/.mcp-memento/context.db",
        };

        let settings_schema = zed_extension_api::serde_json::json!({
            "type": "object",
            "properties": {
                "MEMENTO_DB_PATH": {
                    "type": "string",
                    "description": format!(
                        "Path to the Memento SQLite database file. \
                         Use 'default' to let the server choose the OS default ({}).",
                        db_path_default_hint
                    ),
                    "default": "default"
                },
                "MEMENTO_PROFILE": {
                    "type": "string",
                    "description": "Tool profile: 'core' (basic memory ops), 'extended' (+ stats and decay), 'advanced' (+ graph analytics).",
                    "enum": ["core", "extended", "advanced"],
                    "default": "core"
                },
                "PYTHON_COMMAND": {
                    "type": "string",
                    "description": "Python executable. Use 'default' for automatic discovery, or set an absolute path (e.g. C:/Users/you/AppData/Local/Programs/Python/Python312/python.exe).",
                    "default": "default"
                }
            }
        });

        let default_settings = concat!(
            "{\n",
            "  \"MEMENTO_DB_PATH\": \"default\",\n",
            "  \"MEMENTO_PROFILE\": \"core\",\n",
            "  \"PYTHON_COMMAND\": \"default\"\n",
            "}"
        );

        let installation_instructions = format!(
            "Memento requires Python 3.8+ on your system.\n\n\
             A small native launcher (memento-stub) discovers Python, installs\n\
             mcp-memento if needed, and starts the MCP server automatically.\n\n\
             Settings\n\
             --------\n\
             MEMENTO_DB_PATH  Path to the SQLite database.\n\
             \t'default' uses the OS default: {}\n\
             \tSet a custom absolute path to override.\n\n\
             MEMENTO_PROFILE  Tool set exposed to the AI agent.\n\
             \tcore     — basic memory operations (default)\n\
             \textended — + statistics and confidence decay\n\
             \tadvanced — + graph analytics\n\n\
             PYTHON_COMMAND   Python executable to use.\n\
             \t'default' tries py / python3 / python and common install paths.\n\
             \tSet an absolute path if your Python is not on the system PATH.",
            db_path_default_hint
        );

        Ok(Some(ContextServerConfiguration {
            installation_instructions,
            settings_schema: settings_schema.to_string(),
            default_settings: default_settings.to_string(),
        }))
    }
}

zed::register_extension!(MementoExtension);
