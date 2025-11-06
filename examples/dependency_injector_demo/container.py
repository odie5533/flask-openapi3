# -*- coding: utf-8 -*-
# Dependency injection container module

from dependency_injector import containers, providers


class BookRepository:
    """Simulates a database repository for books"""

    def __init__(self, max_books: int = 100):
        self.max_books = max_books
        self.books = {
            1: {"id": 1, "title": "Sample Book", "author": "John Doe", "year": 2023},
            2: {"id": 2, "title": "Another Book", "author": "Jane Smith", "year": 2022},
        }
        self.next_id = 3

    def get_all(self):
        return list(self.books.values())

    def search(self, query: str):
        return [book for book in self.books.values() if query.lower() in book["title"].lower() or query.lower() in book["author"].lower()]

    def create(self, book_data: dict):
        if len(self.books) >= self.max_books:
            raise ValueError(f"Maximum number of books ({self.max_books}) reached")
        book = {"id": self.next_id, **book_data}
        self.books[self.next_id] = book
        self.next_id += 1
        return book


class BookService:
    """Business logic layer for book operations"""

    def __init__(self, repository: BookRepository):
        self.repository = repository

    def list_books(self, search_query: str | None = None):
        if search_query:
            books = self.repository.search(search_query)
            return {"message": f"Searching for: {search_query}", "books": books}
        return {"books": self.repository.get_all()}

    def create_book(self, book_data: dict):
        try:
            book = self.repository.create(book_data)
            return {"message": "Book created", "book": book}
        except ValueError as e:
            return {"error": str(e)}, 400


class Container(containers.DeclarativeContainer):
    """Dependency injection container"""

    # Configuration provider - can be set from environment, dict, yaml, etc.
    config = providers.Configuration()

    # Singleton repository (shared across requests)
    # Injects max_books from config (uses default in __init__ if not provided)
    book_repository = providers.Singleton(
        BookRepository,
        max_books=config.repository.max_books.as_int(),
    )

    # Factory for book service (creates new instance for each injection)
    book_service = providers.Factory(BookService, repository=book_repository)
