# Guide utilisateur — STT App

## En un coup d'œil

| Action | Comment |
|---|---|
| Lancer l'application | Double-clic sur `start.bat` |
| Démarrer un enregistrement | **F12** → bip aigu |
| Arrêter un enregistrement | **F12** → double bip grave |
| Retrouver les documents | `data/sessions/<nom_réunion>/outputs/` |
| Quitter l'agent | Fermer la fenêtre "Agent window" |

---

## Démarrage

1. Double-cliquer sur **`start.bat`**
2. Si Docker n'est pas actif, il se lance automatiquement — attendre le message `Docker prêt.`
3. Deux fenêtres s'ouvrent :
   - **Docker Worker** — le pipeline de traitement (transcription, PV, résumé)
   - **Agent window** — écoute le clavier et gère les enregistrements
4. Le message `La réunion peut commencer !` s'affiche → tout est prêt

> Ne pas fermer ces fenêtres pendant une session.

---

## Enregistrer une réunion

### Démarrer
- Appuyer sur **F12**
- Un **bip aigu** confirme le démarrage
- L'enregistrement tourne en arrière-plan, aucune manipulation supplémentaire

### Arrêter
- Appuyer à nouveau sur **F12**
- Un **double bip grave** confirme l'arrêt
- Le traitement se lance automatiquement dans la fenêtre Docker Worker

### Arrêt automatique
L'enregistrement s'arrête seul après **4 heures** si F12 n'a pas été pressé.

---

## Récupérer les documents

Une fois le traitement terminé (quelques minutes selon la durée de la réunion), les fichiers sont disponibles dans :

```
data/
└── sessions/
    └── Réunion_YYYYMMDD_HHMMSS/
        └── outputs/
            ├── pv.md        ← Procès-verbal (Markdown)
            ├── pv.docx      ← Procès-verbal (Word)
            ├── resume.md    ← Résumé (Markdown)
            └── resumer.docx ← Résumé (Word)
```

Le nom du dossier est généré automatiquement avec la date et l'heure du démarrage.

---

## Signaux sonores

| Bip | Signification |
|---|---|
| 1 bip aigu (1000 Hz) | Enregistrement démarré |
| 2 bips graves (500 Hz) | Enregistrement arrêté, traitement lancé |
| 3 bips graves courts | Erreur — consulter la fenêtre "Agent window" |

---

## En cas de problème

| Symptôme | Cause probable | Action |
|---|---|---|
| Rien ne se passe au F12 | L'agent n'est pas actif | Vérifier la fenêtre "Agent window" |
| 3 bips d'erreur | Erreur au démarrage/arrêt | Lire le message d'erreur dans "Agent window" |
| Pas de documents après 10 min | Pipeline bloqué | Vérifier la fenêtre "Docker Worker" |
| Docker ne démarre pas | Docker Desktop absent ou chemin incorrect | Lancer Docker Desktop manuellement avant `start.bat` |

Les logs détaillés sont dans `data/logs/`.
