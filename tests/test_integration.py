import threading
import time
import urllib.request
from urllib.error import HTTPError

from pylon import (
    CacheConfig,
    HttpServer,
    Request,
    Response,
)

#
# Server setup
#

app = HttpServer(host="localhost", port=9090)


@app.route("GET", "/cached")
def cached_route(req: Request) -> Response:
    return Response.text(content="This is from cached_route handler").set_cache_config(
        CacheConfig()
    )


def start_server():
    thread = threading.Thread(target=app.run, daemon=True)
    thread.start()
    time.sleep(0.5)  # give server time to bind and listen


#
# Test Cases
#


def test_200_with_cache_headers():
    try:
        # assert status 200
        response = urllib.request.urlopen("http://localhost:9090/cached")
        print("Status code is 200 - PASSED")

        cache_control, etag = False, False
        for line in str(response.headers).splitlines():
            if line.startswith("Cache-Control"):
                cache_control = True
            if line.startswith("ETag"):
                etag = True

        assert cache_control, "FAILED: Cache-Control header missing on 200 response"
        assert etag, "FAILED: ETag header missing on 200 response"
        print("Cache-Control and ETag headers present - PASSED")
    except HTTPError as err:
        assert False, f"FAILED: Unexpected HTTP error {err.code} on 200 request"


def test_304_on_matching_etag():
    try:
        req = urllib.request.Request("http://localhost:9090/cached")
        response = urllib.request.urlopen(req)

        etag = ""
        for line in str(response.headers).splitlines():
            if line.startswith("ETag"):
                etag = line.split(": ")[1]
                break

        # send second GET with If-None-Match header
        req = urllib.request.Request(
            "http://localhost:9090/cached", headers={"If-None-Match": etag}
        )

        response = urllib.request.urlopen(req)  # should raise error

    except HTTPError as err:
        assert err.code == 304, f"FAILED: Expected 304, got {err.code}"
        body = err.read()
        assert not body, f"FAILED: 304 response must have no body, got: {body}"
        print("304 returned with no body - PASSED")


#
# Runner
#

start_server()


def run():
    test_200_with_cache_headers()
    print("Test Case #1 PASSED")
    test_304_on_matching_etag()
    print("Test Case #2 PASSED")
    print("All integration tests passed.")
