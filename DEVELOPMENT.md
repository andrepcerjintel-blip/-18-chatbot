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
      intent_classifier.py
      llm/                # Abstração de LLM (stub/anthropic)
    safety/                # Safety Engine + regras
    character/             # Character Manager + presets
    conversation/           # Conversation Engine + memória
    media/                 # ImageProvider (null/comfyui stub)
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
- Migrações: nesta fase, `init_db()` usa `create_all`. Se o schema
  evoluir de forma incompatível, considerar Alembic.
