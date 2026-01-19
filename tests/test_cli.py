"""Tests for CLI commands."""
import pytest
from click.testing import CliRunner
from src.cli.commands import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


def test_cli_help(runner):
    """Test CLI help output."""
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Event Face Detection CLI" in result.output


def test_config_command(runner):
    """Test config command."""
    result = runner.invoke(cli, ["config"])

    assert result.exit_code == 0
    assert "database:" in result.output
    assert "deepface:" in result.output


def test_search_missing_file(runner):
    """Test search with missing file."""
    result = runner.invoke(cli, ["search", "nonexistent.jpg"])

    assert result.exit_code != 0


def test_register_help(runner):
    """Test register command help."""
    result = runner.invoke(cli, ["register", "--help"])

    assert result.exit_code == 0
    assert "photos" in result.output.lower()


def test_build_help(runner):
    """Test build command help."""
    result = runner.invoke(cli, ["build", "--help"])

    assert result.exit_code == 0
    assert "db-path" in result.output
