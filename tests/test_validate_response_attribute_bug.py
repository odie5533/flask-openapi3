# -*- coding: utf-8 -*-
"""
Test case for issue #246: AttributeError: 'function' object has no attribute 'validate_response'

This test demonstrates the bug that occurs when a view method doesn't use the @doc() decorator,
causing an AttributeError when trying to access func.validate_response during registration.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError

from flask_openapi3 import APIView, Info, OpenAPI


class GoodResponse(BaseModel):
    """Response with correct schema"""

    status: str


class BadResponse(BaseModel):
    """Response schema that doesn't match what we return"""

    status: int  # We return str, but schema expects int


def test_view_with_mixed_decorators():
    """
    Test that a view class with both decorated and non-decorated methods works correctly.
    """
    info = Info(title="test API", version="1.0.0")
    app = OpenAPI(__name__, info=info)
    app.config["TESTING"] = True

    api_view = APIView(validate_response=False)

    class BookBody(BaseModel):
        title: str = Field(..., description="Book title")

    @api_view.route("/books")
    class BooksAPIView:
        # Method with @doc() decorator - has validate_response attribute
        @api_view.doc(summary="Create book", validate_response=True)
        def post(self, body: BookBody):
            return {"title": body.title}

        # Method without @doc() decorator - doesn't have validate_response attribute
        def get(self):
            return {"books": []}

    # Should not raise AttributeError
    app.register_api_view(api_view)

    client = app.test_client()

    # Test GET (no decorator)
    resp = client.get("/books")
    assert resp.status_code == 200

    # Test POST (with decorator)
    resp = client.post("/books", json={"title": "Test Book"})
    assert resp.status_code == 200


def test_view_validate_response_fallback():
    """
    Test that validate_response falls back correctly from function to APIView instance.
    This test verifies that:
    1. Methods without @doc() decorator use APIView's validate_response setting
    2. Methods with @doc() but no validate_response param use APIView's setting
    3. Methods with explicit validate_response=False override APIView's setting
    """
    info = Info(title="test API", version="1.0.0")
    app = OpenAPI(__name__, info=info)
    app.config["TESTING"] = True

    # APIView with validate_response=True
    api_view = APIView(validate_response=True)

    @api_view.route("/test")
    class TestAPIView:
        # No decorator, should use APIView's validate_response=True
        # This should trigger validation and raise error
        def get(self):
            return {"status": "ok"}

        # With decorator but validate_response=None, should use APIView's validate_response=True
        # This should trigger validation and raise error
        @api_view.doc(summary="Post test", responses={200: BadResponse})
        def post(self):
            return {"status": "ok"}

        # With decorator and validate_response=False, should use False
        # This should NOT trigger validation (no error)
        @api_view.doc(summary="Put test", responses={200: BadResponse}, validate_response=False)
        def put(self):
            return {"status": "ok"}

        # With decorator and validate_response=True and correct schema
        # This should trigger validation and pass
        @api_view.doc(summary="Patch test", responses={200: GoodResponse}, validate_response=True)
        def patch(self):
            return {"status": "ok"}

    # Should not raise AttributeError during registration
    app.register_api_view(api_view)

    client = app.test_client()

    # GET: no decorator, inherits APIView validate_response=True, but no response schema defined
    # Should work fine (no validation when no response schema)
    resp = client.get("/test")
    assert resp.status_code == 200

    # POST: has decorator, validate_response=None (inherits True), bad response schema
    # Should raise ValidationError because response doesn't match schema
    with pytest.raises(ValidationError):
        client.post("/test")

    # PUT: has decorator, validate_response=False, bad response schema
    # Should NOT raise error because validation is disabled
    resp = client.put("/test")
    assert resp.status_code == 200

    # PATCH: has decorator, validate_response=True, good response schema
    # Should work fine because response matches schema
    resp = client.patch("/test")
    assert resp.status_code == 200
