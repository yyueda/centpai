import os

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("WEBHOOK_URL", "http://localhost")
os.environ.setdefault("WEBHOOK_SECRET", "abc123")
