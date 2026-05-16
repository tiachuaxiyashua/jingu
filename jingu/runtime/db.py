"""Database initialization and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from jingu.runtime.paths import RuntimePaths
from jingu.runtime.schema import SCHEMA_SQL


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(paths: RuntimePaths) -> None:
    paths.initialize()
    with connect(paths.database_path) as connection:
        connection.executescript(SCHEMA_SQL)
