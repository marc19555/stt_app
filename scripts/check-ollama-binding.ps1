$listeners = Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue
if (-not $listeners) { exit 2 }
$unsafe = $listeners | Where-Object { $_.LocalAddress -notin @("127.0.0.1", "::1") }
if ($unsafe) { exit 1 }
exit 0
