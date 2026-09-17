# Guia de Desenvolvimento

## Estrutura do projeto

```
backend/
  app/
    main.py              # FastAPI app, CORS, lifespan
    api/                 # Endpoints HTTP
    models/               # ORM (SQLAlchemy)
    schemas/               # Contratos Pydantic
    services/
      llm/                # Abstração de LLM (stub/anthropic)
    safety/                # Safety Engine + regras
    character/             # Character Manager
    personality/            # Presets neutros em gênero + tradução de rótulo
    conversation/           # Conversation Engine
    memory/                 # Short-term memory + resumo progressivo
    intent/                 # Intent Classifier
    media/                 # ImageProvider (null real / comfyui real)
    hardware/               # HardwareProfile (NVIDIA/AMD/Intel/CPU)
    database/               # Engine/Session
    config/                 # Settings via .env
  requirements.txt
  pytest.ini
frontend/                  # React + Vite
tests/                      # Testes automatizados (pytest)
  comfyui_mock_server.py    # Servidor ComfyUI simulado p/ testar o provider sem GPU
scripts/
  audit_env.py             # Auditoria de ambiente (somente leitura)
  setup_windows_env.ps1    # Python 3.11 lado a lado + Git/Node (1x, Windows)
  setup_comfyui.ps1        # PyTorch CUDA + ComfyUI + checkpoint (1x, Fase 2)
  start_comfyui.bat        # Inicia o ComfyUI (--lowvram)
  start.bat                # Inicialização no Windows (detecta ComfyUI + Python 3.11)
ComfyUI/                    # Clone do ComfyUI + venv proprio (fora do git, Fase 2+)
                             # checkpoints ficam em ComfyUI/models/checkpoints/
workflows/                  # Reservado para workflows API JSON exportados (opcional)
models/                     # Reservado (não usado -- ComfyUI mantém seus próprios em ComfyUI/models/)
generated/                  # Mídia gerada (fora do git)
logs/                        # Logs da aplicação (fora do git)
```

## Rodando localmente (dev)

> Este projeto usa **Python 3.11.x** especificamente (não a versão mais
> recente instalada no sistema). No Windows, rode
> `scripts\setup_windows_env.ps1` uma vez para instalar 3.11 lado a lado
> sem afetar outras versões, e crie o virtualenv com `py -3.11`, não
> `python`/`python3` genérico.

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: py -3.11 -m venv .venv
pip install -r requirements.txt
cp ../.env.example ../.env
PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## Testes

```bash
cd backend
source .venv/bin/activate
python3 -m pytest -v
```

Os testes usam SQLite em memória (`sqlite:///:memory:`), nunca tocam no
banco de desenvolvimento.

## Adicionando um novo LLM Provider

1. Criar `app/services/llm/<nome>_provider.py` implementando
   `LLMProvider.generate_reply()`.
2. Registrar em `app/services/llm/factory.py`.
3. Nunca deixar o provider lançar exceção não tratada — sempre fazer
   fallback ou capturar erros.

## Adicionando um novo Image Provider

1. Criar `app/media/<nome>_provider.py` implementando `ImageProvider`
   (`generate_image`, `health_check`).
2. Registrar em `app/media/provider_factory.py`.
3. `generate_image()` deve sempre retornar `ImageResult`, nunca lançar
   exceção.
4. Testar contra um servidor HTTP simulado (não uma GPU real) sempre que
   possível — ver `tests/comfyui_mock_server.py` +
   `tests/test_comfyui_provider.py` como referência: valida a lógica de
   fila/poll/download/erro/timeout sem depender de hardware específico.

## Convenções

- Toda mutação de `Character` passa por `CharacterManager`.
- Toda decisão de segurança passa por `SafetyEngine` (nunca pular).
- Toda saída de LLM é tratada como texto de exibição, nunca como
  comando.
- `Character.gender` é sempre obrigatório e nunca tem valor default no
  código (backend ou frontend) — nenhum formulário, schema ou preset deve
  pré-selecionar "female" (nem nenhum outro valor).
- Presets de personalidade (`app.personality.presets`) usam
  identificadores NEUTROS em relação a gênero (`SHY`, `MODEST`, ...,
  `BOLD`). Nunca crie um preset ou eixo de personalidade duplicado "por
  sexo" — a tradução para um rótulo gramaticalmente adequado
  (`preset_display_label` / `frontend/src/personality.ts`) é
  responsabilidade exclusiva da camada de apresentação.
- Nenhum módulo fora de `app/hardware` deve verificar diretamente
  `torch.cuda`, nome de GPU ou variáveis CUDA-específicas — sempre
  consumir `app.hardware.get_hardware_profile()`.
- A GPU alvo conhecida tem apenas 4 GB de VRAM: qualquer implementação
  futura em `app/media/comfyui_provider.py` deve respeitar as restrições
  vinculantes documentadas em [HARDWARE.md](HARDWARE.md) (`batch_size=1`,
  FP16, offload, um pipeline pesado residente por vez, tratamento de
  `CUDA OUT OF MEMORY`) — nunca presumir VRAM abundante.
- Nunca instalar CUDA Toolkit global neste projeto; apenas o wheel do
  PyTorch com runtime CUDA embutido, dentro do virtualenv.
- Migrações: nesta fase, `init_db()` usa `create_all`. Se o schema
  evoluir de forma incompatível, considerar Alembic.
