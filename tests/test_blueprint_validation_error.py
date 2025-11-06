# -*- coding: utf-8 -*-
# @Author  : claude
# @Time    : 2025/11/06
import pytest
from flask import current_app, make_response
from pydantic import BaseModel, Field, ValidationError

from flask_openapi3 import APIBlueprint, OpenAPI


class CustomErrorModel(BaseModel):
    error_type: str
    error_message: str


class RouteErrorModel(BaseModel):
    route_error: str
    details: str


class BookQuery(BaseModel):
    age: int = Field(..., description="Age must be an integer")


class BookBody(BaseModel):
    title: str = Field(..., description="Book title")
    pages: int = Field(..., description="Number of pages")


def app_validation_error_callback(e: ValidationError):
    """App-level validation error callback"""
    error_object = CustomErrorModel(
        error_type="app_level",
        error_message=str(e.errors()[0]["msg"])
    )
    response = make_response(error_object.model_dump_json())
    response.headers["Content-Type"] = "application/json"
    response.status_code = 400
    return response


def blueprint_validation_error_callback(e: ValidationError):
    """Blueprint-level validation error callback"""
    error_object = CustomErrorModel(
        error_type="blueprint_level",
        error_message=str(e.errors()[0]["msg"])
    )
    response = make_response(error_object.model_dump_json())
    response.headers["Content-Type"] = "application/json"
    response.status_code = 401
    return response


def route_validation_error_callback(e: ValidationError):
    """Route-level validation error callback"""
    error_object = RouteErrorModel(
        route_error="route_level",
        details=str(e.errors()[0]["msg"])
    )
    response = make_response(error_object.model_dump_json())
    response.headers["Content-Type"] = "application/json"
    response.status_code = 402
    return response


# Create app with app-level validation_error_callback
app = OpenAPI(
    __name__,
    validation_error_callback=app_validation_error_callback,
)
app.config["TESTING"] = True


# Create blueprint with blueprint-level validation_error_callback
api_blueprint = APIBlueprint(
    "book",
    __name__,
    url_prefix="/book",
    validation_error_callback=blueprint_validation_error_callback
)


# Create blueprint without validation_error_callback (should use app-level)
api_blueprint_no_callback = APIBlueprint(
    "author",
    __name__,
    url_prefix="/author"
)


# Route with blueprint-level callback (should use blueprint callback)
@api_blueprint.get("/query")
def book_query(query: BookQuery):
    return {"age": query.age}


# Route with route-level callback (should override blueprint callback)
@api_blueprint.post("/create", validation_error_callback=route_validation_error_callback)
def book_create(body: BookBody):
    return {"title": body.title}


# Route in blueprint without callback (should use app-level callback)
@api_blueprint_no_callback.get("/query")
def author_query(query: BookQuery):
    return {"age": query.age}


# Route with route-level callback in blueprint without callback (should use route callback)
@api_blueprint_no_callback.post("/create", validation_error_callback=route_validation_error_callback)
def author_create(body: BookBody):
    return {"title": body.title}


app.register_api(api_blueprint)
app.register_api(api_blueprint_no_callback)


@pytest.fixture
def client():
    return app.test_client()


def test_blueprint_level_callback(client):
    """Test that blueprint-level callback is used"""
    resp = client.get("/book/query?age=abc")
    assert resp.status_code == 401
    assert resp.json["error_type"] == "blueprint_level"


def test_route_level_callback_overrides_blueprint(client):
    """Test that route-level callback overrides blueprint-level callback"""
    resp = client.post("/book/create", json={"title": "Test", "pages": "invalid"})
    assert resp.status_code == 402
    assert resp.json["route_error"] == "route_level"


def test_app_level_callback_fallback(client):
    """Test that app-level callback is used when blueprint has no callback"""
    resp = client.get("/author/query?age=xyz")
    assert resp.status_code == 400
    assert resp.json["error_type"] == "app_level"


def test_route_level_callback_in_blueprint_without_callback(client):
    """Test that route-level callback works in blueprint without callback"""
    resp = client.post("/author/create", json={"title": "Test", "pages": "invalid"})
    assert resp.status_code == 402
    assert resp.json["route_error"] == "route_level"


def test_valid_request_blueprint(client):
    """Test that valid requests still work correctly"""
    resp = client.get("/book/query?age=25")
    assert resp.status_code == 200
    assert resp.json["age"] == 25


def test_valid_request_route(client):
    """Test that valid POST requests still work correctly"""
    resp = client.post("/book/create", json={"title": "Test Book", "pages": 100})
    assert resp.status_code == 200
    assert resp.json["title"] == "Test Book"
