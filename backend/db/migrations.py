"""Alembic migration helpers for AI Content OS"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from alembic.config import Config
from alembic import command


def _get_alembic_config() -> Config:
    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini = project_root / "alembic.ini"
    return Config(str(alembic_ini))


def run_migrations() -> None:
    """Run alembic upgrade head programmatically."""
    alembic_cfg = _get_alembic_config()
    command.upgrade(alembic_cfg, "head")


def create_migration(message: str) -> None:
    """Generate a new migration with the given message."""
    alembic_cfg = _get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)


def downgrade_migration(revision: str = "-1") -> None:
    """Downgrade to a specific revision (default: one step back)."""
    alembic_cfg = _get_alembic_config()
    command.downgrade(alembic_cfg, revision)


def current_revision() -> None:
    """Show current migration revision."""
    alembic_cfg = _get_alembic_config()
    command.current(alembic_cfg)
