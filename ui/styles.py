"""ShopMate — dual-theme storefront design system.

A complete visual rebuild: warm editorial light mode, deep forest dark mode,
Space Grotesk display type, lime/emerald accents, and fluid motion.
All styling is injected CSS; the app stays pure Streamlit.
"""

import streamlit as st

LIGHT = r"""
:root {
  --bg:#FAFAF7; --bg-2:#F1F4EE; --surface:#FFFFFF; --surface-2:#F6F8F3;
  --ink:#14201A; --muted:#68766C; --faint:#8C9A90;
  --border:#E2E8E0; --border-strong:#CBD6CB;
  --accent:#157A54; --accent-2:#B8DB3A; --accent-soft:#E6F3E7;
  --amber:#B77815; --shadow:0 10px 30px rgba(20,45,30,.07);
  --shadow-lg:0 22px 50px rgba(20,45,30,.14);
  --side-bg:linear-gradient(170deg,#123A2B 0%,#0B241B 100%);
  --side-fg:#EAF4EC; --side-muted:#A9C6B4; --side-accent:#C7EC60;
  --hero-bg:linear-gradient(115deg,#123B2C 0%,#1B5A3F 52%,#0D2A1E 100%);
  --hero-fg:#FFFFFF; --hero-sub:#CFE6D7;
  --btn-fg:#0B241B; --glow:0 0 0 4px rgba(184,219,58,.22);
}
"""

DARK = r"""
:root {
  --bg:#0D120F; --bg-2:#111813; --surface:#171F1A; --surface-2:#1D2720;
  --ink:#F1F6F0; --muted:#9BACA0; --faint:#7B8C80;
  --border:#2A352C; --border-strong:#3A4A3D;
  --accent:#5FDEA0; --accent-2:#C7EC60; --accent-soft:#1D3327;
  --amber:#E7B95B; --shadow:0 10px 30px rgba(0,0,0,.35);
  --shadow-lg:0 22px 50px rgba(0,0,0,.55);
  --side-bg:linear-gradient(170deg,#101A14 0%,#080D0A 100%);
  --side-fg:#F1F6F0; --side-muted:#9BACA0; --side-accent:#C7EC60;
  --hero-bg:linear-gradient(115deg,#123B2C 0%,#1B5A3F 52%,#0A1E15 100%);
  --hero-fg:#FFFFFF; --hero-sub:#CFE6D7;
  --btn-fg:#08130D; --glow:0 0 0 4px rgba(199,236,96,.16);
}
"""

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

* { font-family:'DM Sans',ui-sans-serif,system-ui,sans-serif; }
h1,h2,h3,h4,.sm-brand-name,.sm-title,.sm-stat-num,.sm-price,.sm-kicker,
.sm-badge,.sm-pill,.sm-hero-title { font-family:'Space Grotesk','DM Sans',sans-serif; }

/* ---------- Motion ---------- */
@keyframes sm-up { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
@keyframes sm-pop { from{opacity:0;transform:scale(.95)} to{opacity:1;transform:scale(1)} }
@keyframes sm-left { from{opacity:0;transform:translateX(-18px)} to{opacity:1;transform:translateX(0)} }
@keyframes sm-right { from{opacity:0;transform:translateX(18px)} to{opacity:1;transform:translateX(0)} }
@keyframes sm-float { 0%,100%{transform:translateY(0) rotate(-2deg)} 50%{transform:translateY(-14px) rotate(2deg)} }
@keyframes sm-float2 { 0%,100%{transform:translateY(0) rotate(3deg)} 50%{transform:translateY(-10px) rotate(-3deg)} }
@keyframes sm-mesh { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes sm-shine { from{transform:translateX(-140%)} to{transform:translateX(140%)} }
@keyframes sm-marquee { from{transform:translateX(0)} to{transform:translateX(-50%)} }

.sm-hero,.sm-panel,.sm-stat,.sm-card,.sm-bento,.sm-chat,.sm-order,
.sm-confirm,.sm-feature,.sm-drop { animation:sm-up .55s cubic-bezier(.2,.8,.3,1) both; }
.sm-kicker,.sm-title,.sm-sub { animation:sm-up .45s ease both; }
.sm-card,.sm-bento,.sm-feature { animation:sm-pop .5s cubic-bezier(.2,.8,.3,1) both; }
.sm-msg.user { animation:sm-right .4s ease both; }
.sm-msg.ai { animation:sm-left .4s ease both; }

/* ---------- Chrome ---------- */
#MainMenu,[data-testid="stAppDeployButton"],footer { visibility:hidden; }
header { display:none !important; }
[data-testid="stExpandSidebarButton"] { display:none !important; }
[data-testid="stAppViewContainer"],[data-testid="stApp"] { background:var(--bg); }
.block-container { max-width:1360px; padding:96px 3rem 5rem 3rem; }

/* ---------- No sidebar — header + footer navigation ---------- */
[data-testid="stSidebar"] { display:none !important; }
[data-testid="stSidebarCollapsedControl"] { display:none !important; }
header { visibility:hidden !important; }

.sm-header {
  position:fixed; top:0; left:0; width:100vw; z-index:80;
  display:grid; grid-template-columns:auto auto minmax(0,1fr) auto; align-items:center; gap:.8rem; box-sizing:border-box;
  height:66px; margin:0; padding:0 max(1.5rem, calc((100vw - 1360px) / 2 + 2rem));
  background:color-mix(in srgb,var(--bg) 94%,transparent);
  backdrop-filter:blur(18px); -webkit-backdrop-filter:blur(18px);
  border-bottom:1px solid var(--border);
}
.sm-header-brand { font-size:1.05rem !important; gap:.45rem !important; }
.sm-header-brand .sm-logo-img { width:32px !important; height:32px !important; border-radius:9px !important; }
.sm-search-slot { width:clamp(190px,20vw,270px); flex-shrink:0; height:38px; }
.sm-controls-slot { flex:1; min-width:0; }
[data-testid="stHorizontalBlock"]:has(div.st-key-navbtn_home) {
  position:fixed; z-index:91; top:12px;
  left:calc(max(1.5rem, (100vw - 1360px) / 2 + 2rem) + 126px + clamp(190px,20vw,270px) + 10px);
  right:max(1.5rem, (100vw - 1360px) / 2 + 2rem);
  width:auto; margin:0 !important; gap:0 !important;
}
[data-testid="stHorizontalBlock"]:has(div.st-key-navbtn_home) > div { min-width:0; }
[data-testid="stHorizontalBlock"]:has(div.st-key-navbtn_home) button {
  font-size:.72rem !important; padding:.3rem .35rem !important; min-height:34px !important;
}
[data-testid="stForm"]:has(input[placeholder="organic honey under 15 dollars"]) {
  position:fixed; z-index:90; top:13px;
  left:calc(max(1.5rem, (100vw - 1360px) / 2 + 2rem) + 126px);
  width:clamp(190px,20vw,270px);
  margin:0 !important; margin-top:0 !important; padding:0 !important;
  background:transparent !important; border:none !important; box-shadow:none !important;
}
[data-testid="stForm"]:has(input[placeholder="organic honey under 15 dollars"]) input {
  height:38px !important; border-radius:9px !important;
  background:var(--surface-2) !important; border:1px solid var(--border) !important;
  font-size:.76rem !important;
}
[data-testid="stForm"]:has(input[placeholder="organic honey under 15 dollars"]) button {
  height:38px !important; padding:.2rem !important; font-size:.72rem !important;
  min-width:34px !important;
}
.sm-header-brand {
  display:flex; align-items:center; gap:.6rem; text-decoration:none !important;
  font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700;
  letter-spacing:-.05em; color:var(--ink) !important; white-space:nowrap;
}
.sm-header-brand .sm-logo,
.sm-logo-img {
  width:36px; height:36px; border-radius:11px; display:block;
  background:var(--accent-2); color:#0B241B; font-size:1rem; font-weight:700;
  box-shadow:0 8px 18px rgba(184,219,58,.22);
}
.sm-logo-img.small { width:34px; height:34px; border-radius:10px; }
.sm-navbar {
  display:flex; align-items:center; gap:.1rem; min-width:0; flex-wrap:nowrap;
  justify-content:center; overflow-x:auto; scrollbar-width:none;
}
.sm-navbar::-webkit-scrollbar { display:none; }
.sm-navlink {
  padding:.42rem .5rem; border-radius:9px; text-decoration:none !important;
  color:var(--muted) !important; font-size:.74rem; font-weight:600;
  transition:all .2s ease; white-space:nowrap;
}
.sm-navlink:hover { color:var(--ink) !important; background:var(--surface-2); }
.sm-navlink.active {
  color:var(--accent) !important; background:var(--accent-soft);
  box-shadow:inset 0 -2px 0 var(--accent);
}
.sm-header-actions { display:flex; align-items:center; gap:.3rem; margin-left:auto; flex-shrink:0; }
.sm-action {
  padding:.42rem .55rem; border-radius:9px; border:1px solid var(--border);
  background:var(--surface); color:var(--ink) !important; text-decoration:none !important;
  font-size:.72rem; font-weight:600; white-space:nowrap; transition:all .2s ease;
}
.sm-action:hover { border-color:var(--accent); color:var(--accent) !important; transform:translateY(-1px); }
.sm-action.primary { background:var(--accent-2); color:var(--btn-fg) !important; border-color:transparent; }

.sm-footer {
  width:100vw; position:relative; left:50%; transform:translateX(-50%);
  box-sizing:border-box; margin:4rem 0 -5rem;
  padding:2.6rem max(3rem, calc((100vw - 1360px) / 2 + 3rem)) 2rem;
  border-top:1px solid var(--border); background:var(--surface);
  display:flex; flex-wrap:wrap; align-items:center; gap:1rem; justify-content:space-between;
}
.sm-footer-brand { display:flex; align-items:center; gap:.55rem; }
.sm-footer-brand b { font-family:'Space Grotesk',sans-serif; font-size:1rem; color:var(--ink); }
.sm-footer-brand span { color:var(--muted); font-size:.75rem; }
.sm-footer-links { display:flex; flex-wrap:wrap; gap:1rem; }
.sm-footer-links a { color:var(--muted) !important; text-decoration:none !important; font-size:.78rem; font-weight:600; }
.sm-footer-links a:hover { color:var(--accent) !important; }
.sm-footer-note { color:var(--faint) !important; font-size:.72rem; width:100%; }

/* ---------- Native widget contrast (both themes) ---------- */
input::placeholder,textarea::placeholder { color:var(--faint) !important; opacity:1 !important; }
[data-testid="stTextInput"] input,[data-testid="stChatInput"] textarea { color:var(--ink) !important; }
[data-testid="stApp"] label,
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stSlider"] label,
[data-testid="stSlider"] [data-baseweb="slider"] div,
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stMultiSelect"] span,
[data-testid="stAlert"] p,
[data-testid="stAlert"] div { color:var(--ink) !important; }
[data-testid="stAlert"] { background:var(--accent-soft) !important; border:1px solid var(--border) !important; }
[data-testid="stAlert"] p { color:var(--muted) !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] { background:var(--surface) !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stMultiSelect"] svg { color:var(--muted) !important; }
[data-baseweb="popover"] { background:var(--surface) !important; color:var(--ink) !important; }
[data-baseweb="menu"] div { color:var(--ink) !important; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"],[data-testid="stSidebar"] > div:first-child {
  background:var(--side-bg) !important; border-right:1px solid rgba(255,255,255,.06);
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.3rem; }
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small,[data-testid="stSidebar"] label { color:var(--side-muted) !important; }
.sm-brand { display:flex; align-items:center; gap:.75rem; padding:.5rem .35rem 1.5rem .35rem; }
.sm-logo {
  width:44px; height:44px; border-radius:14px; display:grid; place-items:center;
  background:var(--accent-2); color:#0B241B; font-family:'Space Grotesk',sans-serif;
  font-size:1.3rem; font-weight:700; box-shadow:0 10px 24px rgba(184,219,58,.22);
}
.sm-brand-name { color:var(--side-fg) !important; font-size:1.4rem; font-weight:700; letter-spacing:-.05em; line-height:1; }
.sm-brand-sub { color:var(--side-accent) !important; font-size:.58rem; font-weight:700; letter-spacing:.24em; margin-top:.3rem; }
.sm-nav-label {
  color:var(--side-muted) !important; opacity:.75; font-size:.62rem; font-weight:700;
  letter-spacing:.2em; text-transform:uppercase; padding:1.1rem .85rem .45rem .85rem;
}
.sm-nav-item {
  display:flex; align-items:center; height:44px; padding:0 .9rem; border-radius:12px;
  font-size:.9rem; font-weight:500; color:var(--side-muted) !important; margin-bottom:.2rem;
  transition:all .2s ease; position:relative;
}
.sm-nav-item.active {
  color:var(--side-fg) !important; font-weight:700;
  background:linear-gradient(100deg,rgba(199,236,96,.16),rgba(199,236,96,.03));
  box-shadow:inset 3px 0 0 var(--side-accent); animation:sm-up .35s ease both;
}
.sm-nav-item.active::after {
  content:""; width:6px; height:6px; border-radius:50%; margin-left:auto;
  background:var(--side-accent); box-shadow:0 0 12px var(--side-accent);
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
  background:transparent !important; border:none !important; color:var(--side-muted) !important;
  height:44px !important; padding:0 .9rem !important; border-radius:12px !important;
  font-size:.9rem !important; font-weight:500 !important; text-align:left !important;
  justify-content:flex-start !important; box-shadow:none !important; margin-bottom:.2rem !important;
  transition:all .2s ease !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] p { color:var(--side-muted) !important; }
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover p {
  background:rgba(255,255,255,.08) !important; color:var(--side-fg) !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
  background:var(--accent-2) !important; color:#0B241B !important; margin-top:1rem !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] p { color:#0B241B !important; }

/* ---------- Authentication ---------- */
.sm-auth-brand { display:flex; align-items:center; justify-content:center; gap:.8rem; margin:4vh 0 1.5rem; }
.sm-auth-brand img { width:46px; height:46px; border-radius:13px; }
.sm-auth-brand b { display:block; font-family:'Space Grotesk',sans-serif; font-size:1.5rem; color:var(--ink); letter-spacing:-.05em; }
.sm-auth-brand span { color:var(--muted); font-size:.75rem; }
.sm-auth-title { font-family:'Space Grotesk',sans-serif; font-size:1.7rem; font-weight:700; color:var(--ink); text-align:center; margin-top:1rem; }
.sm-auth-sub { color:var(--muted); font-size:.85rem; text-align:center; margin:.3rem 0 1.5rem; }
.sm-auth-note { color:var(--faint); font-size:.74rem; text-align:center; margin-top:1.2rem; line-height:1.5; }
.sm-user {
  width:34px; height:34px; border-radius:50%; display:grid; place-items:center; flex-shrink:0;
  background:var(--accent); color:var(--btn-fg) !important; font-family:'Space Grotesk',sans-serif;
  font-size:.72rem; font-weight:700; text-decoration:none !important; transition:box-shadow .2s ease;
}
.sm-user:hover { box-shadow:var(--glow); }

/* ---------- Type ---------- */
h1,h2,h3,h4 { color:var(--ink) !important; letter-spacing:-.04em; }
.sm-kicker {
  display:inline-block; color:var(--accent) !important; font-size:.68rem; font-weight:700;
  letter-spacing:.22em; text-transform:uppercase; margin-bottom:.6rem;
}
.sm-title { font-size:1.7rem; font-weight:700; color:var(--ink); margin:0 0 .25rem 0; letter-spacing:-.05em; }
.sm-sub { color:var(--muted); font-size:.9rem; margin:0 0 1.4rem 0; line-height:1.55; }
.sm-rule { height:1px; background:var(--border); border:0; margin:2.4rem 0; }

/* ---------- Hero ---------- */
.sm-hero {
  position:relative; overflow:hidden; border-radius:28px; padding:3.4rem 3.4rem 3.1rem;
  background:var(--hero-bg); background-size:180% 180%; animation:sm-mesh 16s ease infinite, sm-up .6s ease both;
  color:var(--hero-fg); border:1px solid rgba(199,236,96,.16); box-shadow:var(--shadow-lg);
  margin-bottom:1.6rem; min-height:300px;
}
.sm-hero::before,.sm-hero::after { content:""; position:absolute; border-radius:50%; pointer-events:none; }
.sm-hero::before {
  width:420px; height:420px; right:-120px; top:-150px;
  background:radial-gradient(circle,rgba(199,236,96,.24),transparent 70%);
  animation:sm-float 12s ease-in-out infinite;
}
.sm-hero::after {
  width:340px; height:340px; left:-120px; bottom:-180px;
  background:radial-gradient(circle,rgba(91,222,160,.22),transparent 70%);
  animation:sm-float2 10s ease-in-out infinite;
}
.sm-hero-title {
  font-size:3.2rem; line-height:1.02; font-weight:700; margin:0 0 1rem 0;
  max-width:70%; position:relative; z-index:2; color:var(--hero-fg) !important;
}
.sm-hero-title em { font-style:normal; color:var(--accent-2); }
.sm-hero-copy {
  color:var(--hero-sub) !important; font-size:1rem; line-height:1.65; max-width:56%;
  margin:0 0 1.5rem 0; position:relative; z-index:2;
}
.sm-hero-art {
  position:absolute; right:2rem; top:50%; transform:translateY(-50%); z-index:1;
  display:flex; align-items:center;
}
.sm-hero-art .a1 {
  width:230px; height:230px; border-radius:50%; overflow:hidden; object-fit:cover;
  border:7px solid rgba(255,255,255,.14); box-shadow:0 26px 60px rgba(0,0,0,.45);
  animation:sm-float 8s ease-in-out infinite;
}
.sm-hero-art .a2 {
  width:108px; height:108px; border-radius:50%; overflow:hidden; object-fit:cover;
  border:5px solid rgba(255,255,255,.14); margin-left:-42px; margin-top:110px;
  box-shadow:0 18px 40px rgba(0,0,0,.4); animation:sm-float2 6s ease-in-out infinite;
}
.sm-ticker {
  overflow:hidden; border-top:1px solid rgba(255,255,255,.1); margin-top:2.2rem;
  padding-top:1.1rem; position:relative; z-index:2;
  -webkit-mask-image:linear-gradient(to right,transparent,#000 9%,#000 91%,transparent);
  mask-image:linear-gradient(to right,transparent,#000 9%,#000 91%,transparent);
}
.sm-ticker-track { display:flex; width:max-content; animation:sm-marquee 30s linear infinite; }
.sm-ticker-group { display:flex; align-items:center; gap:4rem; padding-right:4rem; flex-shrink:0; }
.sm-ticker span { color:var(--hero-sub); }
.sm-ticker b { color:var(--accent-2); }
.sm-ticker .claim { text-transform:none; letter-spacing:.01em; font-size:.86rem; font-weight:500; text-align:center; }
.sm-ticker .claim b { font-weight:700; letter-spacing:-.01em; }

/* ---------- Search ---------- */
.sm-search-card {
  background:var(--surface); border:1px solid var(--border); border-radius:18px;
  padding:.6rem .75rem; box-shadow:var(--shadow);
}
.sm-suggest-label { color:var(--faint) !important; font-size:.7rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; margin:1rem 0 .5rem; }
.sm-chip {
  display:inline-block; padding:.45rem .8rem; border-radius:999px; border:1px solid var(--border);
  background:var(--surface); color:var(--ink); font-size:.78rem; font-weight:600;
  text-decoration:none !important; transition:all .2s ease;
}
.sm-chip:hover { border-color:var(--accent); color:var(--accent); transform:translateY(-2px); }

/* ---------- Stat ribbon ---------- */
.sm-stats { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin:1.4rem 0 2rem; }
.sm-stat {
  background:var(--surface); border:1px solid var(--border); border-radius:16px;
  padding:1.1rem 1.2rem; box-shadow:var(--shadow); transition:transform .25s ease,border-color .25s ease;
}
.sm-stat:hover { transform:translateY(-4px); border-color:var(--accent); }
.sm-stat-num { font-size:1.8rem; font-weight:700; color:var(--accent); letter-spacing:-.05em; line-height:1; }
.sm-stat-label { color:var(--muted); font-size:.72rem; font-weight:600; margin-top:.35rem; }

/* ---------- Cards ---------- */
.sm-card {
  position:relative; background:var(--surface); border:1px solid var(--border);
  border-radius:18px; overflow:hidden; box-shadow:var(--shadow); height:100%;
  display:flex; flex-direction:column; transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;
}
.sm-card:hover { transform:translateY(-6px); box-shadow:var(--shadow-lg); border-color:var(--accent); }
.sm-card::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(110deg,transparent 42%,rgba(255,255,255,.12) 50%,transparent 58%);
  transform:translateX(-140%); transition:transform .7s ease;
}
.sm-card:hover::after { animation:sm-shine .9s ease forwards; }
.sm-card-media { height:168px; width:100%; overflow:hidden; background:var(--surface-2); }
.sm-card-media img { width:100%; height:100%; object-fit:cover; transition:transform .5s cubic-bezier(.2,.8,.3,1); }
.sm-card:hover .sm-card-media img { transform:scale(1.08); }
.sm-card-body { padding:1rem 1.05rem 1.1rem; display:flex; flex-direction:column; flex:1; }
.sm-card-top { display:flex; justify-content:space-between; gap:.4rem; margin-bottom:.6rem; }
.sm-badge { font-size:.6rem; font-weight:700; padding:.28rem .6rem; border-radius:999px; white-space:nowrap; }
.sm-badge.green { color:var(--accent); background:var(--accent-soft); border:1px solid rgba(95,222,160,.25); }
.sm-badge.soft { color:var(--muted); background:var(--surface-2); border:1px solid var(--border); }
.sm-badge.lime { color:#3A4A0B; background:var(--accent-2); }
.sm-name { font-size:.98rem; font-weight:700; color:var(--ink); line-height:1.25; margin-bottom:.35rem; }
.sm-desc { font-size:.74rem; color:var(--muted); line-height:1.5; min-height:2.2em; margin-bottom:.8rem; }
.sm-foot { display:flex; align-items:center; justify-content:space-between; margin-top:auto; }
.sm-price { color:var(--accent); font-size:1.1rem; font-weight:700; letter-spacing:-.04em; }
.sm-rating { font-size:.78rem; color:var(--amber); font-weight:700; white-space:nowrap; }
.sm-rating small { color:var(--muted); font-weight:500; font-size:.68rem; margin-left:.2rem; }

/* ---------- Bento categories ---------- */
.sm-bento { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; }
.sm-bento-tile {
  display:block; text-decoration:none !important; border-radius:18px; overflow:hidden;
  border:1px solid var(--border); background:var(--surface); box-shadow:var(--shadow);
  transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;
}
.sm-bento-tile:hover { transform:translateY(-5px); box-shadow:var(--shadow-lg); border-color:var(--accent); }
.sm-bento-tile img { width:100%; height:120px; object-fit:cover; display:block; }
.sm-bento-label { padding:.8rem 1rem 1rem; }
.sm-bento-label b { display:block; color:var(--ink); font-size:.9rem; font-family:'Space Grotesk',sans-serif; }
.sm-bento-label span { color:var(--muted); font-size:.72rem; }

/* ---------- Buttons ---------- */
button[data-testid^="stBaseButton-"] {
  border-radius:11px !important; font-weight:600 !important; font-size:.84rem !important;
  padding:.55rem 1rem !important; border:1px solid transparent !important; transition:all .2s ease !important;
}
button[data-testid^="stBaseButton-primary"] {
  position:relative; overflow:hidden; background:var(--accent-2) !important;
  color:var(--btn-fg) !important; box-shadow:0 8px 20px rgba(184,219,58,.2) !important;
  white-space:nowrap !important;
}
button[data-testid^="stBaseButton-primary"] p { color:var(--btn-fg) !important; }
button[data-testid^="stBaseButton-primary"]::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(110deg,transparent 35%,rgba(255,255,255,.5) 50%,transparent 65%);
  transform:translateX(-140%); transition:transform .6s ease;
}
button[data-testid^="stBaseButton-primary"]:hover::after { transform:translateX(140%); }
button[data-testid^="stBaseButton-primary"]:hover { transform:translateY(-2px); box-shadow:0 14px 28px rgba(184,219,58,.32) !important; }
button[data-testid="stBaseButton-secondary"] {
  background:var(--surface) !important; color:var(--ink) !important; border-color:var(--border) !important;
}
button[data-testid="stBaseButton-secondary"] p { color:var(--ink) !important; }
button[data-testid="stBaseButton-secondary"]:hover { border-color:var(--accent) !important; background:var(--surface-2) !important; box-shadow:var(--glow); }
button[data-testid^="stBaseButton-"]:active { transform:scale(.97) !important; }

/* ---------- Chat ---------- */
.sm-chat {
  background:transparent; border:0; border-radius:0;
  box-shadow:none; padding:.4rem 0; min-height:0;
}
.sm-msg { display:flex; gap:.75rem; margin:1rem 0; align-items:flex-end; }
.sm-msg.user { flex-direction:row-reverse; }
.sm-avatar {
  width:36px; height:36px; border-radius:12px; flex-shrink:0; display:grid; place-items:center;
  font-size:.62rem; font-weight:700; letter-spacing:.04em;
  background:var(--accent-soft); color:var(--accent); border:1px solid rgba(95,222,160,.25);
}
.sm-msg.user .sm-avatar { background:var(--accent-2); color:#0B241B; border:none; }
.sm-bubble {
  max-width:76%; padding:.8rem 1.05rem; border-radius:16px; font-size:.88rem; line-height:1.65;
  background:var(--surface-2); border:1px solid var(--border); color:var(--ink);
  border-bottom-left-radius:5px; white-space:pre-wrap; transition:transform .2s ease;
}
.sm-msg.user .sm-bubble {
  background:var(--accent); color:#08150E; border:none;
  border-bottom-left-radius:16px; border-bottom-right-radius:5px; font-weight:500;
}
.sm-msg.ai .sm-bubble:hover { transform:translateX(3px); }
.sm-msg.user .sm-bubble:hover { transform:translateX(-3px); }
.sm-inline { max-width:76%; margin:.5rem 0 .5rem 3rem; }
.sm-inline .sm-card { border-radius:14px; }
.sm-inline .sm-card-media { height:110px; }
.sm-typing { display:inline-flex; gap:4px; align-items:center; }
.sm-typing i { width:6px; height:6px; border-radius:50%; background:var(--accent); animation:sm-float2 1s infinite; }

[data-testid="stChatInput"] textarea {
  border-radius:14px !important; border:1px solid var(--border) !important;
  background:var(--surface) !important; color:var(--ink) !important;
  box-shadow:var(--shadow) !important; padding:.85rem 1rem !important;
}
[data-testid="stChatInput"] textarea:focus { border-color:var(--accent) !important; box-shadow:var(--glow) !important; }

/* ---------- Panels / orders / confirm ---------- */
.sm-panel {
  background:var(--surface); border:1px solid var(--border); border-radius:20px;
  padding:1.4rem; box-shadow:var(--shadow);
}
.sm-drop {
  border:2px dashed var(--border-strong); border-radius:20px; padding:2.4rem; text-align:center;
  background:var(--surface-2); transition:all .25s ease;
}
.sm-drop:hover { border-color:var(--accent); background:var(--accent-soft); transform:translateY(-2px); }
.sm-drop b { display:block; color:var(--ink); font-size:1rem; font-family:'Space Grotesk',sans-serif; }
.sm-drop span { color:var(--muted); font-size:.8rem; }
.sm-preview { border-radius:18px; overflow:hidden; border:1px solid var(--border); box-shadow:var(--shadow); background:var(--surface); padding:.5rem; }
.sm-preview img { width:100%; max-height:340px; object-fit:contain; border-radius:12px; }
.sm-confirm {
  border:1px solid var(--accent); background:var(--accent-soft); border-radius:18px;
  padding:1.2rem 1.3rem; margin-top:1.2rem; box-shadow:var(--shadow);
}
.sm-confirm b { color:var(--accent); font-family:'Space Grotesk',sans-serif; }
.sm-confirm p { color:var(--muted); font-size:.85rem; line-height:1.6; margin:.4rem 0 0; }
.sm-order {
  display:flex; align-items:center; gap:1.1rem; background:var(--surface);
  border:1px solid var(--border); border-radius:16px; padding:1.1rem 1.3rem;
  margin-bottom:.8rem; box-shadow:var(--shadow); transition:transform .25s ease,border-color .25s ease;
}
.sm-order:hover { transform:translateX(5px); border-color:var(--accent); }
.sm-order-icon {
  width:48px; height:48px; border-radius:14px; display:grid; place-items:center; flex-shrink:0;
  background:var(--accent-soft); color:var(--accent); font-family:'Space Grotesk',sans-serif;
  font-size:1.1rem; font-weight:700; border:1px solid rgba(95,222,160,.22);
}
.sm-order-main { flex:1; min-width:0; }
.sm-order-main b { color:var(--ink); font-size:.94rem; }
.sm-order-main span { color:var(--muted); font-size:.74rem; display:block; margin-top:.25rem; }
.sm-order-price { color:var(--accent); font-weight:700; font-size:1.05rem; font-family:'Space Grotesk',sans-serif; }
.sm-status { font-size:.64rem; font-weight:700; padding:.3rem .65rem; border-radius:999px; background:var(--accent-soft); color:var(--accent); border:1px solid rgba(95,222,160,.25); white-space:nowrap; }
.sm-feature {
  background:var(--surface); border:1px solid var(--border); border-radius:18px;
  padding:1.5rem; height:100%; box-shadow:var(--shadow); transition:transform .25s ease,border-color .25s ease;
}
.sm-feature:hover { transform:translateY(-5px); border-color:var(--accent); }
.sm-feature h4 { margin:.7rem 0 .4rem; font-size:1rem; }
.sm-feature p { color:var(--muted); font-size:.82rem; line-height:1.65; margin:0; }
.sm-step {
  width:30px; height:30px; border-radius:10px; display:grid; place-items:center;
  background:var(--accent-2); color:#0B241B; font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:.8rem;
}
.sm-pill {
  display:inline-block; padding:.4rem .8rem; border-radius:999px; background:var(--accent-soft);
  color:var(--accent); border:1px solid rgba(95,222,160,.22); font-size:.74rem; font-weight:600; margin:.2rem .35rem .2rem 0;
}
.sm-note {
  border-radius:14px; padding:.85rem 1.1rem; font-size:.83rem; line-height:1.5;
  background:var(--accent-soft); border:1px solid rgba(95,222,160,.25); color:var(--accent); margin-bottom:1rem;
}

/* ---------- Widgets ---------- */
[data-testid="stTextInput"] input,[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  border-radius:11px !important; border:1px solid var(--border) !important;
  background:var(--surface) !important; color:var(--ink) !important;
}
[data-testid="stForm"] {
  background:var(--surface) !important; border:1px solid var(--border) !important;
  border-radius:14px !important; padding:.45rem .7rem !important; box-shadow:var(--shadow) !important;
}
[data-testid="stFileUploader"] section,[data-testid="stFileUploaderDropzone"] {
  border:2px dashed var(--border-strong) !important; border-radius:16px !important;
  background:var(--surface) !important; padding:1.1rem !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color:var(--accent) !important; }
[data-testid="stSlider"] { padding-top:.2rem !important; }
hr { border-color:var(--border) !important; }
::-webkit-scrollbar { width:9px;height:9px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border-strong); border-radius:999px; border:2px solid var(--bg); }
::-webkit-scrollbar-thumb:hover { background:var(--accent); }
@media (prefers-reduced-motion:reduce) {
  *,*::before,*::after { animation-duration:.001ms !important; animation-iteration-count:1 !important; transition-duration:.001ms !important; }
}
@media (max-width:900px) {
  .block-container { padding:130px 1.1rem 4rem 1.1rem; }
  .sm-header { padding:.7rem 1.1rem; height:auto; flex-wrap:wrap; gap:.6rem; }
  .sm-search-slot { display:none; }
  [data-testid="stHorizontalBlock"]:has(div.st-key-navbtn_home) {
    position:static; width:auto; margin:.8rem 0 1.2rem !important;
    overflow-x:auto; padding-bottom:.3rem;
  }
  [data-testid="stForm"]:has(input[placeholder="organic honey under 15 dollars"]) {
    position:static; width:auto; margin:.8rem 0 1.2rem !important;
    background:var(--surface) !important; border:1px solid var(--border) !important;
    border-radius:12px !important; padding:.4rem .6rem !important;
  }
  .sm-navbar { order:3; width:100%; overflow-x:auto; }
  .sm-footer { margin:3rem 0 -4rem; padding:2rem 1.1rem; }
  .sm-hero { padding:2.2rem 1.6rem; }
  .sm-hero-title { font-size:2.2rem; max-width:100%; }
  .sm-hero-copy { max-width:100%; }
  .sm-hero-art { display:none; }
  .sm-stats { grid-template-columns:repeat(2,1fr); }
  .sm-bento { grid-template-columns:repeat(2,1fr); }
  .sm-bubble,.sm-inline { max-width:92%; }
}
"""

SIDE_LIGHT = r"""
[data-testid="stSidebar"],[data-testid="stSidebar"] > div:first-child { background:linear-gradient(170deg,#123A2B 0%,#0B241B 100%) !important; }
"""
SIDE_DARK = r"""
[data-testid="stSidebar"],[data-testid="stSidebar"] > div:first-child { background:linear-gradient(170deg,#101A14 0%,#080D0A 100%) !important; }
"""


def inject_css(theme: str = "dark") -> None:
    variables = LIGHT if theme == "light" else DARK
    st.markdown(f"<style>{variables}{CSS}</style>", unsafe_allow_html=True)
