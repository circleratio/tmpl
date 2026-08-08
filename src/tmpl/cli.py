"""Command-line entry point for tmpl."""

from __future__ import annotations

import argparse
import sys

from .exceptions import InvalidInstructionError, TmplError
from .generator import generate_project


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="tmpl",
        description="Scaffold a new project's directory structure and files from a Jinja2-based template.",
    )
    parser.add_argument("kind", help="template kind, resolved under ~/share/tmpl/[kind]")
    parser.add_argument("project_name", help="project name, available in templates as {{ project_name }}")
    parser.add_argument(
        "instructions",
        nargs="*",
        help="template variables in 'name=value' form",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="output directory (default: ./[project_name])",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print each rendered file/directory path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be created without writing anything",
    )
    return parser.parse_args(argv)


def parse_instructions(instructions: list[str]) -> dict[str, str]:
    """Parse 'name=value' instruction strings into a variable dict."""
    variables: dict[str, str] = {}
    for instruction in instructions:
        name, sep, value = instruction.partition("=")
        if not sep:
            raise InvalidInstructionError(f"invalid instruction (expected 'name=value'): {instruction}")
        variables[name] = value
    return variables


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = parse_args(argv)
    try:
        variables = parse_instructions(args.instructions)
        generate_project(
            kind=args.kind,
            project_name=args.project_name,
            output=args.output,
            variables=variables,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
    except TmplError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
