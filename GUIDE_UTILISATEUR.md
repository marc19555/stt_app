# Guide d'installation et de mise en place du projet stt_app sur Windows

## Infos générales + prérequis

Cette page d'information est valide pour Windows.

Vous aurez besoin d'un écran, d'un clavier, d'une souris, d'une connexion internet (pour la mise en place) et d'une clé USB (pour la récupération des fichiers traités).

Pour ouvrir un invite de commande :

- utilisez le raccourci Windows + R,
- dans le champ de saisie qui apparait tapez `cmd` puis Entrée,

ou alors dans la recherche Windows tapez « invite de commande » / « cmd » et cliquez sur l'icône qui apparait.

## Installation

Pour mettre en place un boitier il faut commencer par installer :

**Ollama** : [https://ollama.com/download/windows](https://ollama.com/download/windows)

**WSL** (Windows Subsystem for Linux), dans un invite de commande tapez :

```
wsl --update
```

**Docker** : [https://docs.docker.com/desktop/setup/install/windows-install/](https://docs.docker.com/desktop/setup/install/windows-install/)

Pour Docker il n'est pas nécessaire de se connecter, on peut ignorer l'authentification.

Le projet stt_app qui est sur mon GitHub : [https://github.com/marc19555/stt_app](https://github.com/marc19555/stt_app)

Pour le projet GitHub, cliquez sur le bouton « Code » en vert puis « Download ZIP ».

Ensuite ouvrez le projet dans un éditeur de code comme Visual Studio Code.

Renommez `.env.local.exemple` en `.env.local`.

Dans le `.env.local` vous devez renseigner un token Hugging Face.

Pour obtenir un token valide créez un compte sur Hugging Face : [https://huggingface.co/join](https://huggingface.co/join)

Vous devez accepter les termes et conditions des modèles pyannote et Whisper (à vérifier).

Ensuite lancez la commande :

```
cd stt_app\agent_windows
pip install -r requirements.txt
python database.py
```

Cela installe les dépendances et initialise la base de données.

Pour télécharger le modèle d'IA qu'on utilise ici, faites la commande suivante dans un invite de commande (assurez-vous d'avoir déjà installé Ollama) :

```
ollama pull qwen3.5:4b
```

Vous pouvez configurer une clé USB comme périphérique pour récupérer les données. Vous devez connaitre le label exact de votre clé, par exemple `RESUME` (modifiable dans le `config.py` de `agent_windows`).

Dans le dossier `stt_app` vous trouverez un `start.bat`.

Ce `start.bat` permet de démarrer l'application Windows et Docker (et d'ouvrir le serveur local Ollama).

Vous aurez 3 fenêtres qui s'ouvriront :

- une fenêtre de démarrage Ollama (pas intéressante, à garder ouverte mais à ignorer),
- une fenêtre de l'application,
- une fenêtre Docker.

Docker va donc lancer son build, pour la première fois ça peut prendre plusieurs minutes (installation des composants Linux nécessaires et des dépendances).

Ensuite testez F12 pour enregistrer, puis F12 pour arrêter et lancer le traitement (le résultat est sauvegardé dans la base de données).

Si vous voyez que Docker détecte un job et arrive au bout, bien joué, c'est réussi.

## Ça serait mieux de faire ça aussi

Avec le raccourci Ctrl + Shift + Échap on ouvre le gestionnaire des tâches.

Dans l'onglet « Applications de démarrage », désactivez les services inutiles.

⚠️ **Ne pas désactiver `SecurityHealthSystray.exe`, `ollama.exe` et `docker.exe`** (peut-être j'en oublie d'autres).

## Problèmes possibles anticipés

Dans les deux invites de commande, les logs s'affichent en direct sous vos yeux. C'est ici que se passe le débogage.

Dans Docker on peut avoir :

- une erreur de token Hugging Face (token manquant, invalide, ou conditions d'utilisation des modèles pyannote/Whisper non acceptées) ;
- un serveur Ollama qui ne répond pas (vérifier que la fenêtre Ollama est bien ouverte, relancer `start.bat` si besoin) ;
- un débordement de la RAM si mal géré (je crois — pas sûr que ce soit vraiment possible).

Au lancement de l'agent Windows vous pouvez avoir une erreur de périphérique audio non détecté, mais cette erreur est non bloquante, pas besoin de relancer le script.

*(Cette liste sera complétée au fil des retours d'utilisation.)*

## Comment l'application marche, alors

### Fonctionnement général

De manière très générale, l'application se compose d'une partie qui fonctionne sous Windows (`agent_windows`) et d'une partie qui fonctionne sous Linux (`pipeline_worker`). Et d'une base de données SQLite localisée dans le dossier `data`.

La partie Windows récupère les données et les envoie dans la base de données.

La partie Linux récupère les données de la base de données et les traite (STT + diarisation) puis renvoie les données dans la base de données.

Enfin on peut récupérer les données de la base de données grâce à une clé USB.

L'application se divise en trois grandes parties :

1. agent_windows
2. pipeline_worker
3. data
4. le reste

### 1. agent_windows

L'agent Windows se compose de plusieurs parties.

Le « déclencheur » est `hotkey_listener.py`, il sert notamment à « écouter » l'appui sur la touche F12 pour commencer et arrêter l'enregistrement audio. Il ne peut y avoir qu'une seule instance du hotkey listener grâce à la création d'un verrou via `SingleInstanceLock`.

Ensuite on a `ram_server.py`, lui sert à lancer le serveur HTML en arrière-plan pour permettre d'afficher la RAM dans les logs de Docker.

Puis `usb_listener.py` qui vérifie la présence d'une clé USB toutes les 5 secondes et copie les fichiers traités vers la clé USB si elle est détectée.

`session_manager.py` gère les sessions et les enregistrements, il sauvegarde les données dans la base de données.

`recorder.py` enregistre l'audio.

`audio_chunker.py` découpe l'audio enregistré en morceaux avant traitement (à compléter/vérifier).

`notifier.py` gère les notifications de l'application (à compléter/vérifier).

`database.py` sert à initialiser la base de données.

`config.py` sert à configurer l'application.

`simple_logger.py` gère l'écriture des logs.

### 2. pipeline_worker

C'est la partie qui tourne dans Docker, sous Linux. Elle surveille la base de données, traite les enregistrements en attente (transcription, diarisation, génération du PV et du résumé), puis renvoie les résultats dans la base.

`worker.py` orchestre l'ensemble du pipeline : il détecte les nouveaux jobs et enchaine les étapes de traitement.

`audio_preprocess.py` prépare l'audio avant la transcription.

`transcription.py` transcrit l'audio en texte.

`diarization.py` identifie qui parle et à quel moment.

`speaker_merger.py` fusionne les informations de transcription et de diarisation pour attribuer chaque segment de texte au bon locuteur.

`ollama_client.py` fait le lien avec le serveur Ollama pour générer le compte-rendu et le résumé.

`pv_generator.py` génère le procès-verbal (PV) de la réunion.

`summary_generator.py` génère le résumé de la réunion.

`exporter.py` / `exporter2.py` exportent les résultats finaux (à préciser, différence entre les deux à clarifier).

`database.py` gère l'accès à la base de données depuis le pipeline.

`config.py` sert à configurer le pipeline.

`simple_logger.py` gère l'écriture des logs du pipeline.

`Dockerfile` définit l'image Docker utilisée pour exécuter le pipeline.

`requirements.txt` liste les dépendances Python du pipeline.

### 3. data

Dossier qui contient toutes les données générées par l'application :

- `stt_app.db`, la base de données SQLite ;
- `logs/`, les fichiers de logs, avec un sous-dossier `archive/` pour les anciens logs ;
- `sessions/`, un dossier par réunion enregistrée (ex. `Réunion_20260616_162049`), chacun avec un sous-dossier `audio/` contenant les fichiers audio correspondants.

### 4. le reste

`.env.local` contient les informations sensibles (ex. token Hugging Face), ne doit pas être partagé.

`.env.local.exemple` est le modèle vide à copier et compléter.

`.gitignore` liste les fichiers/dossiers exclus du suivi Git.

`docker-compose.yml` décrit comment lancer le conteneur `pipeline_worker`.

`start.bat` démarre l'application (agent Windows + Docker + Ollama).

`stop.bat` arrête l'application.
