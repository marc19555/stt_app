# Guide utilisateur — Windows, CPU, 8 Go de RAM

Cette version enregistre une réunion, transcrit l'audio localement avec Whisper,
puis produit un PV et un résumé avec Ollama. Aucun service d'IA distant n'est
nécessaire.

> **Important :** les documents générés sont des brouillons. Ils doivent être
> relus avant toute diffusion. Consultez aussi
> [DEPLOIEMENT_PROFESSIONNEL.md](DEPLOIEMENT_PROFESSIONNEL.md) : l'usage au travail
> reste bloqué tant que les autorisations juridiques, DPO et RSSI ne sont pas acquises.

## Configuration recommandée

- Windows 10/11, 8 Go de RAM, CPU uniquement ;
- Python **3.11** ;
- Docker Desktop avec WSL 2 ;
- Ollama ;
- une seule réunion traitée à la fois.

Le modèle par défaut est `granite4.1:3b` (environ 2,1 Go dans Ollama), choisi pour
le français, la sortie structurée et les usages d'entreprise. Le modèle
`qwen3.5:0.8b` est installé comme secours ultra-léger. Le contexte est limité à
8K et la sortie à 2K tokens ; les réunions longues sont synthétisées par étapes.

## Installation

Installez Python 3.11, Docker Desktop et Ollama, puis ouvrez PowerShell dans le
dossier du projet :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Le script vérifie Python, Docker, Ollama, le microphone et les ports ; il crée
`.env.local`, génère le jeton du proxy, installe les dépendances, initialise
SQLite, télécharge les modèles et construit le conteneur.

Si aucun `.wslconfig` n'existe, il installe la limite suivante : 3 Go de RAM,
2 CPU et 2 Go de swap. Fermez les traitements puis exécutez `wsl --shutdown`
pour l'appliquer. Si une configuration existe déjà, vérifiez-la ou lancez
`scripts\configure-wsl.ps1`, qui en crée d'abord une sauvegarde.

## Utilisation

1. Lancez `start.bat`.
2. Appuyez sur `F12` pour démarrer l'enregistrement.
3. Appuyez à nouveau sur `F12` pour l'arrêter et créer le job.
4. Attendez la fin du worker Docker.
5. Relisez les fichiers `pv.docx` et `resume.docx` dans le dossier de session.

Whisper utilise le modèle `base`, le CPU en `int8`, `beam_size=1` et aucun
horodatage par mot. La diarisation est désactivée par défaut ; tous les propos
sont alors associés à `Intervenant_1`. Pour l'activer sur un PC plus puissant,
ajoutez un jeton Hugging Face et passez `DIARIZATION_ENABLED=true` dans
`.env.local`, puis relancez `start.bat` pour reconstruire l'image.

## Sécurité et conservation

- Ollama écoute seulement sur `127.0.0.1:11434`.
- Docker passe par un proxy à jeton sur le port 11435. Seules les routes Ollama
  indispensables sont autorisées et aucun corps de requête n'est journalisé.
- Les contenus transcrits ne sont pas affichés dans les logs.
- Après succès, audio, chunks et JSON intermédiaires sont supprimés.
- Les documents restants sont automatiquement supprimés après sept jours.
- Les intervenants restent nommés `Intervenant_1`, `Intervenant_2`, etc. Le
  modèle ne doit jamais déduire leur identité ou leur fonction.
- `.gitignore` et `scripts\check_git_safety.py` empêchent l'ajout accidentel de
  données de réunion, documents et secrets à Git.

## Clé USB sécurisée

La copie exige une clé amovible nommée `RESUMER`, son numéro de volume, un fichier
secret et BitLocker actif. Après avoir activé BitLocker sur la clé :

```powershell
.\scripts\configure-usb.ps1
```

Le script lie la clé à l'installation. À chaque copie, seuls les `.docx` sont
transférés et leur SHA-256 est vérifié avant validation du fichier de destination.

## Arrêt et diagnostic

Utilisez `stop.bat` pour arrêter le worker, l'agent et Ollama. En cas d'échec :

```powershell
.\.venv\Scripts\python.exe agent_windows\preflight.py
docker compose --env-file .env.local ps
docker compose --env-file .env.local logs --tail 100 pipeline_worker
```

Messages usuels :

- `OLLAMA_PROXY_TOKEN absent` : relancez `install.ps1` ;
- conteneur `unhealthy` : vérifiez que l'agent Windows et Ollama sont actifs ;
- modèle absent : exécutez `ollama pull granite4.1:3b` ;
- diarisation impossible : vérifiez le jeton Hugging Face et l'accès au modèle ;
- clé refusée : vérifiez BitLocker puis relancez le provisionnement USB.

## Validation avant pilote

Exécutez les tests avec Python 3.11 :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_git_safety.py
```

Il reste indispensable de réaliser un essai réel d'une heure sur le PC cible,
puis un essai de fusion de quatre heures, avant toute utilisation opérationnelle.
