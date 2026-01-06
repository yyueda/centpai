from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    BOT_TOKEN: str
    DATABASE_URL: str
    NGROK_URL: str

settings = Settings() # type: ignore
