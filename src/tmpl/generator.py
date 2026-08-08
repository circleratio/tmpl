"""Core logic for resolving a template directory and rendering it into a new project."""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path

import jinja2

from .constants import DEFAULT_EXCLUDE_PATTERNS
from .exceptions import OutputExistsError, TemplateNotFoundError, TmplError


def resolve_template_dir(kind: str) -> Path:
    """Resolve ~/share/tmpl/[kind], raising if it does not exist."""
    template_dir = Path.home() / "share" / "tmpl" / kind
    if not template_dir.is_dir():
        raise TemplateNotFoundError(f"template not found: {template_dir}")
    return template_dir


def resolve_output_dir(project_name: str, output: str | None) -> Path:
    """Resolve the output directory, raising if it already exists."""
    output_dir = Path(output) if output is not None else Path.cwd() / project_name
    if output_dir.exists():
        raise OutputExistsError(f"output already exists: {output_dir}")
    return output_dir


def build_jinja_env() -> jinja2.Environment:
    """Build the Jinja2 environment shared by file content and path-segment rendering."""
    return jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)


def is_excluded(path: Path, root: Path) -> bool:
    """Check whether any path segment relative to root matches a default exclude pattern."""
    relative_parts = path.relative_to(root).parts
    return any(
        fnmatch.fnmatch(part, pattern)
        for part in relative_parts
        for pattern in DEFAULT_EXCLUDE_PATTERNS
    )


def render_path(
    env: jinja2.Environment,
    src: Path,
    template_dir: Path,
    output_dir: Path,
    context: dict,
) -> Path:
    """Render each path segment of src (relative to template_dir) and join under output_dir."""
    try:
        relative_parts = [
            env.from_string(part).render(context)
            for part in src.relative_to(template_dir).parts
        ]
    except jinja2.UndefinedError as e:
        raise TmplError(f"undefined variable in path '{src}': {e}") from e
    return output_dir.joinpath(*relative_parts)


def copy_or_render_file(env: jinja2.Environment, src: Path, dst: Path, context: dict) -> None:
    """Render src as a Jinja2 template if it decodes as UTF-8 text, else copy it verbatim."""
    try:
        text = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        shutil.copy2(src, dst)
        return
    try:
        rendered = env.from_string(text).render(context)
    except jinja2.UndefinedError as e:
        raise TmplError(f"undefined variable in file '{src}': {e}") from e
    dst.write_text(rendered, encoding="utf-8")


def copy_symlink(src: Path, dst: Path) -> None:
    """Duplicate a symlink as-is, without resolving its target."""
    target = os.readlink(src)
    try:
        os.symlink(target, dst, target_is_directory=src.is_dir())
    except OSError as e:
        raise TmplError(f"failed to create symlink '{dst}': {e}") from e


def report(verbose: bool, dry_run: bool, src: Path, dst: Path) -> None:
    """Print the resolved destination path when verbose or dry-run mode is active."""
    if verbose or dry_run:
        print(dst)


def render_tree(
    template_dir: Path,
    output_dir: Path,
    context: dict,
    verbose: bool = False,
    dry_run: bool = False,
) -> None:
    """Walk template_dir and render its contents into output_dir."""
    env = build_jinja_env()
    if not dry_run:
        output_dir.mkdir(parents=True)

    for dirpath, dirnames, filenames in os.walk(template_dir, followlinks=False):
        src_dir = Path(dirpath)
        # Do not descend into excluded directories (e.g. .git, __pycache__).
        dirnames[:] = [d for d in dirnames if not is_excluded(src_dir / d, template_dir)]

        # os.walk(followlinks=False) lists symlinked directories in dirnames
        # without recursing into them, so each entry is visited exactly once.
        for name in dirnames + filenames:
            src = src_dir / name
            if is_excluded(src, template_dir):
                continue
            dst = render_path(env, src, template_dir, output_dir, context)
            report(verbose, dry_run, src, dst)
            if dry_run:
                continue
            if src.is_symlink():
                copy_symlink(src, dst)
            elif src.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                copy_or_render_file(env, src, dst, context)


def generate_project(
    kind: str,
    project_name: str,
    output: str | None,
    variables: dict,
    verbose: bool = False,
    dry_run: bool = False,
) -> Path:
    """Resolve the template/output directories and render the template into a new project."""
    template_dir = resolve_template_dir(kind)
    output_dir = resolve_output_dir(project_name, output)
    # project_name always wins over an instruction of the same name (spec.md 5.1).
    context = {**variables, "project_name": project_name}
    render_tree(template_dir, output_dir, context, verbose=verbose, dry_run=dry_run)
    return output_dir
