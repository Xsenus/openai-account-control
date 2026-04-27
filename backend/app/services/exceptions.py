"""Service-layer exceptions."""

class AuthExpiredError(Exception):
    """Raised when the saved session state is missing or no longer valid."""


class ProbeError(Exception):
    """Raised when the UI probe cannot complete due to layout changes or runtime issues."""
