from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM backend: "claude" | "openai_compat" (Groq, Ollama, OpenRouter, etc.)
    LLM_BACKEND: str = "openai_compat"

    # Anthropic (used when LLM_BACKEND=claude)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL_FAST: str = "claude-sonnet-4-6"
    CLAUDE_MODEL_SMART: str = "claude-opus-4-7"

    # OpenAI-compatible backend (used when LLM_BACKEND=openai_compat)
    OPENAI_COMPAT_BASE_URL: str = "https://api.groq.com/openai/v1"
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL: str = "llama-3.3-70b-versatile"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://yag:yag_dev_password@postgres:5432/yag"
    REDIS_URL: str = "redis://redis:6379/0"

    # Telegram
    TG_ADMIN_BOT_TOKEN: str = ""
    TG_ADMIN_USER_ID: int = 0
    TG_CHANNEL_ID: str = ""
    TG_CHANNEL_URL: str = ""
    TG_SUBSCRIBER_BOT_TOKEN: str = ""
    TG_SUBSCRIBER_BOT_USERNAME: str = ""

    # Sources
    YOUTUBE_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "YAg/1.0"
    X_BEARER_TOKEN: str = ""

    # Publishing
    IG_USER_ID: str = ""
    IG_ACCESS_TOKEN: str = ""
    YT_CLIENT_ID: str = ""
    YT_CLIENT_SECRET: str = ""
    YT_REFRESH_TOKEN: str = ""

    # Payments
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    PRODAMUS_SHOP: str = ""
    PRODAMUS_SECRET: str = ""

    # Misc
    TZ: str = "Europe/Moscow"
    LOG_LEVEL: str = "INFO"
    STORAGE_DIR: str = "/app/storage"

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        (p / "drafts").mkdir(parents=True, exist_ok=True)
        (p / "media").mkdir(parents=True, exist_ok=True)
        (p / "clips").mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
