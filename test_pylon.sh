#!/usr/bin/env bash

# Use xh if available, otherwise fall back to curl
if command -v xh &>/dev/null; then
    echo "--- GET all users"
    xh GET localhost:8080/users

    echo "--- GET single user"
    xh GET localhost:8080/users/1

    echo "--- GET with query param"
    xh GET localhost:8080/users role==admin

    echo "--- POST create user"
    xh POST localhost:8080/users name="Mhmd" role="user"

    echo "--- PATCH update user"
    xh PATCH localhost:8080/users/1 role="superadmin"

    echo "--- DELETE user"
    xh DELETE localhost:8080/users/1

    #
    # CORS support testing
    #
    echo "--- CORS: Preflight from allowed origin"
    xh OPTIONS localhost:8080/users \
        Origin:http://localhost:3000 \
        Access-Control-Request-Method:POST \
        Access-Control-Request-Headers:Content-Type

    echo "--- CORS: Preflight from disallowed origin (no Access-Control-Allowed-Origin header)"
    xh OPTIONS localhost:8080/users \
        Origin:http://not-allowed.com \
        Access-Control-Request-Method:POST

    echo "--- CORS: Preflight with no Origin"
    xh OPTIONS localhost:8080/users \
        Access-Control-Request-Method:POST

    echo "--- CORS: Actual request from allowed origin"
    xh GET localhost:8080/users \
        Origin:http://localhost:3000

    echo "--- CORS: Actual request from disallowed origin (no Access-Control-Allowed-Origin header)"
    xh GET localhost:8080/users \
        Origin:http://not-allowed.com
else
    echo "--- GET all users"
    curl -s localhost:8080/users

    echo "--- GET single user"
    curl -s localhost:8080/users/1

    echo "--- GET with query param"
    curl -s "localhost:8080/users?role=admin"

    echo "--- POST create user"
    curl -s -X POST localhost:8080/users \
        -H "Content-Type: application/json" \
        -d '{"name": "Mhmd", "role": "user"}'

    echo "--- PATCH update user"
    curl -s -X PATCH localhost:8080/users/1 \
        -H "Content-Type: application/json" \
        -d '{"role": "superadmin"}'

    echo "--- DELETE user"
    curl -s -X DELETE localhost:8080/users/1

    #
    # CORS support testing
    #
    echo "--- CORS: Preflight from allowed origin"
    curl -s -X OPTIONS http://localhost:8080/users \
        -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -i

    echo "--- CORS: Preflight from disallowed origin (no Access-Control-Allowed-Origin header)"
    curl -s -X OPTIONS http://localhost:8080/users \
        -H "Origin: http://not-allowed.com" \
        -H "Access-Control-Request-Method: POST" \
        -i

    echo "--- CORS: Preflight with no Origin"
    curl -s -X OPTIONS http://localhost:8080/users \
        -H "Access-Control-Request-Method: POST" \
        -i

    echo "--- CORS: Actual request from allowed origin"
    curl -s http://localhost:8080/users \
        -H "Origin: http://localhost:3000" \
        -i

    echo "--- CORS: Actual request from disallowed origin (no Access-Control-Allowed-Origin header)"
    curl -s http://localhost:8080/users \
        -H "Origin: http://not-allowed.com" \
        -i
fi
