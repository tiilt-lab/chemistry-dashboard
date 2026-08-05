"""
Study Context — Per-participant database and ChromaDB isolation.

When a study participant (P01–P15) is logged in, Flask's `g` object holds
their isolated database name and ChromaDB path, set by the `before_request`
hook in app.py.  Every raw MySQL connection and RAGService instantiation
reads from here so the application code needs zero conditional logic.

Outside a Flask request context (e.g., background threads, CLI scripts),
the helpers fall back to the production defaults.
"""
import mysql.connector


def get_db_name():
    """Return current database name — study_P01 in study mode, discussion_capture otherwise."""
    try:
        from flask import g
        return getattr(g, 'study_db', 'discussion_capture')
    except RuntimeError:
        return 'discussion_capture'


def get_chroma_path():
    """Return current ChromaDB persist directory."""
    try:
        from flask import g
        return getattr(g, 'chroma_path', './chroma_db')
    except RuntimeError:
        return './chroma_db'


def get_study_user_id():
    """Return current study user ID (e.g., 'P01') or None if not in study mode."""
    try:
        from flask import g
        return getattr(g, 'study_user_id', None)
    except RuntimeError:
        return None


def get_db_connection():
    """Create a MySQL connection to the current database (study or production)."""
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database=get_db_name()
    )
