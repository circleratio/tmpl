"""Entry point for `python -m tmpl`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
