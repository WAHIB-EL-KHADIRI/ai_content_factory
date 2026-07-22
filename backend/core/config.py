"""Core configuration for AI Content OS"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///./ai_content_os.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    enabled: bool = False


@dataclass
class SecurityConfig:
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    api_key_prefix: str = "aco_"


@dataclass
class StorageConfig:
    upload_dir: str = "uploads"
    cache_dir: str = "cache"
    output_dir: str = "output"
    max_upload_size: int = 100 * 1024 * 1024  # 100MB


@dataclass
class ModelConfig:
    default_provider: str = "openai"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-sonnet-4-20250514"
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    tts_provider: str = os.getenv("TTS_PROVIDER", "elevenlabs")
    tts_api_key: str = os.getenv("TTS_API_KEY", "")
    image_provider: str = os.getenv("IMAGE_PROVIDER", "openai")
    image_api_key: str = os.getenv("IMAGE_API_KEY", "")


@dataclass
class WorkerConfig:
    enabled: bool = True
    concurrency: int = 4
    queue_max_size: int = 1000
    retry_max_attempts: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class AppConfig:
    name: str = "AI Content OS"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["http://localhost:3000"])
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    workers: WorkerConfig = field(default_factory=WorkerConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        config = cls()
        config.debug = os.getenv("APP_DEBUG", "false").lower() == "true"
        config.host = os.getenv("APP_HOST", config.host)
        config.port = int(os.getenv("APP_PORT", str(config.port)))
        config.database.url = os.getenv("DATABASE_URL", config.database.url)
        config.redis.host = os.getenv("REDIS_HOST", config.redis.host)
        config.redis.port = int(os.getenv("REDIS_PORT", str(config.redis.port)))
        config.redis.enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        config.models.default_provider = os.getenv(
            "DEFAULT_MODEL_PROVIDER", config.models.default_provider
        )
        return config

    def ensure_dirs(self):
        for d in [
            self.storage.upload_dir,
            self.storage.cache_dir,
            self.storage.output_dir,
        ]:
            Path(d).mkdir(parents=True, exist_ok=True)


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        _config.ensure_dirs()
    return _config


def set_config(config: AppConfig):
    global _config
    _config = config
