"""Single source of truth for SQLite access.

All schema changes are additive and idempotent: existing products, reviews and
orders are preserved exactly as they are. New tables/columns are introduced
through safe migrations executed on first use.
"""

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

import config
from utils import dedupe_products, valid_price

_initialized = False

PRODUCT_COLUMNS = (
    "p.id, p.name, p.category, p.price, p.description, p.is_organic, "
    "p.brand, p.availability, p.image_path, "
    "COALESCE(r.avg_rating, 0) AS rating, COALESCE(r.cnt, 0) AS review_count"
)

PRODUCT_FROM = (
    "FROM products p "
    "LEFT JOIN (SELECT product_id, AVG(rating) AS avg_rating, COUNT(*) AS cnt "
    "           FROM reviews GROUP BY product_id) r ON r.product_id = p.id"
)


def db_path() -> str:
    return str(config.DB_PATH)


def _raw_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Transactional connection with automatic commit/rollback and cleanup."""
    initialize_database()
    conn = _raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def initialize_database() -> None:
    """Create missing schema objects and backfill new columns. Safe to rerun."""
    global _initialized
    if _initialized:
        return

    conn = _raw_connection()
    try:
        # Product enrichments.
        _ensure_columns(
            conn,
            "products",
            {
                "brand": "TEXT",
                "availability": "TEXT DEFAULT 'in_stock'",
                "image_path": "TEXT",
                "rating": "REAL DEFAULT 0",
                "review_count": "INTEGER DEFAULT 0",
            },
        )
        # Order ownership, totals and idempotency.
        _ensure_columns(
            conn,
            "orders",
            {
                "session_id": "TEXT",
                "status": "TEXT DEFAULT 'confirmed'",
                "total_amount": "REAL",
                "quantity": "INTEGER DEFAULT 1",
                "idempotency_key": "TEXT",
            },
        )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                purchase_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                client_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE (conversation_id, client_id)
            );

            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
            CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
            CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
            CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency
                ON orders(idempotency_key) WHERE idempotency_key IS NOT NULL;
            """
        )

        # Backfill only missing values; never overwrite existing data.
        conn.execute(
            "UPDATE products SET availability = 'in_stock' "
            "WHERE availability IS NULL OR TRIM(availability) = ''"
        )
        conn.execute(
            "UPDATE products SET "
            "rating = COALESCE((SELECT AVG(r.rating) FROM reviews r "
            "                   WHERE r.product_id = products.id), 0), "
            "review_count = (SELECT COUNT(*) FROM reviews r "
            "                WHERE r.product_id = products.id) "
            "WHERE rating IS NULL OR review_count IS NULL"
        )
        for filename, needle in (("resources/honey.png", "%honey%"), ("resources/oats.png", "%oat%")):
            conn.execute(
                "UPDATE products SET image_path = ? "
                "WHERE image_path IS NULL AND LOWER(name) LIKE ?",
                (filename, needle),
            )
        conn.execute("UPDATE orders SET status = 'confirmed' WHERE status IS NULL")
        conn.execute("UPDATE orders SET total_amount = price WHERE total_amount IS NULL")
        conn.execute(
            "UPDATE orders SET quantity = 1 WHERE quantity IS NULL OR quantity < 1"
        )
        conn.execute("UPDATE orders SET session_id = 'legacy' WHERE session_id IS NULL")

        conn.commit()
    finally:
        conn.close()

    _initialized = True


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------
def product_from_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"] or "",
        "category": row["category"] or "",
        "price": float(row["price"] or 0),
        "description": row["description"] or "",
        "is_organic": bool(row["is_organic"]),
        "brand": row["brand"] or "",
        "availability": row["availability"] or "in_stock",
        "image_path": row["image_path"] or "",
        "rating": round(float(row["rating"] or 0), 2),
        "review_count": int(row["review_count"] or 0),
    }


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def get_product(product_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {PRODUCT_COLUMNS} {PRODUCT_FROM} WHERE p.id = ?", (product_id,)
        ).fetchone()
    return product_from_row(row)


def get_product_by_name(name: str) -> dict | None:
    if not name:
        return None
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {PRODUCT_COLUMNS} {PRODUCT_FROM} "
            "WHERE LOWER(p.name) LIKE ? ORDER BY rating DESC LIMIT 1",
            (f"%{name.lower()}%",),
        ).fetchone()
    return product_from_row(row)


def fetch_products(filters: dict[str, Any] | None = None) -> list[dict]:
    """Parameterized product search with combined filters and safe sorting."""
    filters = filters or {}
    where: list[str] = []
    params: list[Any] = []

    query = (filters.get("query") or "").strip()
    if query:
        where.append(
            "(p.name LIKE ? OR p.description LIKE ? OR p.category LIKE ? OR p.brand LIKE ?)"
        )
        like = f"%{query}%"
        params.extend([like, like, like, like])

    category = filters.get("category")
    if category and str(category).lower() != "all":
        where.append("LOWER(p.category) = LOWER(?)")
        params.append(str(category))

    brand = filters.get("brand")
    if brand and str(brand).lower() != "all":
        where.append("LOWER(p.brand) LIKE ?")
        params.append(f"%{str(brand).lower()}%")

    min_price = valid_price(filters.get("min_price"))
    max_price = valid_price(filters.get("max_price"))
    if min_price is not None:
        where.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("p.price <= ?")
        params.append(max_price)

    min_rating = valid_price(filters.get("min_rating"))
    if min_rating is not None:
        where.append("COALESCE(r.avg_rating, 0) >= ?")
        params.append(min_rating)

    is_organic = filters.get("is_organic")
    if is_organic is not None:
        where.append("p.is_organic = ?")
        params.append(1 if bool(is_organic) else 0)

    availability = filters.get("availability")
    if availability:
        where.append("p.availability = ?")
        params.append(str(availability))

    sql = f"SELECT {PRODUCT_COLUMNS} {PRODUCT_FROM}"
    if where:
        sql += " WHERE " + " AND ".join(where)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    products = [product_from_row(row) for row in rows]
    products = dedupe_products(p for p in products if p is not None)

    sort = str(filters.get("sort") or "relevance")
    if sort == "price_asc":
        products.sort(key=lambda p: (p["price"], p["name"]))
    elif sort == "price_desc":
        products.sort(key=lambda p: (-p["price"], p["name"]))
    elif sort == "name":
        products.sort(key=lambda p: p["name"])
    elif sort == "rating":
        products.sort(key=lambda p: (-p["rating"], -p["review_count"], p["name"]))
    elif sort == "popular":
        products.sort(key=lambda p: (-p["review_count"], -p["rating"], p["name"]))
    elif sort == "newest":
        products.sort(key=lambda p: -p["id"])
    elif query:
        terms = {t for t in query.lower().split() if len(t) > 1}
        def relevance(product: dict) -> tuple[int, int, float, str]:
            haystack = " ".join(
                str(product.get(k, "")).lower()
                for k in ("name", "category", "description", "brand")
            )
            score = sum(1 for term in terms if term in haystack)
            return (-score, -product["rating"], -product["review_count"], product["name"])
        products.sort(key=relevance)

    limit = filters.get("limit")
    if limit:
        try:
            products = products[: max(1, min(int(limit), 100))]
        except (TypeError, ValueError):
            pass
    return products


def get_categories() -> list[tuple[str, int]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) FROM products "
            "GROUP BY category ORDER BY COUNT(*) DESC, category"
        ).fetchall()
    return [(row[0] or "", int(row[1])) for row in rows]


def get_brands() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND TRIM(brand) <> '' "
            "ORDER BY brand"
        ).fetchall()
    return [row[0] for row in rows]


def get_price_bounds() -> tuple[float, float]:
    with get_connection() as conn:
        row = conn.execute("SELECT MIN(price), MAX(price) FROM products").fetchone()
    return (float(row[0] or 0), float(row[1] or 100))


def catalog_overview() -> dict[str, Any]:
    """Real catalogue metrics used by the storefront stat ribbon.

    Every number comes from SQLite — nothing is hard-coded in the UI.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(*),
              COUNT(DISTINCT category),
              SUM(is_organic),
              MIN(price),
              MAX(price),
              (SELECT COUNT(*) FROM reviews),
              (SELECT ROUND(AVG(rating), 2) FROM reviews)
            FROM products
            """
        ).fetchone()
    return {
        "products": int(row[0] or 0),
        "categories": int(row[1] or 0),
        "organic": int(row[2] or 0),
        "min_price": round(float(row[3] or 0), 2),
        "max_price": round(float(row[4] or 0), 2),
        "reviews": int(row[5] or 0),
        "average_rating": round(float(row[6] or 0), 2),
    }


def search_suggestions(prefix: str = "", limit: int = 6) -> list[str]:
    """Return real product names/categories for search autocomplete.

    Parameterized LIKE query; returns unique, deterministic suggestions.
    """
    term = (prefix or "").strip().lower()
    with get_connection() as conn:
        if term:
            rows = conn.execute(
                """
                SELECT DISTINCT value FROM (
                    SELECT name AS value FROM products WHERE LOWER(name) LIKE ?
                    UNION ALL
                    SELECT category AS value FROM products WHERE LOWER(category) LIKE ?
                ) ORDER BY value LIMIT ?
                """,
                (f"%{term}%", f"%{term}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name FROM products ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
    return [str(row[0]) for row in rows if row[0]]


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def find_order_by_idempotency_key(key: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE idempotency_key = ?", (key,)).fetchone()
    return dict(row) if row else None


def insert_order(
    *,
    product_id: int,
    session_id: str,
    quantity: int = 1,
    idempotency_key: str | None = None,
) -> dict:
    """Create an order + order item in one transaction using DB-fetched data."""
    with get_connection() as conn:
        product = product_from_row(
            conn.execute(f"SELECT {PRODUCT_COLUMNS} {PRODUCT_FROM} WHERE p.id = ?", (product_id,)).fetchone()
        )
        if product is None:
            raise LookupError(f"Product with ID {product_id} was not found.")
        if product["availability"] in ("out_of_stock", "discontinued"):
            raise ValueError(f"'{product['name']}' is currently unavailable.")

        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM orders WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if existing:
                return dict(existing)

        total = round(product["price"] * quantity, 2)
        cursor = conn.execute(
            "INSERT INTO orders (product_id, product_name, price, session_id, status, "
            "total_amount, quantity, idempotency_key) VALUES (?, ?, ?, ?, 'confirmed', ?, ?, ?)",
            (
                product_id,
                product["name"],
                product["price"],
                session_id,
                total,
                quantity,
                idempotency_key,
            ),
        )
        order_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, purchase_price) "
            "VALUES (?, ?, ?, ?)",
            (order_id, product_id, quantity, product["price"]),
        )
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return dict(order)


def fetch_orders(session_id: str | None = None) -> list[dict]:
    """Return orders for one session only. Never returns all sessions."""
    if not session_id:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT o.*, p.category, p.is_organic, p.image_path, p.availability "
            "FROM orders o LEFT JOIN products p ON p.id = o.product_id "
            "WHERE o.session_id = ? ORDER BY o.id DESC",
            (session_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "product_id": row["product_id"],
            "name": row["product_name"],
            "price": float(row["price"]),
            "quantity": int(row["quantity"] or 1),
            "total_amount": float(row["total_amount"] or row["price"]),
            "ordered_at": row["ordered_at"],
            "status": row["status"] or "confirmed",
            "session_id": row["session_id"],
            "category": row["category"] or "",
            "is_organic": bool(row["is_organic"]),
            "image_path": row["image_path"] or "",
        }
        for row in rows
    ]
