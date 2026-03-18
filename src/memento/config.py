"""
Configuration management for Memento.

This module centralizes all configuration options and environment variable handling
for the SQLite Memento with YAML file support.

Config attributes are dynamic descriptors that read environment variables on each
access. This ensures tests using patch.dict(os.environ) and direct Config attribute
overrides both work correctly.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_CORE_TOOLS = [
    "store_memento",
    "get_memento",
    "search_mementos",
    "update_memento",
    "delete_memento",
    "create_memento_relationship",
    "get_related_mementos",
    "recall_mementos",
    "get_recent_memento_activity",
    "memento_onboarding",
    # Confidence system tools (essential for all users)
    "get_low_confidence_mementos",
    "boost_memento_confidence",
    "adjust_memento_confidence",
]

_EXTENDED_EXTRA_TOOLS = [
    "get_memento_statistics",
    "search_memento_relationships_by_context",
    "contextual_memento_search",
    # Confidence system tools (technical maintenance)
    "apply_memento_confidence_decay",
]

_ADVANCED_TOOLS = [
    "analyze_memento_graph",
    "find_memento_patterns",
    "suggest_memento_relationships",
    "get_memento_clusters",
    "get_central_mementos",
    "find_path_between_mementos",
    "get_memento_network",
    # Confidence system tools (advanced configuration)
    "set_memento_decay_factor",
]

TOOL_PROFILES = {
    "core": _CORE_TOOLS,
    "extended": _CORE_TOOLS + _EXTENDED_EXTRA_TOOLS,
    "advanced": _CORE_TOOLS + _EXTENDED_EXTRA_TOOLS + _ADVANCED_TOOLS,
}


class _EnvVar:
    """Descriptor that reads environment variables dynamically on each access.

    When accessed as a class attribute (e.g., Config.BACKEND), invokes __get__
    which reads from os.environ at call time. This makes Config reactive to
    env var changes (e.g., via patch.dict(os.environ) in tests).

    Direct assignment (e.g., Config.BACKEND = "sqlite") replaces the descriptor
    with a static value, which is useful for tests that patch Config directly.
    """

    def __init__(self, *env_names: str, default: object = None, cast: object = None):
        """
        Args:
            env_names: Environment variable names to check in priority order.
                       Uses ``is not None`` check: only unset env vars fall
                       through. An explicitly set empty string is returned
                       (consistent with ``is_set()``).
            default: Default value if no env var is set (already the final type).
            cast: Optional type converter (int, float). Use bool for
                  "true"/"false" string parsing.
        """
        self.env_names = env_names
        self.default = default
        self.cast = cast

    def __get__(self, obj: object, objtype: type = None) -> object:
        for name in self.env_names:
            val = os.getenv(name)
            if val is not None:
                return self._convert(val)
        return self.default

    def _convert(self, val: str) -> object:
        if self.cast is None:
            return val
        if self.cast is bool:
            return val.lower() == "true"
        return self.cast(val)  # type: ignore[operator]

    def is_set(self) -> bool:
        """Return True if any of the env var names are explicitly set in os.environ.

        Uses membership testing (``in os.environ``), not truthiness.
        This distinguishes "user explicitly configured" from "using default".
        """
        return any(name in os.environ for name in self.env_names)

    def __repr__(self) -> str:
        return f"_EnvVar({', '.join(repr(n) for n in self.env_names)}, default={self.default!r})"


def _default_db_path() -> str:
    """Return the OS-appropriate default path for the Memento database.

    - Windows : %USERPROFILE%\\.mcp-memento\\context.db
    - macOS/Linux: ~/.mcp-memento/context.db
    """
    if os.name == "nt":
        base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        return os.path.join(base, ".mcp-memento", "context.db")

    return os.path.expanduser("~/.mcp-memento/context.db")


_DEFAULT_DB_PATH = _default_db_path()
_DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "memento.yaml",
    Path.home() / ".mcp-memento" / "config.yaml",
]


class YAMLConfig:
    """YAML configuration loader with environment variable override support."""

    _config_cache: Dict[Path, Dict[str, Any]] = {}

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load configuration from YAML files with environment variable overrides.

        Hierarchy (highest priority last):
        1. Default values
        2. Global config (~/.mcp-memento/config.yaml)
        3. Project config (./memento.yaml)
        4. Environment variables
        """
        config = cls._get_defaults()

        # Load from global config
        try:
            global_config_path = Path.home() / ".mcp-memento" / "config.yaml"
            if global_config_path.exists():
                config.update(cls._load_yaml_file(global_config_path))
        except (RuntimeError, OSError):
            # Home directory may not be available in some environments
            # (e.g., Windows services, containers, test environments)
            pass

        # Load from project config
        project_config_path = Path.cwd() / "memento.yaml"
        if project_config_path.exists():
            config.update(cls._load_yaml_file(project_config_path))

        # Apply environment variable overrides
        config = cls._apply_env_overrides(config)

        return config

    @classmethod
    def _get_defaults(cls) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "backend": "sqlite",
            "sqlite_path": str(_DEFAULT_DB_PATH),
            "tool_profile": "core",
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "features": {
                "allow_relationship_cycles": False,
            },
        }

    @classmethod
    def _load_yaml_file(cls, path: Path) -> Dict[str, Any]:
        """Load YAML configuration from a file."""
        if path in cls._config_cache:
            return cls._config_cache[path]

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                cls._config_cache[path] = config
                return config
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            return {}

    @classmethod
    def _apply_env_overrides(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # SQLite configuration
        if os.getenv("MEMENTO_DB_PATH"):
            config["sqlite_path"] = os.getenv("MEMENTO_DB_PATH")

        # Tool configuration
        if os.getenv("MEMENTO_PROFILE"):
            config["tool_profile"] = os.getenv("MEMENTO_PROFILE")

        # Logging configuration
        if os.getenv("MEMENTO_LOG_LEVEL"):
            config["logging"]["level"] = os.getenv("MEMENTO_LOG_LEVEL")

        # Feature configuration
        if os.getenv("MEMENTO_ALLOW_CYCLES"):
            config["features"]["allow_relationship_cycles"] = (
                os.getenv("MEMENTO_ALLOW_CYCLES").lower() == "true"
            )

        return config

    @classmethod
    def save_config(cls, config: Dict[str, Any], path: Optional[Path] = None) -> None:
        """Save configuration to a YAML file."""
        if path is None:
            path = Path.cwd() / "memento.yaml"

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Clear cache for this path
        if path in cls._config_cache:
            del cls._config_cache[path]


class Config:
    """
    Configuration class for the memory server.

    All attributes are dynamic descriptors that read from environment variables
    on each access. This makes Config the single source of truth for configuration
    while remaining reactive to runtime env var changes.

    Attributes can be overridden via direct assignment for testing or programmatic configuration.

    Environment Variables:
        MEMENTO_DB_PATH: Database file path [default: %USERPROFILE%\\.mcp-memento\\context.db on Windows, ~/.mcp-memento/context.db elsewhere]
        MEMENTO_PROFILE: Tool profile (core|extended|advanced) [default: core]
        MEMENTO_LOG_LEVEL: Log level (DEBUG|INFO|WARNING|ERROR) [default: INFO]
        MEMENTO_ALLOW_CYCLES: Allow cycles in relationship graph [default: false]


    """

    # Load YAML configuration
    _yaml_config = YAMLConfig.load_config()

    # Database configuration (SQLite only)
    DB_PATH = _EnvVar(
        "MEMENTO_DB_PATH",
        default=_yaml_config.get("sqlite_path", _DEFAULT_DB_PATH),
    )

    # Tool configuration
    PROFILE = _EnvVar(
        "MEMENTO_PROFILE",
        default=_yaml_config.get("tool_profile", "core"),
    )

    # Logging configuration
    LOG_LEVEL = _EnvVar(
        "MEMENTO_LOG_LEVEL",
        default=_yaml_config.get("logging", {}).get("level", "INFO"),
    )
    LOG_FORMAT = _yaml_config.get("logging", {}).get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Feature configuration
    ALLOW_RELATIONSHIP_CYCLES = _EnvVar(
        "MEMENTO_ALLOW_CYCLES",
        default=_yaml_config.get("features", {}).get(
            "allow_relationship_cycles", False
        ),
        cast=bool,
    )

    @classmethod
    def is_env_set(cls, attr_name: str) -> bool:
        """Check if a Config attribute's underlying env var is explicitly set.

        When the attribute is still an ``_EnvVar`` descriptor, delegates to
        ``_EnvVar.is_set()`` which checks ``os.environ`` membership (not
        truthiness).  If the descriptor has been replaced by direct assignment
        (e.g. in tests via ``Config.X = val``), returns ``True`` since the
        caller explicitly configured it.
        """
        descriptor = cls.__dict__.get(attr_name)
        if hasattr(descriptor, "is_set"):
            return descriptor.is_set()
        return attr_name in cls.__dict__

    @classmethod
    def get_enabled_tools(cls) -> list[str]:
        """Get the list of enabled tools based on the configured profile.

        Legacy profile names (lite, standard, full) are mapped to their
        modern equivalents. Unrecognized profiles fall back to core.
        """
        profile = cls.PROFILE.lower()
        legacy_map = {"lite": "core", "standard": "extended", "full": "advanced"}
        profile = legacy_map.get(profile, profile)

        # Get base tools from profile
        base_tools = TOOL_PROFILES.get(profile, TOOL_PROFILES["core"])

        return base_tools

    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a summary of current configuration (without sensitive data)."""
        return {
            "database": {"path": cls.DB_PATH},
            "tools": {
                "profile": cls.PROFILE,
                "enabled_tools_count": len(cls.get_enabled_tools()),
            },
            "logging": {
                "level": cls.LOG_LEVEL,
                "format": cls.LOG_FORMAT,
            },
            "features": {
                "allow_relationship_cycles": cls.ALLOW_RELATIONSHIP_CYCLES,
            },
            "config_sources": {
                "yaml_files": [
                    str(path) for path in _DEFAULT_CONFIG_PATHS if path.exists()
                ],
                "env_vars": {
                    attr: cls.is_env_set(attr)
                    for attr in [
                        "DB_PATH",
                        "PROFILE",
                        "LOG_LEVEL",
                        "ALLOW_RELATIONSHIP_CYCLES",
                    ]
                },
            },
        }

    @classmethod
    def reload_config(cls) -> None:
        """Reload configuration from YAML files and environment variables."""
        cls._yaml_config = YAMLConfig.load_config()

        # Update all descriptors with new defaults
        for attr_name, descriptor in cls.__dict__.items():
            if isinstance(descriptor, _EnvVar):
                # Get new default from YAML config
                if attr_name == "BACKEND":
                    descriptor.default = cls._yaml_config.get("backend", "sqlite")
                elif attr_name == "DB_PATH":
                    descriptor.default = cls._yaml_config.get(
                        "sqlite_path", _DEFAULT_DB_PATH
                    )
                elif attr_name == "PROFILE":
                    descriptor.default = cls._yaml_config.get("tool_profile", "core")
                elif attr_name == "LOG_LEVEL":
                    descriptor.default = cls._yaml_config.get("logging", {}).get(
                        "level", "INFO"
                    )

                elif attr_name == "ALLOW_RELATIONSHIP_CYCLES":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "allow_relationship_cycles", False
                    )

    @classmethod
    def create_default_config(cls, path: Optional[Path] = None) -> None:
        """Create a default configuration file."""
        if path is None:
            path = Path.cwd() / "memento.yaml"

        default_config = {
            "backend": "sqlite",
            "sqlite_path": str(_DEFAULT_DB_PATH),
            "tool_profile": "extended",
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "features": {
                "allow_relationship_cycles": False,
            },
        }

        YAMLConfig.save_config(default_config, path)
        print(f"Created default configuration file at: {path}")
