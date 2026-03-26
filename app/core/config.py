from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    BOT_TOKEN: str
    DATABASE_URL: str
<<<<<<< HEAD
    WEBHOOK_URL: str
=======
    NGROK_URL: str
>>>>>>> cc15d5b (chore: clean up and store all variables in env)
    WEBHOOK_SECRET: str


settings = Settings()  # type: ignore
