@echo off
echo lancement STT

start "Ollama" cmd /k "set OLLAMA_HOST=0.0.0.0:11434"

timeout /t 5 /nobreak

start "Docker Worker" cmd /k "docker-compose up"

timeout /t 3 /nobreak

start "Agent window" cmd /k "python agent_windows/hotkey_listener.py"

echo La reunion peut commencer ! appuyez sur f12 pour enregistrer la session.
