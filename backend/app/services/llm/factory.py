from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.logging_config import logger
from app.services.llm.base import LLMProvider
from app.services.llm.stub_provider import StubLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "anthropic" and settings.llm_api_key:
        from app.services.llm.anthropic_provider import AnthropicProvider

        logger.info("provider_status llm_provider=anthropic")
        return AnthropicProvider()

    if provider_name == "local":
        from app.services.llm.local_provider import LocalLLMProvider

        logger.info("provider_status llm_provider=local")
        return LocalLLMProvider()

    if provider_name not in ("", "stub"):
        logger.warning("provider_status unknown_or_unconfigured_llm_provider=%s falling_back=stub", provider_name)
    logger.info("provider_status llm_provider=stub")
    return StubLLMProvider()
