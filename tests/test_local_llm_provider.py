from __future__ import annotations

import sys
import types

import pytest

from app.config import get_settings
from app.services.llm.base import LLMCharacterContext


class _FakeGPT4All:
    last_kwargs: dict | None = None

    def __init__(self, **kwargs):
        _FakeGPT4All.last_kwargs = kwargs

    def generate(self, prompt, *, max_tokens, temp):
        return f"Oi! Entendi: {prompt.splitlines()[-2].removeprefix('Usuário: ')}"


@pytest.fixture()
def fake_gpt4all(monkeypatch):
    fake_module = types.ModuleType("gpt4all")
    fake_module.GPT4All = _FakeGPT4All
    monkeypatch.setitem(sys.modules, "gpt4all", fake_module)
    yield fake_module


def _context() -> LLMCharacterContext:
    return LLMCharacterContext(
        name="Luna",
        age=24,
        gender="female",
        appearance="alta, cabelo escuro",
        personality={"shyness": 50},
        state={"location": "quarto", "time_of_day": "noite", "outfit": "vestido", "mood": "tranquila"},
        conversation_summary="",
        short_term_messages=[],
    )


def test_local_llm_provider_generates_reply_via_gpt4all(monkeypatch, tmp_path, fake_gpt4all):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"fake")
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", str(model_path))
    get_settings.cache_clear()
    try:
        from app.services.llm.local_provider import LocalLLMProvider

        provider = LocalLLMProvider()
        reply = provider.generate_reply(context=_context(), user_text="oi")

        assert "oi" in reply.lower()
        assert _FakeGPT4All.last_kwargs["model_name"] == model_path.name
        assert _FakeGPT4All.last_kwargs["model_path"] == str(model_path.parent)
        assert _FakeGPT4All.last_kwargs["device"] == "cpu"
        assert _FakeGPT4All.last_kwargs["allow_download"] is False
    finally:
        get_settings.cache_clear()


def test_local_llm_provider_falls_back_to_stub_when_model_missing(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", "")
    get_settings.cache_clear()
    try:
        from app.services.llm.local_provider import LocalLLMProvider

        provider = LocalLLMProvider()
        reply = provider.generate_reply(context=_context(), user_text="oi")

        assert reply
    finally:
        get_settings.cache_clear()


def test_local_llm_provider_falls_back_to_stub_when_gpt4all_not_installed(monkeypatch, tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"fake")
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", str(model_path))
    monkeypatch.setitem(sys.modules, "gpt4all", None)  # forca ImportError no import tardio
    get_settings.cache_clear()
    try:
        from app.services.llm.local_provider import LocalLLMProvider

        provider = LocalLLMProvider()
        reply = provider.generate_reply(context=_context(), user_text="oi")

        assert reply
    finally:
        get_settings.cache_clear()


def test_factory_returns_local_provider_when_configured(monkeypatch, fake_gpt4all, tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"fake")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_LLM_MODEL_PATH", str(model_path))
    get_settings.cache_clear()
    try:
        from app.services.llm.factory import get_llm_provider
        from app.services.llm.local_provider import LocalLLMProvider

        get_llm_provider.cache_clear()
        provider = get_llm_provider()
        assert isinstance(provider, LocalLLMProvider)
    finally:
        get_llm_provider.cache_clear()
        get_settings.cache_clear()
