"""Exception hierarchy used across the tmpl package."""


class TmplError(Exception):
    """Base class for all tmpl errors."""


class TemplateNotFoundError(TmplError):
    """Raised when the template directory for the given kind does not exist."""


class OutputExistsError(TmplError):
    """Raised when the output path already exists."""


class InvalidInstructionError(TmplError):
    """Raised when an instruction argument is not in 'name=value' form."""
