from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILES = (".env", ".env.local")


class MyLLMSettings(BaseSettings):
    """
    Settings for the primary LLM endpoint (e.g. Groq).
    Reads all MYLLM_* vars from .env.
    """
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="MYLLM_",
    )

    API_URL:                      str   = ""
    AUTH_TOKEN:                   str   = ""
    MODEL_NAME:                   str   = ""
    TIMEOUT_SECONDS:              int   = 60
    MAX_RETRIES:                  int   = 3
    RETRY_DELAY_SECONDS:          float = 2.0
    HEALTH_CHECK_ATTEMPTS:        int   = 2
    HEALTH_CHECK_TIMEOUT_SECONDS: int   = 10
    HEALTH_CHECK_COOLDOWN_SECONDS: int  = 60


class BackupLLMSettings(BaseSettings):
    """
    Settings for the backup / fallback LLM endpoint (e.g. OpenRouter).
    Reads all BACKUP_LLM_* vars from .env.
    """
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="BACKUP_LLM_",
    )

    ENABLED:                      bool  = False
    API_URL:                      str   = "https://openrouter.ai/api/v1/chat/completions"
    AUTH_TOKEN:                   str   = ""
    MODEL_NAME:                   str   = "inclusionai/ling-3.2-flash:free"
    TIMEOUT_SECONDS:              int   = 30
    MAX_RETRIES:                  int   = 2
    RETRY_DELAY_SECONDS:          float = 1.0


class MCPSettings(BaseSettings):
    """
    Settings for the MCP server connection.
    Reads MCP_* vars from .env.
    """
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="MCP_",
    )

    SERVER_SCRIPT: str = "main.py"


class Settings:
    """
    Master settings object — aggregates all setting groups.
    Use get_settings() factory — never instantiate directly.
    """
    def __init__(self) -> None:
        self.my_llm     = MyLLMSettings()
        self.backup_llm = BackupLLMSettings()
        self.mcp        = MCPSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Factory method — creates Settings once, cached forever.
    Every module calls this — never imports Settings directly.
    """
    return Settings()
