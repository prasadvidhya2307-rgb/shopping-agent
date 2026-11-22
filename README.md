# ShopMate AI

An AI-powered shopping assistant built with Python, Streamlit, LangChain, Groq and SQLite.

## Authentication

The app opens on a sign-in screen. Create an account or log in with username or email.
Passwords are stored as salted PBKDF2 hashes (`backend/auth.py`) — never in plain text.
Orders and chat history are scoped to the signed-in user. Click the initials chip in the
header to log out.

### Admin panel
Sign in with the single form on the sign-in screen — admin credentials go straight to
the panel (the shield icon in the header also opens it). A starter admin account is included:

```
username: admin
email:    admin@shopmate.local
password: Admin@12345
```

Change it after first login, or create your own:

```powershell
python -m backend.create_admin --username myadmin --email you@example.com
```

The panel shows all accounts and orders, store metrics, and lets you enable/disable users
(the last active admin cannot be disabled). Only accounts with `role='admin'` can access it.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Add a `.env` file in the project root with `GROQ_API_KEY=your_key` to enable the full AI agent (optional overrides: `GROQ_MODEL`, `GROQ_VISION_MODEL`).

## Project structure

```
shopping agent/
├── app.py                   Streamlit entry point (header/footer, five pages + admin)
├── store.db                 Local SQLite database (not committed)
├── requirements.txt
├── .env                     Groq API key (not committed)
├── .gitignore
├── .streamlit/config.toml   Streamlit theme
│
├── backend/                 All application logic
│   ├── config.py            Paths, models, limits, env handling
│   ├── auth.py              Accounts, password hashing, login, roles
│   ├── create_admin.py      Admin account bootstrap CLI
│   ├── utils.py             Validation, formatting, safe errors
│   ├── llm.py               Lazy Groq client construction
│   ├── database.py          SQLite connections, migrations, all SQL
│   ├── reviews_api.py       Rating aggregation
│   ├── db_utils.py          Helpers used by the frontend
│   ├── image_search.py      Upload validation + visual search
│   ├── order_service.py     Confirmation tokens, orders, idempotency
│   ├── chat_store.py        Persistent conversations
│   ├── tools.py             LangChain tools (search/rating/checkout/image)
│   ├── agent.py             Agent factory + safety guard
│   ├── shopping_agent.py    Backward-compatible facade
│   └── setup_db.py          Non-destructive database seeder
│
├── ui/                      Presentation layer
│   ├── styles.py            Theme CSS (dark/light)
│   └── components.py        Cards, chat bubbles, confirmations
│
├── assets/                  Product photography + brand logo
│   ├── honey.png
│   ├── oats.png
│   ├── elephant.png
│   └── logo.png
│
└── tests/                   pytest suite (Groq mocked)
    ├── conftest.py
    └── test_backend.py
```

## Tests

```powershell
python -m pytest tests -q
```

## Reseed the database

```powershell
python -m backend.setup_db
python -m backend.setup_db --reset   # explicit rebuild only
```
