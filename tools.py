"""Backend tools exposed to the LangChain agent.

The four original tool names are preserved. They now delegate to dedicated
service modules so database access, ordering and image logic are no longer
mixed into the agent definition.
"""

import base64
from typing import Any, Optional

import config
import database
import image_search
import order_service
import reviews_api
from utils import as_json, safe_error, valid_positive_int, valid_product_id

try:  # Real LangChain tool decorator when available
    from langchain.tools import tool
except ImportError:  # Keeps the backend importable/testable without LangChain

    def tool(func):  # type: ignore[misc]
        class _CallableTool:
            name = func.__name__
            description = func.__doc__ or ""

            def invoke(self, tool_input: Optional[dict] = None, **kwargs: Any):
                payload = dict(tool_input or {})
                payload.update(kwargs)
                return func(**payload)

            def __call__(self, *args: Any, **kwargs: Any):
                return func(*args, **kwargs)

        wrapper = _CallableTool()
        wrapper.func = func
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper


@tool
def search_products(
    query: str = "",
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    is_organic: Optional[bool] = None,
    brand: Optional[str] = None,
    sort: str = "relevance",
    limit: int = 8,
) -> str:
    """Search real store inventory.

    Filters by keyword, category, brand, minimum/maximum price, minimum rating
    and organic status. Sort with 'relevance', 'rating', 'price_asc',
    'price_desc', 'popular' or 'name'. Returns a JSON array of actual products
    including id, name, category, price, description, is_organic, brand,
    availability, image_path, rating and review_count.
    """
    try:
        products = database.fetch_products(
            {
                "query": query,
                "category": category,
                "brand": brand,
                "min_price": min_price,
                "max_price": max_price,
                "min_rating": min_rating,
                "is_organic": is_organic,
                "sort": sort,
                "limit": valid_positive_int(limit, default=8, maximum=50),
            }
        )
        enriched: list[dict] = []
        for product in products:
            notes = [f"rated {product['rating']:.2f}/5 from {product['review_count']} reviews"]
            if product["is_organic"]:
                notes.append("certified organic")
            if product["availability"] == "in_stock":
                notes.append("in stock")
            enriched.append({**product, "why_recommended": "; ".join(notes)})
        if not enriched:
            return as_json({"products": [], "message": "No products matched those filters."})
        return as_json({"products": enriched, "count": len(enriched)})
    except Exception as exc:
        return as_json({"products": [], "error": safe_error(exc, "product search")})


@tool
def get_rating(
    product_id: Optional[int] = None,
    product_name: Optional[str] = None,
    top_n: int = 0,
) -> str:
    """Get actual ratings from customer reviews.

    Pass a product_id or product_name for one product's average rating and
    review count, or top_n to list the highest-rated products. Never guesses.
    """
    try:
        if product_id is not None:
            pid = valid_product_id(product_id)
            if pid is None:
                return as_json({"error": "A valid product ID is required."})
            product = database.get_product(pid)
            rating = reviews_api.get_product_rating(pid)
            if product is None:
                return as_json({"error": f"Product with ID {pid} was not found."})
            return as_json({**rating, "name": product["name"], "has_ratings": rating["review_count"] > 0})

        if product_name:
            product = database.get_product_by_name(product_name)
            if product is None:
                return as_json({"error": f"No product matching '{product_name}' was found."})
            rating = reviews_api.get_product_rating(product["id"])
            return as_json({**rating, "name": product["name"], "has_ratings": rating["review_count"] > 0})

        if top_n and top_n > 0:
            return as_json({"top_rated": reviews_api.get_top_rated(min(int(top_n), 20))})

        return as_json({"error": "Provide a product_id, product_name or top_n."})
    except Exception as exc:
        return as_json({"error": safe_error(exc, "rating lookup")})


@tool
def checkout(
    product_id: int,
    confirmed: bool = False,
    quantity: int = 1,
    session_id: Optional[str] = None,
    confirmation_token: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> str:
    """Prepare or complete an order for a real product.

    Call WITHOUT ``confirmed`` first to get an order summary and confirmation
    token (nothing is purchased). Only after the user explicitly confirms,
    call again with ``confirmed=True`` (or the returned confirmation_token) to
    actually create the order. Prices always come from the database.
    """
    return order_service.checkout(
        product_id=product_id,
        confirmed=confirmed,
        quantity=quantity,
        session_id=session_id,
        confirmation_token=confirmation_token,
        idempotency_key=idempotency_key,
    )


@tool
def describe_product_image(
    image_path: Optional[str] = None,
    image_base64: Optional[str] = None,
    filename: str = "upload.jpg",
    limit: int = 5,
) -> str:
    """Identify a product photo and find similar REAL products in the store.

    Provide either an image file path or base64-encoded image bytes. Returns
    the identified attributes and matching products with explanations.
    """
    try:
        if image_path:
            result = image_search.analyze_image_file(image_path, limit)
        elif image_base64:
            result = image_search.analyze_image_bytes(
                base64.b64decode(image_base64), filename, limit
            )
        else:
            return "No image was provided. Please upload a product photo."
        return image_search.to_agent_json(result)
    except Exception as exc:
        return safe_error(exc, "image search")


@tool
def compare_products(product_ids: list[int]) -> str:
    """Compare two or more real products by price, rating, reviews and organic status."""
    try:
        ids = [pid for pid in (valid_product_id(p) for p in product_ids) if pid is not None][:6]
        if len(ids) < 2:
            return "Please provide at least two valid product IDs to compare."
        products = [p for p in (database.get_product(pid) for pid in ids) if p]
        if len(products) < 2:
            return "At least one of those products does not exist in the store."
        lines: list[str] = []
        for product in products:
            lines.append(
                f"#{len(lines) + 1}. {product['name']} (ID:{product['id']}) — "
                f"${product['price']:.2f} ★{product['rating']:.2f} — "
                f"{'organic' if product['is_organic'] else 'non-organic'}"
            )
        cheapest = min(products, key=lambda p: p["price"])
        best = max(products, key=lambda p: (p["rating"], p["review_count"]))
        lines.append(
            f"Summary: {cheapest['name']} is the lowest priced; "
            f"{best['name']} has the strongest customer ratings."
        )
        return "\n".join(lines)
    except Exception as exc:
        return safe_error(exc, "product comparison")


@tool
def order_history(session_id: str = config.DEFAULT_SESSION_ID) -> str:
    """Return the current session's real order history."""
    try:
        orders = order_service.order_history(session_id)
        if not orders:
            return "You have no orders yet."
        lines = []
        for order in orders:
            lines.append(
                f"Order #{order['id']}: {order['name']} x{order['quantity']} — "
                f"${order['total_amount']:.2f} — {order['status']} — {order['ordered_at']}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return safe_error(exc, "order history")
