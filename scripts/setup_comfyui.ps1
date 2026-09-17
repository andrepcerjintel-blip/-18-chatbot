#Requires -Version 5.1
<#
.SYNOPSIS
    Fase 2: instala e configura o ComfyUI local para geracao de imagem,
    com parametros conservadores para GPUs de baixa VRAM (4 GB).

.DESCRIPTION
    - Clona/atualiza o ComfyUI em <raiz do projeto>\ComfyUI (venv proprio,
      separado do backend, para nao misturar dependencias pesadas).
    - Instala PyTorch com suporte CUDA (build oficialmente suportada;
      tenta cu128, cu126, cu124, cu121 nessa ordem -- nunca instala CUDA
      Toolkit global).
    - Instala as dependencias do ComfyUI.
    - Baixa UM checkpoint leve (Stable Diffusion 1.5, fp16, ~2.1 GB,
      licenca CreativeML Open RAIL-M) para validacao funcional do
      pipeline -- escolhido por ser o mais leve/estavel/compativel para
      4 GB de VRAM, conforme documentado em HARDWARE.md.
    - Atualiza o .env do projeto para usar MEDIA_PROVIDER=comfyui.
    - Valida a instalacao com torch.cuda.is_available().

    NAO instala drivers de GPU, NAO instala CUDA Toolkit global, NAO
    remove Python 3.14 nem qualquer outra versao existente.

.NOTES
    Rode DEPOIS de scripts\setup_windows_env.ps1 (Python 3.11 + Git +
    Node ja devem estar disponiveis).

        powershell -ExecutionPolicy Bypass -File scripts\setup_comfyui.ps1
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendVenv = Join-Path $RepoRoot "backend\.venv"
$ComfyDir = Join-Path $RepoRoot "ComfyUI"
$ComfyVenv = Join-Path $ComfyDir "venv"
$EnvFile = Join-Path $RepoRoot ".env"

# Checkpoint escolhido para validacao funcional do pipeline em 4 GB VRAM.
# Ver HARDWARE.md secao "Candidatos de checkpoint visual" para a
# justificativa completa (mais leve, mais compativel, licenca clara).
$CheckpointName = "v1-5-pruned-emaonly-fp16.safetensors"
$CheckpointUrl = "https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly-fp16.safetensors"
$CheckpointMinBytes = 1.5GB  # sanity check: arquivo real tem ~2.1 GB

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

Write-Host "=== 0/6: Pre-requisitos ===" -ForegroundColor Cyan
if (-not (Test-Path "$BackendVenv\Scripts\python.exe")) {
    Write-Host "[ERRO] backend\.venv nao encontrado. Rode primeiro:" -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1"
    exit 1
}
if (-not (Test-Command "git")) {
    Write-Host "[ERRO] Git nao encontrado. Rode primeiro scripts\setup_windows_env.ps1." -ForegroundColor Red
    exit 1
}
try {
    $null = & py -3.11 --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "py -3.11 indisponivel" }
} catch {
    Write-Host "[ERRO] Python 3.11 (via 'py -3.11') nao encontrado. Rode scripts\setup_windows_env.ps1." -ForegroundColor Red
    exit 1
}
Write-Host "OK." -ForegroundColor Green

Write-Host "`n=== 1/6: ComfyUI (clonar/atualizar para ultima RELEASE estavel) ===" -ForegroundColor Cyan
if (Test-Path (Join-Path $ComfyDir ".git")) {
    Write-Host "Ja clonado em $ComfyDir -- buscando atualizacoes..."
    git -C $ComfyDir fetch --all --tags --prune
} else {
    git clone https://github.com/comfyanonymous/ComfyUI $ComfyDir
    git -C $ComfyDir fetch --tags
}

# Usa a ULTIMA TAG DE RELEASE (ex.: v0.7.x), nunca a branch de
# desenvolvimento (master) diretamente. A branch muda a cada commit e
# suas dependencias transitorias (ex.: comfy-kitchen) frequentemente
# ficam fora de sincronia com o que esta publicado no PyPI naquele
# momento -- causando erros como "AttributeError: module 'comfy_kitchen'
# has no attribute ...". Uma release marcada e testada como um conjunto
# coerente de codigo + requirements.txt.
$latestTag = (git -C $ComfyDir tag --sort=-v:refname | Select-Object -First 1)
if ($latestTag) {
    Write-Host "Usando release estavel: $latestTag"
    git -C $ComfyDir checkout $latestTag --quiet 2>$null
} else {
    Write-Host "[AVISO] Nenhuma tag de release encontrada -- usando a branch padrao (pode ser instavel)." -ForegroundColor Yellow
}

Write-Host "`n=== 2/6: Virtualenv proprio do ComfyUI ===" -ForegroundColor Cyan
if (Test-Path $ComfyVenv) {
    Write-Host "Ja existe em $ComfyVenv -- mantendo."
} else {
    py -3.11 -m venv $ComfyVenv
    Write-Host "Criado em $ComfyVenv." -ForegroundColor Green
}
$ComfyPython = Join-Path $ComfyVenv "Scripts\python.exe"
# Sempre "python -m pip", nunca pip.exe diretamente: pip.exe e um
# launcher com o caminho do python.exe gravado dentro dele no momento da
# instalacao -- se a pasta do projeto for movida depois (ex.: de
# Downloads para Desktop), esse caminho fica obsoleto e pip.exe quebra
# ("Fatal error in launcher"), mesmo com python.exe funcionando normalmente.
& $ComfyPython -m pip install --upgrade pip

Write-Host "`n=== 3/6: PyTorch com suporte CUDA (build oficial, sem Toolkit global) ===" -ForegroundColor Cyan
Write-Host "IMPORTANTE: 'CUDA 13.0' no driver e apenas compatibilidade maxima," -ForegroundColor Yellow
Write-Host "NAO exige instalar o CUDA Toolkit 13.0. Instalando o wheel do PyTorch" -ForegroundColor Yellow
Write-Host "com runtime CUDA embutido -- tags mais novas primeiro (o ComfyUI atual" -ForegroundColor Yellow
Write-Host "exige PyTorch >= 2.7 para funcionar sem erros de compatibilidade)." -ForegroundColor Yellow

$torchOk = $false
foreach ($cudaTag in @("cu128", "cu126", "cu124", "cu121")) {
    Write-Host "Tentando build $cudaTag..."
    & $ComfyPython -m pip install --upgrade torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/$cudaTag"
    if ($LASTEXITCODE -eq 0) {
        $torchOk = $true
        Write-Host "PyTorch ($cudaTag) instalado." -ForegroundColor Green
        break
    }
    Write-Host "Build $cudaTag falhou, tentando proxima opcao..." -ForegroundColor Yellow
}
if (-not $torchOk) {
    Write-Host "[AVISO] Nenhuma build CUDA instalou com sucesso. Instalando PyTorch" -ForegroundColor Yellow
    Write-Host "CPU-only como fallback -- geracao funcionara, porem MUITO mais lenta" -ForegroundColor Yellow
    Write-Host "(sem aceleracao de GPU). Verifique manualmente https://pytorch.org/get-started/locally/" -ForegroundColor Yellow
    & $ComfyPython -m pip install torch torchvision torchaudio
}

Write-Host "`n=== 4/6: Dependencias do ComfyUI ===" -ForegroundColor Cyan
& $ComfyPython -m pip install -r (Join-Path $ComfyDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] pip install -r requirements.txt terminou com erro (codigo $LASTEXITCODE)." -ForegroundColor Yellow
    Write-Host "Continuando mesmo assim -- se o ComfyUI reclamar de um modulo" -ForegroundColor Yellow
    Write-Host "faltando ao iniciar, rode: ComfyUI\venv\Scripts\python.exe -m pip install <nome-do-modulo>" -ForegroundColor Yellow
}
# Dependencia usada pelo recurso de banco de dados do ComfyUI
# (app/database/db.py) que, em algumas combinacoes de versao, nao vem
# resolvida automaticamente so com requirements.txt.
& $ComfyPython -m pip install filelock

# comfy-kitchen (dependencia do ComfyUI, backend de otimizacao) exige
# PyTorch >= 2.7 nas versoes atuais do ComfyUI -- com PyTorch mais antigo,
# o import falha com ValueError (nao ImportError, entao nem o fallback do
# proprio ComfyUI pega) e o app inteiro nao sobe.
# Ver https://github.com/Comfy-Org/ComfyUI/issues/15441
$torchVersionOutput = & $ComfyPython -c "import torch; print(torch.__version__)"
Write-Host "PyTorch instalado: $torchVersionOutput"
$torchMajorMinor = $torchVersionOutput -replace '^(\d+)\.(\d+).*', '$1.$2'
if ([version]$torchMajorMinor -lt [version]"2.7") {
    Write-Host "[AVISO] PyTorch $torchVersionOutput e anterior a 2.7 -- o ComfyUI pode" -ForegroundColor Yellow
    Write-Host "falhar ao iniciar (erro de compatibilidade com comfy-kitchen)." -ForegroundColor Yellow
    Write-Host "Nenhuma build CUDA >= 2.7 foi encontrada para este Python/GPU." -ForegroundColor Yellow
    Write-Host "Verifique manualmente builds mais recentes em https://pytorch.org/get-started/locally/" -ForegroundColor Yellow
}

Write-Host "`n=== 5/6: Checkpoint visual ($CheckpointName, ~2.1 GB) ===" -ForegroundColor Cyan
Write-Host "Origem: Comfy-Org/stable-diffusion-v1-5-archive (Hugging Face)"
Write-Host "Licenca: CreativeML Open RAIL-M | Estilo: geral/ilustrativo-realista"
Write-Host "Motivo da escolha: mais leve e mais compativel para validar o"
Write-Host "pipeline em 4 GB de VRAM (ver HARDWARE.md)."

$checkpointDir = Join-Path $ComfyDir "models\checkpoints"
New-Item -ItemType Directory -Force -Path $checkpointDir | Out-Null
$checkpointPath = Join-Path $checkpointDir $CheckpointName

$needsDownload = $true
if (Test-Path $checkpointPath) {
    $existingSize = (Get-Item $checkpointPath).Length
    if ($existingSize -ge $CheckpointMinBytes) {
        Write-Host "Ja existe e tem tamanho plausivel ($([math]::Round($existingSize/1GB,2)) GB) -- pulando download."
        $needsDownload = $false
    } else {
        Write-Host "Arquivo existente parece incompleto ($([math]::Round($existingSize/1MB,1)) MB) -- baixando novamente."
    }
}

if ($needsDownload) {
    Write-Host "Baixando para $checkpointPath ..."
    Write-Host "Downloads grandes podem cair no meio (conexao instavel) -- o script" -ForegroundColor Yellow
    Write-Host "retoma de onde parou automaticamente, ate 5 tentativas." -ForegroundColor Yellow

    $maxAttempts = 5
    $attempt = 1
    $downloadOk = $false
    while ($attempt -le $maxAttempts -and -not $downloadOk) {
        if ($attempt -gt 1) {
            $resumeSize = 0
            if (Test-Path $checkpointPath) { $resumeSize = (Get-Item $checkpointPath).Length }
            Write-Host "`nTentativa $attempt de $maxAttempts (retomando de $([math]::Round($resumeSize/1MB,1)) MB)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }

        if (Test-Command "curl.exe") {
            # -C - retoma um download parcial existente automaticamente.
            curl.exe -C - -L --fail --progress-bar -o $checkpointPath $CheckpointUrl
        } else {
            # Invoke-WebRequest nao retoma; reinicia do zero a cada tentativa.
            Invoke-WebRequest -Uri $CheckpointUrl -OutFile $checkpointPath
        }

        if ((Test-Path $checkpointPath) -and ((Get-Item $checkpointPath).Length -ge $CheckpointMinBytes)) {
            $downloadOk = $true
        } else {
            $attempt++
        }
    }

    if (-not $downloadOk) {
        $finalSize = 0
        if (Test-Path $checkpointPath) { $finalSize = (Get-Item $checkpointPath).Length }
        Write-Host "[ERRO] Download incompleto apos $maxAttempts tentativas ($([math]::Round($finalSize/1MB,1)) MB, esperado ~2.1 GB)." -ForegroundColor Red
        Write-Host "O arquivo parcial foi mantido -- rode este script novamente mais tarde" -ForegroundColor Red
        Write-Host "para retomar de onde parou (nao precisa recomecar do zero)." -ForegroundColor Red
        exit 1
    }
    $downloadedSize = (Get-Item $checkpointPath).Length
    Write-Host "Download concluido ($([math]::Round($downloadedSize/1GB,2)) GB)." -ForegroundColor Green
}

Write-Host "`n=== 6/6: Validacao + configuracao do projeto ===" -ForegroundColor Cyan
& $ComfyPython -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (sem aceleracao GPU)')"

Set-EnvValue -Path $EnvFile -Key "MEDIA_PROVIDER" -Value "comfyui"
Set-EnvValue -Path $EnvFile -Key "IMAGE_MODEL_PATH" -Value $CheckpointName
Set-EnvValue -Path $EnvFile -Key "COMFYUI_URL" -Value "http://127.0.0.1:8188"
Write-Host "`n.env atualizado: MEDIA_PROVIDER=comfyui, IMAGE_MODEL_PATH=$CheckpointName" -ForegroundColor Green

Write-Host "`nConcluido." -ForegroundColor Green
Write-Host "Para iniciar tudo:"
Write-Host "  1) scripts\start_comfyui.bat   (deixa aberto; primeira geracao demora mais)"
Write-Host "  2) scripts\start.bat           (backend + frontend)"
