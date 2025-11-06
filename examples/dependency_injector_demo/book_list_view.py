# -*- coding: utf-8 -*-
# BookListView module with its own blueprint

from dependency_injector.wiring import Provide, inject
from pydantic import BaseModel, Field

from flask_openapi3 import APIBlueprint, APIView, Tag

# Import the container for DI
from container import BookService, Container


# Define models
class BookQuery(BaseModel):
    search: str | None = Field(None, description="Search query")


class BookBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Book title")
    author: str = Field(..., min_length=1, max_length=100, description="Book author")
    year: int = Field(..., ge=1000, le=9999, description="Publication year")


# Create the blueprint and APIView for this module
book_list_bp = APIBlueprint("book_list_bp", __name__, url_prefix="/api")
api_view = APIView(url_prefix="/v1", view_tags=[Tag(name="books")])


@api_view.route("/books")
class BookListView:
    @inject
    def __init__(self, book_service: BookService = Provide[Container.book_service]):
        self.book_service = book_service

    @api_view.doc(summary="Get all books")
    def get(self, query: BookQuery):
        """Get a list of all books, optionally filtered by search query"""
        return self.book_service.list_books(query.search)

    @api_view.doc(summary="Create a new book")
    def post(self, body: BookBody):
        """Create a new book"""
        return self.book_service.create_book(body.model_dump())


# Register the APIView with this module's blueprint
book_list_bp.register_api_view(api_view)
