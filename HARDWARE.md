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

## Status atual — HARDWARE REAL CONFIRMADO

A máquina alvo (Windows 11, do usuário) foi auditada. Valores confirmados
a colocar no `.env` **local** (nunca commitado — `.env` está no
`.gitignore`; apenas `.env.example` genérico é versionado):

```
GPU_VENDOR=nvidia
GPU_MODEL=NVIDIA GeForce RTX 3050 Laptop GPU
GPU_VRAM_GB=4
GPU_BACKEND=cuda
GPU_DRIVER_VERSION=581.83
CUDA_VERSION=13.0
IMAGE_MODEL_PATH=
```

> `CUDA_VERSION=13.0` aqui é a **compatibilidade máxima reportada pelo
> driver** (saída de `nvidia-smi`), **não** a versão do CUDA Toolkit a
> instalar. Ver "PyTorch/CUDA" abaixo — este projeto nunca instala CUDA
> Toolkit global; usa apenas o runtime CUDA embutido no wheel do PyTorch.

### Resto do ambiente auditado

| Item | Valor | Ação |
|---|---|---|
| SO | Windows 11 | — |
| CPU | 12th Gen Intel Core i7-12650H | — |
| RAM | 16 GB (16.831.713.280 bytes) | ver "RAM e offload" |
| Disco (C:) | ~477 GiB total, ~112 GiB livres | ver "Armazenamento" |
| Python detectado | 3.14.4 | **não usar para este projeto** (ver abaixo) |
| Python do projeto | 3.11.x (lado a lado, não instalado ainda) | rodar `scripts/setup_windows_env.ps1` |
| Git | não instalado | rodar `scripts/setup_windows_env.ps1` |
| Node.js / npm | não instalados | rodar `scripts/setup_windows_env.ps1` |

### Por que Python 3.11, não 3.14

O Python 3.14 encontrado no sistema é mantido **intacto** — não é
desinstalado nem alterado. Este projeto usa exclusivamente um virtualenv
criado com Python 3.11.x (`py -3.11 -m venv backend\.venv`), porque:
- é a versão usada durante todo o desenvolvimento da Fase 1 deste projeto;
- PyTorch e o ecossistema ComfyUI (Fase 2) têm historicamente suporte mais
  maduro e testado em 3.11 do que em versões muito recentes do Python;
- evita depender de compatibilidade ainda não confirmada de todas as
  dependências com 3.14.

Rode `scripts\setup_windows_env.ps1` uma vez para instalar o Python 3.11
lado a lado (sem remover o 3.14), criar o virtualenv do projeto, e
instalar Git/Node.js caso ausentes. Depois, `scripts\start.bat` sempre usa
esse virtualenv.

## O que acontece enquanto a geração visual não está habilitada

- `MEDIA_PROVIDER=null` por padrão → `NullImageProvider` ativo.
- Qualquer `IMAGE_REQUEST`/`VIDEO_REQUEST` é classificado normalmente,
  passa pelo Safety Engine normalmente, e retorna:
  ```json
  {"status": "MEDIA_PROVIDER_NOT_CONFIGURED", "message": "..."}
  ```
  sem quebrar a conversa, sem exceção não tratada, sem alterar
  `Character` indevidamente.

## Segunda auditoria — status das 15 decisões

Hardware real agora conhecido (NVIDIA RTX 3050 Laptop, 4 GB VRAM). Status
de cada decisão da Fase 2 — a maioria continua **deliberadamente adiada**
até a implementação real do `ComfyUIProvider`, para evitar comprometer-se
com parâmetros antes de testar progressivamente, como instruído:

| # | Decisão | Status |
|---|---|---|
| 1 | Build do PyTorch | **Direção definida** (ver "PyTorch/CUDA" abaixo), instalação adiada para o início da Fase 2 |
| 2 | Backend (CUDA) + compat. ComfyUI | **Definido**: CUDA via wheel PyTorch, sem Toolkit global |
| 3 | Checkpoint visual | **Adiado** — candidatos listados abaixo para avaliação, nenhum baixado |
| 4 | Resolução padrão | Adiado — testar progressivamente a partir de 512×512 |
| 5 | Batch size | **Definido: 1** (fixo, dado 4 GB de VRAM) |
| 6 | Precisão | **Direção definida: FP16** prioritário; BF16 não confirmado nesta GPU |
| 7 | Attention backend | Adiado — avaliar SDPA (nativo do PyTorch) primeiro, xFormers só se necessário |
| 8 | VAE | Adiado — usar VAE tiling desde o início por precaução de VRAM |
| 9 | CPU/model offload | **Definido: necessário**, sequential offload como padrão inicial |
| 10 | Outras otimizações de VRAM | Adiado — avaliar quantização apenas se offload não bastar |
| 11 | Viabilidade SDXL | **Improvável como padrão**: checkpoints SDXL costumam exigir 6-8 GB+ para inferência confortável; considerar apenas variantes destiladas/turbo se testado e couber |
| 12 | Viabilidade FLUX | **Não recomendado agora**: modelos FLUX (12B parâmetros) excedem em muito 4 GB VRAM, mesmo quantizados a probabilidade de inferência aceitável é baixa nesta GPU |
| 13 | IP-Adapter | Adiado para Fase 3 (consistência de personagem) |
| 14 | ControlNet | Adiado, e mesmo na Fase 3 usar no máximo um por vez (RAM/VRAM limitadas) |
| 15 | Vídeo local | Adiado para Fase 4; 4 GB VRAM é uma restrição severa para modelos de vídeo atuais |

## Restrições de VRAM (4 GB) — regras vinculantes para a Fase 2

A GPU tem apenas 4 GB de VRAM. Toda a arquitetura de inferência (quando
implementada) **deve**:

- `batch_size = 1`, sempre;
- priorizar FP16 quando suportado pelo checkpoint;
- geração sequencial (nunca paralela) de imagens;
- VAE tiling habilitado quando necessário;
- model offload e CPU offload habilitados quando necessário;
- descarregar (unload) modelos não utilizados da VRAM;
- **apenas um pipeline visual pesado residente por vez** — nunca LLM
  local pesado + pipeline de imagem carregados simultaneamente sem
  avaliação explícita de RAM/VRAM combinadas;
- tratamento automático de `CUDA OUT OF MEMORY` (retry com offload
  adicional ou falha estruturada, nunca crash do processo);
- no máximo um ControlNet pesado por vez, quando implementado.

**Não usar a RAM do sistema (16 GB) como substituto direto de VRAM** —
offload move dados para RAM, mas não elimina a necessidade de VRAM
suficiente para os tensores ativos durante o forward pass.

### RAM e offload

16 GB de RAM permite algum uso de CPU/model offload, mas também é
limitada. Evitar, quando a Fase 2 for implementada:
- múltiplos modelos grandes residentes em RAM simultaneamente;
- LLM local grande carregado junto do pipeline visual sem avaliação;
- múltiplos ControlNets pesados simultâneos;
- workflows ComfyUI excessivamente complexos.

Monitorar em produção: uso de RAM, uso de VRAM, uso de pagefile, tempo de
inferência por imagem.

## PyTorch / CUDA — regra de instalação

**Nunca instalar CUDA Toolkit global** só porque `nvidia-smi` reporta
"CUDA Version 13.0" — esse número é a compatibilidade máxima do driver,
não uma exigência de instalar o Toolkit 13.0 no sistema. O runtime CUDA
necessário vem embutido no próprio wheel do PyTorch.

Quando a Fase 2 (ComfyUIProvider real) começar:
1. Consultar a documentação atual em https://pytorch.org/get-started/locally/
   para a build CUDA oficialmente suportada no momento (tipicamente uma
   linha `cuXXX`, ex. cu121/cu124/cu126 — verificar a atual, não assumir).
2. Consultar a documentação/requisitos atuais do ComfyUI para a mesma.
3. Instalar essa build **dentro do virtualenv do projeto**
   (`backend\.venv`), nunca no Python de sistema.
4. Validar antes de prosseguir:
   ```python
   import torch
   torch.cuda.is_available()
   torch.cuda.get_device_name(0)
   torch.cuda.get_device_properties(0).total_memory
   ```
5. Só então habilitar `MEDIA_PROVIDER=comfyui` de fato.

## Candidatos de checkpoint visual (avaliação futura, nada baixado)

Nenhum destes foi baixado ou selecionado definitivamente. Antes de
baixar qualquer um, este documento será atualizado com: nome exato,
tamanho, finalidade, licença, compatibilidade e espaço restante
esperado, para aprovação explícita — conforme a regra de armazenamento
abaixo. Lista inicial de candidatos plausíveis para 4 GB VRAM (a
confirmar com testes reais, não apenas por qualidade visual):

| Candidato | VRAM aproximada | Observação |
|---|---|---|
| Stable Diffusion 1.5 (fp16) | ~2-3 GB | Mais leve, maior compatibilidade ComfyUI, ecossistema maduro |
| SD Turbo / LCM-LoRA sobre SD 1.5 | ~2-3 GB | Inferência mais rápida (menos steps), útil dado hardware limitado |
| SDXL fp16 | ~6-8 GB+ | Provavelmente inviável sem offload agressivo; avaliar apenas se necessário |
| SDXL Turbo/Lightning (destilado) | ~5-6 GB | Ainda arriscado para 4 GB; testar com offload antes de descartar |

Critérios de avaliação final (nenhum aplicado ainda): VRAM necessária,
RAM necessária, velocidade, arquitetura, licença, suporte ComfyUI,
compatibilidade PyTorch, capacidade de consistência de personagem.

## Armazenamento

~112 GiB livres no disco alvo no momento da auditoria. Regras
vinculantes para a Fase 2:
- nunca baixar automaticamente grandes coleções de checkpoints;
- antes de baixar qualquer modelo, apresentar: nome, tamanho estimado,
  finalidade, licença, compatibilidade, espaço restante esperado após o
  download — e aguardar aprovação;
- manter modelos organizados em `models/`;
- não duplicar checkpoints desnecessariamente.

## Regra permanente

Nunca escolher checkpoint, resolução, batch size, precisão, quantização,
offloading ou attention backend com base em suposições sobre o hardware.
Essas decisões só são tomadas após testes reais nesta GPU específica, e
mesmo com o hardware já conhecido, ainda é necessário validar
empiricamente (não apenas em teoria) antes de fixar valores definitivos.
