from __future__ import annotations

class APIError(Exception):
    """A client-facing validation error."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

