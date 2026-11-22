# ShopMate AI

An AI-powered shopping assistant built with Python, Streamlit, LangChain, Groq and SQLite.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Add a `.env` file in the project root with `GROQ_API_KEY=your_key` to enable the full AI agent (optional overrides: `GROQ_MODEL`, `GROQ_VISION_MODEL`).

## Project structure

```
shopping agent/
├── app.py                   Streamlit entry point (header/footer, six pages)
├── store.db                 Local SQLite database (not committed)
├── requirements.txt
├── .env                     Groq API key (not committed)
├── .gitignore
├── .streamlit/config.toml   Streamlit theme
│
├── backend/                 All application logic
│   ├── config.py            Paths, models, limits, env handling
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
