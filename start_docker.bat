@echo off
setlocal

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker n'est pas installe ou n'est pas dans le PATH.
  exit /b 1
)

call :ensure_docker_daemon
if errorlevel 1 (
  exit /b 1
)

if not exist ".env.local" (
  echo [WARN] Fichier .env.local introuvable. Creation d'un fichier vide.
  type nul > .env.local
  echo [INFO] Ajoute HF_TOKEN=... dans .env.local puis relance si necessaire.
)

echo [INFO] Demarage Ollama avec OLLAMA_HOST=0.0.0.0
set "OLLAMA_HOST=0.0.0.0"
start "" ollama serve
timeout /t 5 /nobreak >nul

echo [INFO] Build + demarrage du service stt-app...
docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] Echec du lancement Docker Compose.
  exit /b 1
)

echo [OK] Service lance.
echo [INFO] Jupyter: http://localhost:8888

echo [INFO] Pour suivre les logs: docker compose logs -f
endlocal
exit /b 0

:ensure_docker_daemon
docker info >nul 2>nul
if not errorlevel 1 (
  echo [INFO] Docker daemon detecte.
  exit /b 0
)

echo [WARN] Docker daemon non joignable. Tentative de demarrage de Docker Desktop...

set "DOCKER_DESKTOP_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not exist "%DOCKER_DESKTOP_EXE%" (
  set "DOCKER_DESKTOP_EXE=%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe"
)

if exist "%DOCKER_DESKTOP_EXE%" (
  start "" "%DOCKER_DESKTOP_EXE%"
) else (
  echo [ERROR] Docker Desktop introuvable. Lance Docker Desktop manuellement puis relance ce script.
  exit /b 1
)

set /a MAX_TRIES=45
set /a TRY=0

:wait_for_docker
docker info >nul 2>nul
if not errorlevel 1 (
  echo [INFO] Docker daemon pret.
  exit /b 0
)

set /a TRY+=1
if %TRY% GEQ %MAX_TRIES% (
  echo [ERROR] Docker Desktop ne repond pas apres 90 secondes.
  echo [ERROR] Ouvre Docker Desktop, attends le statut "Engine running", puis relance ce script.
  exit /b 1
)

timeout /t 2 /nobreak >nul
goto :wait_for_docker
