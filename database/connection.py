"""Conexión centralizada con la base de datos SQLite."""

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_ROOT / "data"
DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIRECTORY / "restaurant_manager_v2.db"


def get_connection():
    """Abre una conexión SQLite y activa las claves foráneas."""
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
