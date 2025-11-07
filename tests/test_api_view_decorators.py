# -*- coding: utf-8 -*-
# Test class-level decorators for APIView

from functools import wraps

import pytest
from pydantic import BaseModel, Field

from flask_openapi3 import APIView, Info, OpenAPI


info = Info(title="Decorator Test API", version="1.0.0")
app = OpenAPI(__name__, info=info)
app.config["TESTING"] = True


# Test decorator that adds a custom header
def add_header_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, str):
            return response, 200, {"X-Custom-Header": "DecoratorApplied"}
        return response
    return decorated_function


# Test decorator that modifies the response
def modify_response_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, str):
            return f"Modified: {response}"
        return response
    return decorated_function


# Test decorator that counts calls
call_counter = {"count": 0}


def count_calls_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        call_counter["count"] += 1
        return f(*args, **kwargs)
    return decorated_function


# Test auth decorator that checks a header and aborts before validation
def require_auth_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != "Bearer valid-token":
            return {"error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    return decorated_function


class BookQuery(BaseModel):
    age: int | None = Field(None, description="Age")


class BookBody(BaseModel):
    title: str = Field(..., description="Book title")


# APIView with single decorator
api_view_single = APIView(url_prefix="/api/v1")


@api_view_single.route("/books")
class BookAPIViewSingleDecorator:
    decorators = [add_header_decorator]

    @api_view_single.doc(summary="get books")
    def get(self, query: BookQuery):
        return "books list"

    @api_view_single.doc(summary="create book")
    def post(self, body: BookBody):
        return f"created: {body.title}"


# APIView with multiple decorators (applied in order)
api_view_multiple = APIView(url_prefix="/api/v2")


@api_view_multiple.route("/books")
class BookAPIViewMultipleDecorators:
    # Decorators are applied in order: first decorator in list is outermost (runs first)
    # So add_header_decorator runs first, then modify_response_decorator, then view
    decorators = [add_header_decorator, modify_response_decorator]

    @api_view_multiple.doc(summary="get books")
    def get(self, query: BookQuery):
        return "books list"

    @api_view_multiple.doc(summary="create book")
    def post(self, body: BookBody):
        return f"created: {body.title}"


# APIView without decorators (to ensure it still works)
api_view_none = APIView(url_prefix="/api/v3")


@api_view_none.route("/books")
class BookAPIViewNoDecorators:
    @api_view_none.doc(summary="get books")
    def get(self, query: BookQuery):
        return "books list"


# APIView with counter decorator
api_view_counter = APIView(url_prefix="/api/v4")


@api_view_counter.route("/books")
class BookAPIViewCounterDecorator:
    decorators = [count_calls_decorator]

    @api_view_counter.doc(summary="get books")
    def get(self, query: BookQuery):
        return "books list"

    @api_view_counter.doc(summary="create book")
    def post(self, body: BookBody):
        return "created book"


# APIView with auth decorator to test decorator runs before validation
api_view_auth = APIView(url_prefix="/api/v5")


@api_view_auth.route("/protected")
class ProtectedAPIView:
    decorators = [require_auth_decorator]

    @api_view_auth.doc(summary="get protected resource")
    def get(self, query: BookQuery):
        return "protected data"

    @api_view_auth.doc(summary="create protected resource")
    def post(self, body: BookBody):
        return f"created protected: {body.title}"


# Register all API views
app.register_api_view(api_view_single)
app.register_api_view(api_view_multiple)
app.register_api_view(api_view_none)
app.register_api_view(api_view_counter)
app.register_api_view(api_view_auth)


@pytest.fixture
def client():
    return app.test_client()


def test_single_decorator_get(client):
    """Test that a single decorator is applied to GET method"""
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "DecoratorApplied"
    assert response.data.decode() == "books list"


def test_single_decorator_post(client):
    """Test that a single decorator is applied to POST method"""
    response = client.post("/api/v1/books", json={"title": "Test Book"})
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "DecoratorApplied"
    assert "created: Test Book" in response.data.decode()


def test_multiple_decorators_order(client):
    """Test that multiple decorators are applied in the correct order"""
    response = client.get("/api/v2/books")
    assert response.status_code == 200
    # Both decorators should be applied
    assert response.headers.get("X-Custom-Header") == "DecoratorApplied"
    # The modify_response_decorator is applied first (closest to the view function)
    assert response.data.decode() == "Modified: books list"


def test_multiple_decorators_post(client):
    """Test multiple decorators on POST method"""
    response = client.post("/api/v2/books", json={"title": "Test Book"})
    assert response.status_code == 200
    assert response.headers.get("X-Custom-Header") == "DecoratorApplied"
    assert response.data.decode() == "Modified: created: Test Book"


def test_no_decorators(client):
    """Test that views without decorators still work normally"""
    response = client.get("/api/v3/books")
    assert response.status_code == 200
    # No custom header should be present
    assert response.headers.get("X-Custom-Header") is None
    assert response.data.decode() == "books list"


def test_decorator_applied_to_all_methods(client):
    """Test that decorators are applied to all HTTP methods in the class"""
    # Reset counter
    call_counter["count"] = 0

    # Call GET
    response = client.get("/api/v4/books")
    assert response.status_code == 200
    assert call_counter["count"] == 1

    # Call POST
    response = client.post("/api/v4/books", json={"title": "Test Book"})
    assert response.status_code == 200
    assert call_counter["count"] == 2


def test_openapi_spec_generation(client):
    """Test that OpenAPI spec is still generated correctly with decorators"""
    response = client.get("/openapi/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    # Check that paths are registered
    assert "/api/v1/books" in spec["paths"]
    assert "/api/v2/books" in spec["paths"]
    assert "/api/v3/books" in spec["paths"]

    # Check that operations are documented
    assert "get" in spec["paths"]["/api/v1/books"]
    assert "post" in spec["paths"]["/api/v1/books"]
    assert spec["paths"]["/api/v1/books"]["get"]["summary"] == "get books"
    assert spec["paths"]["/api/v1/books"]["post"]["summary"] == "create book"


def test_auth_decorator_with_valid_token(client):
    """Test that request succeeds with valid auth token"""
    response = client.get(
        "/api/v5/protected",
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    assert response.data.decode() == "protected data"


def test_auth_decorator_runs_before_validation_get(client):
    """
    Test that auth decorator runs BEFORE validation.
    Send invalid query params (string instead of int for age).
    Should get 401 from auth decorator, not 422 from validation.
    """
    response = client.get(
        "/api/v5/protected?age=invalid",
        headers={"Authorization": "Bearer invalid-token"}
    )
    # Should get 401 from auth decorator, not 422 from validation error
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"


def test_auth_decorator_runs_before_validation_post(client):
    """
    Test that auth decorator runs BEFORE validation on POST.
    Send invalid body (missing required field).
    Should get 401 from auth decorator, not 422 from validation.
    """
    response = client.post(
        "/api/v5/protected",
        json={"invalid_field": "value"},  # Missing required 'title' field
        headers={"Authorization": "Bearer invalid-token"}
    )
    # Should get 401 from auth decorator, not 422 from validation error
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"


def test_auth_decorator_no_header_with_invalid_data(client):
    """
    Test auth decorator blocks request before validation when no auth header.
    Send completely invalid data to ensure validation would fail.
    Should get 401, not 422.
    """
    response = client.post(
        "/api/v5/protected",
        json={"completely": "wrong", "data": "structure"}
    )
    # Should get 401 from auth decorator, not 422 from validation error
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"


def test_auth_decorator_valid_auth_invalid_data(client):
    """
    Test that with valid auth, validation still occurs.
    This confirms decorators don't bypass validation when they should succeed.
    """
    response = client.post(
        "/api/v5/protected",
        json={"invalid_field": "value"},  # Missing required 'title' field
        headers={"Authorization": "Bearer valid-token"}
    )
    # Should get 422 from validation since auth passed
    assert response.status_code == 422


def test_auth_decorator_valid_auth_valid_data(client):
    """Test that with valid auth and valid data, request succeeds"""
    response = client.post(
        "/api/v5/protected",
        json={"title": "Protected Book"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    assert "created protected: Protected Book" in response.data.decode()
