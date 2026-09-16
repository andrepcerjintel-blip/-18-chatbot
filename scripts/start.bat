@echo off
REM =====================================================================
REM start.bat - inicia o aplicativo localmente no Windows.
REM
REM NAO instala drivers NVIDIA, CUDA Toolkit ou qualquer software critico
REM do sistema. Apenas ativa o ambiente virtual Python ja existente,
REM inicia backend e frontend, verifica o Media Provider/ComfyUI e abre
REM o navegador em localhost.
REM =====================================================================

setlocal

set ROOT=%~dp0..
set BACKEND=%ROOT%\backend
set FRONTEND=%ROOT%\frontend

echo [1/6] Verificando ambiente virtual Python...
if not exist "%BACKEND%\.venv\Scripts\activate.bat" (
    echo Ambiente virtual nao encontrado. Criando...
    python -m venv "%BACKEND%\.venv"
    call "%BACKEND%\.venv\Scripts\activate.bat"
    pip install -r "%BACKEND%\requirements.txt"
) else (
    call "%BACKEND%\.venv\Scripts\activate.bat"
)

if not exist "%ROOT%\.env" (
    echo [aviso] .env nao encontrado. Copiando .env.example...
    copy "%ROOT%\.env.example" "%ROOT%\.env"
)

echo [2/6] Iniciando backend (FastAPI) em http://127.0.0.1:8000 ...
start "companion-backend" cmd /k "cd /d %BACKEND% && call .venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [3/6] Verificando dependencias do frontend...
if not exist "%FRONTEND%\node_modules" (
    pushd "%FRONTEND%"
    call npm install
    popd
)

echo [4/6] Iniciando frontend (Vite) em http://127.0.0.1:5173 ...
start "companion-frontend" cmd /k "cd /d %FRONTEND% && npm run dev"

echo [5/6] Verificando Media Provider / ComfyUI (nao bloqueante)...
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8000/health

echo [6/6] Abrindo navegador...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5173

echo.
echo Aplicativo iniciado. Feche as janelas de terminal para encerrar.
endlocal
