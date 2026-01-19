"""Config loader with environment variable support."""
import os
import re
import yaml
from pathlib import Path
import threading

_config = None
_config_lock = threading.Lock()


def _resolve_env_vars(value):
    """Resolve ${VAR:-default} patterns in config values."""
    if isinstance(value, str):
        pattern = r'\$\{(\w+)(?::-([^}]*))?\}'
        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)
        return re.sub(pattern, replacer, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_config(path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file with thread safety."""
    global _config
    with _config_lock:
        if _config is None:
            with open(path) as f:
                raw_config = yaml.safe_load(f)
            _config = _resolve_env_vars(raw_config)
            # Convert port to int
            if "database" in _config and "port" in _config["database"]:
                _config["database"]["port"] = int(_config["database"]["port"])
    return _config


def get_config() -> dict:
    """Get loaded configuration."""
    return _config or load_config()
