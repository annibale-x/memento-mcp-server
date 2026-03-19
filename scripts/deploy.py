#!/usr/bin/env python3
"""
deploy.py — MCP Memento unified release & deploy script.

Workflow
--------
  sviluppo → bump → test & fix → bump → promote → publish

Usage:
    python scripts/deploy.py bump X.Y.Z
    python scripts/deploy.py promote [--yes]
    python scripts/deploy.py publish [-t]
    python scripts/deploy.py build
    python scripts/deploy.py build-zed-stub
    python scripts/deploy.py ext-binaries [--version X.Y.Z]
    python scripts/deploy.py upload-stubs [--version X.Y.Z]
    python scripts/deploy.py status

Commands
--------
  bump X.Y.Z        Dev bump: update versions in all manifests, build stub for
                    current platform, upload to dev-latest pre-release on GitHub.
                    Tag is local only — CI is NOT triggered. Always non-interactive.
                    Use --dry-run to preview without making changes.

  promote           Promote the current dev version to an official release:
                    verify CHANGELOG, merge dev→main, push tag vX.Y.Z (triggers
                    CI stub cross-compile), upload stub binaries to GitHub Release.
                    Version is read from pyproject.toml automatically.

  publish           Upload dist/* to PyPI.
                    Use -t / --test to upload to TestPyPI instead.

  build             Build sdist + wheel (no version bump).

  build-zed-stub    Build the native stub binary for the current platform, copy
                    it into integrations/zed/stub/bin/ and into the Zed extension
                    work directory, then commit and push.
                    Use during active Zed extension development after editing
                    stub/src/main.rs.

  ext-binaries      Download CI-built stub binaries from the GitHub Release
                    vX.Y.Z into stub/bin/ and commit them to the repo.
                    Run after the CI workflow has completed successfully.

  upload-stubs      Create the GitHub Release vX.Y.Z (if it does not exist) and
                    upload the local stub binaries from stub/bin/ as release assets.
                    Use as a manual fallback if the CI upload step failed.

  status            Print current versions across all manifests.

Options
--------
  --dry-run         Print all actions without executing them.
  --skip-tests      Skip pytest before release.
  --version X.Y.Z   Override version (for ext-binaries and upload-stubs).
  --yes, -y         Auto-confirm prompts (promote only).
  --test, -t        Upload to TestPyPI instead of PyPI (publish only).

Examples
--------
  # Bump to 0.3.0 (dev only, non-interactive)
  python scripts/deploy.py bump 0.3.0

  # Preview bump without executing
  python scripts/deploy.py bump 0.3.0 --dry-run

  # Promote current dev version to official release
  python scripts/deploy.py promote --yes

  # Build wheel only
  python scripts/deploy.py build

  # Publish to PyPI
  python scripts/deploy.py publish

  # Publish to TestPyPI
  python scripts/deploy.py publish --test

  # Rebuild stub for current platform and update stub/bin/
  python scripts/deploy.py build-zed-stub

  # Download CI-built binaries after CI completes and commit to repo
  python scripts/deploy.py ext-binaries --version 0.3.0

  # Manually create release and upload local binaries (CI upload fallback)
  python scripts/deploy.py upload-stubs --version 0.3.0

  # Show current version state
  python scripts/deploy.py status
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows console encoding fix
# On Windows, the default console codepage (CP1252) cannot encode Unicode
# characters used in this script's output (e.g. U+2501 BOX DRAWINGS HEAVY).
# Reconfigure stdout/stderr to UTF-8 so the script works without needing
# the PYTHONIOENCODING=utf-8 environment variable.
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

PYPROJECT = ROOT / "pyproject.toml"
INIT_PY = ROOT / "src" / "memento" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
DIST_DIR = ROOT / "dist"

ZED_DIR = ROOT / "integrations" / "zed"
ZED_CARGO = ZED_DIR / "Cargo.toml"
ZED_EXTENSION = ZED_DIR / "extension.toml"
ZED_LIB_RS = ZED_DIR / "src" / "lib.rs"
ZED_STUB_CARGO = ZED_DIR / "stub" / "Cargo.toml"
ZED_STUB_MAIN_RS = ZED_DIR / "stub" / "src" / "main.rs"
ZED_STUB_BIN = ZED_DIR / "stub" / "bin"

GITHUB_REPO = "annibale-x/mcp-memento"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}"

# uv is the project's package manager. Use "uv run" for tests and builds so
# that the correct virtual environment (memento in editable mode + all dev
# deps) is always active — regardless of which Python or shell invoked this
# script.  "uv run --extra dev" resolves [project.optional-dependencies] dev.
UV = "uv"

# Fallback Python for operations that don't need the project venv
# (cargo invocations, git helpers, etc.).
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def info(msg: str) -> None:
    print(f"{Color.CYAN}ℹ {msg}{Color.RESET}")


def ok(msg: str) -> None:
    print(f"{Color.GREEN}✓ {msg}{Color.RESET}")


def warn(msg: str) -> None:
    print(f"{Color.YELLOW}⚠ {msg}{Color.RESET}")


def err(msg: str) -> None:
    print(f"{Color.RED}✗ {msg}{Color.RESET}", file=sys.stderr)


def step(msg: str) -> None:
    print(f"\n{Color.BOLD}{Color.CYAN}━━ {msg}{Color.RESET}")


def die(msg: str) -> None:
    err(msg)
    sys.exit(1)


def confirm(prompt: str, yes: bool) -> bool:
    if yes:
        print(f"{Color.GRAY}  (auto-confirmed) {prompt}{Color.RESET}")
        return True
    answer = input(f"{Color.YELLOW}? {prompt} [y/N] {Color.RESET}").strip().lower()
    return answer in ("y", "yes")


def run(
    cmd: str | list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    dry: bool = False,
    check: bool = True,
) -> str:
    """Execute a shell command, optionally capturing output."""
    cwd = cwd or ROOT
    cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    print(f"{Color.GRAY}  $ {cmd_str}{Color.RESET}")

    if dry:
        return ""

    result = subprocess.run(
        cmd_str,
        shell=True,
        cwd=cwd,
        capture_output=capture,
        text=True,
    )

    if check and result.returncode != 0:
        if capture:
            err(result.stderr.strip())
        die(f"Command failed (exit {result.returncode}): {cmd_str}")

    return result.stdout.strip() if capture else ""


# ---------------------------------------------------------------------------
# Version readers
# ---------------------------------------------------------------------------


def read_pyproject_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        die("Cannot read version from pyproject.toml")
    return m.group(1)


def read_init_version() -> str:
    text = INIT_PY.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "?"


def read_zed_cargo_version() -> str:
    if not ZED_CARGO.exists():
        return "?"
    text = ZED_CARGO.read_text(encoding="utf-8")
    # Skip [workspace] block — grab version from [package] block
    m = re.search(
        r'\[package\].*?^version\s*=\s*"([^"]+)"', text, re.DOTALL | re.MULTILINE
    )
    return m.group(1) if m else "?"


def read_extension_version() -> str:
    if not ZED_EXTENSION.exists():
        return "?"
    text = ZED_EXTENSION.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "?"


def read_stub_ext_release() -> str:
    if not ZED_LIB_RS.exists():
        return "?"
    text = ZED_LIB_RS.read_text(encoding="utf-8")
    m = re.search(r'STUB_EXT_RELEASE:\s*&str\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "?"


# ---------------------------------------------------------------------------
# Version bumpers
# ---------------------------------------------------------------------------


def _replace_in_file(path: Path, pattern: str, replacement: str, dry: bool) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if n == 0:
        warn(f"Pattern not found in {path.relative_to(ROOT)}: {pattern!r}")
        return
    if not dry:
        path.write_text(new_text, encoding="utf-8")
    info(f"Updated {path.relative_to(ROOT)}")


def bump_pyproject(new_ver: str, dry: bool) -> None:
    _replace_in_file(
        PYPROJECT,
        r'^(version\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        dry,
    )


def bump_init(new_ver: str, dry: bool) -> None:
    _replace_in_file(
        INIT_PY,
        r'^(__version__\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        dry,
    )


def bump_zed_cargo(new_ver: str, dry: bool) -> None:
    # Only bump [package] version, not workspace resolver line
    text = ZED_CARGO.read_text(encoding="utf-8")
    pattern = r'(\[package\].*?^version\s*=\s*)"[^"]+"'

    if not re.search(pattern, text, flags=re.DOTALL | re.MULTILINE):
        warn(f"[package] version not found in {ZED_CARGO.relative_to(ROOT)}")
        return

    new_text = re.sub(
        pattern,
        rf'\g<1>"{new_ver}"',
        text,
        flags=re.DOTALL | re.MULTILINE,
    )

    if new_text == text:
        info(f"Already at {new_ver} in {ZED_CARGO.relative_to(ROOT)}")
        return

    if not dry:
        ZED_CARGO.write_text(new_text, encoding="utf-8")
    info(f"Updated {ZED_CARGO.relative_to(ROOT)}")


def bump_extension_toml(new_ver: str, dry: bool) -> None:
    _replace_in_file(
        ZED_EXTENSION,
        r'^(version\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        dry,
    )


def bump_lib_rs_stub_release(new_ver: str, dev_only: bool, dry: bool) -> None:
    """Update STUB_EXT_RELEASE and STUB_CHANNEL in lib.rs; STUB_VERSION in main.rs."""

    tag = f"v{new_ver}"
    _replace_in_file(
        ZED_LIB_RS,
        r'(STUB_EXT_RELEASE:\s*&str\s*=\s*)"[^"]+"',
        rf'\g<1>"{tag}"',
        dry,
    )

    channel = "dev" if dev_only else "prod"
    _replace_in_file(
        ZED_LIB_RS,
        r'(STUB_CHANNEL:\s*&str\s*=\s*)"[^"]+"',
        rf'\g<1>"{channel}"',
        dry,
    )

    _replace_in_file(
        ZED_STUB_MAIN_RS,
        r'(STUB_VERSION:\s*&str\s*=\s*)"[^"]+"',
        rf'\g<1>"{tag}"',
        dry,
    )


def bump_readme_badge(new_ver: str, dry: bool) -> None:
    _replace_in_file(
        README,
        r"(badge/release-v)[^\-]+-",
        rf"\g<1>{new_ver}-",
        dry,
    )
    # Also update hardcoded release URL in badge link
    _replace_in_file(
        README,
        r"(releases/tag/v)[0-9]+\.[0-9]+\.[0-9]+",
        rf"\g<1>{new_ver}",
        dry,
    )


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------


def scaffold_changelog(new_ver: str, dry: bool) -> None:
    """Prepend a placeholder entry to CHANGELOG.md for the upcoming release.

    Called only on the FIRST --dev bump of a new version.  Skipped silently
    if an entry for this version already exists (re-run of --dev).
    The developer is expected to fill in the release notes before the prod bump.
    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = (
        f"* {today}: v{new_ver} - <TITLE> (Hannibal)\n"
        f"  * <release notes here>\n\n"
    )

    if dry:
        info(f"Would scaffold CHANGELOG.md entry for v{new_ver}")
        return

    text = CHANGELOG.read_text(encoding="utf-8")

    if f": v{new_ver} -" in text:
        info(f"CHANGELOG.md already has an entry for v{new_ver} — skipping scaffold.")
        return

    lines = text.split("\n", 1)
    new_text = lines[0] + "\n\n" + entry + (lines[1] if len(lines) > 1 else "")
    CHANGELOG.write_text(new_text, encoding="utf-8")
    ok(f"Scaffolded CHANGELOG.md entry for v{new_ver} — fill in the release notes before the prod bump!")


def check_changelog(new_ver: str, dry: bool) -> None:
    """Verify that a proper release entry for new_ver exists in CHANGELOG.md.

    Blocks the prod bump if:
    - no entry for this version exists (developer forgot to write release notes)
    - the entry still contains the placeholder text from scaffold_changelog
    """
    if dry:
        info(f"Would verify CHANGELOG.md entry for v{new_ver}")
        return

    text = CHANGELOG.read_text(encoding="utf-8")
    marker = f": v{new_ver} -"

    if marker not in text:
        die(
            f"No CHANGELOG.md entry found for v{new_ver}.\n"
            "  Add release notes before running the prod bump."
        )

    # Find the entry and check for placeholder text
    for line in text.splitlines():
        if marker in line:
            if "<TITLE>" in line or "<release notes here>" in line:
                die(
                    f"CHANGELOG.md entry for v{new_ver} still contains placeholder text.\n"
                    "  Edit CHANGELOG.md with real release notes before the prod bump."
                )
            break

    ok(f"CHANGELOG.md entry for v{new_ver} looks good.")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_package(dry: bool) -> None:
    step("Building sdist + wheel")

    # Clean previous dist artefacts for this version only
    if DIST_DIR.exists() and not dry:
        for f in DIST_DIR.iterdir():
            f.unlink()
        ok("Cleaned dist/")

    # Temporarily patch README for PyPI (absolute links)
    readme_backup = _patch_readme_for_pypi(dry)
    try:
        run(f"{UV} build --out-dir {DIST_DIR}", dry=dry)
    finally:
        if readme_backup:
            _restore_readme(readme_backup, dry)

    if not dry:
        files = sorted(f for f in DIST_DIR.glob("*") if f.suffix in (".whl", ".gz"))
        for f in files:
            ok(f"Built: {f.name}  ({f.stat().st_size / 1024:.0f} KB)")


def _patch_readme_for_pypi(dry: bool) -> Path | None:
    """Patch README.md for PyPI:
    - Replace all relative markdown links with absolute GitHub URLs.
    - Inject a compact changelog section above the Links footer.
    """
    backup = README.with_suffix(".md.bak")
    if dry:
        info("Would patch README.md for PyPI (absolute links + changelog section)")
        return None
    shutil.copy2(README, backup)
    text = README.read_text(encoding="utf-8")

    base = f"https://github.com/{GITHUB_REPO}/blob/main/"
    tree = f"https://github.com/{GITHUB_REPO}/tree/main/"
    changelog_url = f"https://github.com/{GITHUB_REPO}/blob/main/CHANGELOG.md"

    # --- Absolute link replacements (order matters: longest prefix first) ---
    for rel, abs_ in [
        ("](./docs/", f"]({base}docs/"),
        ("](docs/", f"]({base}docs/"),
        ("](./CONTRIBUTING.md)", f"]({base}CONTRIBUTING.md)"),
        ("](CONTRIBUTING.md)", f"]({base}CONTRIBUTING.md)"),
        ("](./LICENSE)", f"]({base}LICENSE)"),
        ("](LICENSE)", f"]({base}LICENSE)"),
        ("](./CHANGELOG.md)", f"]({base}CHANGELOG.md)"),
        ("](CHANGELOG.md)", f"]({base}CHANGELOG.md)"),
    ]:
        text = text.replace(rel, abs_)

    # tree-style links for bare directory references
    text = text.replace("](docs/)", f"]({tree}docs/)")

    # --- Inject compact changelog section just before the ## 📄 License section ---
    changelog_section = _build_changelog_snippet(changelog_url)
    license_anchor = "\n## 📄 License"
    if license_anchor in text and "## 📋 Recent Changes" not in text:
        text = text.replace(license_anchor, f"\n{changelog_section}{license_anchor}")

    README.write_text(text, encoding="utf-8")
    info("Patched README.md for PyPI (absolute links + changelog snippet)")
    return backup


def _build_changelog_snippet(changelog_url: str, max_entries: int = 4) -> str:
    """Read CHANGELOG.md and return a compact Markdown table for PyPI."""
    try:
        raw = CHANGELOG.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

    # Each entry starts with "* YYYY-MM-DD: vX.Y.Z - <title> (author)"
    entries = re.findall(
        r"^\* (\d{4}-\d{2}-\d{2}): (v[\d.]+) - (.+?) \(\w+\)",
        raw,
        flags=re.MULTILINE,
    )
    if not entries:
        return ""

    rows = []
    for date, ver, title in entries[:max_entries]:
        rows.append(f"| `{ver}` | {date} | {title} |")

    table = "\n".join(rows)
    return (
        f"## 📋 Recent Changes\n\n"
        f"| Version | Date | Highlights |\n"
        f"|---------|------|------------|\n"
        f"{table}\n\n"
        f"Full history: [{changelog_url}]({changelog_url})\n"
    )


def _restore_readme(backup: Path, dry: bool) -> None:
    if dry or not backup.exists():
        return
    shutil.copy2(backup, README)
    backup.unlink()
    info("Restored README.md")


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------


def git_current_branch(dry: bool = False) -> str:
    return run("git rev-parse --abbrev-ref HEAD", capture=True, dry=False)


def git_is_clean(dry: bool = False) -> bool:
    out = run("git status --porcelain", capture=True, dry=False)
    # Ignore untracked files (lines starting with "??") — only staged/modified
    # files should block a release. On Windows, git sometimes reports a phantom
    # "NUL" untracked entry that must not abort the bump.
    tracked_changes = [
        line for line in out.splitlines() if line and not line.startswith("??")
    ]
    return len(tracked_changes) == 0


def git_add_all(dry: bool) -> None:
    run("git add -A", dry=dry)


def git_commit(message: str, dry: bool) -> None:
    """Commit staged changes. A no-op (not an error) if nothing is staged."""
    if dry:
        run(f'git commit -m "{message}"', dry=True)
        return

    result = subprocess.run(
        f'git commit -m "{message}"',
        shell=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout.strip())
        return

    combined = (result.stdout + result.stderr).lower()

    if "nothing to commit" in combined or "nothing added to commit" in combined:
        info("Nothing new to commit — already up to date.")
        return

    # Real failure
    err(result.stderr.strip())
    die(f"Command failed (exit {result.returncode}): git commit -m \"{message}\"")


def git_push(branch: str, dry: bool) -> None:
    run(f"git push origin {branch}", dry=dry)


def git_tag(tag: str, dry: bool) -> None:
    run(f"git tag {tag}", dry=dry)


def git_tag_exists_local(tag: str) -> bool:
    """Return True if the tag already exists in the local repository."""
    result = run(
        f"git tag -l {tag}",
        capture=True,
        dry=False,
        check=False,
    )
    return result.strip() == tag


def git_tag_exists_remote(tag: str) -> bool:
    """Return True if the tag already exists on the remote repository."""
    result = run(
        f"git ls-remote --tags origin refs/tags/{tag}",
        capture=True,
        dry=False,
        check=False,
    )
    return bool(result.strip())


def git_retag(tag: str, dry: bool) -> None:
    """Delete the local tag and re-create it pointing to HEAD."""
    run(f"git tag -d {tag}", dry=dry)
    run(f"git tag {tag}", dry=dry)


def git_force_push_tag(tag: str, dry: bool) -> None:
    run(f"git push origin {tag} --force", dry=dry)


def git_push_tag(tag: str, dry: bool) -> None:
    run(f"git push origin {tag}", dry=dry)


def git_merge_to_main(dry: bool) -> None:
    step("Merging dev → main")
    run("git checkout main", dry=dry)
    run('git merge dev --no-ff -m "chore(release): merge dev into main"', dry=dry)
    run("git push origin main", dry=dry)
    run("git checkout dev", dry=dry)
    ok("Merged and pushed main, back on dev")


# ---------------------------------------------------------------------------
# PyPI publish
# ---------------------------------------------------------------------------


def publish(target: str, dry: bool) -> None:
    # If we are on dev and main is behind, merge first so the release
    # is always on main before hitting PyPI.
    branch = git_current_branch()

    if branch == "dev":
        # Check if main already contains the current dev HEAD.
        behind = run(
            "git rev-list --count main..dev",
            capture=True,
            dry=False,
            check=False,
        ).strip()

        if behind and behind != "0":
            git_merge_to_main(dry)
        else:
            info("main is already up-to-date with dev — skipping merge.")

        # Push the release tag if it exists locally but not on origin yet.
        # This happens when the bump was done with --dev (tag kept local).
        ver = read_pyproject_version()
        py_tag = f"v{ver}"

        if git_tag_exists_local(py_tag):
            remote_tag = run(
                f"git ls-remote --tags origin refs/tags/{py_tag}",
                capture=True,
                dry=False,
                check=False,
            ).strip()

            if not remote_tag:
                step(f"Pushing release tag {py_tag} to origin (triggers CI)")
                git_push_tag(py_tag, dry)
                ok(f"Tag {py_tag} pushed")
            else:
                info(f"Tag {py_tag} already on origin.")

    step(f"Publishing to {target.upper()}")

    if not DIST_DIR.exists() or not any(DIST_DIR.glob("*.whl")):
        die("No wheel in dist/ — run 'build' first.")

    if target == "testpypi":
        run("twine upload --repository testpypi dist/*", dry=dry)
    elif target == "pypi":
        run("twine upload --repository pypi dist/*", dry=dry)
    else:
        die(f"Unknown target: {target!r}. Use 'testpypi' or 'pypi'.")

    ok(f"Published to {target}")


# ---------------------------------------------------------------------------
# Zed stub release
# ---------------------------------------------------------------------------


def upload_stub_binaries_to_release(python_ver: str, dry: bool) -> None:
    """Create the GitHub Release vX.Y.Z (if needed) and upload local stub binaries.

    The CI workflow (zed-stub-release.yml) will cross-compile and upload the
    remaining targets once the tag is on the remote; here we create the release
    object first (so the CI has a target to upload to) and attach whatever local
    binaries exist in stub/bin/ as a safety-net / fast-path for Windows.
    """
    step(f"Uploading stub binaries to GitHub release v{python_ver}")
    tag = f"v{python_ver}"
    files = sorted(ZED_STUB_BIN.glob("memento-stub-*"))

    if not files:
        die(f"No stub binaries found in {ZED_STUB_BIN}. Build them first.")

    # Create the GitHub Release object so the CI has somewhere to attach assets.
    # --notes-start-tag picks up everything since the previous release for the
    # auto-generated notes.  Errors are ignored if the release already exists.
    run(
        f"gh release create {tag}"
        f" --repo {GITHUB_REPO}"
        f" --title \"v{python_ver}\""
        f" --generate-notes"
        f" --latest",
        dry=dry,
        check=False,
    )

    # Upload local binaries (at minimum the Windows stub built by deploy.py).
    for f in files:
        cmd = f"gh release upload {tag} {f} --repo {GITHUB_REPO} --clobber"
        run(cmd, dry=dry)
        ok(f"Uploaded: {f.name}")


def upload_stub_binaries_to_dev_prerelease(dry: bool) -> None:
    """Create (or update) the rolling pre-release 'dev-latest' and upload stubs.

    Only the locally built binaries in stub/bin/ are uploaded here.
    The CI workflow (zed-stub-dev.yml) cross-compiles the remaining targets
    and uploads them to the same pre-release tag.
    """
    step("Uploading stub binaries to GitHub pre-release 'dev-latest'")

    files = sorted(ZED_STUB_BIN.glob("memento-stub-*"))

    if not files:
        die(f"No stub binaries found in {ZED_STUB_BIN}. Run 'build-zed-stub' first.")

    # Delete existing release+tag so we can recreate cleanly.
    # Errors are ignored — the release may not exist yet.
    run(
        f"gh release delete dev-latest --repo {GITHUB_REPO} --yes",
        dry=dry,
        check=False,
    )
    run(
        "git push origin :refs/tags/dev-latest",
        dry=dry,
        check=False,
    )

    # Build the file list as a space-separated string of quoted paths.
    file_args = " ".join(f'"{f}"' for f in files)

    run(
        f"gh release create dev-latest"
        f" --repo {GITHUB_REPO}"
        f" --title \"Dev stub binaries (rolling)\""
        f" --notes \"Auto-updated on every dev bump. Not for production use.\""
        f" --prerelease"
        f" --latest=false"
        f" {file_args}",
        dry=dry,
    )

    ok("Pre-release 'dev-latest' created and stubs uploaded.")



def _zed_work_dir() -> "Path | None":
    """Return the Zed extension work directory for mcp-memento, or None if not found.

    Zed stores per-extension working files at:
      - Windows : %LOCALAPPDATA%/Zed/extensions/work/mcp-memento
      - macOS   : ~/Library/Application Support/Zed/extensions/work/mcp-memento
      - Linux   : ~/.local/share/zed/extensions/work/mcp-memento  (XDG)
    """
    import platform as _platform

    system = _platform.system().lower()

    if system == "windows":
        base = os.environ.get("LOCALAPPDATA")

        if base:
            return Path(base) / "Zed" / "extensions" / "work" / "mcp-memento"

    elif system == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Zed"
            / "extensions"
            / "work"
            / "mcp-memento"
        )

    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "zed" / "extensions" / "work" / "mcp-memento"

    return None


def build_stub_local(dry: bool) -> None:
    """Build the stub binary for the current platform and copy it into stub/bin/.

    This is a local-only build (cargo release) for the host platform.
    Cross-compiled binaries for other platforms are produced by CI.

    Also copies the binary into the Zed extension work directory so that
    'Install Dev Extension' picks it up without needing a GitHub Release.
    """
    import platform
    import shutil as _shutil

    step("Building stub binary for current platform")

    stub_dir = ZED_DIR / "stub"
    # Cargo outputs to the workspace target dir (integrations/zed/target/),
    # NOT the sub-crate's own target/, because the workspace Cargo.toml in
    # ZED_DIR controls the output location.
    target_dir = ZED_DIR / "target" / "release"

    run(
        f"cargo build --release --manifest-path {stub_dir / 'Cargo.toml'}",
        dry=dry,
    )

    # Determine the output binary name and destination asset name
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        src_name = "memento-stub.exe"
        dst_name = "memento-stub-x86_64-pc-windows-msvc.exe"
    elif system == "darwin":
        src_name = "memento-stub"
        dst_name = (
            "memento-stub-aarch64-apple-darwin"
            if machine in ("arm64", "aarch64")
            else "memento-stub-x86_64-apple-darwin"
        )
    else:
        src_name = "memento-stub"
        dst_name = (
            "memento-stub-aarch64-unknown-linux-gnu"
            if machine in ("arm64", "aarch64")
            else "memento-stub-x86_64-unknown-linux-gnu"
        )

    src = target_dir / src_name
    dst = ZED_STUB_BIN / dst_name

    if not dry:
        if not src.exists():
            die(f"Expected stub binary not found: {src}")
        ZED_STUB_BIN.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(src, dst)

    ok(f"Stub built and copied to {dst.relative_to(ROOT)}")

    # ------------------------------------------------------------------
    # Also copy into the Zed extension work directory so that dev extensions
    # loaded via 'Install Dev Extension' can find the stub without needing a
    # published GitHub Release.
    #
    # Zed uses <data_dir>/extensions/work/<ext-id>/ as the CWD for the WASM
    # sandbox — it does NOT copy the repo source files there.  The WASM looks
    # for stub/bin/<asset> relative to that CWD, so we mirror the layout.
    # ------------------------------------------------------------------
    step("Copying stub into Zed dev-extension work dir")

    zed_work_dir = _zed_work_dir()

    if zed_work_dir is None:
        warn("Could not locate Zed data directory; skipping work-dir copy.")
        warn("Run 'python scripts/deploy.py build-zed-stub' again after installing Zed.")
        return

    zed_stub_dst_dir = zed_work_dir / "stub" / "bin"

    if not dry:
        import os as _os

        zed_stub_dst_dir.mkdir(parents=True, exist_ok=True)

        dst_final = zed_stub_dst_dir / dst_name
        dst_tmp = zed_stub_dst_dir / (dst_name + ".tmp")

        try:
            # Copy to a temp name first, then atomically replace the target.
            # On Windows the destination binary may be memory-mapped by Zed's
            # WASM runtime; a direct overwrite raises PermissionError, but
            # replacing via a temporary file succeeds because Windows allows
            # renaming over an in-use file when the new inode is distinct.
            _shutil.copy2(src, dst_tmp)
            _os.replace(dst_tmp, dst_final)
        except PermissionError:
            dst_tmp.unlink(missing_ok=True)
            warn("Could not update stub in Zed work dir (file locked by Zed).")
            warn("Reload the extension inside Zed to pick up the new binary:")
            warn("  Ctrl+Shift+P → 'zed: extensions' → Reload mcp-memento")
            return

    ok(f"Stub copied to Zed work dir: {zed_stub_dst_dir / dst_name}")


def cmd_dev_stub(dry: bool) -> None:
    """Build the stub for the current platform and commit it to stub/bin/."""
    build_stub_local(dry)

    step("Committing stub binary on dev")
    git_add_all(dry)
    git_commit("chore(zed): rebuild stub binary for current platform", dry)
    git_push("dev", dry)
    ok("Stub binary committed and pushed to dev")


def cmd_upload_stubs(python_ver: str, dry: bool) -> None:
    """Create (if needed) the GitHub Release vX.Y.Z and upload local stub binaries.

    Recovery command for when the full bump completed tagging and merging but
    crashed before the stub upload step.
    """
    upload_stub_binaries_to_release(python_ver, dry)
    ok(f"Stub upload for v{python_ver} complete.")


def download_stub_binaries(python_ver: str, dry: bool) -> None:
    """Download built stub binaries from GitHub Release into stub/bin/."""
    step("Downloading stub binaries from GitHub Release")
    tag = f"v{python_ver}"
    cmd = (
        f"gh release download {tag} --repo {GITHUB_REPO} --dir {ZED_STUB_BIN} --clobber"
        " --pattern 'memento-stub-*'"
    )
    run(cmd, dry=dry)

    if not dry:
        files = sorted(ZED_STUB_BIN.glob("memento-stub-*"))

        for f in files:
            ok(f"Downloaded: {f.name}  ({f.stat().st_size / 1024:.0f} KB)")


# ---------------------------------------------------------------------------
def run_tests(dry: bool) -> None:
    step("Running test suite")
    run(
        f"{UV} run --extra dev python -m pytest tests/ --tb=short -q",
        dry=dry,
    )
    ok("All tests passed")


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------


def cmd_status() -> None:
    step("Current version state")
    py_ver = read_pyproject_version()
    init_v = read_init_version()
    zed_v = read_zed_cargo_version()
    ext_v = read_extension_version()
    stub_r = read_stub_ext_release()

    rows = [
        ("pyproject.toml", py_ver),
        ("src/memento/__init__.py", init_v),
        ("integrations/zed/Cargo.toml (package)", zed_v),
        ("integrations/zed/extension.toml", ext_v),
        ("lib.rs STUB_EXT_RELEASE", stub_r),
    ]

    expected_stub = f"v{py_ver}"
    col = max(len(r[0]) for r in rows) + 2

    for label, value in rows:
        pad = " " * (col - len(label))

        if label.startswith("lib.rs"):
            match = value == expected_stub
        else:
            match = value == py_ver

        color = Color.GREEN if match else Color.YELLOW
        print(f"  {label}{pad}{color}{value}{Color.RESET}")

    # Git status summary
    print()
    branch = git_current_branch()
    clean = git_is_clean()
    state = (
        f"{Color.GREEN}clean{Color.RESET}"
        if clean
        else f"{Color.YELLOW}dirty{Color.RESET}"
    )
    info(f"Branch: {branch}  |  Working tree: {state}")


# ---------------------------------------------------------------------------
# bump command (main orchestrator)
# ---------------------------------------------------------------------------


def cmd_bump(
    new_ver: str,
    skip_tests: bool,
    dev_only: bool,
    dry: bool,
    yes: bool,
) -> None:
    old_ver = read_pyproject_version()

    step(f"Bump {old_ver} → {new_ver}" + ("  (dev only, no merge)" if dev_only else ""))

    if not confirm(
        f"Proceed with full release of v{new_ver}?",
        yes=yes or dry,
    ):
        die("Aborted.")

    # 0. Ensure we are on dev branch
    branch = git_current_branch()

    if branch != "dev" and not dry:
        die(f"Must be on 'dev' branch (currently on '{branch}'). Checkout dev first.")

    # 0b. For prod bumps: verify CHANGELOG before touching anything else.
    # Must run before the working-tree check so that edits to CHANGELOG.md
    # (which are uncommitted by design) are read from disk, not stashed away.
    if not dev_only:
        step("Verifying CHANGELOG entry")
        check_changelog(new_ver, dry)

    # 0c. Ensure working tree is clean.
    # For prod bumps, uncommitted edits to CHANGELOG.md are expected (the developer
    # wrote release notes but didn't commit them yet) — git add -A at step 5 will
    # pick them up.  We only stash on --dev bumps where an unclean tree is unexpected.
    if not git_is_clean() and not dry:
        warn("Working tree has uncommitted changes (likely CHANGELOG.md edits) — will be included in the release commit.")

    # 1. Tests
    if not skip_tests:
        run_tests(dry)

    # 2. Bump version in all manifests (including STUB_EXT_RELEASE in lib.rs)
    step("Bumping versions")
    bump_pyproject(new_ver, dry)
    bump_init(new_ver, dry)
    bump_zed_cargo(new_ver, dry)
    bump_extension_toml(new_ver, dry)
    bump_lib_rs_stub_release(new_ver, dev_only, dry)
    bump_readme_badge(new_ver, dry)

    # 3. Changelog
    if dev_only:
        # First --dev bump: scaffold a placeholder entry for the developer to fill in.
        # Re-runs of --dev on the same version skip this silently.
        step("Scaffolding CHANGELOG entry")
        scaffold_changelog(new_ver, dry)

    # 4. Build wheel
    build_package(dry)

    # 5. Commit dev
    step("Committing on dev")
    git_add_all(dry)
    git_commit(f"chore(release): bump version to {new_ver}", dry)
    git_push("dev", dry)
    ok("dev branch updated and pushed")

    # 6. Python release tag
    # With --dev: tag locally only — do NOT push to origin.
    # Pushing a vX.Y.Z tag triggers CI workflows (stub build + GitHub Release
    # creation), which must only happen on a full official release.
    step(f"Tagging v{new_ver}" + (" (local only — not pushed)" if dev_only else ""))
    py_tag = f"v{new_ver}"

    if not dry and git_tag_exists_local(py_tag):
        if dev_only:
            warn(f"Tag {py_tag} already exists locally.")
            if confirm(f"Move tag {py_tag} to current HEAD (retag)?", yes):
                git_retag(py_tag, dry)
                ok(f"Tag {py_tag} moved to HEAD (local only, not pushed)")
            else:
                info(f"Tag {py_tag} left unchanged.")
        else:
            # Tag exists locally but may not yet be on remote (e.g. after a --dev bump).
            if git_tag_exists_remote(py_tag):
                # Tag is already on remote — this is a resume scenario (bump crashed
                # mid-flight after the tag was pushed). Skip tagging and continue
                # with merge + stub upload.
                warn(f"Tag {py_tag} already on remote — skipping retag, resuming release.")
            else:
                warn(f"Tag {py_tag} exists locally but NOT on remote (likely from a --dev bump).")

                if confirm(f"Move tag {py_tag} to current HEAD and push it?", yes):
                    git_retag(py_tag, dry)
                    git_push_tag(py_tag, dry)
                    ok(f"Tag {py_tag} moved to HEAD and pushed")
                else:
                    die("Aborted. Delete the local tag manually or bump to a new version.")
    else:
        git_tag(py_tag, dry)
        if dev_only:
            ok(f"Tag {py_tag} created locally (not pushed)")
        else:
            git_push_tag(py_tag, dry)
            ok(f"Tag {py_tag} pushed")

    # 7. Merge dev → main (skipped with --dev)
    if not dev_only:
        git_merge_to_main(dry)

    # 8. Stub binaries
    if not dev_only:
        # Full release: upload pre-built binaries to the GitHub release vX.Y.Z.
        # The CI workflow (zed-stub-release.yml) cross-compiles all 5 targets
        # and uploads them; here we also upload the locally pre-built ones from
        # stub/bin/ as a safety net.
        upload_stub_binaries_to_release(new_ver, dry)
    else:
        # Dev-only: build stub for the current platform and upload it to the
        # rolling pre-release "dev-latest" on GitHub.
        # The CI workflow (zed-stub-dev.yml) cross-compiles the remaining 4
        # targets and uploads them to the same pre-release.
        build_stub_local(dry)
        upload_stub_binaries_to_dev_prerelease(dry)

    print()
    ok(f"Release v{new_ver} complete!")

    if dev_only:
        info("Dev-only bump complete. Tag is local only — CI was NOT triggered.")
        info("When ready for the official release:")
        info("  python scripts/deploy.py promote")
        info("  python scripts/deploy.py publish")
    else:
        info("Publish to PyPI with:  python scripts/deploy.py publish")


# ---------------------------------------------------------------------------
# zed-binaries command
# ---------------------------------------------------------------------------


def cmd_zed_binaries(python_ver: str, dry: bool, yes: bool) -> None:
    tag = f"v{python_ver}"
    step(f"Downloading stub binaries from release {tag} and committing to repo")

    # Check release exists and has the expected assets
    result = run(
        f"gh release view {tag} --repo {GITHUB_REPO} --json assets -q '.assets | length'",
        capture=True,
        dry=dry,
        check=False,
    )

    if not dry and (not result or int(result) < 5):
        die(
            f"Release {tag} not found or has fewer than 5 stub assets. "
            "Wait for CI to finish and try again."
        )

    download_stub_binaries(python_ver, dry)

    git_add_all(dry)
    git_commit(
        f"chore(zed): bundle cross-compiled stub binaries from {tag}",
        dry,
    )
    git_push("dev", dry)
    ok("Stub binaries committed and pushed to dev")


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deploy.py",
        description="MCP Memento unified release & deploy script.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── bump ──────────────────────────────────────────────────────────────
    # Always a dev-only bump: local tag, no merge to main, no CI trigger.
    p_bump = sub.add_parser(
        "bump",
        help="Dev bump: update versions locally, build stub, upload to dev-latest.",
    )
    p_bump.add_argument("version", help="New version string (e.g. 0.3.0)")
    p_bump.add_argument(
        "--dry-run", action="store_true", help="Preview actions without executing."
    )
    p_bump.add_argument(
        "--skip-tests", action="store_true", help="Skip pytest before release."
    )

    # ── promote ───────────────────────────────────────────────────────────
    # Promotes the current dev version to an official release:
    # verifies CHANGELOG, merges dev→main, pushes tag, triggers CI.
    p_promote = sub.add_parser(
        "promote",
        help="Promote current dev version to official release (merge, tag push, CI).",
    )
    p_promote.add_argument(
        "--dry-run", action="store_true", help="Preview actions without executing."
    )
    p_promote.add_argument(
        "--skip-tests", action="store_true", help="Skip pytest before release."
    )
    p_promote.add_argument(
        "--yes", "-y", action="store_true", help="Auto-confirm all prompts."
    )

    # ── build ─────────────────────────────────────────────────────────────
    p_build = sub.add_parser("build", help="Build sdist + wheel.")
    p_build.add_argument("--dry-run", action="store_true")

    # ── publish ───────────────────────────────────────────────────────────
    p_pub = sub.add_parser("publish", help="Upload dist/* to PyPI (or TestPyPI with -t).")
    p_pub.add_argument(
        "--test", "-t",
        action="store_true",
        help="Upload to TestPyPI instead of PyPI.",
    )
    p_pub.add_argument("--dry-run", action="store_true")

    # ── build-zed-stub ────────────────────────────────────────────────────
    p_build_zed_stub = sub.add_parser(
        "build-zed-stub",
        help="Build stub binary for current platform and commit to stub/bin/.",
    )
    p_build_zed_stub.add_argument("--dry-run", action="store_true")

    # ── ext-binaries ──────────────────────────────────────────────────────
    p_ext = sub.add_parser(
        "ext-binaries",
        help="Download CI-built stub binaries from GitHub release and commit to repo.",
    )
    p_ext.add_argument(
        "--version",
        metavar="X.Y.Z",
        help="Version override (default: read from pyproject.toml).",
    )
    p_ext.add_argument("--dry-run", action="store_true")
    p_ext.add_argument("--yes", "-y", action="store_true")

    # ── upload-stubs ──────────────────────────────────────────────────────
    p_us = sub.add_parser(
        "upload-stubs",
        help="Create GitHub Release (if needed) and upload local stub binaries.",
    )
    p_us.add_argument(
        "--version",
        metavar="X.Y.Z",
        help="Version override (default: read from pyproject.toml).",
    )
    p_us.add_argument("--dry-run", action="store_true")

    # ── status ────────────────────────────────────────────────────────────
    sub.add_parser("status", help="Show current versions across all manifests.")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        cmd_status()

    elif args.command == "bump":
        if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
            die(f"Invalid version format: {args.version!r}. Expected X.Y.Z")
        cmd_bump(
            new_ver=args.version,
            skip_tests=args.skip_tests,
            dev_only=True,
            dry=args.dry_run,
            yes=True,
        )

    elif args.command == "promote":
        new_ver = read_pyproject_version()
        cmd_bump(
            new_ver=new_ver,
            skip_tests=args.skip_tests,
            dev_only=False,
            dry=args.dry_run,
            yes=args.yes,
        )

    elif args.command == "build":
        build_package(dry=args.dry_run)

    elif args.command == "publish":
        target = "testpypi" if args.test else "pypi"
        publish(target=target, dry=args.dry_run)

    elif args.command == "build-zed-stub":
        cmd_dev_stub(dry=args.dry_run)

    elif args.command == "ext-binaries":
        ver = args.version or read_pyproject_version()
        cmd_zed_binaries(
            python_ver=ver,
            dry=args.dry_run,
            yes=args.yes,
        )

    elif args.command == "upload-stubs":
        ver = args.version or read_pyproject_version()
        cmd_upload_stubs(python_ver=ver, dry=args.dry_run)


if __name__ == "__main__":
    main()
