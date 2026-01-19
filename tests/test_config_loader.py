"""Tests for config loader."""
import os
import pytest


def reset_config():
    """Reset global config state for testing."""
    import src.utils.config_loader as module
    with module._config_lock:
        module._config = None


def test_load_config():
    """Test loading config from yaml file."""
    from src.utils.config_loader import load_config
    reset_config()

    config = load_config("config/config.yaml")

    assert config is not None
    assert "database" in config
    assert "deepface" in config
    assert "storage" in config
    assert "api" in config


def test_get_config():
    """Test getting cached config."""
    from src.utils.config_loader import get_config, load_config
    reset_config()
    load_config("config/config.yaml")

    config = get_config()
    assert config is not None
    assert config["database"]["host"] == "localhost"
    assert config["deepface"]["model_name"] == "Facenet512"


def test_database_config():
    """Test database configuration values."""
    from src.utils.config_loader import load_config
    reset_config()
    config = load_config("config/config.yaml")

    db = config["database"]
    assert db["host"] == "localhost"
    assert db["port"] == 5432
    assert db["user"] == "deepface"
    assert db["database"] == "deepface_db"


def test_deepface_config():
    """Test deepface configuration values."""
    from src.utils.config_loader import load_config
    reset_config()
    config = load_config("config/config.yaml")

    df = config["deepface"]
    assert df["model_name"] == "Facenet512"
    assert df["detector_backend"] == "retinaface"
    assert df["threshold"] == 0.40


def test_env_var_resolution():
    """Test environment variable resolution."""
    from src.utils.config_loader import load_config
    reset_config()

    # Set env var
    os.environ["DB_HOST"] = "testhost"
    config = load_config("config/config.yaml")

    assert config["database"]["host"] == "testhost"

    # Cleanup
    del os.environ["DB_HOST"]
