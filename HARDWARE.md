# Hardware

## Suporte de GPU desacoplado (multi-vendor)

O projeto **nunca presume NVIDIA**. A camada de geração abstrai o hardware
através de um `HardwareProfile` (`app/hardware/profile.py`), consumido
apenas por `app/media/comfyui_provider.py` — nenhuma verificação
específica de CUDA/ROCm/XPU está espalhada pelo restante do código.

Vendors e backends contemplados pela abstração desde já (implementação da
camada de inferência em si é Fase 2, por vendor):

| Vendor | Backend |
|---|---|
| NVIDIA | CUDA |
| AMD | ROCm |
| Intel | XPU (oneAPI / Level Zero) |
| (nenhum detectado) | CPU (fallback, somente quando tecnicamente viável) |

`HardwareProfile` expõe: `vendor`, `model`, `vram_gb`, `backend`,
`driver_version`, `runtime_version`, `supports_fp16`, `supports_bf16`.
Consulte via `GET /hardware` (somente leitura) ou
`app.hardware.get_hardware_profile()`.

## Status atual

```
GPU_VENDOR=UNKNOWN
GPU_MODEL=UNKNOWN
GPU_VRAM_GB=UNKNOWN
GPU_BACKEND=UNKNOWN
GPU_DRIVER_VERSION=UNKNOWN
CUDA_VERSION=UNKNOWN
IMAGE_MODEL_PATH=
```

Estes campos foram registrados como `UNKNOWN` porque o ambiente de
desenvolvimento usado para construir a Fase 1 deste projeto é um sandbox
Linux sem GPU detectável de nenhum fabricante. Isso é **esperado e não
bloqueia** o desenvolvimento: toda a Fase 1 (backend, frontend, banco,
Character Manager, Safety Engine, Intent Classifier, memória, API, chat
textual) funciona de forma independente de hardware gráfico.

Rode a auditoria no computador Windows real que vai executar o app:

```bat
python scripts\audit_env.py
```

O script tenta detectar, nesta ordem, NVIDIA (`nvidia-smi`), AMD
(`rocm-smi`) e Intel (`xpu-smi`/`intel_gpu_top`) — sem instalar nada — e
reporta `gpu_vendor`/`gpu_backend` já inferidos. Atualize `.env` com os
valores encontrados (`GPU_VENDOR`, `GPU_MODEL`, `GPU_VRAM_GB`,
`GPU_BACKEND`, `GPU_DRIVER_VERSION`, `CUDA_VERSION`).

## O que acontece enquanto o hardware é UNKNOWN

- `MEDIA_PROVIDER=null` por padrão → `NullImageProvider` ativo.
- Qualquer `IMAGE_REQUEST`/`VIDEO_REQUEST` é classificado normalmente,
  passa pelo Safety Engine normalmente, e retorna:
  ```json
  {"status": "MEDIA_PROVIDER_NOT_CONFIGURED", "message": "..."}
  ```
  sem quebrar a conversa, sem exceção não tratada, sem alterar
  `Character` indevidamente.

## Segunda auditoria (quando o hardware real for informado)

Quando `GPU_VENDOR`, `GPU_MODEL`, `GPU_VRAM_GB`, `GPU_BACKEND`,
`GPU_DRIVER_VERSION` e `CUDA_VERSION` forem conhecidos, decidir (nesta
ordem, documentando a decisão aqui):

1. Build apropriada do PyTorch (CPU/CUDA/ROCm/XPU, versão compatível com
   o driver e o `vendor` detectado).
2. Suporte do backend (CUDA/ROCm/XPU) e compatibilidade com ComfyUI.
3. Modelo visual adequado (checkpoint) à VRAM disponível.
4. Resolução padrão de geração.
5. Batch size.
6. Precisão (FP16/BF16/FP32).
7. Attention backend (ex.: SDPA, xFormers, Flash Attention).
8. VAE adequado.
9. Necessidade de CPU offload / model offload.
10. Outras otimizações de VRAM (quantização etc.).
11. Viabilidade de SDXL.
12. Viabilidade de FLUX ou equivalente.
13. Viabilidade de IP-Adapter.
14. Viabilidade de ControlNet.
15. Viabilidade futura de geração de vídeo local.

Essas decisões alteram **apenas** a camada de inferência
(`app/media/comfyui_provider.py` e configuração relacionada). Nenhuma
reestruturação do restante da aplicação é esperada.

## Regra permanente

Nunca escolher checkpoint, resolução, batch size, precisão, quantização,
offloading ou attention backend com base em suposições sobre o hardware.
Essas decisões só são tomadas após a auditoria real confirmar os valores
acima.
