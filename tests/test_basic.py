"""Basic tests to verify project setup."""

import sys
from pathlib import Path


def test_python_version():
    """Test that Python version is 3.11+."""
    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version_info}"


def test_project_structure():
    """Test that required directories exist."""
    project_root = Path(__file__).parent.parent

    required_dirs = ["apps", "libs", "infra", "ops"]
    for dir_name in required_dirs:
        assert (project_root / dir_name).exists(), f"Directory {dir_name} not found"


def test_rust_workspace():
    """Test that Rust workspace is properly configured."""
    project_root = Path(__file__).parent.parent
    cargo_toml = project_root / "Cargo.toml"

    assert cargo_toml.exists(), "Cargo.toml not found"

    content = cargo_toml.read_text()
    assert "[workspace]" in content, "Cargo.toml is not a workspace"
    assert "execution-gateway" in content, "execution-gateway not in workspace"


def test_python_config():
    """Test that Python configuration is valid."""
    project_root = Path(__file__).parent.parent
    pyproject_toml = project_root / "pyproject.toml"

    assert pyproject_toml.exists(), "pyproject.toml not found"

    content = pyproject_toml.read_text()
    assert "[tool.poetry]" in content, "Poetry configuration not found"
    assert "python = \"^3.11\"" in content, "Python 3.11+ not specified"
