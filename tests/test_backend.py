"""Backend tests. Groq/LangChain calls are mocked; no API usage required."""

import io
import json
import sqlite3

import pytest

from backend import auth, chat_store, config, database, image_search, order_service, reviews_api, utils
from backend.tools import checkout, compare_products, get_rating, order_history, search_products


def _rows(path, sql):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Database / migrations
# ---------------------------------------------------------------------------
def test_migration_is_additive_and_idempotent(legacy_db):
    database.initialize_database()
    database.initialize_database()  # safe to rerun

    assert len(_rows(legacy_db, "SELECT * FROM products")) == 3
    assert len(_rows(legacy_db, "SELECT * FROM reviews")) == 3
    assert len(_rows(legacy_db, "SELECT * FROM orders")) == 1

    tables = {r[0] for r in _rows(legacy_db, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"order_items", "conversations", "chat_messages"} <= tables

    product_cols = {r[1] for r in _rows(legacy_db, "PRAGMA table_info(products)")}
    assert {"brand", "availability", "image_path", "rating", "review_count"} <= product_cols

    indexes = {r[0] for r in _rows(legacy_db, "SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_reviews_product" in indexes
    assert "idx_orders_session" in indexes

    order = _rows(legacy_db, "SELECT session_id, status, total_amount, quantity FROM orders")[0]
    assert order == ("legacy", "confirmed", 14.99, 1)

    honey = database.get_product(1)
    assert honey["rating"] == 4.5 and honey["review_count"] == 2
    assert honey["image_path"].endswith("honey.png")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def test_search_filters_sorting_and_sql_injection(legacy_db):
    assert [p["id"] for p in database.fetch_products({"max_price": 10, "sort": "price_asc"})] == [3, 2]
    assert [p["id"] for p in database.fetch_products({"min_rating": 4.0})] == [1]
    assert [p["id"] for p in database.fetch_products({"category": "honey", "is_organic": True})] == [1]
    assert database.fetch_products({"query": "clover"})[0]["id"] == 3
    assert database.fetch_products({"query": "' OR 1=1 --"}) == []
    assert database.fetch_products({"min_price": 100}) == []


def test_catalog_overview_and_suggestions_use_real_data(legacy_db):
    overview = database.catalog_overview()
    assert overview["products"] == 3
    assert overview["categories"] == 1
    assert overview["reviews"] == 3
    assert overview["average_rating"] == pytest.approx(4.0, abs=0.01)
    assert overview["organic"] == 1

    assert "Organic Raw Honey" in database.search_suggestions("raw")
    assert "honey" in database.search_suggestions("hon")
    assert database.search_suggestions("does-not-exist") == []
    assert database.search_suggestions()[:1]  # default suggestions are real


def test_search_tool_returns_structured_real_data(legacy_db):
    payload = json.loads(search_products.invoke({"category": "honey", "sort": "rating"}))
    assert payload["count"] == 3
    assert payload["products"][0]["id"] == 1
    assert "why_recommended" in payload["products"][0]
    assert json.loads(search_products.invoke({"query": "nothing-matches"})).get("products") == []


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------
def test_ratings_are_real_and_have_no_rating_case(legacy_db):
    assert reviews_api.get_product_rating(1) == {
        "product_id": 1, "average_rating": 4.5, "review_count": 2
    }
    assert reviews_api.get_product_rating(2)["average_rating"] == 0.0
    ratings = {r["product_id"]: r for r in reviews_api.get_ratings_for_products([1, 2, 999])}
    assert ratings[1]["review_count"] == 2
    assert ratings[2]["review_count"] == 0
    assert reviews_api.get_top_rated(2)[0]["product_id"] == 1
    assert json.loads(get_rating.invoke({"top_n": 2}))["top_rated"][0]["product_id"] == 1


def test_compare_products_uses_database_values(legacy_db):
    result = compare_products.invoke({"product_ids": [1, 3]})
    assert "Organic Raw Honey" in result and "Clover Honey" in result


# ---------------------------------------------------------------------------
# Checkout safety
# ---------------------------------------------------------------------------
def test_checkout_requires_confirmation_and_uses_db_prices(legacy_db):
    before = len(_rows(legacy_db, "SELECT * FROM orders"))
    preview = checkout.invoke({"product_id": 1, "session_id": "s1"})
    assert "Nothing has been purchased" in preview
    assert len(_rows(legacy_db, "SELECT * FROM orders")) == before

    prepared = order_service.prepare_order(1, "s1", quantity=2, idempotency_key="key-1")
    assert prepared["status"] == "awaiting_confirmation"
    assert prepared["summary"]["total"] == pytest.approx(29.98)
    assert len(_rows(legacy_db, "SELECT * FROM orders")) == before

    with pytest.raises(utils.BackendError):
        order_service.confirm_order(prepared["confirmation_token"], "different-session")

    result = order_service.confirm_order(prepared["confirmation_token"], "s1")
    assert "Order #" in result["message"]
    assert len(_rows(legacy_db, "SELECT * FROM orders")) == before + 1
    item = _rows(legacy_db, "SELECT product_id, quantity, purchase_price FROM order_items")[-1]
    assert item == (1, 2, 14.99)


def test_checkout_idempotency_and_validation(legacy_db):
    first = checkout.invoke({"product_id": 1, "confirmed": True, "session_id": "s1", "idempotency_key": "abc"})
    second = checkout.invoke({"product_id": 1, "confirmed": True, "session_id": "s1", "idempotency_key": "abc"})
    assert first == second
    assert len(_rows(legacy_db, "SELECT * FROM orders WHERE idempotency_key='abc'")) == 1
    assert "not found" in checkout.invoke({"product_id": 99999, "confirmed": True})
    # The real Pydantic tool schema rejects non-integers before our code runs;
    # the service layer still validates defensively for direct callers.
    assert "valid product ID" in order_service.checkout("bad-id", confirmed=True)

    with database.get_connection() as conn:
        conn.execute("UPDATE products SET availability='out_of_stock' WHERE id=1")
    assert "unavailable" in checkout.invoke({"product_id": 1, "confirmed": True, "session_id": "s2"})


def test_order_history_is_session_isolated(legacy_db):
    checkout.invoke({"product_id": 2, "confirmed": True, "session_id": "alice"})
    checkout.invoke({"product_id": 3, "confirmed": True, "session_id": "bob"})
    assert len(database.fetch_orders("alice")) == 1
    assert len(database.fetch_orders("bob")) == 1
    assert database.fetch_orders("alice")[0]["name"] == "Wildflower Honey"
    assert database.fetch_orders("nobody") == []
    assert "no orders" in order_history.invoke({"session_id": "nobody"}).lower()


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
def test_auth_hashing_and_account_flow(legacy_db):
    first = auth.hash_password("password123")
    second = auth.hash_password("password123")
    assert first != second  # unique salt
    assert auth.verify_password("password123", first)
    assert not auth.verify_password("wrong-password", first)

    user = auth.create_user("alice", "alice@example.com", "password123")
    assert auth.authenticate("alice", "password123")["id"] == user["id"]
    assert auth.authenticate("ALICE@example.com", "password123")["id"] == user["id"]
    assert auth.authenticate("alice", "wrong-password") is None
    assert auth.get_user(user["id"])["username"] == "alice"

    with pytest.raises(ValueError):
        auth.create_user("alice", "other@example.com", "password123")
    with pytest.raises(ValueError):
        auth.create_user("bob", "bob@example.com", "short")


def test_persistent_web_sessions(legacy_db):
    user = auth.create_user("sessionuser", "session@example.com", "password123")
    token = auth.create_session(user["id"])
    assert auth.get_session_user(token)["id"] == user["id"]
    assert auth.get_session_user(None) is None
    assert auth.get_session_user("not-a-real-token") is None
    auth.delete_session(token)
    assert auth.get_session_user(token) is None


def test_admin_roles_and_user_management(legacy_db):
    user = auth.create_user("bob", "bob@example.com", "password123")
    assert user["role"] == "user"
    assert auth.authenticate("bob", "password123")["role"] == "user"

    admin = auth.promote_to_admin("bob")
    assert admin["role"] == "admin"
    assert auth.authenticate("bob", "password123")["role"] == "admin"
    assert auth.get_user(user["id"])["role"] == "admin"

    with pytest.raises(ValueError):
        auth.promote_to_admin("nobody")

    listings = auth.list_users()
    assert any(u["username"] == "bob" and u["role"] == "admin" for u in listings)

    # The last active admin cannot be disabled.
    assert auth.set_user_active(user["id"], False) is False

    auth.create_user("carol", "carol@example.com", "password123", role="admin")
    assert auth.set_user_active(user["id"], False) is True
    assert auth.authenticate("bob", "password123") is None
    assert auth.set_user_active(user["id"], True) is True
    assert auth.authenticate("bob", "password123")["id"] == user["id"]


def test_chat_history_persistence_and_isolation(legacy_db):
    cid = chat_store.create_conversation("alice")
    chat_store.append_message(cid, "user", "hello", "client-1")
    chat_store.append_message(cid, "user", "hello", "client-1")  # rerun-safe
    chat_store.append_message(cid, "assistant", "hi", "client-2")
    assert len(chat_store.get_messages(cid)) == 2
    assert len(chat_store.list_conversations("alice")) == 1
    assert chat_store.list_conversations("bob") == []
    assert chat_store.delete_conversation(cid, "bob") is False
    assert chat_store.delete_conversation(cid, "alice") is True
    assert chat_store.get_messages(cid) == []


# ---------------------------------------------------------------------------
# Image search (vision model mocked)
# ---------------------------------------------------------------------------
def _valid_image_bytes():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), (220, 160, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_validation_rejects_bad_files():
    image = _valid_image_bytes()
    image_search.validate_image(image, "photo.png")
    for data, name in [(b"", "a.png"), (b"garbage", "b.png"), (image, "c.txt")]:
        with pytest.raises(ValueError):
            image_search.validate_image(data, name)


def test_image_search_matches_only_real_products(legacy_db, monkeypatch):
    monkeypatch.setattr(
        image_search,
        "identify_image",
        lambda _bytes: {
            "product_type": "honey",
            "search_query": "honey",
            "category": "honey",
            "is_organic": True,
            "description": "a jar of honey",
            "visible_features": "amber jar",
        },
    )
    result = image_search.analyze_image_bytes(_valid_image_bytes(), "honey.png", limit=2)
    assert result["error"] is None
    assert result["matches"]
    real_ids = {p["id"] for p in database.fetch_products()}
    assert all(match["id"] in real_ids for match in result["matches"])
    assert all(match["match_reason"] for match in result["matches"])


def test_image_search_handles_vision_failure(legacy_db, monkeypatch):
    def boom(_bytes):
        raise utils.BackendError("vision unavailable")

    monkeypatch.setattr(image_search, "identify_image", boom)
    result = image_search.analyze_image_bytes(_valid_image_bytes(), "honey.png")
    assert result["matches"] == []
    assert result["error"] == "vision unavailable"


# ---------------------------------------------------------------------------
# Security / imports
# ---------------------------------------------------------------------------
def test_safe_error_never_leaks_api_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-key-123")
    message = utils.safe_error(RuntimeError("failed with super-secret-key-123"), "demo")
    assert "super-secret-key-123" not in message
    assert config.groq_api_key() == "super-secret-key-123"  # readable internally only


def test_backend_modules_import_without_langchain():
    from backend import shopping_agent

    for name in ("agent", "search_products", "get_rating", "checkout", "describe_product_image"):
        assert hasattr(shopping_agent, name)


def test_order_claims_require_a_checkout_tool_result():
    from types import SimpleNamespace

    from backend.agent import safe_agent_content

    fabricated = "Your order is confirmed! Order #1001 — thank you."
    assert "no order was created" in safe_agent_content({"messages": []}, fabricated)

    backed = {
        "messages": [
            SimpleNamespace(name="checkout", content="Order #12 confirmed! 'Honey' ordered.")
        ]
    }
    assert safe_agent_content(backed, "Order #12 confirmed! 'Honey' ordered.") == (
        "Order #12 confirmed! 'Honey' ordered."
    )


def test_agent_raises_safe_error_without_llm(monkeypatch):
    from backend import agent as agent_module

    def no_llm():
        raise utils.BackendError("Groq API key is not configured.")

    monkeypatch.setattr(agent_module, "get_reasoning_llm", no_llm)
    with pytest.raises(utils.BackendError):
        agent_module.build_agent()
