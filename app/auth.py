from collections.abc import Callable
from functools import wraps

from flask import current_app, jsonify, request


def require_api_key(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = current_app.config["API_KEY"]
        provided = request.headers.get("X-API-Key")
        if not provided or provided != expected:
            return jsonify({"error": "missing or invalid X-API-Key header"}), 401
        return view(*args, **kwargs)

    return wrapped
