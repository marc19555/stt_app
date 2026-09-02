$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Commande manquante: $Name"
    }
}

function New-RandomHex([int]$Bytes) {
    $buffer = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($buffer)
    $rng.Dispose()
    return -join ($buffer | ForEach-Object { $_.ToString("x2") })
}

function Set-EnvValue([string]$Path, [string]$Name, [string]$Value, [switch]$OnlyIfEmpty) {
    $lines = [Collections.Generic.List[string]](Get-Content -LiteralPath $Path)
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^$([regex]::Escape($Name))=(.*)$") {
            $found = $true
            if (-not $OnlyIfEmpty -or [string]::IsNullOrWhiteSpace($Matches[1])) {
                $lines[$i] = "$Name=$Value"
            }
        }
    }
    if (-not $found) { $lines.Add("$Name=$Value") }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllLines($Path, $lines, $utf8NoBom)
}

Write-Host "Verification des prerequis..."
Require-Command "python"
Require-Command "docker"
Require-Command "ollama"

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne "3.11") {
    throw "Python 3.11 est requis (version detectee: $pythonVersion)"
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop n'est pas demarre" }

$env:OLLAMA_HOST = "127.0.0.1:11434"
& ollama list *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    $ready = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 2
        & ollama list *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    }
    if (-not $ready) { throw "Ollama ne demarre pas sur 127.0.0.1:11434" }
}
$unsafeOllama = Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -notin @("127.0.0.1", "::1") }
if ($unsafeOllama) {
    throw "Ollama ecoute sur le reseau. Arretez l'instance exposee avant de continuer."
}

$envFile = Join-Path $PSScriptRoot ".env.local"
if (-not (Test-Path $envFile)) {
    Copy-Item -LiteralPath ".env.local.exemple" -Destination $envFile
}
Set-EnvValue $envFile "OLLAMA_PROXY_TOKEN" (New-RandomHex 32) -OnlyIfEmpty
Set-EnvValue $envFile "USB_SECRET" (New-RandomHex 32) -OnlyIfEmpty

Write-Host "Installation de l'environnement Python Windows..."
if (-not (Test-Path ".venv\Scripts\python.exe")) { & python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r agent_windows\requirements.txt
& .\.venv\Scripts\python.exe agent_windows\database.py

$settings = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') { $settings[$Matches[1]] = $Matches[2] }
}
$models = @($settings["OLLAMA_MODEL"], $settings["OLLAMA_FALLBACK_MODEL"]) | Where-Object { $_ }
foreach ($model in $models | Select-Object -Unique) {
    Write-Host "Telechargement Ollama: $model"
    & ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw "Echec du telechargement de $model" }
}

Write-Host "Construction du worker Docker..."
& docker compose --env-file .env.local config --quiet
if ($LASTEXITCODE -ne 0) { throw "docker-compose.yml invalide" }
& docker compose --env-file .env.local build
if ($LASTEXITCODE -ne 0) { throw "Echec du build Docker" }

$wslTarget = Join-Path $env:USERPROFILE ".wslconfig"
if (-not (Test-Path $wslTarget)) {
    Copy-Item -LiteralPath ".wslconfig.example" -Destination $wslTarget
    Write-Host "Limites WSL installees; executez 'wsl --shutdown' avant le prochain demarrage."
} else {
    Write-Warning ".wslconfig existe deja; verifiez 3 Go RAM, 2 CPU et 2 Go swap."
}

& .\.venv\Scripts\python.exe agent_windows\preflight.py
if ($LASTEXITCODE -ne 0) { throw "Un controle materiel ou reseau a echoue" }

Write-Host "Installation terminee. Provisionnez la cle avec scripts\configure-usb.ps1."
Write-Host "Le deploiement professionnel reste interdit sans autorisation de l'auteur et validation DPO/RSSI."
