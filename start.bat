@echo off
setlocal
cd /d "%~dp0"
echo lancement STT

if not exist ".env.local" (
    echo [ERREUR] .env.local absent. Lancez d'abord install.ps1.
    pause
    exit /b 1
)

echo Verification du daemon Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker non actif, demarrage en cours...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    :wait_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if errorlevel 1 goto wait_docker
    echo Docker pret.
) else (
    echo Docker deja actif.
)

ollama list >nul 2>&1
if errorlevel 1 start "Ollama" powershell -WindowStyle Hidden -Command "$env:OLLAMA_HOST='127.0.0.1:11434'; ollama serve"

timeout /t 5 /nobreak

powershell -NoProfile -NonInteractive -File "scripts\check-ollama-binding.ps1"
if errorlevel 1 (
    echo [ERREUR] Ollama est absent ou ecoute sur le reseau. Arretez-le puis relancez start.bat.
    pause
    exit /b 1
)

start "Docker Worker" cmd /k "docker compose --env-file .env.local up --build"

timeout /t 3 /nobreak

start "Agent window" cmd /k ".venv\Scripts\python.exe agent_windows\hotkey_listener.py"

echo La reunion peut commencer ! appuyez sur f12 pour enregistrer la session.
endlocal
