# Hardware

## Status atual

```
GPU_MODEL=UNKNOWN
GPU_VRAM_GB=UNKNOWN
CUDA_VERSION=UNKNOWN
IMAGE_MODEL_PATH=
```

Estes campos foram registrados como `UNKNOWN` porque o ambiente de
desenvolvimento usado para construir a Fase 1 deste projeto é um sandbox
Linux sem GPU NVIDIA detectável (`nvidia-smi` ausente). Isso é **esperado
e não bloqueia** o desenvolvimento: toda a Fase 1 (backend, frontend,
banco, Character Manager, Safety Engine, Intent Classifier, memória,
API, chat textual) funciona de forma independente de hardware gráfico.

Rode a auditoria no computador Windows real que vai executar o app:

```bat
python scripts\audit_env.py
```

e atualize `.env` com os valores encontrados (`GPU_MODEL`, `GPU_VRAM_GB`,
`CUDA_VERSION`).

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

Quando `GPU_MODEL`, `GPU_VRAM_GB`, `DRIVER_VERSION` e `CUDA_VERSION`
forem conhecidos, decidir (nesta ordem, documentando a decisão aqui):

1. Build apropriada do PyTorch (CPU/CUDA, versão compatível com o driver).
2. Suporte CUDA e compatibilidade com ComfyUI.
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
