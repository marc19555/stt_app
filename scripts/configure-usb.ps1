$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $root ".env.local"

if (-not (Test-Path $envPath)) {
    throw ".env.local absent. Lancez d'abord install.ps1."
}

$drive = Read-Host "Lettre de la cle USB BitLocker (ex: E)"
$drive = $drive.Trim().TrimEnd(":").ToUpperInvariant()
if ($drive -notmatch '^[A-Z]$') { throw "Lettre de lecteur invalide" }
$mount = "${drive}:"
$volume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$mount'"
if (-not $volume) { throw "Lecteur $mount introuvable" }
if ($volume.VolumeName -ne "RESUMER") {
    Set-Volume -DriveLetter $drive -NewFileSystemLabel "RESUMER"
    $volume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$mount'"
}

$bitlocker = Get-BitLockerVolume -MountPoint $mount
if (-not $bitlocker -or $bitlocker.ProtectionStatus -ne "On") {
    throw "BitLocker doit etre active sur $mount avant le provisionnement"
}

$serial = $volume.VolumeSerialNumber.Replace("-", "").ToUpperInvariant()
$secretBytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($secretBytes)
$rng.Dispose()
$secret = -join ($secretBytes | ForEach-Object { $_.ToString("x2") })
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText("$mount\.stt-usb-token", $secret, $utf8NoBom)

$content = Get-Content -LiteralPath $envPath
$content = $content -replace '^USB_VOLUME_SERIAL=.*$', "USB_VOLUME_SERIAL=$serial"
$content = $content -replace '^USB_SECRET=.*$', "USB_SECRET=$secret"
[IO.File]::WriteAllLines($envPath, $content, $utf8NoBom)
Write-Host "Cle configuree: $mount, numero $serial, BitLocker actif."
