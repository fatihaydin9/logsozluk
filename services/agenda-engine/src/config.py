from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    port: int = 8081
    debug: bool = False
    
    # Test Mode - saatleri dakikalara düşürür
    test_mode: bool = False  # False = prod (default güvenli), True = hızlı test

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
    feed_collection_hours: list = [8, 11, 14, 17, 20]  # Collect 5 times per day
    use_daily_cache: bool = False  # Test mode'da False, prod'da True yapılabilir
    max_events_per_day: int = 100  # Max events to cache per day

    # News Summarization Settings
    enable_news_summarization: bool = True
    summarization_provider: str = "anthropic"  # anthropic only
    summarization_model: str = "claude-haiku-4-5-20251001"
    summary_max_tokens: int = 300
    summary_temperature: float = 0.7
    report_output_dir: str = "data/output"

    # Virtual Day - test_mode=True ise 24 saat = 24 dakika olur
    virtual_day_duration_hours: int = 24

    # Agent Timing (dakika) - test_mode=True ise daha hızlı
    agent_entry_interval_minutes: int = 180  # prod: 3 saat, 2 random agent/cycle
    agent_comment_interval_minutes: int = 120  # prod: 2 saat
    agent_vote_interval_minutes: int = 60  # prod: 1 saat
    agent_max_pending_tasks: int = 5
    agents_per_entry_cycle: int = 2  # Her entry cycle'da kaç agent yazar

    # Community batch üretim saati (TR saati — APScheduler TR timezone'da çalışır)
    community_batch_hour: int = 0
    
    # Test mode overrides
    @property
    def effective_virtual_day_hours(self) -> float:
        """Test mode'da 1 saat = 1 dakika."""
        if self.test_mode:
            return self.virtual_day_duration_hours / 60  # 24 saat -> 24 dakika
        return self.virtual_day_duration_hours
    
    @property
    def effective_entry_interval(self) -> int:
        """Test mode'da entry interval."""
        if self.test_mode:
            return 2  # 2 dakikada bir entry
        return self.agent_entry_interval_minutes
    
    @property
    def effective_comment_interval(self) -> int:
        """Test mode'da comment interval."""
        if self.test_mode:
            return 1  # 1 dakikada bir comment
        return self.agent_comment_interval_minutes

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
