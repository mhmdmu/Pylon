from pylon import (
    CorsConfig,
    CorsMiddleware,
    HttpServer,
    HttpStatus,
    Request,
    Response,
    configure_logging,
)

configure_logging()  # enable logging

cors = CorsConfig(allow_origins=["http://localhost:3000", "https://example.com"])

app = HttpServer()

app.middleware.after(CorsMiddleware(cors))

# In-memory database
users_db = {
    "1": {"id": "1", "name": "Alice", "role": "admin"},
    "2": {"id": "2", "name": "Bob", "role": "user"},
    "3": {"id": "3", "name": "Charlie", "role": "user"},
}


@app.route("GET", "/")
def index(_) -> Response:
    return Response.json({"message": "Welcome to Pylon!"})


@app.route("GET", "/users")
def list_users(req: Request) -> Response:
    role = req.query_params.get("role")
    if role:
        filtered = [u for u in users_db.values() if u["role"] == role]
        return Response.json(filtered)
    return Response.json(list(users_db.values()))


@app.route("GET", "/users/{id}")
def get_user(req: Request) -> Response:
    user_id = req.path_params["id"]
    user = users_db.get(user_id)
    if not user:
        return Response.json(
            {"error": f"User {user_id} not found"}, status=HttpStatus.NOT_FOUND
        )
    return Response.json(user)


@app.route("POST", "/users")
def create_user(req: Request) -> Response:
    import json

    if not req.body:
        return Response.json(
            {"error": "Request body is required"}, status=HttpStatus.BAD_REQUEST
        )

    try:
        data = json.loads(req.body)
    except json.JSONDecodeError:
        return Response.json(
            {"error": "Invalid JSON body"}, status=HttpStatus.BAD_REQUEST
        )

    if "name" not in data:
        return Response.json(
            {"error": "Field 'name' is required"}, status=HttpStatus.BAD_REQUEST
        )

    new_id = str(len(users_db) + 1)
    new_user = {"id": new_id, "name": data["name"], "role": data.get("role", "user")}
    users_db[new_id] = new_user
    return Response.json(new_user, status=HttpStatus.CREATED)


@app.route("PATCH", "/users/{id}")
def update_user(req: Request) -> Response:
    import json

    user_id = req.path_params["id"]
    user = users_db.get(user_id)
    if not user:
        return Response.json(
            {"error": f"User {user_id} not found"}, status=HttpStatus.NOT_FOUND
        )

    if not req.body:
        return Response.json(
            {"error": "Request body is required"}, status=HttpStatus.BAD_REQUEST
        )

    try:
        data = json.loads(req.body)
    except json.JSONDecodeError:
        return Response.json(
            {"error": "Invalid JSON body"}, status=HttpStatus.BAD_REQUEST
        )

    user.update({k: v for k, v in data.items() if k != "id"})
    return Response.json(user)


@app.route("DELETE", "/users/{id}")
def delete_user(req: Request) -> Response:
    user_id = req.path_params["id"]
    if user_id not in users_db:
        return Response.json(
            {"error": f"User {user_id} not found"}, status=HttpStatus.NOT_FOUND
        )
    del users_db[user_id]
    return Response(status=HttpStatus.NO_CONTENT)


if __name__ == "__main__":
    app.run()
