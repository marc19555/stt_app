# Recommandations d'Amélioration pour le Dépôt `stt_app`

Ce document présente une série de constats et d'axes d'amélioration identifiés lors du déploiement du pipeline de transcription en local. Ces retours visent à rendre le projet plus robuste, plus simple à lancer et plus performant.

---

### 1. Optimisation et gestion des performances CPU
* **Problème technique :** Les modèles de transcription (Whisper) et de traitement (PyTorch/Pyannote) s'exécutent avec des configurations de threads figées ou par défaut très basses (généralement 4 threads maximum). Sur des machines avec des processeurs multi-cœurs modernes, le CPU est largement sous-exploité, ce qui ralentit considérablement la transcription.
* **Axe d'amélioration :** Intégrer une détection dynamique des cœurs du système pour ajuster à la volée le nombre de threads alloués aux bibliothèques de calcul lors du chargement des modèles.

---

### 2. Résolution réseau d'Ollama dans un conteneur
* **Problème technique :** Le point d'accès d'Ollama est configuré en dur sur `localhost`. Lors d'une exécution conteneurisée, le conteneur tente de joindre Ollama à l'intérieur de sa propre interface isolée et échoue avec une erreur de connexion refusée, car Ollama tourne sur la machine hôte.
* **Axe d'amélioration :** Ajouter une détection automatique dans le script pour identifier si le code tourne dans un conteneur ou en local, afin d'adapter dynamiquement l'adresse de l'hôte cible.

---

### 3. Facilité de déploiement et d'orchestration (Docker)
* **Problème technique :** Le dépôt contient un `Dockerfile` mais aucun outil pour l'orchestrer. Les utilisateurs doivent lancer manuellement des commandes Docker complexes pour mapper les ports, monter les volumes nécessaires aux données d'entrée/sortie, et injecter les variables d'environnement.
* **Axe d'amélioration :** Fournir une configuration Docker Compose standardisée pour gérer automatiquement le montage des dossiers locaux, le routage réseau vers l'hôte, et les variables d'environnement. Mettre également à disposition des scripts de lancement rapide en un clic pour les utilisateurs.

---

### 4. Structure des dossiers et variables d'environnement au premier lancement
* **Problème technique :** Si l'utilisateur exécute le notebook juste après avoir cloné le dépôt, il rencontre des erreurs de dossiers manquants (comme pour les fichiers audio d'entrée) et n'a pas d'indication claire sur les variables d'environnement requises (comme le token Hugging Face).
* **Axe d'amélioration :** Versionner la structure minimale des répertoires de travail via Git (en utilisant des fichiers de marquage) et ajouter un modèle d'exemple pour les variables de configuration indispensables.
