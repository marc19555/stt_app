@echo off
echo lancement STT

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

start "Ollama" powershell -WindowStyle Hidden -Command "$env:OLLAMA_HOST='0.0.0.0:11434'; ollama serve"

timeout /t 5 /nobreak

start "Docker Worker" cmd /k "docker-compose up"

timeout /t 3 /nobreak

start "Agent window" cmd /k "python agent_windows/hotkey_listener.py"

echo La reunion peut commencer ! appuyez sur f12 pour enregistrer la session.
