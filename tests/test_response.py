from pylon import CacheConfig, HttpStatus, Response

response = Response(HttpStatus.OK)
res_with_config = response.set_cache_config(CacheConfig())


def run():
    assert response.cache_config is not None, (
        "Test Case #1 FAILED: cache config not set on response"
    )
    print("Test Case #1 PASSED")

    assert res_with_config is response, (
        "Test Case #2 FAILED: Returned response different"
    )
    print("Test Case #2 PASSED")
