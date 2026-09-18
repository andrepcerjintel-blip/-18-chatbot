"""Configuracao central da aplicacao.

Toda configuracao vem de variaveis de ambiente / arquivo .env. Nenhum
segredo deve ser hardcoded no codigo-fonte.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT / 'backend' / 'data' / 'app.db'}",
        alias="DATABASE_URL",
    )

    llm_provider: str = Field(default="stub", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    # LLM local via gpt4all (motor compativel com llama.cpp), 100% offline,
    # sem chave de API. CPU por padrao (LOCAL_LLM_DEVICE=cpu) para nao
    # disputar VRAM com o ComfyUI na mesma GPU de 4 GB -- ver HARDWARE.md.
    local_llm_model_path: str = Field(default="", alias="LOCAL_LLM_MODEL_PATH")
    local_llm_ctx_size: int = Field(default=4096, alias="LOCAL_LLM_CTX_SIZE")
    local_llm_threads: int = Field(default=0, alias="LOCAL_LLM_THREADS")
    local_llm_device: str = Field(default="cpu", alias="LOCAL_LLM_DEVICE")
    local_llm_max_tokens: int = Field(default=300, alias="LOCAL_LLM_MAX_TOKENS")
    local_llm_temperature: float = Field(default=0.8, alias="LOCAL_LLM_TEMPERATURE")

    gpu_vendor: str = Field(default="UNKNOWN", alias="GPU_VENDOR")
    gpu_model: str = Field(default="UNKNOWN", alias="GPU_MODEL")
    gpu_vram_gb: str = Field(default="UNKNOWN", alias="GPU_VRAM_GB")
    gpu_backend: str = Field(default="UNKNOWN", alias="GPU_BACKEND")
    gpu_driver_version: str = Field(default="UNKNOWN", alias="GPU_DRIVER_VERSION")
    cuda_version: str = Field(default="UNKNOWN", alias="CUDA_VERSION")

    media_provider: str = Field(default="null", alias="MEDIA_PROVIDER")
    comfyui_url: str = Field(default="http://127.0.0.1:8188", alias="COMFYUI_URL")
    # Nome do arquivo de checkpoint tal como ComfyUI o enxerga em
    # ComfyUI/models/checkpoints/ (nao um caminho absoluto no disco).
    image_model_path: str = Field(default="", alias="IMAGE_MODEL_PATH")

    # Parametros de geracao -- padroes conservadores para 4 GB de VRAM
    # (batch_size=1 e sempre fixo no codigo, nunca configuravel via .env).
    comfyui_width: int = Field(default=512, alias="COMFYUI_WIDTH")
    comfyui_height: int = Field(default=512, alias="COMFYUI_HEIGHT")
    comfyui_steps: int = Field(default=20, alias="COMFYUI_STEPS")
    comfyui_cfg: float = Field(default=7.0, alias="COMFYUI_CFG")
    comfyui_sampler: str = Field(default="euler", alias="COMFYUI_SAMPLER")
    comfyui_scheduler: str = Field(default="normal", alias="COMFYUI_SCHEDULER")
    comfyui_negative_prompt: str = Field(default="", alias="COMFYUI_NEGATIVE_PROMPT")
    comfyui_timeout_seconds: float = Field(default=180.0, alias="COMFYUI_TIMEOUT_SECONDS")

    generated_dir: str = Field(default=str(PROJECT_ROOT / "generated"), alias="GENERATED_DIR")
    logs_dir: str = Field(default=str(PROJECT_ROOT / "logs"), alias="LOGS_DIR")

    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
