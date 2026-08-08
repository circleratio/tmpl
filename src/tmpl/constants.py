"""Shared constants for the tmpl package."""

# Directory/file name patterns excluded from template rendering (fnmatch against each path segment).
DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
]
