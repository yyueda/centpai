# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Centpai

A Telegram bot for splitting expenses in group chats. Users add the bot to a Telegram group, join via `/join`, and then track shared expenses. The bot handles expense tracking, equal splits, and balance calculation.

## Development Setup

Requires a `.env` file with:
```
BOT_TOKEN=<telegram bot token>
DATABASE_URL=<postgres or sqlite async url>
NGROK_URL=<public url for webhook>
```

### Running locally (Docker)

```bash
docker compose -f docker-compose.dev.yml up --build
```

This runs FastAPI on port 8000 with hot-reload and a Postgres 17 instance. The app resets the database on every startup in dev mode (`init_reset_db_dev`).

### Running without Docker

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

There are no tests currently.

## Architecture

### Request Flow

Telegram sends webhook `POST /webhook` → `app/main.py` parses the update → dispatches to command handlers in `app/features/telegram/commands/` → handlers call `ExpensesService` → service calls `ExpensesRepository` → repository executes SQLAlchemy async queries.

### Layer Responsibilities

- **`app/main.py`**: FastAPI app, lifespan (webhook registration, DB init), webhook endpoint routing via `match` on `CommandName` or callback data.
- **`app/features/telegram/`**:
  - `client.py` — `TelegramAPI` wraps the Telegram Bot API over httpx. `Messenger` protocol allows testing.
  - `schemas.py` — Pydantic models for Telegram `Update`, `Message`, `CallbackQuery`, etc.
  - `context.py` — Builds a `Context` object (chat_id, user info) from an `Update`.
  - `commands/` — One file per command group: `admin.py` (help, init), `expenses.py` (add/view/remove), `members.py` (join/leave/list). Command parsing lives in `command_parser.py`.
- **`app/features/expenses/`**:
  - `service.py` — `ExpensesService`: business logic, transaction management (begin/commit/rollback), domain error enforcement.
  - `repo.py` — `ExpensesRepository`: all SQLAlchemy queries, no business logic.
  - `models.py` — SQLAlchemy ORM: `Chat`, `User`, `ChatMember`, `Expense`, `ExpenseSplit`, `Payment`, `Balance`.
  - `dto.py` — Data transfer objects returned from service to handlers.
  - `errors.py` — Domain-specific exceptions (`ChatNotFound`, `NotMember`, `ExpenseNotFoundError`, etc.) extending `app/core/errors.DomainError`.
- **`app/db/database.py`**: SQLAlchemy async engine setup, `get_session` dependency.
- **`app/core/config.py`**: `pydantic-settings` config loaded from `.env`.

### Database Models

`Chat` ←→ `User` via `ChatMember` (join table). `Expense` belongs to `Chat` + `User` (payer). `ExpenseSplit` tracks per-user share of an expense. `Balance` is a denormalized net balance per user per chat, updated on every `create_expense`.

### Key Design Notes

- Expenses are currently split equally among all chat members (splits for non-payers only; payer's balance increases by full amount).
- `init_reset_db_dev()` drops and recreates all tables on startup — switch to `init_db()` for production.
- The `add_member` repo method uses PostgreSQL's `ON CONFLICT DO NOTHING` — SQLite may not support this without dialect-aware handling.
- Transaction management is explicit in the service layer: `begin()` → work → `commit()` or `rollback()`.
