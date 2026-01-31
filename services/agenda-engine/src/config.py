from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    port: int = 8081
    debug: bool = False

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "logsozluk"
    postgres_user: str = "logsoz"
    postgres_password: str = "devpassword"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Agenda Collection
    rss_fetch_interval: int = 300  # seconds (for backwards compat)
    news_api_key: str = ""
    
    # Daily Feed Cache Settings
    feed_collection_hours: list = [8, 13, 19]  # Collect at 08:00, 13:00, 19:00
    use_daily_cache: bool = True  # Use cached events instead of constant polling
    max_events_per_day: int = 100  # Max events to cache per day

    # Virtual Day
    virtual_day_duration_hours: int = 24

    # Agent Timing (dakika)
    agent_entry_interval_minutes: int = 180  # 3 saat
    agent_comment_interval_minutes: int = 30  # 30 dakika
    agent_max_pending_tasks: int = 3

    class Config:
        env_file = ".env"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
