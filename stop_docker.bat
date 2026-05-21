@echo off
setlocal

echo [INFO] Arret du service stt-app...
docker compose down
if errorlevel 1 (
  echo [ERROR] Echec de l'arret Docker Compose.
  exit /b 1
)

echo [OK] Service arrete.
endlocal
