import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import config, database  # noqa: E402


LEGACY_SCHEMA = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price REAL,
    description TEXT,
    is_organic INTEGER DEFAULT 0
);
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    rating REAL,
    reviewer_name TEXT,
    review_text TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    ordered_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


@pytest.fixture
def legacy_db(tmp_path, monkeypatch):
    """A pre-migration database with real-looking rows to prove safety."""
    target = tmp_path / "store.db"
    conn = sqlite3.connect(target)
    conn.executescript(LEGACY_SCHEMA)
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "Organic Raw Honey", "honey", 14.99, "Pure raw honey", 1),
            (2, "Wildflower Honey", "honey", 9.99, "Local wildflower honey", 0),
            (3, "Clover Honey", "honey", 7.99, "Classic clover honey", 0),
        ],
    )
    conn.executemany(
        "INSERT INTO reviews (product_id, rating, reviewer_name, review_text) VALUES (?, ?, ?, ?)",
        [
            (1, 5.0, "A", "great"),
            (1, 4.0, "B", "good"),
            (3, 3.0, "C", "ok"),
        ],
    )
    conn.execute(
        "INSERT INTO orders (product_id, product_name, price, ordered_at) "
        "VALUES (1, 'Organic Raw Honey', 14.99, '2026-01-01 10:00:00')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", target)
    database._initialized = False
    yield target
    database._initialized = False
