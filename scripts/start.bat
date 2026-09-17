@echo off
REM =====================================================================
REM start.bat - inicia o aplicativo localmente no Windows.
REM
REM NAO instala drivers NVIDIA, CUDA Toolkit ou qualquer software critico
REM do sistema. Ativa o ambiente virtual Python ja existente, inicia o
REM ComfyUI (se configurado via scripts\setup_comfyui.ps1), o backend e o
REM frontend, e abre o navegador em localhost.
REM
REM Escrito sem blocos "if (...)" ou "for (...) do (...)" multi-linha de
REM proposito: se o caminho do projeto contiver parenteses (ex.: pasta
REM baixada duas vezes e renomeada pelo Windows para "... (2)"), uma linha
REM dentro desses blocos que expanda %VARIAVEL% com parenteses no valor
REM quebra o interpretador do cmd.exe ("... foi inesperado neste
REM momento."). goto/labels e "if condicao comando" (sem parenteses) nao
REM tem esse problema.
REM =====================================================================

setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "COMFYDIR=%ROOT%\ComfyUI"

REM --- 0/6: ComfyUI (opcional, deteccao automatica) ---------------------
if not exist "%COMFYDIR%\venv\Scripts\activate.bat" goto :comfy_not_configured

echo [0/6] Iniciando ComfyUI (deteccao automatica)...
start "companion-comfyui" cmd /k "call "%~dp0start_comfyui.bat""
echo Aguardando ComfyUI responder em http://127.0.0.1:8188 ...
set "COMFY_READY=0"
set "COMFY_TRIES=0"

:comfy_wait_loop
set /a COMFY_TRIES+=1
curl -s -o nul -w "%{http_code}" http://127.0.0.1:8188/system_stats > "%TEMP%\comfy_status.txt" 2>nul
set /p COMFY_STATUS=<"%TEMP%\comfy_status.txt"
if "!COMFY_STATUS!"=="200" set "COMFY_READY=1"
if "!COMFY_READY!"=="1" goto :comfy_wait_done
if !COMFY_TRIES! GEQ 30 goto :comfy_wait_done
timeout /t 2 /nobreak >nul
goto :comfy_wait_loop

:comfy_wait_done
if "!COMFY_READY!"=="1" echo ComfyUI pronto.
if "!COMFY_READY!"=="0" echo [aviso] ComfyUI ainda nao respondeu apos ~60s. O app continua normalmente -- pedidos de imagem podem falhar ate o ComfyUI terminar de subir.
goto :after_comfy

:comfy_not_configured
echo [0/6] ComfyUI nao configurado. Rode scripts\setup_comfyui.ps1 para habilitar
echo geracao real de imagem. Continuando em modo textual/NullImageProvider.

:after_comfy

REM --- 1/6: virtualenv do backend (Python 3.11 especificamente) ----------
echo [1/6] Verificando ambiente virtual Python (3.11.x especificamente)...
if exist "%BACKEND%\.venv\Scripts\activate.bat" goto :venv_ready

echo Ambiente virtual nao encontrado. Criando com Python 3.11...
py -3.11 -m venv "%BACKEND%\.venv"
if errorlevel 1 goto :python311_missing
call "%BACKEND%\.venv\Scripts\activate.bat"
pip install -r "%BACKEND%\requirements.txt"
goto :venv_done

:python311_missing
echo.
echo [ERRO] Python 3.11 nao encontrado via "py -3.11".
echo Este projeto exige especificamente Python 3.11.x (nao usa a versao
echo padrao do sistema, seja qual for). Rode primeiro:
echo     powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1
echo para instalar o Python 3.11 lado a lado, sem remover outras versoes.
exit /b 1

:venv_ready
call "%BACKEND%\.venv\Scripts\activate.bat"

:venv_done

if not exist "%ROOT%\.env" echo [aviso] .env nao encontrado. Copiando .env.example...
if not exist "%ROOT%\.env" copy "%ROOT%\.env.example" "%ROOT%\.env"

echo [2/6] Iniciando backend (FastAPI) em http://127.0.0.1:8000 ...
start "companion-backend" cmd /k "cd /d "%BACKEND%" && call .venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [3/6] Verificando dependencias do frontend...
if exist "%FRONTEND%\node_modules" goto :frontend_deps_done
pushd "%FRONTEND%"
call npm install
popd
:frontend_deps_done

echo [4/6] Iniciando frontend (Vite) em http://127.0.0.1:5173 ...
start "companion-frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo [5/6] Verificando Media Provider / ComfyUI (nao bloqueante)...
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8000/health

echo [6/6] Abrindo navegador...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5173

echo.
echo Aplicativo iniciado. Feche as janelas de terminal para encerrar.
endlocal
