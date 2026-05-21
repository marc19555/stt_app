#!/usr/bin/env sh
set -eu

echo "[INFO] Arret du service stt-app..."
docker compose down

echo "[OK] Service arrete."
