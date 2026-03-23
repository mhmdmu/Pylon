from enum import Enum


class HttpStatus(Enum):
    OK = (200, "OK")
    CREATED = (201, "Created")
    NO_CONTENT = (204, "No Content")
    MOVED_PERMANENTLY = (301, "Moved Permanently")
    FOUND = (302, "Found")
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Unauthorized")
    FORBIDDEN = (403, "Forbidden")
    NOT_FOUND = (404, "Not Found")
    METHOD_NOT_ALLOWED = (405, "Method Not Allowed")
    INTERNAL_SERVER_ERROR = (500, "Internal Server Error")
    SERVICE_UNAVAILABLE = (503, "Service Unavailable")

    def __init__(self, code: int, phrase: str) -> None:
        self.code = code
        self.phrase = phrase

    def __str__(self) -> str:
        return f"{self.code} {self.phrase}"
