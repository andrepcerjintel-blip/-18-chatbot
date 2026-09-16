# Companion App (Local & Privado)

Aplicativo de companion conversacional adulto, com personagens **exclusivamente
sintéticos**, projetado para rodar localmente e de forma privada, prioritariamente
no Windows.

> Idade mínima fixa de personagens: **21 anos**. Todos os personagens são
> sintéticos (`synthetic = true`), nunca baseados em pessoas reais. Veja
> [SECURITY.md](SECURITY.md) para todas as invariantes de segurança.

## Status atual (Fase 1)

- ✅ Backend completo (FastAPI + SQLite) funcionando em modo textual.
- ✅ Frontend completo (React + Vite) com chat estilo mensageiro.
- ✅ Character Manager, Personalidade, Memória, Intent Classifier, Safety Engine.
- ✅ `ImageProvider` abstrato com `NullImageProvider` (padrão) e `ComfyUIProvider`
  em modo stub/configurável.
- ⏳ Geração visual real: depende de hardware (GPU/VRAM/CUDA) ainda **desconhecido**.
  Veja [HARDWARE.md](HARDWARE.md).

## Requisitos

- Windows 10/11
- Python 3.11+
- Node.js 18+ e npm
- Git

## Instalação e execução (Windows)

```bat
:: 1. Clonar o repositório e entrar na pasta
git clone <repo> companion-app
cd companion-app

:: 2. Copiar variáveis de ambiente
copy .env.example .env

:: 3. Executar o script de inicialização
scripts\start.bat
```

O `start.bat`:
1. cria/ativa o virtualenv Python do backend;
2. instala dependências (se necessário);
3. inicia o backend em `http://127.0.0.1:8000`;
4. instala dependências do frontend (se necessário);
5. inicia o frontend em `http://127.0.0.1:5173`;
6. verifica o status do Media Provider (não bloqueia se não configurado);
7. abre o navegador.

Ele **não** instala drivers NVIDIA, CUDA Toolkit ou qualquer software crítico do
sistema.

### Execução manual (qualquer SO, para desenvolvimento)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (em outro terminal)
cd frontend
npm install
npm run dev
```

Acesse `http://127.0.0.1:5173`.

## Testes

```bash
cd backend
source .venv/bin/activate
python3 -m pytest -v
```

## Auditoria de ambiente

```bash
python3 scripts/audit_env.py
```

Reporta SO, Python, Git, Node, GPU/CUDA (se detectável), RAM, disco e status do
ComfyUI. Campos não detectáveis são reportados como `UNKNOWN` e nunca bloqueiam
o desenvolvimento ou a execução do app em modo textual.

## Documentação

- [ARCHITECTURE.md](ARCHITECTURE.md) — fluxo de dados e módulos.
- [SECURITY.md](SECURITY.md) — invariantes de segurança e privacidade.
- [DEVELOPMENT.md](DEVELOPMENT.md) — guia para desenvolvedores.
- [HARDWARE.md](HARDWARE.md) — status do hardware e decisões pendentes.

## Privacidade

Tudo roda localmente por padrão: sem analytics, sem telemetry, sem upload
automático, sem armazenamento em nuvem. A API é vinculada a `127.0.0.1` e o
CORS é restrito a origens locais. Veja [SECURITY.md](SECURITY.md).
