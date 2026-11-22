"""Lazy Groq client construction.

Keeping client creation here (instead of at module import) means the whole
backend remains importable and testable when the optional LangChain/Groq
packages or an API key are unavailable.
"""

from functools import lru_cache

from config import REASONING_MODEL, VISION_MODEL, has_groq_credentials
from utils import BackendError


@lru_cache(maxsize=1)
def get_reasoning_llm():
    if not has_groq_credentials():
        raise BackendError("Groq API key is not configured.")
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise BackendError("LangChain Groq integration is not installed.") from exc
    return ChatGroq(model=REASONING_MODEL, temperature=0)


@lru_cache(maxsize=1)
def get_vision_llm():
    if not has_groq_credentials():
        raise BackendError("Groq API key is not configured.")
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise BackendError("LangChain Groq integration is not installed.") from exc
    return ChatGroq(model=VISION_MODEL, temperature=0)
