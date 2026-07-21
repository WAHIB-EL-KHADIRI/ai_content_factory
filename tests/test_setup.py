"""
Setup verification tests for AI Content OS Platform

Validates that all components are properly imported and configured.
"""

from pathlib import Path


def test_backend_imports():
    """Test that all backend modules can be imported."""
    modules = [
        "backend.agents.base",
        "backend.agents.router",
        "backend.agents.research",
        "backend.agents.writer",
        "backend.agents.seo",
        "backend.agents.editor",
        "backend.services.model_router",
        "backend.services.content",
        "backend.services.brand",
        "backend.services.memory",
        "backend.services.background",
        "backend.workflows.engine",
        "backend.workflows.builder",
        "backend.analytics.engine",
        "backend.plugins.base",
        "backend.core.config",
        "backend.core.auth",
        "backend.core.exceptions",
        "backend.core.pagination",
        "backend.db.models",
        "backend.api.middleware",
        "backend.api.websocket",
        "backend.api.admin",
        "backend.api.webhooks",
    ]

    for module in modules:
        __import__(module)


def test_src_imports():
    """Test that video generation pipeline imports work (skipped if moviepy not installed)."""
    try:
        from src.main import VideoGenerationPipeline
        assert VideoGenerationPipeline is not None
    except ImportError:
        import pytest
        pytest.skip("moviepy not installed - video pipeline optional")


def test_api_imports():
    """Test that FastAPI app can be imported."""
    from backend.api.app import create_app
    assert create_app is not None


def test_directory_structure():
    """Test that required directories exist."""
    required_dirs = [
        "backend",
        "backend/agents",
        "backend/services",
        "backend/workflows",
        "backend/plugins",
        "backend/analytics",
        "backend/core",
        "backend/db",
        "backend/api",
        "src",
        "config",
        "frontend/src",
        "tests",
    ]

    for dir_path in required_dirs:
        assert Path(dir_path).exists(), f"Missing directory: {dir_path}"


def test_config():
    """Test that configuration module works."""
    from backend.core.config import get_config
    config = get_config()
    assert config.name is not None
    assert config.version is not None


def test_dependencies():
    """Test that core dependencies are installed."""
    required = ["fastapi", "sqlalchemy", "pydantic", "starlette"]
    for module in required:
        __import__(module)
