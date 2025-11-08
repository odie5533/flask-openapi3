# -*- coding: utf-8 -*-
# Shared test utilities and decorators for decorator tests

from functools import wraps


def require_auth_decorator(f):
    """Test decorator that requires Bearer token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != "Bearer valid-token":
            return {"error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    return decorated_function


def require_admin_decorator(f):
    """Test decorator that requires admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        admin_header = request.headers.get("X-Admin")
        if not admin_header or admin_header != "admin-secret":
            return {"error": "Forbidden - Admin required"}, 403
        return f(*args, **kwargs)
    return decorated_function


def inject_user_decorator(f):
    """Test decorator that injects authenticated user into view function"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != "Bearer valid-token":
            return {"error": "Unauthorized"}, 401
        # Inject user object into kwargs
        user = {"id": 123, "name": "Test User", "role": "admin"}
        kwargs["user"] = user
        return f(*args, **kwargs)
    return decorated_function


def add_header_decorator(f):
    """Test decorator that adds a custom response header"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, str):
            return response, 200, {"X-Custom-Header": "DecoratorApplied"}
        return response
    return decorated_function


def modify_response_decorator(f):
    """Test decorator that modifies the response content"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, str):
            return f"Modified: {response}"
        return response
    return decorated_function


# Counter for testing decorator application
call_counter = {"count": 0}


def count_calls_decorator(f):
    """Test decorator that counts function calls"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        call_counter["count"] += 1
        return f(*args, **kwargs)
    return decorated_function
