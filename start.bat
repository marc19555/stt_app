@echo off
echo lancement STT

start "Docker Worker" cmd /k "docker-compose up"

timeout /t 3 /nobreak

start "Agent window" cmd /k "python agent_windows/hotkey_listener.py"

echo La reunion peut commencer ! appuyez sur f12 pour enregistrer la session.
