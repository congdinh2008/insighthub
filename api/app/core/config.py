"""
InsightHub API — Configuration
Provider-agnostic: chuyển embedding/LLM provider qua env var, không sửa code.

Hỗ trợ:
  LLM:        gemini (default) | anthropic | bedrock | ollama
  Embedding:  gemini (default) | voyage | openai | ollama | local

Mặc định Gemini vì free tier hào phóng + chất lượng tốt cho RAG.
Đổi provider chỉ cần sửa .env, không sửa code.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "InsightHub API"
    environment: str = "development"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "postgresql://insighthub:insighthub@postgres:5432/insighthub"

    # --- Redis (job queue) ---
    redis_url: str = "redis://redis:6379"

    # --- LLM provider: gemini (default) | anthropic | bedrock | ollama ---
    llm_provider: str = "gemini"

    # Gemini (Google AI Studio) — https://ai.google.dev/
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3-flash-preview"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-6"

    # Ollama (local) — chạy cùng cluster, không cần API key
    ollama_base_url: str = "http://ollama:11434"
    ollama_chat_model: str = "deepseek-r1:14b"

    # Generic LLM params (apply mọi provider)
    llm_model: str = ""           # nếu trống → dùng <provider>_chat_model
    llm_max_tokens: int = 1024

    # Day 4 (AIOps) chaos injection — delay nhân tạo trước mỗi LLM call (ms).
    # 0 = tắt (mặc định production). scripts/chaos/inject-llm-latency.sh set env
    # LLM_CHAOS_LATENCY_MS để mô phỏng Incident #1 (LLM latency spike). KHÔNG dùng prod.
    llm_chaos_latency_ms: int = 0

    # --- Embedding provider: gemini (default) | voyage | openai | ollama | local ---
    embedding_provider: str = "gemini"

    # Gemini embedding — Matryoshka support, output_dimensionality configurable
    # Ref: https://ai.google.dev/gemini-api/docs/embeddings
    gemini_embedding_model: str = "gemini-embedding-2"

    # Voyage AI
    voyage_api_key: str = ""
    voyage_embedding_model: str = "voyage-3.5"

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Ollama embedding — cùng model deepseek-r1 cho cả chat + embed
    ollama_embedding_model: str = "deepseek-r1:14b"

    # Generic embedding model name (nếu set, override provider-specific)
    embedding_model: str = ""

    # Vector dimension — PHẢI khớp VECTOR(n) trong infra/db/init.sql.
    # Default 1024:
    #   - Gemini: output_dimensionality=1024 (Matryoshka truncation, supported)
    #   - voyage-3.5: native 1024
    #   - openai text-embedding-3-small: cần đổi schema sang 1536 nếu dùng
    #   - Ollama (deepseek-r1:14b): native ~5120, truncate xuống 1024
    embedding_dim: int = 1024

    # --- RAG params ---
    chunk_size: int = 800          # tokens per chunk
    chunk_overlap: int = 100       # token overlap between chunks
    retrieval_top_k: int = 5       # chunks retrieved per query
    hnsw_ef_search: int = 100      # pgvector HNSW search width

    # ----- Helpers (provider-specific model resolution) -----

    @property
    def resolved_chat_model(self) -> str:
        """Trả về model name theo provider, ưu tiên override llm_model."""
        if self.llm_model:
            return self.llm_model
        provider = self.llm_provider.lower()
        if provider == "gemini":
            return self.gemini_chat_model
        if provider in ("anthropic", "bedrock"):
            return self.anthropic_chat_model
        if provider == "ollama":
            return self.ollama_chat_model
        return self.anthropic_chat_model  # safe default

    @property
    def resolved_embedding_model(self) -> str:
        """Trả về embedding model theo provider, ưu tiên override embedding_model."""
        if self.embedding_model:
            return self.embedding_model
        provider = self.embedding_provider.lower()
        if provider == "gemini":
            return self.gemini_embedding_model
        if provider == "voyage":
            return self.voyage_embedding_model
        if provider == "openai":
            return self.openai_embedding_model
        if provider == "ollama":
            return self.ollama_embedding_model
        return self.gemini_embedding_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
