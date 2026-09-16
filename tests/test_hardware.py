from __future__ import annotations

from app.hardware.profile import HardwareProfile, get_hardware_profile


def test_hardware_profile_defaults_to_unknown_without_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
    profile = get_hardware_profile()

    assert isinstance(profile, HardwareProfile)
    assert profile.vendor == "UNKNOWN"
    assert profile.is_known is False
    # Ausencia de hardware conhecido nunca deve travar a aplicacao.
    assert profile.supports_fp16 is False
    assert profile.supports_bf16 is False


def test_hardware_profile_never_assumes_nvidia(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("GPU_VENDOR", "amd")
    monkeypatch.setenv("GPU_BACKEND", "UNKNOWN")
    get_settings.cache_clear()
    get_hardware_profile.cache_clear()

    profile = get_hardware_profile()
    assert profile.vendor == "amd"
    # backend nao informado -> inferido a partir do vendor (rocm), nunca cuda.
    assert profile.backend == "rocm"

    get_settings.cache_clear()
    get_hardware_profile.cache_clear()
