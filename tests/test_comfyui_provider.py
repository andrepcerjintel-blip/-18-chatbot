from __future__ import annotations

import pytest

from app.config import get_settings
from app.hardware.profile import get_hardware_profile
from app.schemas.media import ImageRequest, MediaStatus
from comfyui_mock_server import MockComfyUIServer


@pytest.fixture()
def mock_comfyui():
    server = MockComfyUIServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def comfyui_provider(monkeypatch, tmp_path, mock_comfyui):
    """Configura Settings/HardwareProfile para apontar para o servidor
    ComfyUI simulado, e devolve um ComfyUIProvider real (mesmo codigo que
    roda em producao) conectado a ele."""
    monkeypatch.setenv("GPU_VENDOR", "nvidia")
    monkeypatch.setenv("MEDIA_PROVIDER", "comfyui")
    monkeypatch.setenv("COMFYUI_URL", mock_comfyui.url)
    monkeypatch.setenv("IMAGE_MODEL_PATH", "v1-5-pruned-emaonly-fp16.safetensors")
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    monkeypatch.setenv("COMFYUI_TIMEOUT_SECONDS", "3")
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()

    from app.media.comfyui_provider import ComfyUIProvider

    provider = ComfyUIProvider()
    yield provider

    get_settings.cache_clear()
    get_hardware_profile.cache_clear()


def _sample_request() -> ImageRequest:
    return ImageRequest(character_id="char-1", conversation_id="conv-1", prompt_hint="a synthetic woman, adult")


def test_health_check_reports_available(comfyui_provider):
    health = comfyui_provider.health_check()
    assert health.available is True


def test_health_check_reports_unavailable_when_unreachable(monkeypatch, tmp_path):
    monkeypatch.setenv("GPU_VENDOR", "nvidia")
    monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:1")  # porta sem servidor
    monkeypatch.setenv("IMAGE_MODEL_PATH", "x.safetensors")
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
    from app.media.comfyui_provider import ComfyUIProvider

    provider = ComfyUIProvider()
    health = provider.health_check()
    assert health.available is False
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()


def test_generate_image_success(comfyui_provider, mock_comfyui, tmp_path):
    mock_comfyui.scenario = "success"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.SUCCESS
    assert result.image_id is not None
    assert result.file_path is not None
    assert (tmp_path / "char-1" / "conv-1" / f"{result.image_id}.png").exists()
    assert result.metadata["model"] == "v1-5-pruned-emaonly-fp16.safetensors"
    assert result.metadata["workflow"] == "txt2img_basic_lowvram"

    # batch_size=1 e demais defaults de baixa VRAM devem estar no workflow enviado.
    sent_prompt = mock_comfyui.received_prompts[-1]["prompt"]
    assert sent_prompt["5"]["inputs"]["batch_size"] == 1
    assert sent_prompt["4"]["inputs"]["ckpt_name"] == "v1-5-pruned-emaonly-fp16.safetensors"
    assert sent_prompt["6"]["inputs"]["text"] == "a synthetic woman, adult"


def test_generate_image_oom_returns_friendly_error(comfyui_provider, mock_comfyui):
    mock_comfyui.scenario = "oom"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.ERROR
    assert "out of memory" in result.message.lower() or "cuda" in result.message.lower()


def test_generate_image_execution_error(comfyui_provider, mock_comfyui):
    mock_comfyui.scenario = "error"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.ERROR
    assert "some node failed" in result.message


def test_generate_image_no_output_is_error(comfyui_provider, mock_comfyui):
    mock_comfyui.scenario = "no_output"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.ERROR


def test_generate_image_rejected_prompt_is_error(comfyui_provider, mock_comfyui):
    mock_comfyui.scenario = "reject"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.ERROR
    assert "rejected" in result.message.lower()


def test_generate_image_timeout(comfyui_provider, mock_comfyui):
    mock_comfyui.scenario = "pending"
    result = comfyui_provider.generate_image(_sample_request())

    assert result.status == MediaStatus.ERROR
    assert "timed out" in result.message.lower()


def test_generate_image_not_configured_when_hardware_unknown(monkeypatch, tmp_path, mock_comfyui):
    monkeypatch.setenv("GPU_VENDOR", "UNKNOWN")
    monkeypatch.setenv("MEDIA_PROVIDER", "comfyui")
    monkeypatch.setenv("COMFYUI_URL", mock_comfyui.url)
    monkeypatch.setenv("IMAGE_MODEL_PATH", "v1-5-pruned-emaonly-fp16.safetensors")
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
    from app.media.comfyui_provider import ComfyUIProvider

    provider = ComfyUIProvider()
    result = provider.generate_image(_sample_request())

    assert result.status == MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()


def test_generate_image_not_configured_without_checkpoint(monkeypatch, tmp_path, mock_comfyui):
    monkeypatch.setenv("GPU_VENDOR", "nvidia")
    monkeypatch.setenv("MEDIA_PROVIDER", "comfyui")
    monkeypatch.setenv("COMFYUI_URL", mock_comfyui.url)
    monkeypatch.setenv("IMAGE_MODEL_PATH", "")
    monkeypatch.setenv("GENERATED_DIR", str(tmp_path))
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
    from app.media.comfyui_provider import ComfyUIProvider

    provider = ComfyUIProvider()
    result = provider.generate_image(_sample_request())

    assert result.status == MediaStatus.MEDIA_PROVIDER_NOT_CONFIGURED
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
