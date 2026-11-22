"""Small shared helpers: validation, formatting and safe error handling."""

import json
import logging
import re
from typing import Any, Iterable

from config import redact

logger = logging.getLogger("shopmate")


class BackendError(Exception):
    """A safe, user-presentable backend failure."""


def safe_error(exc: BaseException, context: str = "request") -> str:
    """Log the full (redacted) exception internally, return a generic message."""
    logger.exception("%s failed: %s", context, redact(str(exc)))
    return (
        f"Sorry, the {context} could not be completed. "
        "Please try again or adjust your request."
    )


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def clean_text(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()[:limit]


def valid_product_id(value: Any) -> int | None:
    try:
        product_id = int(value)
    except (TypeError, ValueError):
        return None
    return product_id if product_id > 0 else None


def valid_positive_int(value: Any, default: int = 1, maximum: int = 50) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, maximum))


def valid_price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price >= 0 else None


def dedupe_products(products: Iterable[dict]) -> list[dict]:
    """Remove duplicate products by id while preserving order."""
    seen: set[int] = set()
    result: list[dict] = []
    for product in products:
        pid = product.get("id")
        if pid is not None and pid in seen:
            continue
        if pid is not None:
            seen.add(pid)
        result.append(product)
    return result


def money(amount: float) -> str:
    return f"${float(amount):.2f}"


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))
