import json
from email.utils import formatdate

from .cache import CacheConfig
from .status import HttpStatus


class Request:
    def __init__(self) -> None:
        self.raw_request: bytes = b""
        self.method: str = ""
        self.path: str = ""
        self.http_version: str = ""
        self.headers: dict[str, str] = {}
        self.body: str | None = None
        self.path_params: dict[str, str] = {}
        self.query_params: dict[str, str | bool] = {}

    def __str__(self) -> str:
        return self.raw_request.decode(errors="replace")


class Response:
    def __init__(
        self,
        status: HttpStatus,
        headers: dict | None = None,
        body: str = "",
        http_version: str = "HTTP/1.1",
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.http_version = http_version
        self.cache_config = None

    def build(self) -> bytes:
        encoded_body = self.body.encode()
        status_line = f"{self.http_version} {self.status.code} {self.status.phrase}"
        headers = self._build_headers(len(encoded_body))

        return f"{status_line}\r\n{headers}\r\n".encode() + encoded_body

    def set_cache_config(self, config: CacheConfig) -> "Response":
        self.cache_config = config
        return self

    def _build_headers(self, content_length: int) -> str:
        default_headers = {
            "Date": formatdate(timeval=None, localtime=False, usegmt=True),
            "Server": "Pylon/1.0",
        }

        if content_length > 0:
            default_headers["Content-Length"] = str(content_length)

        merged = default_headers | self.headers
        return "".join(f"{k}: {v}\r\n" for k, v in merged.items())

    @classmethod
    def json(cls, data: dict | list, status: HttpStatus | None = None) -> "Response":
        return cls(
            status=status or HttpStatus.OK,
            headers={"Content-Type": "application/json"},
            body=json.dumps(data),
        )

    @classmethod
    def text(cls, content: str, status: HttpStatus | None = None) -> "Response":
        return cls(
            status=status or HttpStatus.OK,
            headers={"Content-Type": "text/plain"},
            body=content,
        )

    @classmethod
    def html(cls, content: str, status: HttpStatus | None = None) -> "Response":
        return cls(
            status=status or HttpStatus.OK,
            headers={"Content-Type": "text/html"},
            body=content,
        )
