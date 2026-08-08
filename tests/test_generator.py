"""Tests for tmpl.generator (spec.md 6.2)."""

from __future__ import annotations

import os
import platform

import pytest

from tmpl import generator
from tmpl.exceptions import OutputExistsError, TemplateNotFoundError, TmplError


class TestResolveTemplateDir:
    def test_raises_when_missing(self, home_dir):
        with pytest.raises(TemplateNotFoundError):
            generator.resolve_template_dir("missing")

    def test_returns_path_when_exists(self, make_template):
        template_dir = make_template("sample", {"a.txt": "hi"})
        assert generator.resolve_template_dir("sample") == template_dir


class TestResolveOutputDir:
    def test_raises_when_output_exists(self, tmp_path):
        existing = tmp_path / "existing"
        existing.mkdir()
        with pytest.raises(OutputExistsError):
            generator.resolve_output_dir("proj", str(existing))

    def test_defaults_to_cwd_project_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = generator.resolve_output_dir("myproj", None)
        assert result == tmp_path / "myproj"


class TestIsExcluded:
    def test_matches_default_pattern(self, tmp_path):
        assert generator.is_excluded(tmp_path / ".git" / "config", tmp_path) is True

    def test_does_not_match_regular_file(self, tmp_path):
        assert generator.is_excluded(tmp_path / "src" / "main.py", tmp_path) is False


class TestRenderTree:
    def test_renders_content_filename_and_dirname(self, make_template, tmp_path):
        template_dir = make_template(
            "sample",
            {
                "{{ project_name }}/README.md": "# {{ project_name }}\n",
                "{{ project_name }}/src/{{ module }}.py": "print('{{ module }}')\n",
            },
        )
        output_dir = tmp_path / "out"
        context = {"project_name": "myproj", "module": "app"}
        generator.render_tree(template_dir, output_dir, context)

        readme = output_dir / "myproj" / "README.md"
        module_file = output_dir / "myproj" / "src" / "app.py"
        assert readme.read_text(encoding="utf-8") == "# myproj\n"
        assert module_file.read_text(encoding="utf-8") == "print('app')\n"

    def test_excluded_directory_contents_are_not_copied(self, make_template, tmp_path):
        template_dir = make_template(
            "sample",
            {"README.md": "hello\n", ".git/config": "secret\n"},
        )
        output_dir = tmp_path / "out"
        generator.render_tree(template_dir, output_dir, {"project_name": "p"})

        assert (output_dir / "README.md").exists()
        assert not (output_dir / ".git").exists()

    def test_undefined_variable_raises(self, make_template, tmp_path):
        template_dir = make_template("sample", {"a.txt": "{{ missing }}"})
        output_dir = tmp_path / "out"
        with pytest.raises(TmplError):
            generator.render_tree(template_dir, output_dir, {"project_name": "p"})

    def test_binary_file_is_copied_verbatim(self, make_template, tmp_path):
        binary_content = bytes(range(256))
        template_dir = make_template("sample", {"logo.bin": binary_content})
        output_dir = tmp_path / "out"
        generator.render_tree(template_dir, output_dir, {"project_name": "p"})
        assert (output_dir / "logo.bin").read_bytes() == binary_content

    def test_dry_run_creates_nothing(self, make_template, tmp_path):
        template_dir = make_template("sample", {"a.txt": "hi"})
        output_dir = tmp_path / "out"
        generator.render_tree(template_dir, output_dir, {"project_name": "p"}, dry_run=True)
        assert not output_dir.exists()

    def test_verbose_prints_destination_paths(self, make_template, tmp_path, capsys):
        template_dir = make_template("sample", {"a.txt": "hi"})
        output_dir = tmp_path / "out"
        generator.render_tree(template_dir, output_dir, {"project_name": "p"}, verbose=True)
        captured = capsys.readouterr()
        assert str(output_dir / "a.txt") in captured.out

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="symlink creation requires elevated privileges on Windows",
    )
    def test_symlink_is_copied_as_symlink(self, home_dir, tmp_path):
        template_dir = home_dir / "share" / "tmpl" / "sample"
        template_dir.mkdir(parents=True)
        target = template_dir / "real.txt"
        target.write_text("real\n", encoding="utf-8")
        link = template_dir / "link.txt"
        link.symlink_to(target)

        output_dir = tmp_path / "out"
        generator.render_tree(template_dir, output_dir, {"project_name": "p"})

        dst_link = output_dir / "link.txt"
        assert dst_link.is_symlink()
        assert os.readlink(dst_link) == os.readlink(link)


class TestGenerateProject:
    def test_full_integration(self, make_template, tmp_path, monkeypatch):
        make_template(
            "sample",
            {"{{ project_name }}.txt": "hello {{ project_name }}, {{ author }}\n"},
        )
        monkeypatch.chdir(tmp_path)
        output_dir = generator.generate_project(
            kind="sample",
            project_name="myproj",
            output=None,
            variables={"author": "alice"},
        )
        assert output_dir == tmp_path / "myproj"
        rendered = (output_dir / "myproj.txt").read_text(encoding="utf-8")
        assert rendered == "hello myproj, alice\n"

    def test_project_name_argument_wins_over_instruction(self, make_template, tmp_path, monkeypatch):
        make_template("sample", {"a.txt": "{{ project_name }}\n"})
        monkeypatch.chdir(tmp_path)
        output_dir = generator.generate_project(
            kind="sample",
            project_name="myproj",
            output=None,
            variables={"project_name": "should-be-ignored"},
        )
        assert (output_dir / "a.txt").read_text(encoding="utf-8") == "myproj\n"
