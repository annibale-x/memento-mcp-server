use std::io::Write;
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
const STUB_EXT_RELEASE: &str = "v0.2.25";

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

/// Returns true if debug logging is enabled.
///
/// Logging is OFF by default. To enable, create the marker file:
///   touch ~/.local/share/zed/extensions/work/mcp-memento/debug.enable
///   (Linux/macOS)
///   New-Item "$env:LOCALAPPDATA\Zed\extensions\work\mcp-memento\debug.enable"
///   (Windows PowerShell)
fn debug_enabled() -> bool {
    std::fs::metadata("debug.enable").is_ok()
}

/// Append a timestamped log line to the platform temp directory.
/// On Linux/macOS: $TMPDIR or /tmp → memento-zed.log
/// On Windows:     %TEMP%          → memento-zed.log
///
/// No-op unless debug.enable marker file exists in the extension work directory.
fn log(msg: &str) {
    if !debug_enabled() {
        return;
    }

    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let path = std::env::temp_dir().join("memento-zed.log");

    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
    {
        let _ = writeln!(f, "[{ts}] [Memento] {msg}");
    }
}

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
            log(&format!("Using cached stub: {}", cached));
            return Ok(cached.clone());
        }

        let asset_name = Self::stub_asset_name(os, arch);
        log(&format!("Looking for stub asset: {}", asset_name));

        // ------------------------------------------------------------------
        // Step 1: bundled binary in the Zed extension work directory.
        //
        // Zed uses  <data>/extensions/work/<ext-id>/  as the WASM sandbox CWD.
        // It does NOT copy repo source files there.  The binary is placed here
        // by running:  python scripts/deploy.py build-zed-stub
        // ------------------------------------------------------------------
        let bundled_path = format!("{}/{}", BUNDLED_BIN_DIR, asset_name);
        log(&format!("Step 1: checking bundled path: {}", bundled_path));

        match std::fs::metadata(&bundled_path) {
            Ok(meta) => {
                log(&format!(
                    "Found bundled stub at: {} (size={} bytes)",
                    bundled_path,
                    meta.len()
                ));
                zed::make_file_executable(&bundled_path)
                    .map_err(|e| format!("Failed to make bundled stub executable: {e}"))?;

                let abs = self.to_abs_path(&bundled_path);
                log(&format!("Bundled stub absolute path: {}", abs));
                self.cached_stub = Some(abs.clone());
                return Ok(abs);
            }
            Err(e) => {
                log(&format!(
                    "Bundled stub NOT found at '{}': {}",
                    bundled_path, e
                ));
            }
        }

        // ------------------------------------------------------------------
        // Step 2 + 3: cached download or fresh download.
        // ------------------------------------------------------------------
        let download_name = Self::stub_download_name(os, arch);
        log(&format!(
            "Step 2/3: checking for cached download: {}",
            download_name
        ));

        match std::fs::metadata(&download_name) {
            Ok(meta) => {
                log(&format!(
                    "Found cached stub: {} (size={} bytes)",
                    download_name,
                    meta.len()
                ));
            }
            Err(_) => {
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

                log(&format!("Downloading stub from: {}", url));

                match zed::download_file(&url, &download_name, DownloadedFileType::Uncompressed) {
                    Ok(_) => {
                        log(&format!("Download completed: {}", download_name));
                    }
                    Err(e) => {
                        let msg = format!("Failed to download memento stub from {url}: {e}");
                        log(&format!("ERROR: {}", msg));
                        return Err(msg);
                    }
                }
            }
        }

        match zed::make_file_executable(&download_name) {
            Ok(_) => log(&format!("Made executable: {}", download_name)),
            Err(e) => {
                let msg = format!("Failed to make downloaded stub executable: {e}");
                log(&format!("ERROR: {}", msg));
                return Err(msg);
            }
        }

        let abs = self.to_abs_path(&download_name);
        log(&format!("Stub absolute path: {}", abs));
        self.cached_stub = Some(abs.clone());
        Ok(abs)
    }

    /// Builds an absolute path from a relative one using the WASM working
    /// directory.  Falls back to the relative path if `current_dir` fails.
    fn to_abs_path(&self, relative: &str) -> String {
        match std::env::current_dir() {
            Ok(cwd) => {
                let abs = cwd.join(relative).to_string_lossy().into_owned();
                log(&format!("current_dir={:?} -> abs={}", cwd, abs));
                abs
            }
            Err(e) => {
                log(&format!(
                    "WARNING: current_dir() failed: {} — using relative path: {}",
                    e, relative
                ));
                relative.to_owned()
            }
        }
    }
}

impl zed::Extension for MementoExtension {
    fn new() -> Self {
        log("Extension initialized");
        Self { cached_stub: None }
    }

    fn context_server_command(
        &mut self,
        context_server_id: &ContextServerId,
        project: &Project,
    ) -> Result<Command> {
        log(&format!(
            "context_server_command called for: {}",
            context_server_id.as_ref()
        ));

        let (os, arch) = zed::current_platform();
        log(&format!("Platform: os={:?}, arch={:?}", os, arch));

        // --- Read user settings ---
        let mut env_vars = vec![("PYTHONUNBUFFERED".to_string(), "1".to_string())];

        match ContextServerSettings::for_project(context_server_id.as_ref(), project) {
            Ok(settings) => {
                log("Settings loaded successfully");
                if let Some(zed_extension_api::serde_json::Value::Object(map)) = settings.settings {
                    log(&format!(
                        "Settings map keys: {:?}",
                        map.keys().collect::<Vec<_>>()
                    ));

                    if let Some(cmd) = map.get("PYTHON_COMMAND").and_then(|v| v.as_str()) {
                        if !cmd.is_empty() && cmd != "default" {
                            log(&format!("Using custom PYTHON_COMMAND: {}", cmd));
                            env_vars.push(("PYTHON_COMMAND".to_string(), cmd.to_string()));
                        } else {
                            log("PYTHON_COMMAND is 'default' — stub will auto-discover Python");
                        }
                    }

                    if let Some(path) = map.get("MEMENTO_DB_PATH").and_then(|v| v.as_str()) {
                        if !path.is_empty() && path != "default" {
                            log(&format!("Using custom MEMENTO_DB_PATH: {}", path));
                            env_vars.push(("MEMENTO_DB_PATH".to_string(), path.to_string()));
                        } else {
                            log("MEMENTO_DB_PATH is 'default'");
                        }
                    }

                    if let Some(profile) = map.get("MEMENTO_PROFILE").and_then(|v| v.as_str()) {
                        log(&format!("Using MEMENTO_PROFILE: {}", profile));
                        env_vars.push(("MEMENTO_PROFILE".to_string(), profile.to_string()));
                    }
                } else {
                    log("WARNING: settings.settings is None or not an Object");
                }
            }
            Err(e) => {
                log(&format!(
                    "WARNING: Could not load settings ({}), using defaults",
                    e
                ));
            }
        }

        // --- Pass extension work directory so stub can place venv there ---
        match std::env::current_dir() {
            Ok(cwd) => {
                let work_dir = cwd.to_string_lossy().into_owned();
                log(&format!("Passing MEMENTO_WORK_DIR: {}", work_dir));
                env_vars.push(("MEMENTO_WORK_DIR".to_string(), work_dir));
            }
            Err(e) => {
                log(&format!(
                    "WARNING: current_dir() failed ({}), stub will use fallback venv location",
                    e
                ));
            }
        }

        // --- Resolve stub binary (bundle-first) ---
        log("Resolving stub binary...");
        let stub_path = self.ensure_stub(os, arch)?;
        log(&format!(
            "Final command: {} (env={:?})",
            stub_path, env_vars
        ));

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
            "  \"MEMENTO_PROFILE\": \"core\",\n",
            "  \"MEMENTO_DB_PATH\": \"default\",\n",
            "  \"PYTHON_COMMAND\" : \"default\"\n",
            "}"
        );

        let installation_instructions = format!(
            r#"
> **First install / update note:** On the very first install (and sometimes after an
> update), Memento may initially report only **1 tool available** — this is expected.
> The launcher is downloading and installing the Python package in the background.
> Once installation completes (usually a few seconds), Zed will automatically refresh
> and expose all tools for the selected profile.

---

**Memento** requires **Python 3.10+** on your system.
A small native launcher discovers Python, installs **mcp-memento** if needed,
and starts the MCP server automatically.

---

__**Configuration parameters:**__

- **MEMENTO_DB_PATH**: Path to the SQLite database.
  - **default**: **`{}`**

  (_Set a custom absolute path to override._)

- **MEMENTO_PROFILE**: Tool set exposed to the AI agent.
  - **core** : basic memory operations (default)
  - **extended** : **core** + statistics and confidence decay
  - **advanced** : **extended** + graph analytics

- **PYTHON_COMMAND**: Python executable to use.
  - **default** : tries **py**, **python3**, **python** and common install paths.

  (_Set an absolute path if your Python is not on the system **PATH**._)
	        "#,
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
