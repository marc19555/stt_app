$ErrorActionPreference = "Stop"
$source = Join-Path (Split-Path $PSScriptRoot -Parent) ".wslconfig.example"
$target = Join-Path $env:USERPROFILE ".wslconfig"

if (Test-Path $target) {
    $backup = "$target.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $target -Destination $backup
    Write-Host "Configuration WSL existante sauvegardee: $backup"
}

Copy-Item -LiteralPath $source -Destination $target -Force
Write-Host "WSL limite a 3 Go de RAM, 2 CPU et 2 Go de swap."
Write-Host "Executez 'wsl --shutdown' apres avoir ferme les traitements en cours."
