from .msg_type import Request, Response
from .status import HttpStatus


class MiddlewarePipeline:
    def __init__(self, server) -> None:
        self._server = server

    def after(self, func):
        self._server._after_middlewares.append(func)
        return func

    def before(self, func):
        self._server._before_middlewares.append(func)
        return func


class CorsMiddleware:
    def __init__(self, config) -> None:
        self.config = config

    def __call__(self, request: Request, response: Response) -> Response:
        if request.method == "OPTIONS":
            response = self._handle_preflight(request)

        config_headers = {}
        origin = request.headers.get("Origin", None)

        # No Origin header = no browser = no config
        if not origin:
            return response

        if "*" in self.config.allow_origins or origin in self.config.allow_origins:
            config_headers["Access-Control-Allow-Origin"] = (
                "*" if "*" in self.config.allow_origins else origin
            )

        if self.config.allow_credentials:
            config_headers["Access-Control-Allow-Credentials"] = "true"

        response.headers |= config_headers  # merge config headers

        return response

    def _handle_preflight(self, request) -> Response:
        origin = request.headers.get("Origin", None)
        if not origin:
            return Response(HttpStatus.BAD_REQUEST, body="Missing Origin header.")

        headers = {}

        headers["Access-Control-Allow-Methods"] = ", ".join(self.config.allow_methods)
        headers["Access-Control-Allow-Headers"] = ", ".join(self.config.allow_headers)
        headers["Access-Control-Allow-Max-Age"] = self.config.max_age

        return Response(HttpStatus.NO_CONTENT, headers=headers)
