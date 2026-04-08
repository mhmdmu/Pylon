import logging
import socket
import threading
from hashlib import sha1

from .exceptions import BadRequest, HttpError, MethodNotAllowed, NotFound
from .middleware import MiddlewarePipeline
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
            return route["handler"], params, route["protected"]

    raise NotFound(f"Resource {request.path} not found")


# ---------------------------------------------------------------------------
# TCPServer — socket layer
# ---------------------------------------------------------------------------


class TCPServer:
    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def listen(self, handler) -> None:
        """Accept connections in a loop, call handler(conn, addr) for each."""
        with socket.create_server((self.host, self.port)) as server:
            log.info(f"Pylon running on http://{self.host}:{self.port}")

            while True:
                conn, addr = server.accept()
                log.debug(f"Connection from {addr[0]}:{addr[1]}")

                threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr, handler),
                    daemon=True,
                ).start()

    def read_header(self, conn: socket.socket) -> bytes:
        """Read raw bytes from the socket until the HTTP header terminator."""
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(1)
            if not chunk:
                break
            raw += chunk
        return raw

    def _handle_connection(self, conn, addr, handler):
        conn.settimeout(self.timeout)

        try:
            with conn:
                conn.sendall(handler(conn, addr))
        except TimeoutError:
            log.warning(f"Timeout for {addr[0]}:{addr[1]}")


# ---------------------------------------------------------------------------
# HttpServer — HTTP layer
# ---------------------------------------------------------------------------


class HttpServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        timeout: int = 5,
    ) -> None:
        self._tcp = TCPServer(host, port, timeout)
        self._routes: dict[str, list] = {}
        self._before_middlewares = []
        self._after_middlewares = []
        self.middleware = MiddlewarePipeline(self)
        self._auth_middleware = None

    def route(self, method: str, path: str, protected: bool = False):
        """Decorator to register a route handler."""
        method = method.upper()

        def wrapper(handler):
            log.info(f"Registering route: {method} {path} -> {handler.__name__}")

            self._routes.setdefault(method, []).append(
                {"pattern": path, "handler": handler, "protected": protected}
            )
            return handler

        return wrapper

    def run(self) -> None:
        self._tcp.listen(self._handle)

    def auth(self, middleware) -> None:
        self._auth_middleware = middleware

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle(self, conn: socket.socket, addr: tuple) -> bytes:
        raw_header = self._tcp.read_header(conn)
        request = _parse_request(raw_header, conn)
        response = None

        try:
            # Run before middlewares
            for stage in self._before_middlewares:
                request = stage(request)

            handler, params, protected = _resolve(self._routes, request)
            request.path_params = params

            # Authentication
            if protected and self._auth_middleware:
                request = self._auth_middleware(request)

            response = handler(request)
        except MethodNotAllowed:
            # Preflight request
            if request.method == "OPTIONS":
                response = Response(HttpStatus.NO_CONTENT)
        except HttpError as err:
            log.warning(f"HTTP error {err.status.code}: {err.message}")
            response = Response(err.status, body=err.message)
        except Exception as err:
            log.error(f"Unhandled exception: {err}", exc_info=True)
            response = Response(
                HttpStatus.INTERNAL_SERVER_ERROR, body="Internal Server Error"
            )
        finally:
            if response is None:
                response = Response(
                    HttpStatus.INTERNAL_SERVER_ERROR, body="Internal Server Error"
                )

            response = self._apply_cache_headers(request, response)

            # Run after middlewares
            for stage in self._after_middlewares:
                response = stage(request, response)

            log.info(
                f"{addr[0]}:{addr[1]} — {request.method} {request.path} {response.status}"
            )

        return response.build()

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
