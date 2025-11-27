# SLH Investor Gateway Bot (BOT_FACTORY)

FastAPI + python-telegram-bot v21 service running on Railway.

## Features

- Strategic investors gateway for SLH
- Link BNB (BSC) wallet to Telegram profile
- Off-chain SLH ledger (PostgreSQL via SQLAlchemy)
- Admin credit tool for allocations
- Internal transfers between investors
- On-chain balances placeholder module (for future BSC integration)
- Rich Telegram UX:
  - /menu with inline keyboard
  - /summary investor dashboard
  - /history – last transactions
  - /docs – link to investor documentation

## Project Structure

- `app/main.py` – FastAPI app + webhook endpoint + startup init
- `app/core/config.py` – Pydantic settings (env-based)
- `app/database.py` – SQLAlchemy engine, SessionLocal, Base
- `app/models.py` – User, Transaction models
- `app/crud.py` – DB helpers for users, balances and transfers
- `app/blockchain.py` – On-chain balance placeholder (SLH/BNB)
- `app/bot/investor_wallet_bot.py` – all Telegram logic

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# create .env from example
cp .env.example .env
# edit BOT_TOKEN, DATABASE_URL, etc.

uvicorn app.main:app --reload
```

Expose `http://localhost:8000/webhook/telegram` via ngrok if you want webhook locally.

## Deploying to Railway

- Create a new service from this repo.
- Set environment variables according to `.env.example`.
- Make sure `PORT` is set to `8080` in Railway (or change the Docker CMD).
- Telegram webhook will be set automatically on startup using `WEBHOOK_URL`.
