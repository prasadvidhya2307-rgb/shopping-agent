"""Reusable UI components for the ShopMate storefront."""

import base64
import html
import os
import re
import uuid
from urllib.parse import quote

import streamlit as st

from backend import config
from backend.db_utils import get_product, place_order as fallback_place_order
from backend.reviews_api import get_product_rating


def current_session_id() -> str:
    return st.session_state.get("session_id") or config.DEFAULT_SESSION_ID


_RES = str(config.RESOURCES_DIR)


def _svg_uri(markup: str) -> str:
    return "data:image/svg+xml;utf8," + quote(markup, safe="")


def _art(bg1: str, bg2: str, shapes: str) -> str:
    return _svg_uri(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/>'
        "</linearGradient></defs>"
        '<rect width="400" height="300" fill="url(#g)"/>'
        f"{shapes}</svg>"
    )


CATEGORY_ART = {
    "oil": _art("#DCE9B8", "#9FBF6A",
        '<ellipse cx="200" cy="255" rx="62" ry="10" fill="#2F4A1A" opacity=".22"/>'
        '<rect x="167" y="92" width="66" height="150" rx="20" fill="#3C6327"/>'
        '<rect x="182" y="64" width="36" height="34" rx="7" fill="#2C4A1B"/>'
        '<rect x="175" y="132" width="50" height="64" rx="8" fill="#F5E9C8"/>'
        '<path d="M200 148c-13 10-13 24 0 34 13-10 13-24 0-34z" fill="#6E9A32"/>'),
    "nuts": _art("#EAD2AC", "#C99A63",
        '<ellipse cx="200" cy="258" rx="78" ry="11" fill="#5A3A1B" opacity=".2"/>'
        '<path d="M140 190c-8-40 22-78 52-60 26 16 8 66-24 78-14 5-26-2-28-18z" fill="#A96F3C"/>'
        '<path d="M262 196c8-40-22-78-52-60-26 16-8 66 24 78 14 5 26-2 28-18z" fill="#8B5A2E"/>'
        '<path d="M200 120c-14 28-14 68 0 96 14-28 14-68 0-96z" fill="#B8804A"/>'),
    "seeds": _art("#CFE6CE", "#86B89A",
        '<ellipse cx="200" cy="256" rx="76" ry="10" fill="#1B5138" opacity=".2"/>'
        '<path d="M200 230c-30-30-30-86 0-122 30 36 30 92 0 122z" fill="#2F7A50"/>'
        '<g fill="#1E5C3C"><ellipse cx="184" cy="160" rx="7" ry="11"/>'
        '<ellipse cx="212" cy="150" rx="7" ry="11"/><ellipse cx="190" cy="192" rx="7" ry="11"/>'
        '<ellipse cx="216" cy="186" rx="7" ry="11"/><ellipse cx="200" cy="132" rx="7" ry="11"/></g>'),
    "grains": _art("#F0E1A8", "#D6B45E",
        '<ellipse cx="200" cy="258" rx="80" ry="11" fill="#6B5016" opacity=".2"/>'
        '<path d="M200 246V96" stroke="#8A6A1E" stroke-width="7" stroke-linecap="round"/>'
        '<g fill="#E7C463"><ellipse cx="174" cy="124" rx="12" ry="22" transform="rotate(-28 174 124)"/>'
        '<ellipse cx="226" cy="124" rx="12" ry="22" transform="rotate(28 226 124)"/>'
        '<ellipse cx="174" cy="168" rx="12" ry="22" transform="rotate(-28 174 168)"/>'
        '<ellipse cx="226" cy="168" rx="12" ry="22" transform="rotate(28 226 168)"/>'
        '<ellipse cx="200" cy="104" rx="11" ry="20"/></g>'),
    "tea": _art("#CFE7D2", "#8CBFA2",
        '<ellipse cx="200" cy="246" rx="76" ry="11" fill="#1B5138" opacity=".18"/>'
        '<path d="M126 142h132c0 52-28 84-66 84s-66-32-66-84z" fill="#F4F8F2"/>'
        '<path d="M258 158c30-4 38 34 4 42" stroke="#F4F8F2" stroke-width="12" fill="none" stroke-linecap="round"/>'
        '<ellipse cx="192" cy="144" rx="64" ry="14" fill="#9CC47C"/>'
        '<path d="M176 118c-8-14 8-18 0-32M210 118c-8-14 8-18 0-32" stroke="#FFFFFF" stroke-width="5" fill="none" opacity=".65" stroke-linecap="round"/>'),
    "coffee": _art("#E2CBA9", "#A87B4F",
        '<ellipse cx="200" cy="250" rx="76" ry="11" fill="#3E2411" opacity=".22"/>'
        '<path d="M122 130h134c0 56-30 92-67 92s-67-36-67-92z" fill="#F6EFE4"/>'
        '<path d="M256 150c32-4 40 36 4 46" stroke="#F6EFE4" stroke-width="13" fill="none" stroke-linecap="round"/>'
        '<ellipse cx="189" cy="132" rx="66" ry="15" fill="#5A3520"/>'),
    "snacks": _art("#F1D9C2", "#D9A981",
        '<ellipse cx="200" cy="250" rx="76" ry="11" fill="#5A3210" opacity=".2"/>'
        '<rect x="128" y="128" width="144" height="76" rx="18" fill="#B5793C" transform="rotate(-8 200 166)"/>'
        '<rect x="142" y="140" width="116" height="52" rx="12" fill="#D89A54" transform="rotate(-8 200 166)"/>'
        '<g fill="#5A3210"><circle cx="170" cy="160" r="6"/><circle cx="200" cy="172" r="6"/>'
        '<circle cx="230" cy="158" r="6"/></g>'),
    "dairy-alt": _art("#D3E7EE", "#8FBED0",
        '<ellipse cx="200" cy="254" rx="70" ry="11" fill="#174E63" opacity=".2"/>'
        '<path d="M148 106h104l18 136H130z" fill="#F7FBFD" opacity=".95"/>'
        '<path d="M166 106h68l6 136h-80z" fill="#FFFFFF"/>'
        '<path d="M170 156h60l8 86h-76z" fill="#EAF4F8"/>'),
}

DEFAULT_ART = _art("#DDE8E2", "#A9C8B8",
    '<path d="M130 130h140l14 118H116z" fill="#FFFFFF" opacity=".92"/>'
    '<path d="M168 132c0-28 12-44 32-44s32 16 32 44" stroke="#FFFFFF" stroke-width="12" fill="none"/>')


@st.cache_data(show_spinner=False)
def _image_data_uri(filename: str) -> str | None:
    path = os.path.join(_RES, filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return f"data:{mime};base64,{b64}"


HONEY_URI = _image_data_uri("honey.png")
OATS_URI = _image_data_uri("oats.png")
LOGO_URI = _image_data_uri("logo.png")


def category_art(category: str) -> str:
    return CATEGORY_ART.get(category, DEFAULT_ART)


def product_art(product: dict) -> str:
    name = product["name"].lower()
    if "honey" in name and HONEY_URI:
        return HONEY_URI
    if product["category"] == "honey" and HONEY_URI:
        return HONEY_URI
    if product["category"] == "grains" and OATS_URI:
        return OATS_URI
    return category_art(product["category"])


def rating_html(product: dict) -> str:
    rating = product.get("rating", 0.0)
    count = product.get("review_count", 0)
    return (
        f'<span class="sm-rating">{rating:.2f}<small>/5 · {count}</small></span>'
    )


def render_product_card(product: dict, key_prefix: str, show_order: bool = True) -> None:
    """Render one ShopMate product card."""
    if "rating" not in product:
        info = get_product_rating(product["id"])
        product = dict(product)
        product["rating"] = info["average_rating"]
        product["review_count"] = info["review_count"]

    organic = (
        '<span class="sm-badge green">Organic</span>'
        if product["is_organic"]
        else '<span class="sm-badge soft">Classic</span>'
    )
    cat = html.escape(product["category"].replace("-", " ").title())
    markup = f"""
    <div class="sm-card">
      <div class="sm-card-media"><img src="{product_art(product)}" alt=""></div>
      <div class="sm-card-body">
        <div class="sm-card-top">{organic}<span class="sm-badge soft">{cat}</span></div>
        <div class="sm-name">{html.escape(product['name'])}</div>
        <div class="sm-desc">{html.escape(product['description'])}</div>
        <div class="sm-foot"><span class="sm-price">${product['price']:.2f}</span>{rating_html(product)}</div>
      </div>
    </div>
    """
    st.markdown(markup, unsafe_allow_html=True)

    if show_order:
        if st.button(
            "Order now",
            key=f"ord_{key_prefix}_{product['id']}",
            use_container_width=True,
        ):
            st.session_state.pending_order = {
                "id": product["id"],
                "name": product["name"],
                "price": float(product["price"]),
                "source": key_prefix,
                "idempotency_key": uuid.uuid4().hex,
            }


PRODUCT_LINE = re.compile(
    r"^\s*#\d+\.\s*(.*?)\s*\(ID:\s*(\d+)\)\s*[—–-]\s*\$?\s*([\d.]+)\s*★\s*([\d.]+)\s*[—–-]\s*(.*)$"
)


def render_agent_text(content: str, key_prefix: str) -> None:
    """Render agent text, converting real product lines into cards."""
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if text:
            st.markdown(
                f'<div class="sm-bubble">{html.escape(text).replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True,
            )
        buffer.clear()

    seen: dict[int, int] = {}
    for line in content.split("\n"):
        match = PRODUCT_LINE.match(line)
        if not match:
            buffer.append(line)
            continue
        pid = int(match.group(2))
        product = get_product(pid)
        if not product:
            buffer.append(line)
            continue
        flush()
        seen[pid] = seen.get(pid, 0) + 1
        st.markdown('<div class="sm-inline">', unsafe_allow_html=True)
        render_product_card(product, key_prefix=f"{key_prefix}_{pid}_{seen[pid]}")
        st.markdown("</div>", unsafe_allow_html=True)
    flush()


def execute_checkout(product_id: int, idempotency_key: str | None = None) -> str:
    payload = {
        "product_id": int(product_id),
        "confirmed": True,
        "session_id": current_session_id(),
        "idempotency_key": idempotency_key,
    }
    try:
        from backend.shopping_agent import checkout

        return str(checkout.invoke(payload))
    except Exception:
        return fallback_place_order(
            int(product_id),
            session_id=payload["session_id"],
            idempotency_key=idempotency_key,
        )


def render_confirmation() -> None:
    pending = st.session_state.get("pending_order")
    if not pending:
        return
    product = get_product(pending["id"])
    if not product:
        st.session_state.pending_order = None
        return

    st.markdown(
        f"""
        <div class="sm-confirm">
          <b>Confirm your order</b>
          <p>{html.escape(product['name'])} · ${product['price']:.2f} · Product ID {product['id']}<br>
          Nothing is purchased until you confirm. This order will appear in My Orders.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1])
    if c1.button("Confirm order", key="confirm_order_btn", type="primary", use_container_width=True):
        result = execute_checkout(product["id"], pending.get("idempotency_key"))
        st.session_state.pending_order = None
        st.session_state.last_order_result = result
        if st.session_state.get("messages"):
            st.session_state.messages.append({"role": "assistant", "content": result})
        st.toast("Order placed successfully!")
        st.rerun()
    if c2.button("Cancel", key="cancel_order_btn", use_container_width=True):
        st.session_state.pending_order = None
        st.rerun()


def render_message(index: int, message: dict) -> None:
    if message["role"] == "user":
        st.markdown(
            f"""
            <div class="sm-msg user">
              <div class="sm-avatar">YOU</div>
              <div class="sm-bubble">{html.escape(message['content']).replace(chr(10), '<br>')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sm-msg ai"><div class="sm-avatar">SM</div></div>',
            unsafe_allow_html=True,
        )
        render_agent_text(message["content"], key_prefix=f"msg{index}")
