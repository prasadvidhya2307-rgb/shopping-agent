"""ShopMate AI — premium Streamlit storefront.

A complete front-end rebuild wired to the hardened backend (LangChain + Groq,
SQLite). The agent, tools, order service and chat store are unchanged.
"""

import html
import os
import uuid
from datetime import datetime
from urllib.parse import quote

import streamlit as st

from backend import auth, chat_store, config, image_search
from backend.agent import safe_agent_content
from ui.components import (
    LOGO_URI,
    category_art,
    current_session_id,
    render_agent_text,
    render_confirmation,
    render_message,
    render_product_card,
)
from backend.db_utils import (
    catalog_overview,
    enrich_with_ratings,
    get_all_products,
    get_categories,
    get_orders,
    get_price_bounds,
    local_search_response,
    search_products_db,
    search_suggestions,
)
from ui.styles import inject_css
from backend.utils import safe_error

st.set_page_config(
    page_title="ShopMate AI — The Smart Marketplace",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme_param = st.query_params.get("theme")
if theme_param in ("light", "dark"):
    st.session_state.theme = theme_param
    st.query_params.pop("theme", None)
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
inject_css(st.session_state.theme)

PAGES = [
    ("home", "Home"),
    ("assistant", "Assistant"),
    ("explore", "Explore"),
    ("image", "Image Search"),
    ("orders", "Orders"),
    ("about", "About"),
]
PAGE_KEYS = {key for key, _ in PAGES}


# ---------------------------------------------------------------------------
# Session state + helpers
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "messages": [],
        "session_id": uuid.uuid4().hex,
        "user": None,
        "conversation_id": None,
        "theme": "dark",
        "auto_process": False,
        "pending_order": None,
        "last_order_result": None,
        "agent_checked": False,
        "agent": None,
        "agent_error": "",
        "image_result": None,
        "explore_initialised": False,
        "explore_category": "All",
        "handled_q": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

if st.query_params.get("logout") == "1":
    for key in (
        "user", "messages", "conversation_id", "pending_order",
        "image_result", "auto_process", "handled_q",
    ):
        st.session_state[key] = None if key != "messages" else []
    st.session_state.session_id = uuid.uuid4().hex
    st.query_params.pop("logout", None)
    st.rerun()

if st.query_params.get("new_chat") == "1":
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.pending_order = None
    st.session_state.image_result = None
    st.session_state.auto_process = False
    st.session_state.handled_q = None
    st.query_params.pop("new_chat", None)


def ensure_conversation() -> str:
    if not st.session_state.get("conversation_id"):
        st.session_state.conversation_id = chat_store.create_conversation(
            current_session_id(), title="Shopping chat"
        )
    return st.session_state.conversation_id


def persist_message(role: str, content: str, client_id: str | None = None) -> None:
    try:
        chat_store.append_message(ensure_conversation(), role, content, client_id)
    except Exception:
        pass


def get_agent():
    if not st.session_state.agent_checked:
        st.session_state.agent_checked = True
        try:
            from backend.shopping_agent import agent as real_agent

            st.session_state.agent = real_agent
        except Exception:
            st.session_state.agent = None
            st.session_state.agent_error = safe_error(
                RuntimeError("agent unavailable"), "AI engine initialisation"
            )
    return st.session_state.agent


def current_page() -> str:
    page = st.query_params.get("page", "home")
    return page if page in PAGE_KEYS else "home"


def navigate(page: str, **params) -> None:
    st.query_params["page"] = page
    for key, value in params.items():
        st.query_params[key] = value
    st.rerun()


def submit_prompt(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    client_id = uuid.uuid4().hex
    st.session_state.messages.append(
        {"role": "user", "content": text, "client_id": client_id}
    )
    persist_message("user", text, client_id)
    st.session_state.auto_process = True
    navigate("assistant")


def run_agent() -> None:
    agent = get_agent()
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]
    try:
        if agent is not None:
            result = agent.invoke({"messages": history})
            content = safe_agent_content(
                result, result["messages"][-1].content.replace("`", "")
            )
        else:
            content = local_search_response(history[-1]["content"])
    except Exception:
        content = (
            safe_error(RuntimeError("agent invocation"), "AI request")
            + "\n\nYou can still browse products in Explore Products."
        )
    client_id = uuid.uuid4().hex
    st.session_state.messages.append(
        {"role": "assistant", "content": content, "client_id": client_id}
    )
    persist_message("assistant", content, client_id)
    st.session_state.auto_process = False
    st.rerun()


def _b64(filename: str) -> str | None:
    import base64

    path = os.path.join(config.RESOURCES_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def section_head(kicker: str, title: str, sub: str = "") -> None:
    markup = f'<div class="sm-kicker">{html.escape(kicker)}</div>'
    markup += f'<div class="sm-title">{html.escape(title)}</div>'
    if sub:
        markup += f'<div class="sm-sub">{html.escape(sub)}</div>'
    st.markdown(markup, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Authentication gate
# ---------------------------------------------------------------------------
def render_auth_page() -> None:
    st.markdown(
        f"""
        <div class="sm-auth-brand">
          <img src="{LOGO_URI}" alt="ShopMate">
          <div><b>ShopMate</b><span>The smart marketplace</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, middle, _ = st.columns([1, 2.2, 1])
    with middle:
        st.markdown(
            '<div class="sm-auth-title">Your account</div>'
            '<div class="sm-auth-sub">Sign in to shop, compare and track your orders.</div>',
            unsafe_allow_html=True,
        )
        login_tab, register_tab = st.tabs(["Log in", "Create account"])
        with login_tab:
            with st.form("login_form", border=False):
                identifier = st.text_input("Username or email", key="login_id")
                password = st.text_input("Password", type="password", key="login_pw")
                do_login = st.form_submit_button("Log in", type="primary", use_container_width=True)
            if do_login:
                user = auth.authenticate(identifier, password)
                if user:
                    st.session_state.user = user
                    st.session_state.session_id = "user_" + user["id"]
                    st.rerun()
                else:
                    st.error("Invalid username/email or password.")
        with register_tab:
            with st.form("register_form", border=False):
                new_name = st.text_input("Username", key="reg_user")
                new_email = st.text_input("Email", key="reg_email")
                new_password = st.text_input("Password", type="password", key="reg_pw")
                confirm_password = st.text_input("Confirm password", type="password", key="reg_pw2")
                do_register = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if do_register:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user = auth.create_user(new_name, new_email, new_password)
                        st.session_state.user = user
                        st.session_state.session_id = "user_" + user["id"]
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        st.markdown(
            '<div class="sm-auth-note">Passwords are stored as salted PBKDF2 hashes. '
            'Your orders and chat history stay private to your account.</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Header + footer navigation (no sidebar)
# ---------------------------------------------------------------------------
def render_header() -> None:
    active = current_page()
    links = "".join(
        f'<a class="sm-navlink{" active" if key == active else ""}" '
        f'href="?page={key}" target="_self">{html.escape(label)}</a>'
        for key, label in PAGES
    )
    theme_label = "Light mode" if st.session_state.theme == "dark" else "Dark mode"
    next_theme = "light" if st.session_state.theme == "dark" else "dark"
    theme_href = f"?page={active}&theme={next_theme}"
    username = (st.session_state.get("user") or {}).get("username", "?")
    user_initials = html.escape(username[:2].upper())
    st.markdown(
        f"""
        <div class="sm-header">
          <a class="sm-header-brand" href="?page=home" target="_self">
            <img class="sm-logo-img" src="{LOGO_URI}" alt="ShopMate"><span>ShopMate</span>
          </a>
          <div class="sm-search-slot"></div>
          <nav class="sm-navbar">{links}</nav>
          <div class="sm-header-actions">
            <a class="sm-action" href="?page=assistant&new_chat=1" target="_self">New chat</a>
            <a class="sm-action primary" href="{theme_href}" target="_self">{theme_label}</a>
            <a class="sm-user" href="?logout=1" target="_self" title="Log out">{user_initials}</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Search form — CSS positions this inline in the fixed header, after the logo.
    with st.form("header_search", border=False):
        c1, c2 = st.columns([5, 1])
        q = c1.text_input(
            "Header search",
            placeholder="organic honey under 15 dollars",
            label_visibility="collapsed",
            key="header_q",
        )
        with c2:
            go = st.form_submit_button("Go", type="primary", use_container_width=True)
    if go and q.strip():
        submit_prompt(q)


def render_footer() -> None:
    links = "".join(
        f'<a href="?page={key}" target="_self">{html.escape(label)}</a>' for key, label in PAGES
    )
    st.markdown(
        f"""
        <div class="sm-footer">
          <div class="sm-footer-brand">
            <img class="sm-logo-img small" src="{LOGO_URI}" alt="ShopMate">
            <div><b>ShopMate</b><br><span>The smart marketplace</span></div>
          </div>
          <div class="sm-footer-links">{links}</div>
          <p class="sm-footer-note">Built with real inventory, genuine reviews and confirmed orders only.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
def render_home() -> None:
    honey = _b64("honey.png") or ""
    oats = _b64("oats.png") or ""
    st.markdown(
        f"""
        <div class="sm-hero">
          <div class="sm-hero-title">Find the good stuff.<br><em>Without the hunt.</em></div>
          <p class="sm-hero-copy">Describe what you need. We search real inventory,
             check genuine customer ratings, and shortlist the right picks in seconds.</p>
          <div class="sm-hero-art">
            <img class="a1" src="data:image/png;base64,{honey}" alt="">
            <img class="a2" src="data:image/png;base64,{oats}" alt="">
          </div>
          <div class="sm-ticker"><div class="sm-ticker-track">
            <div class="sm-ticker-group">
              <span class="claim"><b>Not every product. Only the top 1%.</b></span>
              <span class="claim">Agents read everything, several times over — so you buy right the first time.</span>
            </div>
            <div class="sm-ticker-group">
              <span class="claim"><b>Not every product. Only the top 1%.</b></span>
              <span class="claim">Agents read everything, several times over — so you buy right the first time.</span>
            </div>
          </div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    suggestions = search_suggestions("", limit=6)
    if suggestions:
        st.markdown('<div class="sm-suggest-label">FROM OUR CATALOGUE</div>', unsafe_allow_html=True)
        chips = "".join(
            f'<a class="sm-chip" href="?page=assistant&q={quote(s)}" target="_self">{html.escape(s)}</a>'
            for s in suggestions
        )
        st.markdown(chips, unsafe_allow_html=True)

    overview = catalog_overview()
    st.markdown(
        '<div class="sm-stats">'
        f'<div class="sm-stat"><div class="sm-stat-num">{overview["products"]}</div>'
        '<div class="sm-stat-label">Real products</div></div>'
        f'<div class="sm-stat"><div class="sm-stat-num">{overview["categories"]}</div>'
        '<div class="sm-stat-label">Aisles to explore</div></div>'
        f'<div class="sm-stat"><div class="sm-stat-num">{overview["reviews"]}</div>'
        '<div class="sm-stat-label">Customer reviews</div></div>'
        f'<div class="sm-stat"><div class="sm-stat-num">{overview["average_rating"]:.2f}</div>'
        '<div class="sm-stat-label">Average rating</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    section_head(
        "TOP RATED", "Loved by our customers",
        "The highest-scoring picks across the store, ranked by real reviews.",
    )
    products = enrich_with_ratings(get_all_products())
    products.sort(key=lambda p: (-p["rating"], -p["review_count"]))
    cols = st.columns(4)
    for col, product in zip(cols, products[:4]):
        with col:
            render_product_card(product, key_prefix="home")

    st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
    section_head("BROWSE", "Shop by aisle", "Every category, with real artwork from our catalogue.")
    categories = get_categories()
    st.markdown('<div class="sm-bento">', unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (cat, count) in enumerate(categories):
        with cols[idx % 3]:
            st.markdown(
                f'<a class="sm-bento-tile" href="?page=explore&category={quote(cat)}" target="_self">'
                f'<img src="{category_art(cat)}" alt="">'
                f'<div class="sm-bento-label"><b>{html.escape(cat.replace("-", " ").title())}</b>'
                f'<span>{count} {"product" if count == 1 else "products"}</span></div></a>',
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
    section_head("WHY SHOPMATE", "A smarter way to shop")
    features = [
        ("01", "Ask naturally", "Tell us what you want in plain language — budget, category, rating, organic. We get it."),
        ("02", "See the evidence", "Every recommendation shows its real price, rating and review count from SQLite."),
        ("03", "Confirm with control", "Orders are only written after you explicitly confirm. No silent purchases."),
    ]
    cols = st.columns(3)
    for col, (num, title, body) in zip(cols, features):
        with col:
            st.markdown(
                f'<div class="sm-feature"><div class="sm-step">{num}</div>'
                f'<h4>{html.escape(title)}</h4><p>{html.escape(body)}</p></div>',
                unsafe_allow_html=True,
            )
    render_confirmation()
    render_footer()


# ---------------------------------------------------------------------------
# Explore
# ---------------------------------------------------------------------------
def render_explore() -> None:
    section_head(
        "THE CATALOGUE", "Explore Products",
        "Filter real inventory by category, price, rating and organic status.",
    )
    categories = ["All"] + [cat for cat, _ in get_categories()]
    price_min, price_max = get_price_bounds()

    if not st.session_state.explore_initialised:
        st.session_state.explore_initialised = True
        requested = st.query_params.get("category", "All")
        if requested in categories:
            st.session_state.explore_category = requested

    st.markdown('<div class="sm-panel">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1.2, 1, 1])
    with f1:
        query = st.text_input("Keyword", placeholder="Search name, description, category…", key="ex_query")
        category = st.selectbox(
            "Category", categories,
            index=categories.index(
                st.session_state.explore_category
                if st.session_state.explore_category in categories else "All"
            ),
            key="ex_cat",
        )
    with f2:
        organic = st.selectbox("Attribute", ["All", "Organic only", "Non-organic"], key="ex_org")
        sort = st.selectbox(
            "Sort",
            ["Top rated", "Price: low to high", "Price: high to low", "Name A–Z", "Most reviewed"],
            key="ex_sort",
        )
    with f3:
        max_price = st.slider(
            "Maximum price", float(price_min), float(price_max), float(price_max),
            step=0.5, key="ex_price", format="$%.2f",
        )
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5, key="ex_rating")
    st.markdown("</div>", unsafe_allow_html=True)

    results = search_products_db(
        query=query, category=category, max_price=max_price,
        organic=organic, sort=sort, min_rating=min_rating,
    )
    st.markdown(
        f'<p class="sm-sub" style="margin:.9rem 0 1rem">'
        f'<b style="color:var(--accent)">{len(results)}</b> real '
        f'{"product" if len(results) == 1 else "products"} found.</p>',
        unsafe_allow_html=True,
    )

    if not results:
        st.info("No products match those filters. Try a higher price limit or fewer filters.")
    else:
        cols = st.columns(4)
        for idx, product in enumerate(results):
            with cols[idx % 4]:
                render_product_card(product, key_prefix="explore")

        st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
        section_head("SIDE BY SIDE", "Compare picks", "Select up to three products for a real comparison.")
        options = {f"{p['id']} — {p['name']}": p["id"] for p in results[:20]}
        chosen = st.multiselect("Products to compare", list(options), max_selections=3, key="compare_pick")
        if st.button("Compare selected", key="compare_btn", disabled=len(chosen) < 2):
            from backend.tools import compare_products

            ids = [options[c] for c in chosen]
            verdict = compare_products.invoke({"product_ids": ids})
            st.markdown(
                f'<div class="sm-panel"><div class="sm-bubble">{html.escape(verdict).replace(chr(10), "<br>")}</div></div>',
                unsafe_allow_html=True,
            )
    render_confirmation()


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------
def render_assistant() -> None:
    q = st.query_params.get("q")
    if q and st.session_state.handled_q != q:
        st.session_state.handled_q = q
        st.query_params.pop("q", None)
        submit_prompt(q)

    section_head(
        "YOUR SHOPPING PARTNER", "AI Shopping Assistant",
        "Describe what you want, compare rated picks, then confirm your order.",
    )
    if get_agent() is None:
        st.markdown(
            '<div class="sm-note">Local search mode — chat uses real database search. '
            'Add Groq credentials for full AI reasoning.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sm-chat">', unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown(
            '<div class="sm-msg ai"><div class="sm-avatar">SM</div>'
            '<div class="sm-bubble">Hey! I\'m ShopMate. Tell me what you\'re after — '
            'like <em>"organic honey under $15 with 4+ rating"</em> — and I\'ll search '
            'the store, check reviews and show you the best options.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        for index, message in enumerate(st.session_state.messages):
            render_message(index, message)
    render_confirmation()
    st.markdown("</div>", unsafe_allow_html=True)

    prompt = st.chat_input("Ask about products, budgets, ratings or comparisons…")
    if prompt:
        client_id = uuid.uuid4().hex
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "client_id": client_id}
        )
        persist_message("user", prompt, client_id)
        st.session_state.auto_process = True
        st.rerun()

    if st.session_state.auto_process and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.spinner("ShopMate is thinking…"):
            run_agent()


# ---------------------------------------------------------------------------
# Image search
# ---------------------------------------------------------------------------
def render_image_search() -> None:
    section_head(
        "VISUAL SEARCH", "Shop by Image",
        "Upload a product photo and we'll identify it, then match it to real inventory.",
    )
    vision_ready = config.has_groq_credentials()
    if not vision_ready:
        st.markdown(
            '<div class="sm-note">Image analysis needs a vision-capable Groq model. '
            'Add GROQ_VISION_MODEL to your .env file, or describe the product in Explore.</div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown(
            '<div class="sm-drop"><b>Drop a product photo here</b>'
            '<span>JPG, PNG or WEBP · max 10 MB · never stored permanently</span></div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Upload product image", type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed", key="image_uploader",
        )
        find = st.button(
            "Find Similar Products", type="primary", use_container_width=True,
            disabled=(uploaded is None or not vision_ready),
        )
    with right:
        if uploaded is not None:
            st.markdown('<div class="sm-preview">', unsafe_allow_html=True)
            st.image(uploaded, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown(
                f'<p class="sm-sub" style="text-align:center;margin-top:.7rem">{html.escape(uploaded.name)}</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="sm-drop" style="opacity:.7"><b>Your preview appears here</b>'
                '<span>Upload an image to get started</span></div>',
                unsafe_allow_html=True,
            )

    if find and uploaded is not None and vision_ready:
        with st.spinner("Analyzing image and searching…"):
            result = image_search.analyze_image_bytes(uploaded.getvalue(), uploaded.name, limit=5)
        st.session_state.image_result = image_search.to_agent_json(result)

    if st.session_state.image_result:
        st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
        section_head("MATCHES", "What we found", "Matched against real store products only.")
        st.markdown('<div class="sm-chat">', unsafe_allow_html=True)
        render_agent_text(st.session_state.image_result, key_prefix="image")
        st.markdown("</div>", unsafe_allow_html=True)
        render_confirmation()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def _format_date(raw: str) -> str:
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(raw)


def render_orders() -> None:
    orders = get_orders(current_session_id())
    section_head(
        "YOUR ACCOUNT", "My Orders",
        "Every confirmed order, pulled straight from SQLite.",
    )
    spent = sum(float(o.get("total_amount") or o["price"]) for o in orders)
    avg = spent / len(orders) if orders else 0.0
    st.markdown(
        '<div class="sm-stats">'
        f'<div class="sm-stat"><div class="sm-stat-num">{len(orders)}</div><div class="sm-stat-label">Orders placed</div></div>'
        f'<div class="sm-stat"><div class="sm-stat-num">${spent:.2f}</div><div class="sm-stat-label">Total spent</div></div>'
        f'<div class="sm-stat"><div class="sm-stat-num">${avg:.2f}</div><div class="sm-stat-label">Average order</div></div>'
        '<div class="sm-stat"><div class="sm-stat-num">3–5</div><div class="sm-stat-label">Days to deliver</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if not orders:
        st.info("No orders yet. Find something you love in Explore, then confirm your order.")
        return
    for order in orders:
        st.markdown(
            f"""
            <div class="sm-order">
              <div class="sm-order-icon">{(order['category'][:1] or 'P').upper()}</div>
              <div class="sm-order-main">
                <b>Order #{order['id']:03d} &nbsp; {html.escape(order['name'])}</b>
                <span>Qty {order['quantity']} · Ordered {_format_date(order['ordered_at'])}
                · Product ID {order['product_id']}
                · {'Organic' if order['is_organic'] else 'Classic'}</span>
              </div>
              <div class="sm-status">{html.escape(order['status'].upper())}</div>
              <div class="sm-order-price">${float(order.get('total_amount') or order['price']):.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_confirmation()


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------
def render_about() -> None:
    st.markdown(
        """
        <div class="sm-hero" style="padding:2.6rem 3rem;min-height:auto">
          <div class="sm-hero-title">Good things, found <em>intelligently.</em></div>
          <p class="sm-hero-copy">ShopMate is a small marketplace for wholesome pantry
             staples. Finding the right product should feel like a conversation, not a chore.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    section_head("HOW IT WORKS", "Three simple steps")
    steps = [
        ("01", "Describe or upload", "Tell us what you need, or drop in a photo of a product you like."),
        ("02", "Compare rated picks", "We search real inventory, check reviews and shortlist the best matches."),
        ("03", "Confirm & relax", "Pick a product, approve the order, and track it in My Orders."),
    ]
    cols = st.columns(3)
    for col, (num, title, body) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div class="sm-feature"><div class="sm-step">{num}</div>'
                f'<h4>{html.escape(title)}</h4><p>{html.escape(body)}</p></div>',
                unsafe_allow_html=True,
            )
    st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
    section_head("BUILT ON REAL DATA", "No invented products. Ever.")
    values = [
        ("Real inventory", "Every product, price and review comes from our SQLite store."),
        ("Explainable AI", "LangChain tools search, rate and compare; Groq powers reasoning and vision."),
        ("You stay in control", "An order is written only after you explicitly confirm it."),
    ]
    cols = st.columns(3)
    for col, (title, body) in zip(cols, values):
        with col:
            st.markdown(
                f'<div class="sm-feature"><h4>{html.escape(title)}</h4><p>{html.escape(body)}</p></div>',
                unsafe_allow_html=True,
            )
    st.markdown('<hr class="sm-rule">', unsafe_allow_html=True)
    section_head("POWERED BY", "The stack")
    st.markdown(
        '<div style="margin-top:.7rem">'
        '<span class="sm-pill">LangChain</span><span class="sm-pill">Groq</span>'
        '<span class="sm-pill">Streamlit</span><span class="sm-pill">SQLite</span>'
        '<span class="sm-pill">Python</span></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if not st.session_state.get("user"):
    render_auth_page()
    st.stop()

render_header()
page = current_page()
{
    "home": render_home,
    "assistant": render_assistant,
    "explore": render_explore,
    "image": render_image_search,
    "orders": render_orders,
    "about": render_about,
}[page]()
