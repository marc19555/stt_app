@echo off
echo Arret STT...

echo Arret du conteneur Docker...
docker-compose down

echo Arret du hotkey listener...
taskkill /FI "WINDOWTITLE eq Agent window" /T /F >nul 2>&1
wmic process where "commandline like '%%hotkey_listener%%'" delete >nul 2>&1

echo Arret Ollama...
taskkill /FI "WINDOWTITLE eq Ollama" /T /F >nul 2>&1

echo Tout est arrete.
pause
