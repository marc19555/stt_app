@echo off
setlocal

echo [INFO] Arret du service stt-app...
docker compose down
if errorlevel 1 (
  echo [ERROR] Echec de l'arret Docker Compose.
  exit /b 1
)

echo [OK] Service arrete.
echo [INFO] Arret d'Ollama...
taskkill /F /IM ollama.exe /T >nul 2>nul
if errorlevel 1 (
  echo [WARN] Echec de l'arret d'Ollama. Il se peut qu'Ollama ne soit pas en cours d'execution.
) else (
  echo [OK] Ollama arrete.
)
endlocal
