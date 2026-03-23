# Pylon

A lightweight HTTP server framework built from scratch in Python — no frameworks, no third-party libraries, just raw TCP sockets and the standard library.

## Why I built this

Most backend tutorials teach you how to use a framework. You type `@app.route`, a request shows up in your handler, and everything in between stays hidden. I wanted to know what was actually happening in that gap.

So I built Pylon from the ground up. Reading raw bytes off a TCP connection, parsing HTTP by hand, matching routes, building responses from scratch. By the end the magic was gone — and that was the whole point.

## Why the name Pylon

A pylon is the massive gateway structure at the entrance of an ancient Egyptian temple — built from the ground up, stone by stone, no shortcuts. That felt like the right metaphor for this project.

There’s also the `Py` prefix, not by accident — it reflects ***Python***, the foundation this project is built on.

## Project structure

```
pylon/                  ← repo root
├── pylon/              ← the package
│   ├── __init__.py
│   ├── framework.py    ← TCPServer and HttpServer
│   ├── msg_type.py     ← Request and Response
│   ├── status.py       ← HttpStatus enum
│   └── exceptions.py   ← HttpError and subclasses
├── main.py             ← sample app with a basic user CRUD API
├── test_pylon.sh       ← end-to-end tests
└── README.md
```

## How to run

Start the server:

```bash
python main.py
```

Then in a separate terminal, run the test script:

```bash
bash test_pylon.sh
```

The script uses [`xh`](https://github.com/ducaale/xh) if it's installed, and falls back to `curl` automatically. `xh` is optional — everything works with just `curl`.

What the script covers: listing all users, fetching a single user by ID, filtering by query param, creating a new user, partially updating one, and deleting one.

## How it works

There are two layers and they don't know about each other:

**TCPServer** handles the socket — it opens a connection, accepts clients, reads raw bytes until it sees `\r\n\r\n` (the HTTP header terminator), and passes everything up. It has no idea what HTTP is.

**HttpServer** handles everything HTTP — it takes those raw bytes, parses them into a `Request`, matches the path against registered routes, calls the right handler, and builds a `Response` to send back.

Each request gets a fresh `Request` object. Nothing is shared between connections.

## Usage

```python
from pylon import HttpServer, Request, Response, HttpStatus, configure_logging

configure_logging()

app = HttpServer(host="localhost", port=8080)


@app.route("GET", "/")
def index(req: Request) -> Response:
    return Response.json({"message": "hello"})


@app.route("GET", "/users/{id}")
def get_user(req: Request) -> Response:
    user_id = req.path_params["id"]
    return Response.json({"id": user_id})


@app.route("POST", "/users")
def create_user(req: Request) -> Response:
    # req.body contains the raw request body as a string
    return Response.json({"created": True}, status=HttpStatus.CREATED)


if __name__ == "__main__":
    app.run()
```

Run it:

```bash
python main.py
```

## Routing

Routes support static and dynamic segments. Dynamic segments use `{name}` syntax and are available on `req.path_params`.

```python
@app.route("GET", "/posts/{post_id}/comments/{comment_id}")
def get_comment(req: Request) -> Response:
    post_id = req.path_params["post_id"]
    comment_id = req.path_params["comment_id"]
    ...
```

Query parameters are parsed automatically and available on `req.query_params`:

```
GET /users?role=admin&active
```

```python
req.query_params["role"]    # "admin"
req.query_params["active"]  # True  (flag param, no value)
```

## Request

| Attribute | Type | Description |
|---|---|---|
| `method` | `str` | `"GET"`, `"POST"`, etc. |
| `path` | `str` | Path without query string |
| `headers` | `dict` | Request headers |
| `body` | `str \| None` | Body for POST, PUT, PATCH |
| `path_params` | `dict` | Dynamic route segments |
| `query_params` | `dict` | Query string key-value pairs |

## Response

Three convenience constructors:

```python
Response.json({"key": "value"})
Response.text("plain text")
Response.html("<h1>hello</h1>")
```

Or build one manually with any status:

```python
Response(status=HttpStatus.NO_CONTENT)
Response(status=HttpStatus.CREATED, body="created", headers={"X-Id": "42"})
```

## Error handling

Raise any of the built-in exceptions from a handler and Pylon will return the right status code automatically:

```python
from pylon import BadRequest, NotFound

@app.route("GET", "/users/{id}")
def get_user(req: Request) -> Response:
    user = db.get(req.path_params["id"])
    if not user:
        raise NotFound(f"User not found")
    return Response.json(user)
```

| Exception | Status |
|---|---|
| `BadRequest` | 400 |
| `NotFound` | 404 |
| `MethodNotAllowed` | 405 |
| `HttpError(status, message)` | any |

Unhandled exceptions are caught, logged with a full traceback, and returned as `500 Internal Server Error`.

## Logging

Logging is off by default. Call `configure_logging()` once at startup to turn it on:

```python
from pylon import configure_logging
import logging

configure_logging()                        # INFO by default
configure_logging(level=logging.DEBUG)     # for more detail
```

Log output looks like:

```
2025-03-23 12:00:00 [INFO] pylon.framework: Registering route: GET / -> index
2025-03-23 12:00:00 [INFO] pylon.framework: Pylon running on http://localhost:8080
2025-03-23 12:00:01 [INFO] pylon.framework: 127.0.0.1:52341 — GET / 200 OK
```

## What's next

- [ ] CORS — handle preflight and inject `Access-Control-*` headers
- [ ] Concurrency — `threading.Thread` per connection
- [ ] Timeouts — `conn.settimeout(5)`
- [ ] Auth — parse and validate `Authorization` header
- [ ] Caching — `Cache-Control` and `ETag` headers, return `304` when unchanged
