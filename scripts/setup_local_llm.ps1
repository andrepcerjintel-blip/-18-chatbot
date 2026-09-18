#Requires -Version 5.1
<#
.SYNOPSIS
    Instala e configura um LLM local (gpt4all, motor compativel com
    llama.cpp) para a conversa ter personalidade real -- sem filtro de
    conteudo, 100% offline, sem chave de API.

.DESCRIPTION
    - Instala o pacote "gpt4all" (wheel pre-compilada oficial do PyPI,
      sem precisar de compilador C/C++) dentro do venv ja existente do
      backend (backend\.venv) -- sem venv separado.
      Preferido a llama-cpp-python porque este ultimo so tem wheel
      pronta para versoes exatas publicadas pelo mantenedor; fora dessas
      versoes, o pip tenta compilar do zero (CMake + Visual Studio Build
      Tools), o que falhou em teste real nesta maquina.
    - Baixa UM modelo do catalogo OFICIAL do gpt4all (Mistral 7B OpenOrca,
      ~4.1 GB, licenca Apache 2.0 -- sem clausula de uso restringindo
      conteudo adulto, ao contrario da licenca do Llama), via o proprio
      mecanismo de download do gpt4all (com verificacao de integridade),
      para <raiz do projeto>\models\llm\. Um .gguf baixado manualmente de
      outra fonte (ex.: Hugging Face) pode nao ser compativel com o motor
      nativo do gpt4all e travar com "access violation" -- por isso so
      usamos modelos do catalogo que o proprio gpt4all testa e suporta.
    - Roda no CPU por padrao (LOCAL_LLM_DEVICE=cpu): a GPU de 4 GB fica
      inteira disponivel para o ComfyUI, evitando falta de VRAM quando os
      dois rodam ao mesmo tempo -- prioridade "funcionar hoje" sobre
      "resposta mais rapida", conforme decidido para este projeto.
    - Atualiza o .env do projeto para LLM_PROVIDER=local.

    NAO instala GPU, driver ou CUDA Toolkit. NAO remove Python 3.14 nem
    qualquer outra versao existente.

.NOTES
    Rode DEPOIS de scripts\setup_windows_env.ps1 (backend\.venv ja deve
    existir).

        powershell -ExecutionPolicy Bypass -File scripts\setup_local_llm.ps1
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendVenv = Join-Path $RepoRoot "backend\.venv"
$BackendPython = Join-Path $BackendVenv "Scripts\python.exe"
$EnvFile = Join-Path $RepoRoot ".env"
$ModelDir = Join-Path $RepoRoot "models\llm"

# Modelo escolhido: Mistral 7B OpenOrca, do catalogo OFICIAL do gpt4all
# (licenca Apache 2.0 -- base Mistral-7B, sem clausula de uso
# restringindo conteudo adulto, ao contrario da AUP da Meta/Llama).
# Baixado pelo PROPRIO gpt4all (nao por download manual): assim a
# verificacao de integridade e o formato sao garantidamente compativeis
# com o motor nativo instalado -- um .gguf de outra fonte (ja testado
# nesta maquina) causou "access violation" (crash nativo) ao gerar texto.
# Nao e um finetune especializado em roleplay "sem filtro", mas e o ponto
# de partida mais confiavel para deixar a conversa funcional hoje; pode
# ser trocado depois por outro modelo do catalogo do gpt4all apenas
# mudando este nome e reexecutando o script.
$ModelName = "mistral-7b-openorca.gguf2.Q4_0.gguf"

function Set-EnvValue {
    param([string]$Path, [string]$Key, [string]$Value)
    if (-not (Test-Path $Path)) {
        Set-Content -Path $Path -Value "$Key=$Value"
        return
    }
    $lines = Get-Content $Path
    $found = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match "^\s*$Key=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) { $newLines += "$Key=$Value" }
    Set-Content -Path $Path -Value $newLines
}

Write-Host "=== 0/3: Pre-requisitos ===" -ForegroundColor Cyan
if (-not (Test-Path $BackendPython)) {
    Write-Host "[ERRO] backend\.venv nao encontrado. Rode primeiro:" -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1"
    exit 1
}
Write-Host "OK." -ForegroundColor Green

Write-Host "`n=== 1/3: gpt4all (CPU, dentro do backend\.venv) ===" -ForegroundColor Cyan
Write-Host "Rodando no CPU por padrao -- a GPU de 4 GB fica reservada para o" -ForegroundColor Yellow
Write-Host "ComfyUI, evitando falta de VRAM quando texto e imagem sao usados" -ForegroundColor Yellow
Write-Host "juntos (ver HARDWARE.md)." -ForegroundColor Yellow
# "python -m pip", nunca pip.exe diretamente -- mesmo motivo documentado
# em setup_comfyui.ps1/setup_windows_env.ps1 (launcher com caminho
# obsoleto se a pasta do projeto for movida).
& $BackendPython -m pip install --upgrade pip

# gpt4all publica wheel pre-compilada padrao no PyPI para Windows -- ao
# contrario de llama-cpp-python, que so tem wheel pronta para versoes
# exatas publicadas pelo mantenedor num indice separado; fora dessas
# versoes, pip tenta compilar do zero (CMake + Visual Studio Build
# Tools), o que falhou repetidamente em teste real nesta maquina.
& $BackendPython -m pip install gpt4all

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao instalar gpt4all." -ForegroundColor Red
    Write-Host "Verifique sua conexao com a internet e rode este script de novo." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 2/3: Modelo de linguagem local ($ModelName, ~4.1 GB) ===" -ForegroundColor Cyan
Write-Host "Origem: catalogo oficial do gpt4all (Mistral 7B OpenOrca)"
Write-Host "Licenca: Apache 2.0 (base Mistral-7B, sem clausula de uso"
Write-Host "restringindo conteudo adulto). RAM recomendada: ~8 GB."
Write-Host "Motivo da escolha: modelo testado/verificado pelo proprio gpt4all"
Write-Host "(evita o crash nativo de usar um .gguf de fonte externa)."
Write-Host "Pode ser trocado depois por outro modelo do catalogo do gpt4all"
Write-Host "apenas mudando o nome no topo deste script e rodando de novo."

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
$modelPath = Join-Path $ModelDir $ModelName

if (Test-Path $modelPath) {
    Write-Host "Ja existe em $modelPath -- pulando download."
} else {
    Write-Host "Baixando via gpt4all (com verificacao de integridade automatica)..."
    Write-Host "Downloads grandes podem demorar dependendo da conexao." -ForegroundColor Yellow

    $pyCode = @"
from gpt4all import GPT4All
GPT4All(r'$ModelName', model_path=r'$ModelDir', allow_download=True, device='cpu', verbose=True)
print('MODEL_READY')
"@
    $pyCode | & $BackendPython -

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $modelPath)) {
        Write-Host "[ERRO] Falha ao baixar/carregar o modelo via gpt4all." -ForegroundColor Red
        Write-Host "Verifique sua conexao com a internet e rode este script de novo" -ForegroundColor Red
        Write-Host "(o gpt4all retoma downloads parciais automaticamente)." -ForegroundColor Red
        exit 1
    }
    Write-Host "Modelo baixado e validado com sucesso." -ForegroundColor Green
}

Write-Host "`n=== 3/3: Configuracao do projeto ===" -ForegroundColor Cyan
Set-EnvValue -Path $EnvFile -Key "LLM_PROVIDER" -Value "local"
Set-EnvValue -Path $EnvFile -Key "LOCAL_LLM_MODEL_PATH" -Value $modelPath
Write-Host "`n.env atualizado: LLM_PROVIDER=local, LOCAL_LLM_MODEL_PATH=$modelPath" -ForegroundColor Green

Write-Host "`nConcluido." -ForegroundColor Green
Write-Host "Reinicie o backend (scripts\start.bat, ou Ctrl+C + subir de novo o" -ForegroundColor Yellow
Write-Host "uvicorn) para carregar o modelo local. A primeira resposta demora" -ForegroundColor Yellow
Write-Host "mais (carregando o modelo na memoria); as seguintes sao mais rapidas." -ForegroundColor Yellow
