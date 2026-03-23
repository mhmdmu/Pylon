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
fi
