"""HardwareProfile: camada conceitual que abstrai o hardware de aceleracao.

O restante da aplicacao (ImageProvider, Conversation Engine, etc.) nunca
deve verificar diretamente "e CUDA?" ou "e NVIDIA?" espalhado pelo codigo.
Em vez disso, consome este HardwareProfile estruturado, que sera usado
futuramente (Fase 2) para selecionar build de PyTorch, precisao,
attention backend e demais parametros de inferencia -- SEM exigir
mudancas no restante do projeto quando o vendor/backend mudar.

Nesta fase (hardware ainda desconhecido), get_hardware_profile() apenas
reflete os valores registrados em Settings (preenchidos por
scripts/audit_env.py ou manualmente no .env). Nenhuma decisao de
inferencia e tomada aqui.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel

from app.config import get_settings

UNKNOWN = "UNKNOWN"

# Vendors e backends suportados pela abstracao (mesmo que ainda nao
# implementados na camada de inferencia).
KNOWN_VENDORS = frozenset({"nvidia", "amd", "intel", "cpu", UNKNOWN.lower()})
KNOWN_BACKENDS = frozenset({"cuda", "rocm", "xpu", "cpu", UNKNOWN.lower()})

_VENDOR_DEFAULT_BACKEND = {
    "nvidia": "cuda",
    "amd": "rocm",
    "intel": "xpu",
    "cpu": "cpu",
}


class HardwareProfile(BaseModel):
    vendor: str = UNKNOWN
    model: str = UNKNOWN
    vram_gb: str = UNKNOWN
    backend: str = UNKNOWN
    driver_version: str = UNKNOWN
    # Populado a partir de CUDA_VERSION no .env. Enquanto nenhum PyTorch
    # com CUDA estiver instalado no venv, isto reflete a compatibilidade
    # MAXIMA reportada pelo driver (saida de `nvidia-smi`), NAO a versao
    # de runtime CUDA efetivamente em uso -- essas sao coisas diferentes e
    # nao podem ser tratadas como equivalentes ao decidir builds/parametros.
    runtime_version: str = UNKNOWN
    supports_fp16: bool = False
    supports_bf16: bool = False

    @property
    def is_known(self) -> bool:
        return self.vendor.lower() not in (UNKNOWN.lower(), "")


@lru_cache
def get_hardware_profile() -> HardwareProfile:
    """Constroi o HardwareProfile a partir das variaveis de ambiente
    (GPU_VENDOR, GPU_MODEL, GPU_VRAM_GB, GPU_BACKEND, CUDA_VERSION etc.).

    Nao presume NVIDIA: se GPU_VENDOR nao for informado explicitamente,
    o profile permanece UNKNOWN em todos os campos dependentes de
    hardware -- o app continua funcionando normalmente em modo textual.
    """
    settings = get_settings()

    vendor = (settings.gpu_vendor or UNKNOWN).strip() or UNKNOWN
    backend = (settings.gpu_backend or UNKNOWN).strip() or UNKNOWN

    if backend.lower() == UNKNOWN.lower() and vendor.lower() in _VENDOR_DEFAULT_BACKEND:
        backend = _VENDOR_DEFAULT_BACKEND[vendor.lower()]

    # Capacidades de precisao sao apenas um indicativo grosseiro nesta
    # fase; a decisao definitiva (Fase 2) exige deteccao real de compute
    # capability / arquitetura, feita somente apos a auditoria de hardware.
    known = vendor.lower() not in (UNKNOWN.lower(), "", "cpu")
    supports_fp16 = known
    supports_bf16 = False

    return HardwareProfile(
        vendor=vendor,
        model=settings.gpu_model or UNKNOWN,
        vram_gb=str(settings.gpu_vram_gb or UNKNOWN),
        backend=backend,
        driver_version=settings.gpu_driver_version or UNKNOWN,
        runtime_version=settings.cuda_version or UNKNOWN,
        supports_fp16=supports_fp16,
        supports_bf16=supports_bf16,
    )
