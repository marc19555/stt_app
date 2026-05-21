#!/usr/bin/env sh
set -eu

if [ ! -f .env.local ]; then
	echo "[WARN] Fichier .env.local introuvable. Creation d'un fichier vide."
	: > .env.local
	echo "[INFO] Ajoute HF_TOKEN=... dans .env.local puis relance si necessaire."
fi

echo "[INFO] Build + demarrage du service stt-app..."
docker compose up -d --build

echo "[OK] Service lance."
echo "[INFO] Jupyter: http://localhost:8888"
echo "[INFO] Pour suivre les logs: docker compose logs -f"
