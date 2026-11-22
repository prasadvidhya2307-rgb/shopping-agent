"""Database helpers used by the Streamlit front-end.

Thin compatibility layer over ``database.py`` so the UI never duplicates SQL
or checkout logic.
"""

from typing import Any

import config
import database
import order_service
from reviews_api import get_ratings_for_products

SORT_MAP = {
    "Top rated": "rating",
    "Price: low to high": "price_asc",
    "Price: high to low": "price_desc",
    "Name A–Z": "name",
    "Newest first": "newest",
    "Most reviewed": "popular",
}


def get_all_products() -> list[dict]:
    return database.fetch_products({"sort": "name", "limit": 100})


def get_product(product_id: int) -> dict | None:
    return database.get_product(product_id)


def get_categories() -> list[tuple[str, int]]:
    return database.get_categories()


def get_brands() -> list[str]:
    return database.get_brands()


def get_price_bounds() -> tuple[float, float]:
    return database.get_price_bounds()


def catalog_overview() -> dict:
    """Real store metrics for the storefront dashboard."""
    return database.catalog_overview()


def search_suggestions(prefix: str = "", limit: int = 6) -> list[str]:
    """Real autocomplete suggestions from the product table."""
    return database.search_suggestions(prefix, limit)


def enrich_with_ratings(products: list[dict]) -> list[dict]:
    """Backwards-compatible helper; products already carry live ratings."""
    if not products:
        return products
    if all("rating" in product for product in products):
        return products
    ratings = get_ratings_for_products([p["id"] for p in products])
    rmap = {r["product_id"]: r for r in ratings}
    for product in products:
        info = rmap.get(product["id"], {})
        product["rating"] = info.get("average_rating", 0.0)
        product["review_count"] = info.get("review_count", 0)
    return products


def search_products_db(
    query: str = "",
    category: str = "All",
    max_price: float | None = None,
    min_price: float | None = None,
    organic: str = "All",
    sort: str = "Top rated",
    brand: str = "All",
    min_rating: float | None = None,
) -> list[dict]:
    is_organic: bool | None = None
    if organic == "Organic only":
        is_organic = True
    elif organic == "Non-organic":
        is_organic = False

    filters: dict[str, Any] = {
        "query": query,
        "category": category,
        "brand": brand,
        "min_price": min_price,
        "max_price": max_price,
        "min_rating": min_rating,
        "is_organic": is_organic,
        "sort": SORT_MAP.get(sort, "relevance"),
        "limit": 100,
    }
    return database.fetch_products(filters)


def get_orders(session_id: str | None = None) -> list[dict]:
    """Session-scoped order history. An empty session returns no orders."""
    return order_service.order_history(session_id or config.DEFAULT_SESSION_ID)


def place_order(
    product_id: int,
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """Explicitly confirmed checkout (used after the UI confirmation step)."""
    return order_service.checkout(
        product_id=product_id,
        confirmed=True,
        session_id=session_id,
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# Deterministic fallback used only when the AI engine is unavailable
# ---------------------------------------------------------------------------
_CATEGORY_HINTS = {
    "honey": "honey", "oil": "oil", "olive": "oil", "coconut": "oil",
    "almond": "nuts", "cashew": "nuts", "nut": "nuts", "seed": "seeds",
    "chia": "seeds", "quinoa": "grains", "oat": "grains", "rice": "grains",
    "grain": "grains", "tea": "tea", "coffee": "coffee",
    "granola": "snacks", "snack": "snacks", "mango": "snacks", "trail": "snacks",
    "milk": "dairy-alt", "cereal": "grains",
}
_STOP = {
    "i", "want", "to", "buy", "a", "an", "the", "some", "with", "and", "under",
    "below", "less", "than", "for", "me", "please", "show", "find", "give",
    "organic", "non-organic", "rated", "rating", "stars", "star", "price",
    "product", "products", "something", "looking", "am", "is", "it", "of",
    "at", "have", "that", "this", "about", "do", "you", "get", "buying",
    "best", "affordable", "cheap", "suggest", "recommend", "me", "under",
}


def local_search_response(text: str) -> str:
    """DB-backed reply when Groq/LangChain is unavailable."""
    import re

    t = (text or "").lower()
    price_match = re.search(r"(?:under|below|less than|up to|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)", t)
    max_price = float(price_match.group(1)) if price_match else None

    min_match = re.search(r"(?:over|above|at least|more than)\s*\$?\s*(\d+(?:\.\d+)?)", t)
    min_price = float(min_match.group(1)) if min_match else None

    rating_match = re.search(r"(\d(?:\.\d+)?)\s*\+?\s*(?:star|rating|rated)", t)
    min_rating = float(rating_match.group(1)) if rating_match else None

    if re.search(r"\bnon[-\s]?organic\b", t):
        organic = "Non-organic"
    elif "organic" in t:
        organic = "Organic only"
    else:
        organic = "All"

    category = "All"
    for key, cat in _CATEGORY_HINTS.items():
        if re.search(rf"\b{re.escape(key)}\w*\b", t):
            category = cat
            break

    query = ""
    if category == "All":
        tokens = [w for w in re.findall(r"[a-z]+", t) if w not in _STOP and len(w) > 2]
        query = tokens[0] if tokens else ""

    sort = "Top rated"
    if any(word in t for word in ("cheap", "affordable", "budget", "lowest")):
        sort = "Price: low to high"
    elif any(word in t for word in ("best", "highest", "top rated")):
        sort = "Top rated"

    products = search_products_db(
        query=query,
        category=category,
        max_price=max_price,
        min_price=min_price,
        min_rating=min_rating,
        organic=organic,
        sort=sort,
    )
    products = [p for p in products if p.get("availability") == "in_stock"]

    if not products:
        return (
            "I couldn't find any products matching those filters in the store. "
            "Try widening your price range or removing the organic/rating filter."
        )

    lines = ["Here are the best matches I found in our store:\n"]
    for index, product in enumerate(products[:6], 1):
        lines.append(
            f"#{index}. {product['name']} (ID:{product['id']}) — ${product['price']:.2f} "
            f"★{product['rating']:.2f} — {'organic' if product['is_organic'] else 'non-organic'}"
        )
    lines.append("\nWould you like to order one? Just say yes or give me the number.")
    return "\n".join(lines)
