# -*- coding: utf-8 -*-
# Test class-level decorators for APIView

import pytest
from pydantic import BaseModel, Field

from flask_openapi3 import APIView, Info, OpenAPI

# Import shared test decorators
from shared_decorators import (
    add_header_decorator,
    call_counter,
    count_calls_decorator,
    inject_user_decorator,
    modify_response_decorator,
    require_admin_decorator,
    require_auth_decorator,
)


info = Info(title="Decorator Test API", version="1.0.0")
app = OpenAPI(__name__, info=info)
app.config["TESTING"] = True


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


# APIView with method-level decorators only
api_view_method = APIView(url_prefix="/api/v6")


@api_view_method.route("/items")
class ItemAPIViewMethodDecorators:
    @api_view_method.doc(summary="get items - no auth required")
    def get(self, query: BookQuery):
        return "public items list"

    @api_view_method.doc(summary="create item - auth required", decorators=[require_auth_decorator])
    def post(self, body: BookBody):
        return f"created item: {body.title}"

    @api_view_method.doc(summary="delete item - admin required", decorators=[require_admin_decorator])
    def delete(self, query: BookQuery):
        return "item deleted"


# APIView with both class and method decorators to test order
api_view_mixed = APIView(url_prefix="/api/v7")


@api_view_mixed.route("/users")
class UserAPIViewMixedDecorators:
    # Class-level auth required for all methods
    decorators = [require_auth_decorator]

    @api_view_mixed.doc(summary="get user")
    def get(self, query: BookQuery):
        return "user data"

    @api_view_mixed.doc(summary="delete user - requires both auth and admin", decorators=[require_admin_decorator])
    def delete(self, query: BookQuery):
        return "user deleted"


# APIView to test method decorator runs before validation
api_view_method_validation = APIView(url_prefix="/api/v8")


@api_view_method_validation.route("/secure")
class SecureAPIViewMethodValidation:
    @api_view_method_validation.doc(summary="secure endpoint", decorators=[require_auth_decorator])
    def post(self, body: BookBody):
        return f"secure: {body.title}"


# APIView to test decorator argument injection
api_view_inject = APIView(url_prefix="/api/v9")


@api_view_inject.route("/profile")
class ProfileAPIViewWithInjection:
    @api_view_inject.doc(summary="get user profile", decorators=[inject_user_decorator])
    def get(self, query: BookQuery, user=None):
        """View receives user object injected by decorator"""
        return {"message": f"Profile for {user['name']}", "user_id": user["id"], "role": user["role"]}

    @api_view_inject.doc(summary="update profile", decorators=[inject_user_decorator])
    def post(self, body: BookBody, user=None):
        """View receives both body and injected user"""
        return {
            "message": f"Updated {body.title} for user {user['name']}",
            "user_id": user["id"]
        }


# Register all API views
app.register_api_view(api_view_single)
app.register_api_view(api_view_multiple)
app.register_api_view(api_view_none)
app.register_api_view(api_view_counter)
app.register_api_view(api_view_auth)
app.register_api_view(api_view_method)
app.register_api_view(api_view_mixed)
app.register_api_view(api_view_method_validation)
app.register_api_view(api_view_inject)


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


# Tests for method-level decorators


def test_method_decorators_selective(client):
    """Test that method decorators can be applied selectively to different HTTP methods"""
    # GET has no decorator - should work without auth
    response = client.get("/api/v6/items")
    assert response.status_code == 200
    assert response.data.decode() == "public items list"

    # POST has auth decorator - should fail without auth
    response = client.post("/api/v6/items", json={"title": "Test"})
    assert response.status_code == 401

    # POST with auth should succeed
    response = client.post(
        "/api/v6/items",
        json={"title": "Test"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200

    # DELETE has different decorator (admin) - should fail without admin
    response = client.delete("/api/v6/items")
    assert response.status_code == 403

    # DELETE with admin should succeed
    response = client.delete("/api/v6/items", headers={"X-Admin": "admin-secret"})
    assert response.status_code == 200


def test_method_decorator_runs_before_validation(client):
    """Test that method-level decorators run BEFORE validation"""
    # Send invalid data without auth - should get 401, not 422
    response = client.post("/api/v8/secure", json={"invalid": "data"})
    assert response.status_code == 401

    # With valid auth, validation should occur - should get 422
    response = client.post(
        "/api/v8/secure",
        json={"invalid": "data"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 422


# Tests for mixed class and method decorators


def test_mixed_decorators_layered_auth(client):
    """Test that class and method decorators layer correctly (both required)"""
    # GET has only class-level auth
    response = client.get("/api/v7/users")
    assert response.status_code == 401  # No auth

    response = client.get("/api/v7/users", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200  # Auth sufficient

    # DELETE has both class auth AND method admin
    response = client.delete("/api/v7/users")
    assert response.status_code == 401  # No auth

    response = client.delete("/api/v7/users", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 403  # Has auth but missing admin

    response = client.delete("/api/v7/users", headers={"X-Admin": "admin-secret"})
    assert response.status_code == 401  # Has admin but missing auth (class decorator runs first)

    response = client.delete(
        "/api/v7/users",
        headers={"Authorization": "Bearer valid-token", "X-Admin": "admin-secret"}
    )
    assert response.status_code == 200  # Both auth and admin - success


def test_mixed_decorators_run_before_validation(client):
    """Test that mixed decorators run before validation"""
    # Invalid data, no auth - should fail at class auth, not validation
    response = client.delete("/api/v7/users?age=invalid")
    assert response.status_code == 401


# Tests for decorator argument injection


def test_decorator_injects_user_into_get(client):
    """Test that decorator can inject user object into GET method"""
    response = client.get(
        "/api/v9/profile",
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Profile for Test User"
    assert data["user_id"] == 123
    assert data["role"] == "admin"


def test_decorator_injects_user_into_post(client):
    """Test that decorator can inject user object into POST with body params"""
    response = client.post(
        "/api/v9/profile",
        json={"title": "New Title"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Updated New Title for user Test User"
    assert data["user_id"] == 123


def test_decorator_injection_fails_without_auth(client):
    """Test that injecting decorator still enforces auth"""
    response = client.get("/api/v9/profile")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"


def test_decorator_injection_runs_before_validation(client):
    """Test that injecting decorator runs before validation"""
    # Send invalid query param without auth
    response = client.get("/api/v9/profile?age=invalid")
    assert response.status_code == 401  # Auth fails before validation
