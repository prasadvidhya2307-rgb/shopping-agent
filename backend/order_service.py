"""Order validation, confirmation tokens and transactional checkout.

Nothing is written to SQLite until ``confirm_order`` (or an explicitly
confirmed checkout) is called. Prices are always re-read from the database.
"""

import secrets
import time
from typing import Any

from . import config, database
from .utils import BackendError, safe_error, valid_product_id, valid_positive_int

_confirmations: dict[str, dict[str, Any]] = {}


def _cleanup_expired() -> None:
    now = time.time()
    for token in list(_confirmations):
        if now - _confirmations[token]["created_at"] > config.CONFIRMATION_TTL_SECONDS:
            _confirmations.pop(token, None)


def get_order_summary(product_id: int, quantity: int = 1) -> dict:
    quantity = valid_positive_int(quantity)
    pid = valid_product_id(product_id)
    if pid is None:
        raise BackendError("A valid product ID is required.")
    product = database.get_product(pid)
    if product is None:
        raise LookupError(f"Product with ID {pid} was not found.")
    return {
        "product_id": pid,
        "name": product["name"],
        "category": product["category"],
        "price": product["price"],
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "availability": product["availability"],
        "image_path": product["image_path"],
    }


def prepare_order(
    product_id: int,
    session_id: str | None = None,
    quantity: int = 1,
    idempotency_key: str | None = None,
) -> dict:
    """Return a confirmation summary + short-lived token. Performs NO writes."""
    _cleanup_expired()
    session_id = session_id or config.DEFAULT_SESSION_ID
    summary = get_order_summary(product_id, quantity)
    if summary["availability"] in ("out_of_stock", "discontinued"):
        raise BackendError(f"'{summary['name']}' is currently unavailable.")

    token = secrets.token_urlsafe(24)
    _confirmations[token] = {
        "product_id": summary["product_id"],
        "session_id": session_id,
        "quantity": summary["quantity"],
        "idempotency_key": idempotency_key,
        "created_at": time.time(),
    }
    return {
        "status": "awaiting_confirmation",
        "confirmation_token": token,
        "summary": summary,
        "message": (
            f"Ready to order {summary['name']} x{summary['quantity']} for "
            f"${summary['total']:.2f}. Nothing has been purchased yet. "
            "Ask me to confirm to place the order."
        ),
    }


def confirm_order(token: str, session_id: str | None = None) -> dict:
    """Validate a token and create the order in one transaction."""
    _cleanup_expired()
    session_id = session_id or config.DEFAULT_SESSION_ID
    pending = _confirmations.get(token)
    if not pending:
        raise BackendError("This confirmation has expired. Please select the product again.")
    if pending["session_id"] != session_id:
        raise BackendError("This confirmation belongs to a different session.")

    order = database.insert_order(
        product_id=pending["product_id"],
        session_id=session_id,
        quantity=pending["quantity"],
        idempotency_key=pending["idempotency_key"],
    )
    _confirmations.pop(token, None)
    product_name = order["product_name"]
    total = float(order["total_amount"] or order["price"])
    return {
        "status": "confirmed",
        "order": order,
        "message": (
            f"Order #{order['id']} confirmed! '{product_name}' has been ordered "
            f"for ${total:.2f}. Your order will arrive in 3-5 business days. "
            "Thank you for shopping with us!"
        ),
    }


def checkout(
    product_id: int,
    confirmed: bool = False,
    quantity: int = 1,
    session_id: str | None = None,
    confirmation_token: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """Unified checkout entry point used by the LangChain tool and the UI.

    - No confirmation -> returns a summary + token, writes nothing.
    - ``confirmation_token`` -> validates and writes.
    - ``confirmed=True`` -> the caller (UI or user dialogue) already obtained
      explicit confirmation; writes immediately with DB-fetched details.
    """
    session_id = session_id or config.DEFAULT_SESSION_ID
    try:
        pid = valid_product_id(product_id)
        if pid is None:
            raise BackendError("A valid product ID is required.")

        if confirmation_token:
            return confirm_order(confirmation_token, session_id)["message"]

        if not confirmed:
            return prepare_order(pid, session_id, quantity, idempotency_key)["message"]

        order = database.insert_order(
            product_id=pid,
            session_id=session_id,
            quantity=valid_positive_int(quantity),
            idempotency_key=idempotency_key,
        )
        total = float(order["total_amount"] or order["price"])
        return (
            f"Order #{order['id']} confirmed! '{order['product_name']}' has been "
            f"successfully ordered for ${total:.2f}. Your order will arrive in "
            "3-5 business days. Thank you for shopping with us!"
        )
    except (BackendError, LookupError, ValueError) as exc:
        return str(exc)
    except Exception as exc:
        return safe_error(exc, "checkout")


def order_history(session_id: str | None = None) -> list[dict]:
    """Session-scoped order history for the My Orders page."""
    return database.fetch_orders(session_id or config.DEFAULT_SESSION_ID)
