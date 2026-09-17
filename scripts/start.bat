@echo off
REM =====================================================================
REM start.bat - inicia o aplicativo localmente no Windows.
REM
REM NAO instala drivers NVIDIA, CUDA Toolkit ou qualquer software critico
REM do sistema. Ativa o ambiente virtual Python ja existente, inicia o
REM ComfyUI (se configurado via scripts\setup_comfyui.ps1), o backend e o
REM frontend, e abre o navegador em localhost.
REM =====================================================================

setlocal EnableDelayedExpansion

set ROOT=%~dp0..
set BACKEND=%ROOT%\backend
set FRONTEND=%ROOT%\frontend
set COMFYDIR=%ROOT%\ComfyUI

if exist "%COMFYDIR%\venv\Scripts\activate.bat" (
    echo [0/6] Iniciando ComfyUI ^(deteccao automatica^)...
    start "companion-comfyui" cmd /k "%~dp0start_comfyui.bat"
    echo Aguardando ComfyUI responder em http://127.0.0.1:8188 ...
    set COMFY_READY=0
    for /l %%i in (1,1,30) do (
        curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8188/system_stats > "%TEMP%\comfy_status.txt" 2>nul
        set /p COMFY_STATUS=<"%TEMP%\comfy_status.txt"
        if "!COMFY_STATUS!"=="200" (
            set COMFY_READY=1
            goto :comfy_ready
        )
        timeout /t 2 /nobreak >nul
    )
    :comfy_ready
    if "!COMFY_READY!"=="1" (
        echo ComfyUI pronto.
    ) else (
        echo [aviso] ComfyUI ainda nao respondeu apos ~60s ^(pode estar carregando
        echo o modelo pela primeira vez^). O app continua normalmente -- pedidos de
        echo imagem podem falhar ate o ComfyUI terminar de subir.
    )
) else (
    echo [0/6] ComfyUI nao configurado ^(rode scripts\setup_comfyui.ps1 para habilitar
    echo geracao real de imagem^). Continuando em modo textual/NullImageProvider.
)

echo [1/6] Verificando ambiente virtual Python (3.11.x especificamente)...
if not exist "%BACKEND%\.venv\Scripts\activate.bat" (
    echo Ambiente virtual nao encontrado. Criando com Python 3.11...
    py -3.11 -m venv "%BACKEND%\.venv"
    if errorlevel 1 (
        echo.
        echo [ERRO] Python 3.11 nao encontrado via "py -3.11".
        echo Este projeto exige especificamente Python 3.11.x ^(nao usa a versao
        echo padrao do sistema, seja qual for^). Rode primeiro:
        echo     powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1
        echo para instalar o Python 3.11 lado a lado, sem remover outras versoes.
        exit /b 1
    )
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
