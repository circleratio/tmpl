"""Shared pytest fixtures for tmpl tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def home_dir(tmp_path, monkeypatch):
    """Fake home directory so tests never touch the real ~/share/tmpl."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


@pytest.fixture
def make_template(home_dir):
    """Factory fixture: create a template directory under home_dir/share/tmpl/[kind]."""

    def _make_template(kind: str, files: dict) -> Path:
        template_dir = home_dir / "share" / "tmpl" / kind
        template_dir.mkdir(parents=True)
        for rel_path, content in files.items():
            path = template_dir / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        return template_dir

    return _make_template
