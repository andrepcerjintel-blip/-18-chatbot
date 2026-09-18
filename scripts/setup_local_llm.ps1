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
    - Baixa UM modelo GGUF (Mistral-7B-Instruct-v0.2, quantizado Q4_K_M,
      ~4.4 GB, licenca Apache 2.0 -- sem clausula de uso restringindo
      conteudo adulto, ao contrario da licenca do Llama) para
      <raiz do projeto>\models\llm\.
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

# Modelo escolhido: base Mistral-7B-Instruct-v0.2 (licenca Apache 2.0, sem
# clausula de uso restringindo conteudo adulto -- ao contrario da AUP da
# Meta/Llama). Nao e um finetune especializado em roleplay "sem filtro",
# mas e o ponto de partida mais confiavel/verificavel para deixar a
# conversa funcional hoje; pode ser trocado depois por outro .gguf apenas
# atualizando LOCAL_LLM_MODEL_PATH no .env.
$ModelName = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
$ModelUrl = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
$ModelMinBytes = 3.5GB  # sanity check: arquivo real tem ~4.37 GB

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

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

Write-Host "`n=== 2/3: Modelo de linguagem local ($ModelName, ~4.4 GB) ===" -ForegroundColor Cyan
Write-Host "Origem: TheBloke/Mistral-7B-Instruct-v0.2-GGUF (Hugging Face)"
Write-Host "Licenca: Apache 2.0 (base Mistral-7B-Instruct-v0.2, sem clausula de"
Write-Host "uso restringindo conteudo adulto)."
Write-Host "Motivo da escolha: quantizacao Q4_K_M roda em CPU comum, e e o ponto"
Write-Host "de partida mais confiavel para validar o pipeline de conversa hoje."
Write-Host "Pode ser trocado depois por outro .gguf (ex.: um finetune de"
Write-Host "roleplay) apenas atualizando LOCAL_LLM_MODEL_PATH no .env."

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
$modelPath = Join-Path $ModelDir $ModelName

$needsDownload = $true
if (Test-Path $modelPath) {
    $existingSize = (Get-Item $modelPath).Length
    if ($existingSize -ge $ModelMinBytes) {
        Write-Host "Ja existe e tem tamanho plausivel ($([math]::Round($existingSize/1GB,2)) GB) -- pulando download."
        $needsDownload = $false
    } else {
        Write-Host "Arquivo existente parece incompleto ($([math]::Round($existingSize/1MB,1)) MB) -- baixando novamente."
    }
}

if ($needsDownload) {
    Write-Host "Baixando para $modelPath ..."
    Write-Host "Downloads grandes podem cair no meio (conexao instavel) -- o script" -ForegroundColor Yellow
    Write-Host "retoma de onde parou automaticamente, ate 5 tentativas." -ForegroundColor Yellow

    $maxAttempts = 5
    $attempt = 1
    $downloadOk = $false
    while ($attempt -le $maxAttempts -and -not $downloadOk) {
        if ($attempt -gt 1) {
            $resumeSize = 0
            if (Test-Path $modelPath) { $resumeSize = (Get-Item $modelPath).Length }
            Write-Host "`nTentativa $attempt de $maxAttempts (retomando de $([math]::Round($resumeSize/1MB,1)) MB)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }

        if (Test-Command "curl.exe") {
            curl.exe -C - -L --fail --progress-bar -o $modelPath $ModelUrl
        } else {
            Invoke-WebRequest -Uri $ModelUrl -OutFile $modelPath
        }

        if ((Test-Path $modelPath) -and ((Get-Item $modelPath).Length -ge $ModelMinBytes)) {
            $downloadOk = $true
        } else {
            $attempt++
        }
    }

    if (-not $downloadOk) {
        $finalSize = 0
        if (Test-Path $modelPath) { $finalSize = (Get-Item $modelPath).Length }
        Write-Host "[ERRO] Download incompleto apos $maxAttempts tentativas ($([math]::Round($finalSize/1MB,1)) MB, esperado ~4.4 GB)." -ForegroundColor Red
        Write-Host "O arquivo parcial foi mantido -- rode este script novamente mais tarde" -ForegroundColor Red
        Write-Host "para retomar de onde parou (nao precisa recomecar do zero)." -ForegroundColor Red
        exit 1
    }
    $downloadedSize = (Get-Item $modelPath).Length
    Write-Host "Download concluido ($([math]::Round($downloadedSize/1GB,2)) GB)." -ForegroundColor Green
}

Write-Host "`n=== 3/3: Validacao + configuracao do projeto ===" -ForegroundColor Cyan
& $BackendPython -c "from gpt4all import GPT4All; print('gpt4all OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Nao foi possivel importar gpt4all apos a instalacao." -ForegroundColor Yellow
}

Set-EnvValue -Path $EnvFile -Key "LLM_PROVIDER" -Value "local"
Set-EnvValue -Path $EnvFile -Key "LOCAL_LLM_MODEL_PATH" -Value $modelPath
Write-Host "`n.env atualizado: LLM_PROVIDER=local, LOCAL_LLM_MODEL_PATH=$modelPath" -ForegroundColor Green

Write-Host "`nConcluido." -ForegroundColor Green
Write-Host "Reinicie o backend (scripts\start.bat, ou Ctrl+C + subir de novo o" -ForegroundColor Yellow
Write-Host "uvicorn) para carregar o modelo local. A primeira resposta demora" -ForegroundColor Yellow
Write-Host "mais (carregando o modelo na memoria); as seguintes sao mais rapidas." -ForegroundColor Yellow
