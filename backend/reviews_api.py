"""Rating aggregation backed by the single SQLite access layer.

Public functions keep their original names and return shapes.
"""

from .database import get_connection
from .utils import valid_product_id


def get_product_rating(product_id: int) -> dict:
    """Return average rating and review count for a single product."""
    pid = valid_product_id(product_id)
    if pid is None:
        return {"product_id": product_id, "average_rating": 0.0, "review_count": 0}
    with get_connection() as conn:
        row = conn.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ?", (pid,)
        ).fetchone()
    avg = round(row[0], 2) if row and row[0] is not None else 0.0
    count = int(row[1]) if row else 0
    return {"product_id": pid, "average_rating": avg, "review_count": count}


def get_ratings_for_products(product_ids: list[int]) -> list[dict]:
    """Return ratings for a list of product IDs, preserving input order."""
    ids = [pid for pid in (valid_product_id(p) for p in product_ids) if pid is not None]
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT product_id, AVG(rating), COUNT(*) FROM reviews "
            f"WHERE product_id IN ({placeholders}) GROUP BY product_id",
            ids,
        ).fetchall()
    ratings_map = {
        int(r[0]): {"average_rating": round(r[1], 2), "review_count": int(r[2])}
        for r in rows
    }
    return [
        {
            "product_id": pid,
            "average_rating": ratings_map.get(pid, {}).get("average_rating", 0.0),
            "review_count": ratings_map.get(pid, {}).get("review_count", 0),
        }
        for pid in ids
    ]


def get_top_rated(limit: int = 5) -> list[dict]:
    """Return the highest-rated products using actual review data."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, AVG(r.rating) AS avg_rating, COUNT(r.id) AS cnt "
            "FROM products p JOIN reviews r ON r.product_id = p.id "
            "GROUP BY p.id ORDER BY avg_rating DESC, cnt DESC, p.name ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "product_id": int(r[0]),
            "name": r[1],
            "average_rating": round(r[2], 2),
            "review_count": int(r[3]),
        }
        for r in rows
    ]


if __name__ == "__main__":
    result = get_product_rating(1)
    print("Single product rating:", result)
    print("Batch ratings:", get_ratings_for_products([1, 3, 5, 7]))
