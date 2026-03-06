<div align="center">

![Centpai](assets/centpai.svg)

# Centpai

[𝙷𝚘𝚠 𝚝𝚘 Use](#) ✦ [𝙲𝚘𝚗𝚝𝚛𝚒𝚋𝚞𝚝𝚘𝚛𝚜](#contributors) ✦ [𝚂𝚙𝚘𝚗𝚜𝚘𝚛](#sponsor) ✦ 

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

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) (recommended)
- Python 3.11+ and [Poetry](https://python-poetry.org/)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A public URL for the webhook (e.g. [ngrok](https://ngrok.com/))

### Setup

1. Clone the repository

   ```bash
   git clone https://github.com/yyueda/centpai.git
   cd centpai
   ```

2. Create a `.env` file in the project root

   ```env
   BOT_TOKEN=<your telegram bot token>
   DATABASE_URL=<postgres or sqlite async url>
   NGROK_URL=<your public webhook url>
   ```

3. Run with Docker

   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```

   Or without Docker

   ```bash
   poetry install
   poetry run uvicorn app.main:app --reload
   ```

