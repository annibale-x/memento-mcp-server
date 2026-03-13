"""
Configuration management for MemoryGraph.

This module centralizes all configuration options and environment variable handling
for the SQLite-only memory server with YAML file support.

Config attributes are dynamic descriptors that read environment variables on each
access. This ensures tests using patch.dict(os.environ) and direct Config attribute
overrides both work correctly.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class BackendType(Enum):
    """Supported backend types (SQLite only)."""

    SQLITE = "sqlite"
    AUTO = "auto"


_CORE_TOOLS = [
    "store_memory",
    "get_memory",
    "search_memories",
    "update_memory",
    "delete_memory",
    "create_relationship",
    "get_related_memories",
    "recall_memories",
    "get_recent_activity",
]

_EXTENDED_EXTRA_TOOLS = [
    "get_memory_statistics",
    "search_relationships_by_context",
    "contextual_search",
]

_ADVANCED_TOOLS = [
    "analyze_memory_graph",
    "find_patterns",
    "suggest_relationships",
    "get_memory_clusters",
    "get_central_memories",
    "find_path_between_memories",
    "get_memory_network",
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


_DEFAULT_DB_PATH = os.path.expanduser("~/.memorygraph/memory.db")
_DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "memorygraph.yaml",
    Path.home() / ".memorygraph" / "config.yaml",
]


class YAMLConfig:
    """YAML configuration loader with environment variable override support."""

    _config_cache: Dict[Path, Dict[str, Any]] = {}

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load configuration from YAML files with environment variable overrides.

        Hierarchy (highest priority last):
        1. Default values
        2. Global config (~/.memorygraph/config.yaml)
        3. Project config (./memorygraph.yaml)
        4. Environment variables
        """
        config = cls._get_defaults()

        # Load from global config
        global_config_path = Path.home() / ".memorygraph" / "config.yaml"
        if global_config_path.exists():
            config.update(cls._load_yaml_file(global_config_path))

        # Load from project config
        project_config_path = Path.cwd() / "memorygraph.yaml"
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
            "enable_advanced_tools": False,
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "features": {
                "auto_extract_entities": True,
                "session_briefing": True,
                "briefing_verbosity": "standard",
                "briefing_recency_days": 7,
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
        # Backend configuration
        if os.getenv("MEMORY_BACKEND"):
            config["backend"] = os.getenv("MEMORY_BACKEND")

        # SQLite configuration
        if os.getenv("MEMORY_SQLITE_PATH"):
            config["sqlite_path"] = os.getenv("MEMORY_SQLITE_PATH")

        # Tool configuration
        if os.getenv("MEMORY_TOOL_PROFILE"):
            config["tool_profile"] = os.getenv("MEMORY_TOOL_PROFILE")

        if os.getenv("MEMORY_ENABLE_ADVANCED_TOOLS"):
            config["enable_advanced_tools"] = (
                os.getenv("MEMORY_ENABLE_ADVANCED_TOOLS").lower() == "true"
            )

        # Logging configuration
        if os.getenv("MEMORY_LOG_LEVEL"):
            config["logging"]["level"] = os.getenv("MEMORY_LOG_LEVEL")

        # Feature configuration
        if os.getenv("MEMORY_AUTO_EXTRACT_ENTITIES"):
            config["features"]["auto_extract_entities"] = (
                os.getenv("MEMORY_AUTO_EXTRACT_ENTITIES").lower() == "true"
            )

        if os.getenv("MEMORY_SESSION_BRIEFING"):
            config["features"]["session_briefing"] = (
                os.getenv("MEMORY_SESSION_BRIEFING").lower() == "true"
            )

        if os.getenv("MEMORY_BRIEFING_VERBOSITY"):
            config["features"]["briefing_verbosity"] = os.getenv(
                "MEMORY_BRIEFING_VERBOSITY"
            )

        if os.getenv("MEMORY_BRIEFING_RECENCY_DAYS"):
            config["features"]["briefing_recency_days"] = int(
                os.getenv("MEMORY_BRIEFING_RECENCY_DAYS")
            )

        if os.getenv("MEMORY_ALLOW_CYCLES"):
            config["features"]["allow_relationship_cycles"] = (
                os.getenv("MEMORY_ALLOW_CYCLES").lower() == "true"
            )

        return config

    @classmethod
    def save_config(cls, config: Dict[str, Any], path: Optional[Path] = None) -> None:
        """Save configuration to a YAML file."""
        if path is None:
            path = Path.cwd() / "memorygraph.yaml"

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

    Attributes can be overridden via direct assignment (e.g., Config.BACKEND = "sqlite")
    for testing or programmatic configuration.

    Environment Variables:
        MEMORY_BACKEND: Backend type (sqlite|auto) [default: sqlite]
        MEMORY_SQLITE_PATH: Database file path [default: ~/.memorygraph/memory.db]
        MEMORY_TOOL_PROFILE: Tool profile (core|extended|advanced) [default: core]
        MEMORY_ENABLE_ADVANCED_TOOLS: Enable advanced tools [default: false]
        MEMORY_LOG_LEVEL: Log level (DEBUG|INFO|WARNING|ERROR) [default: INFO]
        MEMORY_AUTO_EXTRACT_ENTITIES: Automatically extract entities from memory content [default: true]
        MEMORY_SESSION_BRIEFING: Enable session briefing feature [default: true]
        MEMORY_BRIEFING_VERBOSITY: Briefing verbosity level [default: standard]
        MEMORY_BRIEFING_RECENCY_DAYS: Number of days to consider for briefing [default: 7]
        MEMORY_ALLOW_CYCLES: Allow cycles in relationship graph [default: false]
    """

    # Load YAML configuration
    _yaml_config = YAMLConfig.load_config()

    # Backend configuration
    BACKEND = _EnvVar("MEMORY_BACKEND", default=_yaml_config.get("backend", "sqlite"))
    SQLITE_PATH = _EnvVar(
        "MEMORY_SQLITE_PATH", default=_yaml_config.get("sqlite_path", _DEFAULT_DB_PATH)
    )

    # Tool configuration
    TOOL_PROFILE = _EnvVar(
        "MEMORY_TOOL_PROFILE", default=_yaml_config.get("tool_profile", "core")
    )
    ENABLE_ADVANCED_TOOLS = _EnvVar(
        "MEMORY_ENABLE_ADVANCED_TOOLS",
        default=_yaml_config.get("enable_advanced_tools", False),
        cast=bool,
    )

    # Logging configuration
    LOG_LEVEL = _EnvVar(
        "MEMORY_LOG_LEVEL", default=_yaml_config.get("logging", {}).get("level", "INFO")
    )
    LOG_FORMAT = _yaml_config.get("logging", {}).get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Feature configuration
    AUTO_EXTRACT_ENTITIES = _EnvVar(
        "MEMORY_AUTO_EXTRACT_ENTITIES",
        default=_yaml_config.get("features", {}).get("auto_extract_entities", True),
        cast=bool,
    )
    SESSION_BRIEFING = _EnvVar(
        "MEMORY_SESSION_BRIEFING",
        default=_yaml_config.get("features", {}).get("session_briefing", True),
        cast=bool,
    )
    BRIEFING_VERBOSITY = _EnvVar(
        "MEMORY_BRIEFING_VERBOSITY",
        default=_yaml_config.get("features", {}).get("briefing_verbosity", "standard"),
    )
    BRIEFING_RECENCY_DAYS = _EnvVar(
        "MEMORY_BRIEFING_RECENCY_DAYS",
        default=_yaml_config.get("features", {}).get("briefing_recency_days", 7),
        cast=int,
    )
    ALLOW_RELATIONSHIP_CYCLES = _EnvVar(
        "MEMORY_ALLOW_CYCLES",
        default=_yaml_config.get("features", {}).get(
            "allow_relationship_cycles", False
        ),
        cast=bool,
    )

    @classmethod
    def get_backend_type(cls) -> BackendType:
        """Get the configured backend type, falling back to AUTO for unknown values."""
        backend_str = cls.BACKEND.lower()
        try:
            return BackendType(backend_str)
        except ValueError:
            return BackendType.AUTO

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
        profile = cls.TOOL_PROFILE.lower()
        legacy_map = {"lite": "core", "standard": "extended", "full": "advanced"}
        profile = legacy_map.get(profile, profile)

        # Get base tools from profile
        base_tools = TOOL_PROFILES.get(profile, TOOL_PROFILES["core"])

        # Add advanced tools if enabled
        if cls.ENABLE_ADVANCED_TOOLS and profile != "advanced":
            base_tools = list(set(base_tools + _ADVANCED_TOOLS))

        return base_tools

    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a summary of current configuration (without sensitive data)."""
        return {
            "backend": cls.BACKEND,
            "sqlite": {"path": cls.SQLITE_PATH},
            "tools": {
                "profile": cls.TOOL_PROFILE,
                "enable_advanced": cls.ENABLE_ADVANCED_TOOLS,
                "enabled_tools_count": len(cls.get_enabled_tools()),
            },
            "logging": {
                "level": cls.LOG_LEVEL,
                "format": cls.LOG_FORMAT,
            },
            "features": {
                "auto_extract_entities": cls.AUTO_EXTRACT_ENTITIES,
                "session_briefing": cls.SESSION_BRIEFING,
                "briefing_verbosity": cls.BRIEFING_VERBOSITY,
                "briefing_recency_days": cls.BRIEFING_RECENCY_DAYS,
                "allow_relationship_cycles": cls.ALLOW_RELATIONSHIP_CYCLES,
            },
            "config_sources": {
                "yaml_files": [
                    str(path) for path in _DEFAULT_CONFIG_PATHS if path.exists()
                ],
                "env_vars": {
                    attr: cls.is_env_set(attr)
                    for attr in [
                        "BACKEND",
                        "SQLITE_PATH",
                        "TOOL_PROFILE",
                        "ENABLE_ADVANCED_TOOLS",
                        "LOG_LEVEL",
                        "AUTO_EXTRACT_ENTITIES",
                        "SESSION_BRIEFING",
                        "BRIEFING_VERBOSITY",
                        "BRIEFING_RECENCY_DAYS",
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
                elif attr_name == "SQLITE_PATH":
                    descriptor.default = cls._yaml_config.get(
                        "sqlite_path", _DEFAULT_DB_PATH
                    )
                elif attr_name == "TOOL_PROFILE":
                    descriptor.default = cls._yaml_config.get("tool_profile", "core")
                elif attr_name == "ENABLE_ADVANCED_TOOLS":
                    descriptor.default = cls._yaml_config.get(
                        "enable_advanced_tools", False
                    )
                elif attr_name == "LOG_LEVEL":
                    descriptor.default = cls._yaml_config.get("logging", {}).get(
                        "level", "INFO"
                    )
                elif attr_name == "AUTO_EXTRACT_ENTITIES":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "auto_extract_entities", True
                    )
                elif attr_name == "SESSION_BRIEFING":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "session_briefing", True
                    )
                elif attr_name == "BRIEFING_VERBOSITY":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "briefing_verbosity", "standard"
                    )
                elif attr_name == "BRIEFING_RECENCY_DAYS":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "briefing_recency_days", 7
                    )
                elif attr_name == "ALLOW_RELATIONSHIP_CYCLES":
                    descriptor.default = cls._yaml_config.get("features", {}).get(
                        "allow_relationship_cycles", False
                    )

    @classmethod
    def create_default_config(cls, path: Optional[Path] = None) -> None:
        """Create a default configuration file."""
        if path is None:
            path = Path.cwd() / "memorygraph.yaml"

        default_config = {
            "backend": "sqlite",
            "sqlite_path": str(_DEFAULT_DB_PATH),
            "tool_profile": "extended",
            "enable_advanced_tools": True,
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "features": {
                "auto_extract_entities": True,
                "session_briefing": True,
                "briefing_verbosity": "standard",
                "briefing_recency_days": 7,
                "allow_relationship_cycles": False,
            },
        }

        YAMLConfig.save_config(default_config, path)
        print(f"Created default configuration file at: {path}")
