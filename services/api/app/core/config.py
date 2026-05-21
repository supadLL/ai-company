from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Company Local API"
    database_url: str = "sqlite:///./ai_company.db"
    local_session_secret: str = "dev-local-secret"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
