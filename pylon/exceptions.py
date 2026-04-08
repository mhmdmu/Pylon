from .status import HttpStatus


class HttpError(Exception):
    def __init__(self, status: HttpStatus, message: str | None = None) -> None:
        self.status = status
        self.message = message or status.phrase
        super().__init__(self.message)


class BadRequest(HttpError):
    def __init__(self, message: str = "") -> None:
        super().__init__(HttpStatus.BAD_REQUEST, message)


class NotFound(HttpError):
    def __init__(self, message: str = "") -> None:
        super().__init__(HttpStatus.NOT_FOUND, message)


class MethodNotAllowed(HttpError):
    def __init__(self, message: str = "") -> None:
        super().__init__(HttpStatus.METHOD_NOT_ALLOWED, message)


class Unauthorized(HttpError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(HttpStatus.UNAUTHORIZED, message)
