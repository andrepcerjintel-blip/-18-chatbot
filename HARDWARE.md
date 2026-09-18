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

## Status: Fase 2 implementada (geração real via ComfyUI)

O `ComfyUIProvider` (`backend/app/media/comfyui_provider.py`) agora
implementa geração real (fila via `/prompt`, espera via `/history`,
download via `/view`, tratamento de timeout/OOM/erro de execução — nunca
lança exceção, sempre retorna `ImageResult` estruturado). Testado neste
repositório contra um servidor ComfyUI simulado (`tests/test_comfyui_provider.py`
+ `tests/comfyui_mock_server.py`), já que o ambiente de desenvolvimento
não tem a GPU real do usuário. **A validação com a GPU real (RTX 3050)
acontece na máquina do usuário**, rodando:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_comfyui.ps1
scripts\start_comfyui.bat   # janela 1, deixar aberta
scripts\start.bat           # janela 2 (detecta e aguarda o ComfyUI sozinho)
```

Enquanto isso não for rodado (`MEDIA_PROVIDER=null`, padrão de fábrica),
`IMAGE_REQUEST`/`VIDEO_REQUEST` continuam sendo classificados e passando
pelo Safety Engine normalmente, retornando
`{"status": "MEDIA_PROVIDER_NOT_CONFIGURED", ...}` sem quebrar a conversa.

## Segunda auditoria — status das 15 decisões

Hardware real conhecido (NVIDIA RTX 3050 Laptop, 4 GB VRAM). Prioridade
explícita do usuário: **"funcionar hoje" > qualidade máxima**. Status de
cada decisão:

| # | Decisão | Status |
|---|---|---|
| 1 | Build do PyTorch | **Definido**: instalado pelo `scripts/setup_comfyui.ps1` dentro do venv próprio do ComfyUI, tentando `cu128`, `cu126`, `cu124`, `cu121` nessa ordem (fallback CPU-only se todas falharem). PyTorch **>= 2.7** é necessário — versões mais antigas quebram a inicialização do ComfyUI por incompatibilidade com `comfy-kitchen` (ver nota abaixo) |
| 2 | Backend (CUDA) + compat. ComfyUI | **Definido**: CUDA via wheel PyTorch, sem Toolkit global |
| 3 | Checkpoint visual | **Definido**: Stable Diffusion 1.5 fp16 pruned-emaonly (`v1-5-pruned-emaonly-fp16.safetensors`, ~2.13 GB, CreativeML Open RAIL-M) — ver justificativa abaixo |
| 4 | Resolução padrão | **Definido: 512×512** (nativo do SD1.5, seguro para 4 GB) — `COMFYUI_WIDTH`/`COMFYUI_HEIGHT` no `.env` |
| 5 | Batch size | **Definido: 1**, fixado no código (`comfyui_workflow.py`), não configurável via `.env` |
| 6 | Precisão | FP16 vem embutido no checkpoint escolhido; PyTorch usa autocast padrão do ComfyUI |
| 7 | Attention backend | Usa o padrão do ComfyUI (SDPA/pytorch nativo); nada customizado |
| 8 | VAE | VAE embutido no checkpoint (não separado); tiling não necessário em 512×512 |
| 9 | CPU/model offload | **Definido**: `start_comfyui.bat` roda com a flag `--lowvram` do próprio ComfyUI |
| 10 | Outras otimizações de VRAM | Não aplicadas ainda — `--lowvram` + 512×512 + batch=1 já é bem conservador; reavaliar apenas se houver OOM real |
| 11 | Viabilidade SDXL | **Não usado como padrão** (mantém-se a análise anterior: exige 6-8 GB+) |
| 12 | Viabilidade FLUX | **Não usado** (12B parâmetros, incompatível com 4 GB) |
| 13 | IP-Adapter | Adiado para Fase 3 (consistência de personagem) |
| 14 | ControlNet | Adiado, e mesmo na Fase 3 usar no máximo um por vez (RAM/VRAM limitadas) |
| 15 | Vídeo local | Adiado para Fase 4; 4 GB VRAM é uma restrição severa para modelos de vídeo atuais |

### Por que Stable Diffusion 1.5 fp16 pruned-emaonly

- **Tamanho**: ~2,13 GB — a opção mais leve entre os candidatos avaliados.
- **Origem**: `Comfy-Org/stable-diffusion-v1-5-archive` no Hugging Face
  (mantido pela própria organização do ComfyUI).
- **Licença**: CreativeML Open RAIL-M — permissiva, com restrições de uso
  (não gerar conteúdo ilegal), compatível com o uso local/privado deste
  projeto.
- **Estilo**: modelo base geral, capaz de saídas realistas e ilustrativas
  dependendo do prompt — não especializado.
- **Compatibilidade**: workflow txt2img mínimo padrão do ComfyUI
  (`CheckpointLoaderSimple` → `KSampler` → `VAEDecode`), sem nós extras.
- Escolhido automaticamente pela regra de fallback combinada com a
  prioridade explícita do usuário ("funcionar hoje" > qualidade máxima) —
  não houve resposta bloqueando a decisão, e esta é a opção mais leve,
  estável e amplamente compatível para validar o pipeline. SDXL/FLUX e
  variantes turbo/destiladas ficam para avaliação futura, uma vez que o
  pipeline básico esteja confirmado funcionando.

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

### Problema conhecido: PyTorch < 2.7 quebra o ComfyUI atual

O ComfyUI (branch principal) depende de `comfy-kitchen`, que usa
anotações de tipo modernas (`list[int]`) em `torch.library.custom_op`.
Com PyTorch anterior a 2.7, isso levanta `ValueError` (não
`ImportError`) durante o import, então nem o próprio mecanismo de
fallback do ComfyUI consegue capturar o erro — a inicialização inteira
trava. Ver [issue #15441](https://github.com/Comfy-Org/ComfyUI/issues/15441).
`scripts/setup_comfyui.ps1` já tenta instalar PyTorch >= 2.7 por padrão
(tags `cu128`/`cu126` antes de `cu124`/`cu121`) e avisa se não
conseguir. **Não** tente contornar isso baixando a versão do
`comfy-kitchen` — isso só troca esse erro por outro (`AttributeError`
em funções que o ComfyUI atual espera que existam). A correção correta
é sempre ter PyTorch >= 2.7.

## Checkpoint escolhido vs. alternativas futuras

O checkpoint ativo é o SD 1.5 fp16 descrito acima, baixado por
`scripts/setup_comfyui.ps1` para `ComfyUI/models/checkpoints/`. Outras
opções ficam para quando o pipeline básico estiver validado e houver
motivo concreto para trocar (nenhuma delas foi baixada):

| Candidato | VRAM aproximada | Observação |
|---|---|---|
| SD Turbo / LCM-LoRA sobre SD 1.5 | ~2-3 GB | Inferência mais rápida (1-4 steps); avaliar depois de confirmar o pipeline básico |
| SDXL fp16 | ~6-8 GB+ | Provavelmente inviável sem offload agressivo nesta GPU |
| SDXL Turbo/Lightning (destilado) | ~5-6 GB | Ainda arriscado para 4 GB; só testar com `--lowvram`/offload se houver necessidade real |

Antes de baixar qualquer um destes, seguir a mesma regra de
"Armazenamento" abaixo (nome, tamanho, finalidade, licença,
compatibilidade, espaço restante esperado, aprovação explícita).

## Armazenamento

~112 GiB livres no disco alvo no momento da auditoria. Regras
vinculantes para a Fase 2:
- nunca baixar automaticamente grandes coleções de checkpoints;
- antes de baixar qualquer modelo, apresentar: nome, tamanho estimado,
  finalidade, licença, compatibilidade, espaço restante esperado após o
  download — e aguardar aprovação;
- manter modelos organizados em `models/`;
- não duplicar checkpoints desnecessariamente.

## Fase 3: LLM local (conversa com personalidade real)

O `StubLLMProvider` (respostas fixas/eco) era só um placeholder para o app
funcionar sem dependências durante a Fase 1/2. Para a conversa realmente
interpretar a personagem, foi adicionado `LocalLLMProvider`
(`app/services/llm/local_provider.py`), via `gpt4all` (motor compatível
com llama.cpp):

- **`gpt4all`, não `llama-cpp-python`**: a primeira tentativa usou
  `llama-cpp-python`, mas em teste real no Windows o `pip install`
  tentou compilar do zero (exige CMake + Visual Studio Build Tools, que
  a máquina não tinha) porque a versão exata pedida não tinha wheel
  pré-compilada publicada pelo mantenedor. `gpt4all` publica wheel
  pré-compilada padrão no PyPI, sem essa fragilidade.
- **CPU por padrão** (`LOCAL_LLM_DEVICE=cpu`): a GPU de 4 GB fica
  reservada inteiramente para o ComfyUI. Rodar o LLM na mesma GPU
  economizaria tempo de resposta, mas arrisca falta de VRAM sempre que
  texto e imagem forem usados ao mesmo tempo — prioridade "funcionar
  hoje" sobre "resposta mais rápida" (decisão já usada na Fase 2).
- **Modelo padrão**: `mistral-7b-openorca.gguf2.Q4_0.gguf` (Mistral 7B
  OpenOrca, ~4.1 GB, ~8 GB de RAM recomendada, licença Apache 2.0 — sem
  cláusula de uso restringindo conteúdo adulto, ao contrário da AUP da
  Meta/Llama), baixado do **catálogo oficial do próprio gpt4all** (não
  de um `.gguf` externo). Testado uma primeira vez com um `.gguf` baixado
  manualmente do Hugging Face (Mistral-7B-Instruct-v0.2): carregava sem
  erro, mas travava com `OSError: access violation` (crash nativo, ponteiro
  nulo) ao tentar gerar texto de verdade — o motor nativo do gpt4all só
  garante compatibilidade total com os modelos do próprio catálogo, não
  com qualquer `.gguf` de terceiros. Não é um finetune especializado em
  roleplay "sem filtro"; foi escolhido por ser o ponto de partida mais
  confiável/verificável para validar o pipeline de conversa hoje. Pode
  ser trocado depois por outro modelo do catálogo do gpt4all apenas
  mudando o nome em `scripts/setup_local_llm.ps1` e reexecutando.
- Instalado via `scripts/setup_local_llm.ps1`, dentro do `backend\.venv`
  já existente (sem venv separado — `gpt4all` não tem dependências
  pesadas conflitantes). O download do modelo é feito pelo próprio
  `gpt4all` (com verificação de integridade), não por download manual.

## Regra permanente

Nunca escolher checkpoint, resolução, batch size, precisão, quantização,
offloading ou attention backend com base em suposições sobre o hardware.
Essas decisões só são tomadas após testes reais nesta GPU específica, e
mesmo com o hardware já conhecido, ainda é necessário validar
empiricamente (não apenas em teoria) antes de fixar valores definitivos.
