from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    discord_token: str | None = Field(default=None, alias="DISCORD_TOKEN")
    discord_guild_id: int | None = Field(default=None, alias="DISCORD_GUILD_ID")
    worklog_channel_id: int | None = Field(default=None, alias="WORKLOG_CHANNEL_ID")
    review_channel_id: int | None = Field(default=None, alias="REVIEW_CHANNEL_ID")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        alias="GEMINI_EMBEDDING_MODEL",
    )
    digest_trigger_token: str | None = Field(default=None, alias="DIGEST_TRIGGER_TOKEN")
    digest_channel_id: int | None = Field(default=None, alias="DIGEST_CHANNEL_ID")
    digest_post_hour_utc: int = Field(default=14, alias="DIGEST_POST_HOUR_UTC")
    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self._strip_sslmode_query(url)

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    @property
    def async_database_connect_args(self) -> dict[str, object]:
        parsed = urlparse(self.database_url)
        sslmode = parse_qs(parsed.query).get("sslmode", [None])[0]
        if sslmode in {"require", "verify-ca", "verify-full", "prefer"}:
            return {"ssl": True}
        if sslmode == "disable":
            return {"ssl": False}
        return {}

    @staticmethod
    def _strip_sslmode_query(url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.pop("sslmode", None)
        clean_query = urlencode({key: values[0] for key, values in query.items()})
        return urlunparse(parsed._replace(query=clean_query))


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
