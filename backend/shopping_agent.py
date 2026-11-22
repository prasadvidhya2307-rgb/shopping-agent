"""Backward-compatible facade for the original backend module.

The implementation now lives in focused modules (``agent.py``, ``tools.py``,
``order_service.py``, ...). These names are preserved so existing callers and
the Streamlit UI keep working unchanged.
"""

from .agent import SYSTEM_PROMPT, agent
from .tools import (
    checkout,
    compare_products,
    describe_product_image,
    get_rating,
    order_history,
    search_products,
)

__all__ = [
    "agent",
    "SYSTEM_PROMPT",
    "search_products",
    "get_rating",
    "checkout",
    "describe_product_image",
    "compare_products",
    "order_history",
]

if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "I want organic honey with a 4.5+ rating under $20.",
                }
            ]
        }
    )
    print(result["messages"][-1].content)
