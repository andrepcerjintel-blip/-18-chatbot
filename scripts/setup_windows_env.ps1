#Requires -Version 5.1
<#
.SYNOPSIS
    Prepara o ambiente Windows para este projeto: Python 3.11 lado a lado
    (sem tocar em outras versoes existentes), virtualenv do backend, e
    Git/Node.js/npm caso ausentes.

.DESCRIPTION
    NAO desinstala, substitui ou altera nenhuma versao de Python ja
    instalada (ex.: Python 3.14). NAO instala drivers de GPU, CUDA
    Toolkit, nem qualquer software critico do sistema. Roda uma unica vez
    (ou sempre que quiser reverificar/reinstalar dependencias ausentes).

.NOTES
    Execute a partir da raiz do projeto ou de qualquer lugar:
        powershell -ExecutionPolicy Bypass -File scripts\setup_windows_env.ps1
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$VenvDir = Join-Path $BackendDir ".venv"

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Confirm-Install {
    param([string]$What)
    $answer = Read-Host "Instalar $What via winget agora? [S/n]"
    return ($answer -eq "" -or $answer -match '^[SsYy]')
}

Write-Host "=== 1/5: Python 3.11 (lado a lado, sem remover outras versoes) ===" -ForegroundColor Cyan
$py311Ok = $false
try {
    $null = & py -3.11 --version 2>$null
    if ($LASTEXITCODE -eq 0) { $py311Ok = $true }
} catch { $py311Ok = $false }

if ($py311Ok) {
    Write-Host "Python 3.11 ja disponivel via 'py -3.11'." -ForegroundColor Green
} else {
    Write-Host "Python 3.11 nao encontrado (isso NAO afeta o Python 3.14 existente)."
    if (Test-Command "winget") {
        if (Confirm-Install "Python 3.11") {
            winget install --id Python.Python.3.11 -e --source winget
        }
    } else {
        Write-Host "winget nao disponivel. Baixe o instalador oficial em:" -ForegroundColor Yellow
        Write-Host "  https://www.python.org/downloads/release/python-3119/"
        Write-Host "Instale normalmente; nao e necessario remover o Python 3.14."
    }
    try {
        $null = & py -3.11 --version 2>$null
        if ($LASTEXITCODE -eq 0) { $py311Ok = $true }
    } catch { $py311Ok = $false }
    if (-not $py311Ok) {
        Write-Host "Python 3.11 ainda nao detectado. Se acabou de instalar, feche e reabra" -ForegroundColor Yellow
        Write-Host "este terminal (PATH precisa recarregar) e rode este script novamente."
        exit 1
    }
}

Write-Host "`n=== 2/5: Virtualenv do projeto (backend\.venv) ===" -ForegroundColor Cyan
if (Test-Path $VenvDir) {
    Write-Host "Ja existe em $VenvDir -- mantendo como esta."
} else {
    py -3.11 -m venv $VenvDir
    Write-Host "Criado em $VenvDir." -ForegroundColor Green
}

Write-Host "`n=== 3/5: Dependencias do backend (dentro do virtualenv) ===" -ForegroundColor Cyan
# "python -m pip", nunca pip.exe diretamente: pip.exe grava o caminho do
# python.exe dentro de si no momento da instalacao -- se a pasta do
# projeto for movida depois, esse caminho fica obsoleto e pip.exe quebra
# ("Fatal error in launcher"), mesmo com python.exe funcionando normalmente.
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip
& "$VenvDir\Scripts\python.exe" -m pip install -r (Join-Path $BackendDir "requirements.txt")

Write-Host "`n=== 4/5: Git ===" -ForegroundColor Cyan
if (Test-Command "git") {
    git --version
} elseif (Test-Command "winget") {
    if (Confirm-Install "Git for Windows") {
        winget install --id Git.Git -e --source winget
    }
} else {
    Write-Host "Git e winget nao encontrados. Instale manualmente:" -ForegroundColor Yellow
    Write-Host "  https://git-scm.com/download/win"
}

Write-Host "`n=== 5/5: Node.js (LTS) e npm ===" -ForegroundColor Cyan
if (Test-Command "node") {
    node --version
    npm --version
} elseif (Test-Command "winget") {
    if (Confirm-Install "Node.js LTS") {
        winget install --id OpenJS.NodeJS.LTS -e --source winget
    }
} else {
    Write-Host "Node.js e winget nao encontrados. Instale manualmente (versao LTS):" -ForegroundColor Yellow
    Write-Host "  https://nodejs.org/"
}

Write-Host "`nConcluido." -ForegroundColor Green
Write-Host "Se Git e/ou Node.js foram instalados agora, FECHE e REABRA o terminal" -ForegroundColor Yellow
Write-Host "(o PATH so atualiza em uma nova sessao) e confirme com:"
Write-Host "  git --version"
Write-Host "  node --version"
Write-Host "  npm --version"
Write-Host "  py -0p"
Write-Host "`nDepois disso, use scripts\start.bat para iniciar o aplicativo."
