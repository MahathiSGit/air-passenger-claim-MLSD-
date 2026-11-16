"""Application configuration supplied at runtime."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    app_title: str = "Air Passenger Claim Triage API"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    max_complaint_length: int = 10_000
    database_url: str = "sqlite:///./data/claims.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    rq_queue_name: str = "air-claim-queue"
    agent_mode: str = "demo"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    rate_limit_per_window: int = 20
    rate_limit_window_seconds: int = 60
    model_api_url: str = ""
    model_id: str = ""
    model_api_key: str = ""
    model_timeout_seconds: float = 20.0
    model_max_tokens: int = 512
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    otel_exporter_endpoint: str = ""
    @classmethod
    def from_environment(cls):
        return cls(
            app_title=os.getenv("API_TITLE", cls.app_title), app_version=os.getenv("API_VERSION", cls.app_version),
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
            max_complaint_length=int(os.getenv("MAX_COMPLAINT_LENGTH", cls.max_complaint_length)),
            database_url=os.getenv("DATABASE_URL", cls.database_url), redis_url=os.getenv("REDIS_URL", cls.redis_url),
            rq_queue_name=os.getenv("RQ_QUEUE_NAME", cls.rq_queue_name), agent_mode=os.getenv("AGENT_MODE", cls.agent_mode).strip().lower(),
            cors_origins=os.getenv("CORS_ORIGINS", cls.cors_origins),
            rate_limit_per_window=int(os.getenv("RATE_LIMIT_PER_WINDOW", cls.rate_limit_per_window)),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", cls.rate_limit_window_seconds)),
            model_api_url=os.getenv("MODEL_API_URL", ""), model_id=os.getenv("MODEL_ID", ""), model_api_key=os.getenv("MODEL_API_KEY", ""),
            model_timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", cls.model_timeout_seconds)),
            model_max_tokens=max(64, min(4096, int(os.getenv("MODEL_MAX_TOKENS", cls.model_max_tokens)))),
            input_cost_per_million=float(os.getenv("INPUT_COST_PER_MILLION", 0)), output_cost_per_million=float(os.getenv("OUTPUT_COST_PER_MILLION", 0)),
            otel_exporter_endpoint=os.getenv("OTEL_EXPORTER_ENDPOINT", ""),
        )
    @property
    def allowed_origins(self):
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
settings = Settings.from_environment()
