"""Tests for tmpl.cli (spec.md 6.1)."""

from __future__ import annotations

import pytest

from tmpl import cli
from tmpl.exceptions import InvalidInstructionError


class TestParseInstructions:
    def test_parses_name_value_pairs(self):
        assert cli.parse_instructions(["author=alice", "year=2026"]) == {
            "author": "alice",
            "year": "2026",
        }

    def test_raises_on_missing_equals_sign(self):
        with pytest.raises(InvalidInstructionError):
            cli.parse_instructions(["not-a-pair"])


class TestParseArgs:
    def test_missing_required_arguments_exits_with_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cli.parse_args([])
        assert exc_info.value.code == 2
        assert "usage" in capsys.readouterr().err.lower()

    def test_defaults(self):
        args = cli.parse_args(["sample", "myproj"])
        assert args.kind == "sample"
        assert args.project_name == "myproj"
        assert args.instructions == []
        assert args.output is None
        assert args.verbose is False
        assert args.dry_run is False

    def test_options_and_instructions(self):
        args = cli.parse_args(
            ["sample", "myproj", "-o", "out", "--verbose", "--dry-run", "author=alice"]
        )
        assert args.output == "out"
        assert args.verbose is True
        assert args.dry_run is True
        assert args.instructions == ["author=alice"]


class TestMain:
    def test_invalid_instruction_returns_1_and_prints_error(self, capsys, home_dir):
        exit_code = cli.main(["sample", "myproj", "not-a-pair"])
        assert exit_code == 1
        assert "error:" in capsys.readouterr().err

    def test_missing_template_returns_1_and_prints_error(self, capsys, home_dir, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        exit_code = cli.main(["missing-kind", "myproj"])
        assert exit_code == 1
        assert "error:" in capsys.readouterr().err

    def test_success_returns_0_and_renders_template(self, make_template, tmp_path, monkeypatch):
        make_template("sample", {"a.txt": "{{ project_name }}\n"})
        monkeypatch.chdir(tmp_path)
        exit_code = cli.main(["sample", "myproj"])
        assert exit_code == 0
        assert (tmp_path / "myproj" / "a.txt").read_text(encoding="utf-8") == "myproj\n"

    def test_dry_run_creates_nothing(self, make_template, tmp_path, monkeypatch):
        make_template("sample", {"a.txt": "hi"})
        monkeypatch.chdir(tmp_path)
        exit_code = cli.main(["sample", "myproj", "--dry-run"])
        assert exit_code == 0
        assert not (tmp_path / "myproj").exists()

    def test_verbose_prints_paths(self, make_template, tmp_path, monkeypatch, capsys):
        make_template("sample", {"a.txt": "hi"})
        monkeypatch.chdir(tmp_path)
        exit_code = cli.main(["sample", "myproj", "--verbose"])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert str(tmp_path / "myproj" / "a.txt") in out
