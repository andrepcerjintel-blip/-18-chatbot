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
    media/                 # ImageProvider (null/comfyui stub)
    hardware/               # HardwareProfile (NVIDIA/AMD/Intel/CPU)
    database/               # Engine/Session
    config/                 # Settings via .env
  requirements.txt
  pytest.ini
frontend/                  # React + Vite
tests/                      # Testes automatizados (pytest)
scripts/
  audit_env.py             # Auditoria de ambiente (somente leitura)
  start.bat                # Inicialização no Windows
workflows/                  # Workflows ComfyUI (Fase 2+)
models/                     # Checkpoints visuais (Fase 2+, fora do git)
generated/                  # Mídia gerada (fora do git)
logs/                        # Logs da aplicação (fora do git)
```

## Rodando localmente (dev)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
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
- Migrações: nesta fase, `init_db()` usa `create_all`. Se o schema
  evoluir de forma incompatível, considerar Alembic.
