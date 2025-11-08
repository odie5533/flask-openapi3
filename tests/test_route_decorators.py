# -*- coding: utf-8 -*-
# Test decorators on regular (non-APIView) routes

import pytest
from pydantic import BaseModel, Field

from flask_openapi3 import Info, OpenAPI

# Import shared test decorators
from shared_decorators import inject_user_decorator, require_auth_decorator


info = Info(title="Regular Route Decorator Test", version="1.0.0")
app = OpenAPI(__name__, info=info)
app.config["TESTING"] = True


class BookQuery(BaseModel):
    age: int | None = Field(None, description="Age")


class BookBody(BaseModel):
    title: str = Field(..., description="Book title")


# Regular route with decorator
@app.get("/books", summary="Get books", decorators=[require_auth_decorator])
def get_books(query: BookQuery):
    return {"books": ["Book 1", "Book 2"]}


# Regular route with user injection
@app.post("/books", summary="Create book", decorators=[inject_user_decorator])
def create_book(body: BookBody, user=None):
    return {"title": body.title, "created_by": user["name"], "user_id": user["id"]}


# Regular route without decorator
@app.get("/public", summary="Public endpoint")
def get_public():
    return {"message": "public data"}


# Regular route with multiple decorators - not using this pattern anymore but kept for reference
# We'll just test single decorator for now


@pytest.fixture
def client():
    return app.test_client()


def test_regular_route_with_auth_decorator(client):
    """Test that decorator on regular route requires auth"""
    # Without auth should fail
    response = client.get("/books")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Unauthorized"

    # With auth should succeed
    response = client.get("/books", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    data = response.get_json()
    assert "books" in data


def test_regular_route_decorator_runs_before_validation(client):
    """Test that decorator runs BEFORE validation on regular routes"""
    # Send invalid query param without auth - should get 401 not 422
    response = client.get("/books?age=invalid")
    assert response.status_code == 401

    # With valid auth, validation should occur - should get 422
    response = client.get("/books?age=invalid", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 422


def test_regular_route_with_user_injection(client):
    """Test that decorator can inject user object on regular routes"""
    response = client.post(
        "/books",
        json={"title": "New Book"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "New Book"
    assert data["created_by"] == "Test User"
    assert data["user_id"] == 123


def test_regular_route_injection_runs_before_validation(client):
    """Test that injecting decorator runs before validation on regular routes"""
    # Send invalid body without auth
    response = client.post("/books", json={"invalid": "data"})
    assert response.status_code == 401

    # With auth, validation should occur
    response = client.post(
        "/books",
        json={"invalid": "data"},
        headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 422


def test_regular_route_without_decorator(client):
    """Test that routes without decorators still work normally"""
    response = client.get("/public")
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "public data"


def test_openapi_spec_includes_decorated_routes(client):
    """Test that OpenAPI spec includes decorated routes"""
    response = client.get("/openapi/openapi.json")
    assert response.status_code == 200
    spec = response.get_json()

    # Check paths are registered
    assert "/books" in spec["paths"]
    assert "/public" in spec["paths"]

    # Check operations are documented
    assert "get" in spec["paths"]["/books"]
    assert "post" in spec["paths"]["/books"]
    assert spec["paths"]["/books"]["get"]["summary"] == "Get books"
    assert spec["paths"]["/books"]["post"]["summary"] == "Create book"
