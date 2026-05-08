# Déploiement Qual.IA sur Streamlit Community Cloud

Ce guide explique comment déployer l'application Qual.IA sur [Streamlit Community Cloud](https://share.streamlit.io) à partir d'un dépôt GitHub privé.

---

## Prérequis

- Un compte GitHub (gratuit) : [github.com](https://github.com)
- Un compte Streamlit Cloud (gratuit) : [share.streamlit.io](https://share.streamlit.io)
- Une clé API Anthropic valide : [console.anthropic.com](https://console.anthropic.com)

---

## Étape 1 — Créer un compte et un dépôt GitHub

1. Rendez-vous sur [github.com](https://github.com) et créez un compte si vous n'en avez pas.
2. Cliquez sur **New repository** (bouton vert en haut à droite).
3. Nommez le dépôt (ex : `qual-ia`), choisissez **Private**, puis cliquez sur **Create repository**.

---

## Étape 2 — Uploader le projet sur GitHub

### Option A — Via l'interface web (drag & drop)

1. Dans votre dépôt vide, cliquez sur **uploading an existing file**.
2. Glissez-déposez tous les fichiers du projet (sauf les dossiers `.env`, `backups/`, `exports/`).
3. Cliquez sur **Commit changes**.

> ⚠️ Le fichier `.gitignore` exclut automatiquement les fichiers sensibles. Ne commitez jamais `.env` ni `config/users.json`.

### Option B — Via Git (terminal)

```bash
git init
git remote add origin https://github.com/VOTRE_NOM/qual-ia.git
git add .
git commit -m "Initial commit — Qual.IA"
git push -u origin main
```

---

## Étape 3 — Connecter le dépôt à Streamlit Cloud

1. Connectez-vous sur [share.streamlit.io](https://share.streamlit.io) avec votre compte GitHub.
2. Cliquez sur **New app**.
3. Sélectionnez votre dépôt (`qual-ia`) et la branche (`main`).
4. Dans le champ **Main file path**, saisissez : `frontend/app.py`
5. Cliquez sur **Deploy !**

---

## Étape 4 — Configurer les secrets

L'application a besoin de la clé API Anthropic. Elle ne doit **jamais** être dans le code.

1. Dans Streamlit Cloud, ouvrez votre application déployée.
2. Cliquez sur **⋮ (trois points)** → **Settings** → **Secrets**.
3. Collez le contenu suivant dans l'éditeur TOML :

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-VOTRE_CLE_ICI"
CLAUDE_MODEL = "claude-sonnet-4-6"
```

4. Cliquez sur **Save**. L'application redémarre automatiquement.

> La valeur `CLAUDE_MODEL` est optionnelle — si absente, le modèle `claude-sonnet-4-6` est utilisé par défaut.

---

## Étape 5 — Accéder à l'application

Une fois déployée, votre application est accessible via une URL publique du type :

```
https://VOTRE_NOM-qual-ia-frontend-app-XXXXXX.streamlit.app
```

Partagez cette URL avec vos utilisateurs. L'accès est protégé par l'authentification intégrée de Qual.IA (identifiants par défaut créés au premier démarrage).

---

## Comptes par défaut (premier démarrage)

| Identifiant | Mot de passe    | Rôle                  |
|-------------|-----------------|------------------------|
| admin       | Admin123!       | Administrateur         |
| bt          | BT123!          | Bureau Technique       |
| qualite     | Qualite123!     | Responsable Qualité    |
| direction   | Direction123!   | Direction              |

> **Important :** Changez ces mots de passe dès le premier accès via l'interface **Admin → Gestion des utilisateurs**.

---

## Notes importantes pour Streamlit Cloud

- **Données éphémères** : le système de fichiers de Streamlit Cloud est réinitialisé à chaque redémarrage. Les modifications de comptes utilisateurs et les notifications sont perdues. Pour une utilisation en production, envisagez une base de données externe (ex : Supabase, Firebase).
- **Catégories et références** : les fichiers dans `categories/` sont dans le dépôt git et persistent entre les redémarrages.
- **Exports** : les fichiers générés (Excel, PDF) ne persistent pas. Téléchargez-les immédiatement après génération.
- **Logs** : accessibles depuis Streamlit Cloud dans l'onglet **Logs** de votre application.

---

## Dépannage

| Problème | Solution |
|----------|----------|
| "Secret 'ANTHROPIC_API_KEY' introuvable" | Vérifier la configuration dans Settings → Secrets |
| L'app ne démarre pas | Consulter les logs dans Streamlit Cloud → Logs |
| Module introuvable | Vérifier que toutes les dépendances sont dans `requirements.txt` |
| Erreur 429 / API surchargée | Normal — l'app retente automatiquement jusqu'à 3 fois |
