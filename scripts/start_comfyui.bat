@echo off
REM =====================================================================
REM start_comfyui.bat - inicia o ComfyUI local com parametros
REM conservadores para GPUs de baixa VRAM (--lowvram).
REM
REM Requer que scripts\setup_comfyui.ps1 ja tenha sido executado (clona
REM o ComfyUI, cria seu virtualenv proprio e baixa o checkpoint).
REM
REM Escrito sem blocos "if (...)" multi-linha de proposito: se o caminho
REM do projeto contiver parenteses (ex.: pasta baixada duas vezes e
REM renomeada pelo Windows para "... (2)"), blocos if/for com parenteses
REM quebram o interpretador do cmd.exe ("... foi inesperado neste
REM momento."). goto/labels nao tem esse problema.
REM =====================================================================

setlocal

set "ROOT=%~dp0.."
set "COMFYDIR=%ROOT%\ComfyUI"

if exist "%COMFYDIR%\venv\Scripts\activate.bat" goto :run

echo [ERRO] ComfyUI nao encontrado/configurado em "%COMFYDIR%".
echo Rode primeiro:
echo     powershell -ExecutionPolicy Bypass -File scripts\setup_comfyui.ps1
exit /b 1

:run
echo Iniciando ComfyUI em http://127.0.0.1:8188 (modo --lowvram, 4 GB VRAM)...
echo A primeira geracao apos iniciar pode demorar mais (carregando o modelo).
cd /d "%COMFYDIR%"
call venv\Scripts\activate.bat
python main.py --lowvram --preview-method none

endlocal
