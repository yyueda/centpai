<div align="center">

![Centpai](assets/centpai.svg)

# Centpai

[𝙷𝚘𝚠 𝚃𝚘 𝚄𝚜𝚎](#how-to-use) ✦ [Getting Started](#getting-started) ✦ [𝙲𝚘𝚗𝚝𝚛𝚒𝚋𝚞𝚝𝚘𝚛𝚜](#contributors) ✦ [𝚂𝚙𝚘𝚗𝚜𝚘𝚛](#sponsor) ✦

Split expenses effortlessly in Telegram with Centpai. Track shared costs, settle balances, and keep everyone in sync — all without leaving your chat.

![Centpai Demo]()

</div>

<br>

<div align="center">

![Stars](https://img.shields.io/github/stars/yyueda/centpai?labelColor=F0F0E8&style=for-the-badge&color=1d4ed8)
![Forks](https://img.shields.io/github/forks/yyueda/centpai?labelColor=F0F0E8&style=for-the-badge&color=1d4ed8)
![Apache 2.0](https://img.shields.io/github/license/yyueda/centpai?labelColor=F0F0E8&style=for-the-badge&color=1d4ed8)
![version](https://img.shields.io/badge/Version-1.0-FFF?labelColor=F0F0E8&style=for-the-badge&color=1d4ed8)

</div>

> \[!IMPORTANT]
>
> This project is in active development. New features are being added continuously, and we welcome contributions from the community. If you have any suggestions or feature requests, please feel free to open an issue on GitHub.

## How To Use

No setup required — just find [@CentpaiBot](https://t.me/CentpaiBot) on Telegram and add it to any group of your choice. The bot will guide you from there.

1. Search for `@CentpaiBot` on Telegram
2. Add the bot to your group
3. Each member runs `/join` to register
4. Start adding expenses with `/expense_add <Amount> <Category> [split rule]`

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) (recommended)
- Python 3.11+ and [Poetry](https://python-poetry.org/)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A public URL for the webhook — sign up at [ngrok](https://ngrok.com/) and install the CLI

### Setup

1. Clone the repository

   ```bash
   git clone https://github.com/yyueda/centpai.git
   cd centpai
   ```

2. Create a `.env` file in the project root, following the example given in `.env.example`

   **With Docker:**
   ```env
   BOT_TOKEN=<your telegram bot token>
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/centpai_db
   WEBHOOK_URL=<your public webhook url>
   WEBHOOK_SECRET=<random secret string>
   ```

   **Without Docker** (use your own Postgres credentials):
   ```env
   BOT_TOKEN=<your telegram bot token>
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/<database>
   WEBHOOK_URL=<your public webhook url>
   WEBHOOK_SECRET=<random secret string>
   ```

   To get your `WEBHOOK_URL`, you can run ngrok in a separate terminal and copy the `Forwarding` URL:
   ```bash
   ngrok http 8000
   # Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
   ```

   > **Why ngrok?** Telegram's webhook requires a publicly reachable HTTPS URL to push updates to your bot. Since `localhost` isn't accessible from the internet, ngrok creates a secure tunnel that forwards Telegram's requests to your local server.

   You can generate a `WEBHOOK_SECRET` with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Run with Docker

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

   Or without Docker (requires a running Postgres instance on port 5432)

   ```bash
   poetry install
   poetry run uvicorn app.main:app --reload
   ```

## Sponsor

If you find Centpai useful, consider supporting its development:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/calvinchuayh)

## Contributors

<a href="https://github.com/yyueda/centpai/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=yyueda/centpai" />
</a>

