"""LangChain agent factory with lazy Groq integration.

Importing this module never constructs an LLM. ``agent.invoke(...)`` builds the
real agent on first use, so the rest of the backend stays importable in
environments without the optional AI dependencies.
"""

from .llm import get_reasoning_llm
from .tools import (
    compare_products,
    describe_product_image,
    get_rating,
    order_history,
    search_products,
    checkout,
)
from .utils import BackendError

SYSTEM_PROMPT = """You are ShopMate, a helpful AI shopping assistant for a real store.

STRICT RULES
- Use ONLY these exact tool names: search_products (plural), get_rating,
  checkout, describe_product_image, compare_products, order_history.
  Never write a tool name that is not in this list (e.g. never "search_product").
- Only use product information returned by the tools. Never invent products,
  prices, ratings, brands, availability or order IDs.
- If a tool returns no products, say so plainly and suggest different filters.
- If the request is ambiguous (for example no category or budget), ask one
  short clarifying question before searching.
- Always explain WHY a recommended product fits the user's request, using the
  tool's `why_recommended`, rating and price data.
- Keep answers concise, friendly and relevant. Do not use emojis.

PRODUCT LIST FORMAT
When presenting products, use this exact plain-text line for each item so the
interface can turn it into a product card:

#<number>. <name> (ID:<id>) — $<price> ★<rating> — <organic|non-organic>

Put a blank line between items. Always include (ID:X).

WORKFLOW
1. BROWSING: call search_products with filters parsed from the user's message
   (category, budget as min_price/max_price, min_rating, is_organic, brand).
   Use `sort='rating'` for "best rated", `price_asc` for "cheapest/affordable".
2. RATINGS: use get_rating for a specific product, product name, or top_n for
   "highest rated". Use compare_products when the user compares two or more.
3. IMAGE SEARCH: call describe_product_image with the provided image path,
   then present the real products it returns with their match explanations.
4. ORDERS:
   - Call checkout with the chosen product ID and NO `confirmed` flag first.
     This returns a summary and a confirmation token and does NOT buy anything.
   - Show the summary and ask the user to confirm explicitly.
   - Only after the user says yes, call checkout again with `confirmed=True`
     (or the confirmation_token). Never call checkout with confirmation unless
     the user has just explicitly agreed.
   - You MUST call the checkout tool and receive its result before saying an
     order was placed. Never invent an order ID — quote only the ID returned
     by the checkout tool. If you did not call checkout, say clearly that the
     order was NOT placed and ask the user to confirm again.
   - Never guess a product ID; use only IDs from your own previous message.
5. HISTORY: use order_history when the user asks about their orders.
"""


def safe_agent_content(result: dict, content: str) -> str:
    """Deterministic guard: strip order claims not backed by a checkout result."""
    text = content or ""
    lowered = text.lower()
    claims_order = any(
        phrase in lowered
        for phrase in ("order #", "order is confirmed", "has been ordered", "order placed")
    )
    if not claims_order:
        return text
    checkout_results = [
        str(getattr(message, "content", ""))
        for message in result.get("messages", [])
        if getattr(message, "name", None) == "checkout"
    ]
    if any("order #" in str(item).lower() for item in checkout_results):
        return text
    return (
        "I wasn't able to place that order — no order was created. "
        "Please confirm again and I'll retry."
    )



class LazyAgent:
    """Proxy that builds the real LangChain agent only when first invoked."""

    def invoke(self, payload: dict, *args, **kwargs):
        last_error = None
        for attempt in range(2):
            try:
                return build_agent().invoke(payload, *args, **kwargs)
            except Exception as exc:
                last_error = exc
                # Some Groq models occasionally emit a near-miss tool name.
                # Retry once with a fresh sampling of the same request.
                if attempt == 0 and "tool call validation failed" in str(exc):
                    continue
                raise
        raise last_error  # pragma: no cover


def build_agent():
    """Construct the real LangChain agent using the configured Groq model."""
    try:
        from langchain.agents import create_agent
    except ImportError as exc:
        raise BackendError("LangChain agent support is not installed.") from exc

    return create_agent(
        tools=[
            search_products,
            get_rating,
            checkout,
            describe_product_image,
            compare_products,
            order_history,
        ],
        model=get_reasoning_llm(),
        system_prompt=SYSTEM_PROMPT,
    )


agent = LazyAgent()


__all__ = ["agent", "build_agent", "SYSTEM_PROMPT", "LazyAgent"]
