"""Sphinx configuration for the Contacts REST API documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# Avoid importing settings from a real .env during doc builds.
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@localhost/db")

project = "Contacts REST API"
copyright = "2026"
author = "t-kolomiiets"
release = "3.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_mock_imports = ["redis", "cloudinary", "fastapi_mail", "libgravatar"]
