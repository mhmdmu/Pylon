import logging
import socket
from hashlib import sha1

from .cors import CorsConfig
from .exceptions import BadRequest, HttpError, MethodNotAllowed, NotFound
from .msg_type import Request, Response
from .status import HttpStatus

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging(level: int = logging.INFO) -> None:
    """Call this once at startup to enable Pylon's log output."""

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Suppress logs by default unless the user calls configure_logging().
logging.getLogger("pylon").addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Request parsing  (stateless — returns a fresh Request each call)
# ---------------------------------------------------------------------------


def _parse_request(raw_header: bytes, conn: socket.socket) -> Request:
    request = Request()

    header_text = raw_header[:-4].decode()  # strip trailing \r\n\r\n
    lines = header_text.splitlines()

    # Request line
    parts = lines[0].split()
    if len(parts) != 3:
        raise BadRequest("Malformed request line")

    request.method, request.path, request.http_version = parts

    # Query parameters — strip from path before storing
    query_idx = request.path.find("?")
    if query_idx != -1:
        query_string = request.path[query_idx + 1 :]
        request.path = request.path[:query_idx]
        for param in query_string.split("&"):
            if not param:
                continue
            if "=" in param:
                k, v = param.split("=", maxsplit=1)
                request.query_params[k] = v
            else:
                request.query_params[param] = True  # flag param e.g. ?debug

    # Headers
    for line in lines[1:]:
        try:
            key, val = line.split(":", maxsplit=1)
            request.headers[key.strip()] = val.strip()
        except ValueError:
            continue  # skip malformed header lines

    # Body — read from socket using Content-Length from headers above
    raw_body = b""
    content_length = int(request.headers.get("Content-Length", 0))
    if content_length and request.method in ("POST", "PUT", "PATCH"):
        raw_body = conn.recv(content_length)
        request.body = raw_body.decode()

    request.raw_request = raw_header + raw_body

    return request


# ---------------------------------------------------------------------------
# Route registry
# ---------------------------------------------------------------------------


def _match_route(pattern: str, path: str) -> tuple[bool, dict]:
    pattern_parts = pattern.strip("/").split("/")
    path_parts = path.strip("/").split("/")

    if len(pattern_parts) != len(path_parts):
        return False, {}

    params = {}
    for p, r in zip(pattern_parts, path_parts):
        if p.startswith("{") and p.endswith("}"):
            params[p[1:-1]] = r
        elif p != r:
            return False, {}

    return True, params


def _resolve(routes: dict, request: Request) -> tuple:
    method_routes = routes.get(request.method)
    if method_routes is None:
        raise MethodNotAllowed(f"Method {request.method} not supported")

    for route in method_routes:
        matched, params = _match_route(route["pattern"], request.path)
        if matched:
            return route["handler"], params

    raise NotFound(f"Resource {request.path} not found")


# ---------------------------------------------------------------------------
# TCPServer — socket layer
# ---------------------------------------------------------------------------


class TCPServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def listen(self, handler) -> None:
        """Accept connections in a loop, call handler(conn, addr) for each."""
        with socket.create_server((self.host, self.port)) as server:
            log.info(f"Pylon running on http://{self.host}:{self.port}")

            while True:
                conn, addr = server.accept()
                log.debug(f"Connection from {addr[0]}:{addr[1]}")
                with conn:
                    conn.sendall(handler(conn, addr))

    def read_header(self, conn: socket.socket) -> bytes:
        """Read raw bytes from the socket until the HTTP header terminator."""
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(1)
            if not chunk:
                break
            raw += chunk
        return raw


# ---------------------------------------------------------------------------
# HttpServer — HTTP layer
# ---------------------------------------------------------------------------


class HttpServer:
    def __init__(
        self, host: str = "localhost", port: int = 8080, cors: CorsConfig | None = None
    ) -> None:
        self._tcp = TCPServer(host, port)
        self._routes: dict[str, list] = {}
        self.cors = cors

    def route(self, method: str, path: str):
        """Decorator to register a route handler."""
        method = method.upper()

        def wrapper(handler):
            log.info(f"Registering route: {method} {path} -> {handler.__name__}")

            self._routes.setdefault(method, []).append(
                {"pattern": path, "handler": handler}
            )
            return handler

        return wrapper

    def run(self) -> None:
        self._tcp.listen(self._handle)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle(self, conn: socket.socket, addr: tuple) -> bytes:
        raw_header = self._tcp.read_header(conn)
        request = _parse_request(raw_header, conn)

        try:
            # Preflight request
            if request.method == "OPTIONS":
                response = self._handle_preflight(request)
            else:
                handler, params = _resolve(self._routes, request)
                request.path_params = params
                response = handler(request)
        except HttpError as err:
            log.warning(f"HTTP error {err.status.code}: {err.message}")
            response = Response(err.status, body=err.message)
        except Exception as err:
            log.error(f"Unhandled exception: {err}", exc_info=True)
            response = Response(
                HttpStatus.INTERNAL_SERVER_ERROR, body="Internal Server Error"
            )

        if response is None:
            response = Response(
                HttpStatus.INTERNAL_SERVER_ERROR, body="Internal Server Error"
            )

        response = self._apply_cache_headers(request, response)
        response = self._apply_cors_headers(request, response)

        log.info(
            f"{addr[0]}:{addr[1]} — {request.method} {request.path} {response.status}"
        )

        return response.build()

    def _apply_cors_headers(self, request: Request, response: Response) -> Response:
        # CORS is not configured
        if not self.cors:
            return response

        cors_headers = {}
        origin = request.headers.get("Origin", None)

        # No Origin header = no browser = no CORS
        if not origin:
            return response

        if "*" in self.cors.allow_origins or origin in self.cors.allow_origins:
            cors_headers["Access-Control-Allow-Origin"] = (
                "*" if "*" in self.cors.allow_origins else origin
            )

        if self.cors.allow_credentials:
            cors_headers["Access-Control-Allow-Credentials"] = "true"

        response.headers |= cors_headers  # merge cors headers

        return response

    def _handle_preflight(self, request) -> Response | None:
        origin = request.headers.get("Origin", None)
        if not origin:
            return Response(HttpStatus.BAD_REQUEST, body="Missing Origin header.")

        # CORS is not configured
        if not self.cors:
            return Response(HttpStatus.METHOD_NOT_ALLOWED)

        headers = {}

        headers["Access-Control-Allow-Methods"] = ", ".join(self.cors.allow_methods)
        headers["Access-Control-Allow-Headers"] = ", ".join(self.cors.allow_headers)
        headers["Access-Control-Allow-Max-Age"] = self.cors.max_age

        return Response(HttpStatus.NO_CONTENT, headers=headers)

    # Cache support
    def _apply_cache_headers(self, request: Request, response: Response) -> Response:
        # Cache is not configured
        if not response.cache_config:
            return response

        config = response.cache_config
        cache_headers = {"Cache-Control": config.build_cache_header()}

        if not config.no_store:
            hashed_val = sha1(response.body.encode()).hexdigest()
            cache_headers["ETag"] = f'"{hashed_val}"'

            request_etag = request.headers.get("If-None-Match", None)

            if request_etag:
                # NOTE: weak ETags (W/"...") are not supported
                if request_etag.strip('"') == hashed_val:
                    return Response(HttpStatus.NOT_MODIFIED, headers=cache_headers)

        response.headers |= cache_headers

        return response
