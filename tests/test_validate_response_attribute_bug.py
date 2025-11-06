# -*- coding: utf-8 -*-
"""
Test case for issue #246: AttributeError: 'function' object has no attribute 'validate_response'

This test demonstrates the bug that occurs when a view method doesn't use the @doc() decorator,
causing an AttributeError when trying to access func.validate_response during registration.
"""

import pytest
from pydantic import BaseModel, Field

from flask_openapi3 import APIView, Info, OpenAPI


def test_view_without_doc_decorator():
    """
    Test that a view method without @doc() decorator doesn't cause AttributeError.

    This reproduces the bug reported in issue #246 where upgrading from 4.2.x to 4.3
    causes AttributeError when a function doesn't have the validate_response attribute.
    """
    info = Info(title="test API", version="1.0.0")
    app = OpenAPI(__name__, info=info)
    app.config["TESTING"] = True

    # Create APIView with validate_response enabled
    api_view = APIView(validate_response=True)

    class BookPath(BaseModel):
        id: int = Field(..., description="book ID")

    @api_view.route("/book/<id>")
    class BookAPIView:
        # This method does NOT use @api_view.doc() decorator
        # In version 4.3, this causes: AttributeError: 'function' object has no attribute 'validate_response'
        def get(self, path: BookPath):
            return {"id": path.id}

    # This should not raise AttributeError
    # Before the fix, this would fail with:
    # AttributeError: 'function' object has no attribute 'validate_response'
    app.register_api_view(api_view)

    # Verify the endpoint works
    client = app.test_client()
    resp = client.get("/book/123")
    assert resp.status_code == 200


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
    """
    info = Info(title="test API", version="1.0.0")
    app = OpenAPI(__name__, info=info)
    app.config["TESTING"] = True

    # APIView with validate_response=True
    api_view = APIView(validate_response=True)

    @api_view.route("/test")
    class TestAPIView:
        # No decorator, should use APIView's validate_response=True
        def get(self):
            return {"status": "ok"}

        # With decorator but validate_response=None, should use APIView's validate_response=True
        @api_view.doc(summary="Post test")
        def post(self):
            return {"status": "ok"}

        # With decorator and validate_response=False, should use False
        @api_view.doc(summary="Put test", validate_response=False)
        def put(self):
            return {"status": "ok"}

    # Should not raise AttributeError
    app.register_api_view(api_view)

    client = app.test_client()
    assert client.get("/test").status_code == 200
    assert client.post("/test").status_code == 200
    assert client.put("/test").status_code == 200
