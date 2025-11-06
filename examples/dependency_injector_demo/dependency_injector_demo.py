# -*- coding: utf-8 -*-
# Example demonstrating how to use dependency-injector with Flask-OpenAPI3
# Modular architecture with separate blueprint modules

from flask_openapi3 import Info, OpenAPI

# Import the container
from container import Container

# Import the book list view module and its blueprint
import book_list_view
from book_list_view import book_list_bp


# Initialize container
container = Container()

# Configure the container (can also load from environment, yaml, etc.)
container.config.from_dict({
    "repository": {
        "max_books": 10  # Limit for demo purposes
    }
})

# Wire the container to enable dependency injection
# IMPORTANT: Must happen after all view classes are imported or defined
container.wire(modules=[book_list_view])

# Initialize the OpenAPI app
info = Info(title="Dependency Injection Demo with Flask-OpenAPI3", version="1.0.0")
app = OpenAPI(__name__, info=info)

# Register the blueprint
app.register_api(book_list_bp)

if __name__ == "__main__":
    print("Visit http://127.0.0.1:5000/openapi for API documentation")
    app.run(debug=True)
