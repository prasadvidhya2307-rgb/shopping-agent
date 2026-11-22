"""Image validation, visual identification and database-backed similarity search.

Uploaded images are processed in memory and deleted immediately. Nothing is
persisted, and no product is returned unless it exists in SQLite.
"""

import base64
import io
import json
import os
import re
from typing import Any

import config
from database import fetch_products, get_categories
from utils import BackendError, as_json, clean_text, tokenize, valid_positive_int


def validate_image(data: bytes, filename: str = "") -> None:
    """Raise ValueError for unsupported, oversized, empty or corrupt images."""
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValueError("The image is too large. Maximum size is 10 MB.")

    extension = os.path.splitext(filename or "")[1].lower()
    if extension and extension not in config.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Unsupported file type. Use JPG, PNG or WEBP.")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - pillow is a declared dependency
        raise BackendError("Image processing library is unavailable.") from exc

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise ValueError("The file is not a valid or readable image.") from exc


def preprocess_image(data: bytes) -> bytes:
    """Normalise orientation/format and cap resolution; return JPEG bytes."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(
            (config.MAX_IMAGE_EDGE, config.MAX_IMAGE_EDGE), Image.Resampling.LANCZOS
        )
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _parse_attributes(raw: str) -> dict:
    """Extract a JSON object from an LLM reply that may include markdown fences."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        raise BackendError("The vision model did not return structured attributes.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise BackendError("The vision model returned an unexpected format.")
    return {
        "product_type": clean_text(payload.get("product_type"), 80),
        "search_query": clean_text(payload.get("search_query"), 80),
        "is_organic": payload.get("is_organic") if isinstance(payload.get("is_organic"), bool) else None,
        "description": clean_text(payload.get("description"), 200),
        "visible_features": clean_text(payload.get("visible_features"), 200),
        "category": clean_text(payload.get("category"), 40),
    }


def identify_image(image_bytes: bytes) -> dict:
    """Call the Groq vision model and return structured product attributes."""
    from llm import get_vision_llm
    from langchain_core.messages import HumanMessage

    encoded = base64.b64encode(image_bytes).decode()
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
            },
            {
                "type": "text",
                "text": (
                    "Identify the product in this image. Return ONLY a JSON object with: "
                    "product_type (e.g. honey, olive oil, almonds), "
                    "search_query (a short keyword for product search), "
                    "category (one of: " + ", ".join(c for c, _ in get_categories()) + "), "
                    "is_organic (true/false/null if the label is unclear), "
                    "visible_features (colour, packaging, design), "
                    "description (one sentence). Do not invent brands or prices."
                ),
            },
        ]
    )
    response = get_vision_llm().invoke([message])
    return _parse_attributes(response.content)


def search_similar(attributes: dict, limit: int = 5) -> list[dict]:
    """Match identified attributes against real SQLite products with explanations."""
    limit = valid_positive_int(limit, default=5, maximum=20)
    query = attributes.get("search_query") or attributes.get("product_type") or ""
    known_categories = {cat.lower() for cat, _ in get_categories()}
    raw_category = str(attributes.get("category") or "").lower()
    category = raw_category if raw_category in known_categories else None

    candidates = fetch_products(
        {
            "query": query,
            "category": category,
            "is_organic": attributes.get("is_organic"),
            "sort": "relevance",
            "limit": max(limit * 4, 20),
        }
    )
    if not candidates and category:
        candidates = fetch_products({"query": query, "limit": max(limit * 4, 20)})

    attr_tokens = tokenize(
        " ".join(
            str(attributes.get(k, ""))
            for k in ("product_type", "search_query", "description", "visible_features")
        )
    )
    scored: list[dict] = []
    for product in candidates:
        product_tokens = tokenize(
            " ".join(str(product.get(k, "")) for k in ("name", "description", "category", "brand"))
        )
        overlap = attr_tokens & product_tokens
        reasons: list[str] = []
        if overlap:
            reasons.append("matches detected features: " + ", ".join(sorted(overlap)[:4]))
        if category and product["category"] == category:
            reasons.append(f"same category ({category})")
        if attributes.get("is_organic") is True and product["is_organic"]:
            reasons.append("organic label matches")
        if not reasons:
            reasons.append("closest available match in the store")
        scored.append({**product, "match_score": round(min(1.0, 0.4 + 0.12 * len(overlap) + 0.15 * len(reasons)), 2), "match_reason": "; ".join(reasons)})

    scored.sort(key=lambda p: (-p["match_score"], -p["rating"], p["name"]))
    return scored[:limit]


def analyze_image_file(path: str, limit: int = 5) -> dict:
    """Full workflow for a temporary upload path. Always removes the file."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        validate_image(raw, os.path.basename(path))
        processed = preprocess_image(raw)
        attributes = identify_image(processed)
        matches = search_similar(attributes, limit)
        if matches:
            summary = (
                f"I identified this as {attributes['product_type'] or 'a product'} and found "
                f"{len(matches)} real item(s) in the store that match."
            )
        else:
            summary = (
                "I identified the image but could not find a matching product in the store. "
                "Try describing what you are looking for in words."
            )
        return {
            "identified": attributes,
            "matches": matches,
            "summary": summary,
            "error": None,
        }
    except (ValueError, BackendError) as exc:
        return {"identified": {}, "matches": [], "summary": str(exc), "error": str(exc)}
    except Exception as exc:
        if "model_not_found" in str(exc):
            message = (
                "Image analysis is unavailable for this Groq account (no vision model access). "
                "Set GROQ_VISION_MODEL to an accessible vision model, or describe the product in words."
            )
            return {"identified": {}, "matches": [], "summary": message, "error": "vision_unavailable"}
        from utils import safe_error

        return {"identified": {}, "matches": [], "summary": safe_error(exc, "image analysis"), "error": "analysis_failed"}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def analyze_image_bytes(data: bytes, filename: str, limit: int = 5) -> dict:
    """Full workflow for in-memory upload bytes (no temp file needed)."""
    try:
        validate_image(data, filename)
        processed = preprocess_image(data)
        attributes = identify_image(processed)
        matches = search_similar(attributes, limit)
        summary = (
            f"I identified this as {attributes['product_type'] or 'a product'} and found "
            f"{len(matches)} real item(s) in the store that match."
            if matches
            else "I identified the image but found no matching products in the store."
        )
        return {"identified": attributes, "matches": matches, "summary": summary, "error": None}
    except (ValueError, BackendError) as exc:
        return {"identified": {}, "matches": [], "summary": str(exc), "error": str(exc)}
    except Exception as exc:
        if "model_not_found" in str(exc):
            message = (
                "Image analysis is unavailable for this Groq account (no vision model access). "
                "Set GROQ_VISION_MODEL to an accessible vision model, or describe the product in words."
            )
            return {"identified": {}, "matches": [], "summary": message, "error": "vision_unavailable"}
        from utils import safe_error

        return {"identified": {}, "matches": [], "summary": safe_error(exc, "image analysis"), "error": "analysis_failed"}


def to_agent_json(result: dict) -> str:
    """Format image results in the same product-line format the UI parser understands."""
    lines = [result.get("summary", "")]
    for index, product in enumerate(result.get("matches", []), 1):
        lines.append(
            f"#{index}. {product['name']} (ID:{product['id']}) — ${product['price']:.2f} "
            f"★{product['rating']:.2f} — {'organic' if product['is_organic'] else 'non-organic'}"
        )
        reason = product.get("match_reason")
        if reason:
            lines.append(f"   Why: {reason}")
    return "\n".join(line for line in lines if line is not None)
