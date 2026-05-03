from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    admin_user_id: int
    database_path: str = "./data/bot.db"
    log_level: str = "INFO"
    environment: str = "development"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    free_quota_per_month: int = 3
    subscription_stars: int = 500
    single_summary_stars: int = 50

    # Proxy for youtube-transcript-api (needed on cloud/datacenter IPs)
    # Option A — Webshare rotating residential proxies (recommended):
    #   set both WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD
    # Option B — any HTTP/HTTPS proxy URL:
    #   set HTTPS_PROXY=http://user:pass@host:port
    supadata_api_key: str = ""

    # Proxy for youtube-transcript-api (fallback only, not needed when supadata_api_key is set)
    webshare_proxy_username: str = ""
    webshare_proxy_password: str = ""
    https_proxy: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
