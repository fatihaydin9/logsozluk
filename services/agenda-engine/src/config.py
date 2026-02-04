from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    port: int = 8081
    debug: bool = False
    
    # Test Mode - saatleri dakikalara düşürür
    test_mode: bool = True  # True = hızlı test, False = prod

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

    # Ollama Settings (local LLM)
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3:8b"
    use_ollama_for_comments: bool = True
    use_ollama_for_summarization: bool = True
    
    # News Summarization Settings
    enable_news_summarization: bool = True
    summarization_provider: str = "ollama"  # openai, ollama
    summarization_model: str = "llama3:8b"  # openai: gpt-4o-mini, ollama: llama3:8b
    summary_max_tokens: int = 300
    summary_temperature: float = 0.7
    report_output_dir: str = "data/output"

    # Virtual Day - test_mode=True ise 24 saat = 24 dakika olur
    virtual_day_duration_hours: int = 24

    # Agent Timing (dakika) - test_mode=True ise daha hızlı
    agent_entry_interval_minutes: int = 180  # prod: 3 saat
    agent_comment_interval_minutes: int = 30  # prod: 30 dk
    agent_max_pending_tasks: int = 5
    
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
