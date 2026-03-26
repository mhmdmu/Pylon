from pylon import CacheConfig

test_cases = {
    1: (CacheConfig(no_store=True, private=True).build_cache_header(), "no-store"),
    2: (CacheConfig(no_cache=True, max_age=300).build_cache_header(), "no-cache"),
    3: (
        CacheConfig(public=True, immutable=True, max_age=31536000).build_cache_header(),
        "max-age=31536000, public, immutable",
    ),
    4: (CacheConfig().build_cache_header(), "max-age=60"),
}


def run():
    for no, t_case in test_cases.items():
        actual, expected = t_case

        assert actual == expected, (
            f"Test Case #{no} FAILED -> expected: {expected}, got: {actual}"
        )
        print(f"Test Case #{no}: PASSED")

    try:
        CacheConfig(public=True, private=True)
        assert False, "Should have raised ValueError"
    except ValueError:
        print("Test Case #5: PASSED")
