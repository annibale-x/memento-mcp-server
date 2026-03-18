#!/usr/bin/env python3
"""
deploy.py — MCP Memento unified release & deploy script.

Usage:
    python scripts/deploy.py bump X.Y.Z [--ext N] [options]
    python scripts/deploy.py build
    python scripts/deploy.py publish --target {testpypi|pypi}
    python scripts/deploy.py ext-release --ext N     # alias: zed-release
    python scripts/deploy.py ext-binaries --ext N    # alias: zed-binaries
    python scripts/deploy.py status

Commands
--------
  bump X.Y.Z        Full release cycle: bump versions, update changelog/README,
                    commit dev, merge dev→main, push both, create Python tag,
                    build wheel, trigger IDE extension stub CI (if --ext given).
                    Use --dry-run to preview without making changes.

  build             Build sdist + wheel (no version bump).

  publish           Upload to TestPyPI or PyPI with twine.
                    --target testpypi  →  twine upload --repository testpypi dist/*
                    --target pypi      →  twine upload --repository pypi dist/*

  ext-release       Push tag vX.Y.Z-ext.N to trigger GitHub Actions stub build.
                    Uses current version from pyproject.toml unless --version given.
                    Alias: zed-release (kept for backward compatibility).

  ext-binaries      Download CI-built stub binaries into stub/bin/ and commit.
                    Alias: zed-binaries (kept for backward compatibility).

  status            Print current versions across all manifests.

Options
-------
  --ext N           Extension release counter (integer). Required for bump when
                    you also want to trigger an IDE extension stub release.
  --dry-run         Print all actions without executing them.
  --skip-tests      Skip pytest before release.
  --skip-merge      Do not merge dev→main (stays on dev branch only).
  --version X.Y.Z   Override Python version (for ext-release command).
  --yes             Non-interactive: skip all confirmation prompts.

Examples
--------
  # Full bump to 0.3.0, create extension ext.2 release, publish to PyPI
  python scripts/deploy.py bump 0.3.0 --ext 2 --yes

  # Dry run to preview everything
  python scripts/deploy.py bump 0.3.0 --ext 2 --dry-run

  # Build wheel only
  python scripts/deploy.py build

  # Publish to TestPyPI
  python scripts/deploy.py publish --target testpypi

  # Publish to PyPI
  python scripts/deploy.py publish --target pypi

  # Push extension stub tag only (already on correct version)
  python scripts/deploy.py ext-release --ext 3

  # Download CI binaries and commit to repo
  python scripts/deploy.py ext-binaries --ext 3

  # Show current version state
  python scripts/deploy.py status
"""

from __future__ import annotations

import argparse
import datetime
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
ZED_STUB_BIN = ZED_DIR / "stub" / "bin"

GITHUB_REPO = "annibale-x/mcp-memento"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}"


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
    new_text = re.sub(
        r'(\[package\].*?^version\s*=\s*)"[^"]+"',
        rf'\g<1>"{new_ver}"',
        text,
        flags=re.DOTALL | re.MULTILINE,
    )
    if new_text == text:
        warn(f"[package] version not found in {ZED_CARGO.relative_to(ROOT)}")
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


def bump_lib_rs_stub_release(new_ver: str, dry: bool) -> None:
    tag = f"v{new_ver}"
    _replace_in_file(
        ZED_LIB_RS,
        r'(STUB_EXT_RELEASE:\s*&str\s*=\s*)"[^"]+"',
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


def prepend_changelog(new_ver: str, dry: bool) -> None:
    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = (
        f"* {today}: v{new_ver} - Release (Hannibal)\n  * Version bump to {new_ver}\n\n"
    )
    if dry:
        info(f"Would prepend to CHANGELOG.md:\n  {entry.strip()}")
        return
    text = CHANGELOG.read_text(encoding="utf-8")
    # Insert after the first line (# Changelog header)
    lines = text.split("\n", 1)
    new_text = lines[0] + "\n\n" + entry + (lines[1] if len(lines) > 1 else "")
    CHANGELOG.write_text(new_text, encoding="utf-8")
    info("Prepended entry to CHANGELOG.md — edit it to add release notes!")


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
        run("python -m build", dry=dry)
    finally:
        if readme_backup:
            _restore_readme(readme_backup, dry)

    if not dry:
        files = sorted(DIST_DIR.glob("*"))
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
        line for line in out.splitlines()
        if line and not line.startswith("??")
    ]
    return len(tracked_changes) == 0


def git_add_all(dry: bool) -> None:
    run("git add -A", dry=dry)


def git_commit(message: str, dry: bool) -> None:
    run(f'git commit -m "{message}"', dry=dry)


def git_push(branch: str, dry: bool) -> None:
    run(f"git push origin {branch}", dry=dry)


def git_tag(tag: str, dry: bool) -> None:
    run(f"git tag {tag}", dry=dry)


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
    """Upload the bundled stub binaries from stub/bin/ to the GitHub release vX.Y.Z."""
    step(f"Uploading stub binaries to GitHub release v{python_ver}")
    tag = f"v{python_ver}"
    files = sorted(ZED_STUB_BIN.glob("memento-stub-*"))

    if not files:
        die(f"No stub binaries found in {ZED_STUB_BIN}. Build them first.")

    for f in files:
        cmd = f"gh release upload {tag} {f} --repo {GITHUB_REPO} --clobber"
        run(cmd, dry=dry)
        ok(f"Uploaded: {f.name}")


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
# Tests
# ---------------------------------------------------------------------------


def run_tests(dry: bool) -> None:
    step("Running test suite")
    run("python -m pytest tests/ --tb=short -q", dry=dry)
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
        yes=yes,
    ):
        die("Aborted.")

    # 0. Ensure we are on dev branch
    branch = git_current_branch()

    if branch != "dev" and not dry:
        die(f"Must be on 'dev' branch (currently on '{branch}'). Checkout dev first.")

    # 0b. Ensure working tree is clean
    if not git_is_clean() and not dry:
        warn("Working tree has uncommitted changes.")

        if not confirm("Stash them and continue?", yes=yes):
            die("Aborted. Please commit or stash changes first.")
        run("git stash", dry=dry)

    # 1. Tests
    if not skip_tests:
        run_tests(dry)

    # 2. Bump version in all manifests (including STUB_EXT_RELEASE in lib.rs)
    step("Bumping versions")
    bump_pyproject(new_ver, dry)
    bump_init(new_ver, dry)
    bump_zed_cargo(new_ver, dry)
    bump_extension_toml(new_ver, dry)
    bump_lib_rs_stub_release(new_ver, dry)
    bump_readme_badge(new_ver, dry)

    # 3. Changelog
    step("Updating CHANGELOG")
    prepend_changelog(new_ver, dry)

    # 4. Build wheel
    build_package(dry)

    # 5. Commit dev
    step("Committing on dev")
    git_add_all(dry)
    git_commit(f"chore(release): bump version to {new_ver}", dry)
    git_push("dev", dry)
    ok("dev branch updated and pushed")

    # 6. Python release tag
    step(f"Tagging v{new_ver}")
    py_tag = f"v{new_ver}"
    git_tag(py_tag, dry)
    git_push_tag(py_tag, dry)
    ok(f"Tag {py_tag} pushed")

    # 7. Merge dev → main (skipped with --dev)
    if not dev_only:
        git_merge_to_main(dry)

    # 8. Upload stub binaries to the GitHub release
    upload_stub_binaries_to_release(new_ver, dry)

    print()
    ok(f"Release v{new_ver} complete!")

    if dev_only:
        info("Merge skipped (--dev). When ready:")
        info("  git checkout main && git merge dev --no-ff && git push origin main")

    info("Publish to PyPI with:  python scripts/deploy.py publish --target pypi")


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
    p_bump = sub.add_parser("bump", help="Full release cycle: bump, build, tag, push.")
    p_bump.add_argument("version", help="New version string (e.g. 0.3.0)")
    p_bump.add_argument(
        "--dry-run", action="store_true", help="Preview actions without executing."
    )
    p_bump.add_argument(
        "--skip-tests", action="store_true", help="Skip pytest before release."
    )
    p_bump.add_argument(
        "--dev",
        action="store_true",
        help="Stay on dev branch only — do not merge into main.",
    )
    p_bump.add_argument(
        "--yes", "-y", action="store_true", help="Auto-confirm all prompts."
    )

    # ── build ─────────────────────────────────────────────────────────────
    p_build = sub.add_parser("build", help="Build sdist + wheel.")
    p_build.add_argument("--dry-run", action="store_true")

    # ── publish ───────────────────────────────────────────────────────────
    p_pub = sub.add_parser("publish", help="Upload dist/* to TestPyPI or PyPI.")
    p_pub.add_argument(
        "--target",
        required=True,
        choices=["testpypi", "pypi"],
        help="Upload destination.",
    )
    p_pub.add_argument("--dry-run", action="store_true")

    # ── ext-binaries ──────────────────────────────────────────────────────
    # Downloads CI-built stub binaries from the GitHub release vX.Y.Z and
    # commits them into stub/bin/.  Use after CI has finished building.
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
            dev_only=args.dev,
            dry=args.dry_run,
            yes=args.yes,
        )

    elif args.command == "build":
        build_package(dry=args.dry_run)

    elif args.command == "publish":
        publish(target=args.target, dry=args.dry_run)

    elif args.command == "ext-binaries":
        ver = args.version or read_pyproject_version()
        cmd_zed_binaries(
            python_ver=ver,
            dry=args.dry_run,
            yes=args.yes,
        )


if __name__ == "__main__":
    main()
