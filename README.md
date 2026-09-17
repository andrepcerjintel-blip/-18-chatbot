# Companion App (Local & Privado)

Aplicativo de companion conversacional adulto, com personagens **exclusivamente
sintéticos**, projetado para rodar localmente e de forma privada, prioritariamente
no Windows.

> Idade mínima fixa de personagens: **21 anos**. Todos os personagens são
> sintéticos (`synthetic = true`), nunca baseados em pessoas reais, e
> podem ser **masculinos ou femininos** (`gender` é obrigatório, sem
> valor padrão — o sistema nunca presume um gênero). Veja
> [SECURITY.md](SECURITY.md) para todas as invariantes de segurança.

## Status atual (Fase 1 + Fase 2)

- ✅ Backend completo (FastAPI + SQLite) funcionando em modo textual.
- ✅ Frontend completo (React + Vite) com chat estilo mensageiro.
- ✅ Personagens masculinos e femininos como cidadãos de primeira classe;
  personalidade com identificadores neutros de gênero (`app.personality`).
- ✅ Character Manager, Personalidade, Memória, Intent Classifier, Safety Engine.
- ✅ `ImageProvider` abstrato com `NullImageProvider` (padrão, sem GPU) e
  `ComfyUIProvider` **real** (fila via `/prompt`, espera, download,
  tratamento de OOM/timeout/erro) — testado neste repositório contra um
  ComfyUI simulado; validado na GPU real do usuário via
  `scripts/setup_comfyui.ps1`.
- ✅ `HardwareProfile` desacoplado de vendor (NVIDIA/AMD/Intel/CPU) — veja
  [HARDWARE.md](HARDWARE.md).
- ✅ Hardware real auditado (NVIDIA RTX 3050 Laptop, 4 GB VRAM) e usado
  para escolher parâmetros conservadores (SD 1.5 fp16, 512×512,
  batch_size=1, `--lowvram`) — detalhes em [HARDWARE.md](HARDWARE.md).

## Requisitos

- Windows 10/11
- **Python 3.11.x especificamente** (não a versão mais recente do
  sistema) — instale lado a lado sem remover outras versões; veja
  `scripts/setup_windows_env.ps1`
- Node.js 18+ e npm
- Git

Se Python 3.11, Git ou Node.js ainda não estiverem instalados, rode
primeiro:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1
```

Esse script instala apenas essas três ferramentas de desenvolvimento
(via winget, quando disponível, ou orienta o download oficial), cria o
virtualenv do projeto com Python 3.11 e instala as dependências do
backend. Ele **nunca** remove ou substitui um Python já existente
(ex.: Python 3.14), nunca instala drivers de GPU ou CUDA Toolkit.

## Instalação e execução (Windows)

```bat
:: 1. Clonar o repositório e entrar na pasta
git clone <repo> companion-app
cd companion-app

:: 2. Copiar variáveis de ambiente
copy .env.example .env

:: 3. (uma vez) Configurar Python 3.11 + Git + Node, se ausentes
powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1

:: 4. (uma vez, opcional) Instalar ComfyUI + PyTorch CUDA + checkpoint
::    para habilitar geração real de imagem (downloads de alguns GB)
powershell -ExecutionPolicy Bypass -File scripts\setup_comfyui.ps1

:: 5. Executar o script de inicialização
scripts\start.bat
```

O `start.bat`:
1. detecta automaticamente se o ComfyUI foi configurado (passo 4) e, se
   sim, inicia-o e aguarda ficar pronto antes de continuar;
2. cria/ativa o virtualenv Python do backend (Python 3.11 especificamente,
   via `py -3.11`; falha com instruções claras se não encontrado);
3. instala dependências (se necessário);
4. inicia o backend em `http://127.0.0.1:8000`;
5. instala dependências do frontend (se necessário);
6. inicia o frontend em `http://127.0.0.1:5173`;
7. abre o navegador.

Sem o passo 4 (ComfyUI), o app funciona normalmente em modo textual e
`IMAGE_REQUEST` retorna `MEDIA_PROVIDER_NOT_CONFIGURED` sem quebrar nada.

Nenhum desses scripts instala drivers NVIDIA, CUDA Toolkit ou qualquer
software crítico do sistema — veja [HARDWARE.md](HARDWARE.md) para os
detalhes de cada decisão (checkpoint, resolução, VRAM).

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
