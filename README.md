# IA Qualité — Guide d'installation et d'utilisation

Système de génération automatique de dossiers qualité (AMDEC Produit, AMDEC Process, Gamme de Production) par intelligence artificielle.

---

## Prérequis

- **Windows 10 ou 11** (64 bits)
- **Python 3.11 ou supérieur** — [télécharger ici](https://www.python.org/downloads/)
  - Lors de l'installation, cocher **"Add Python to PATH"**
- **Connexion internet** (pour l'API Claude d'Anthropic)
- **Clé API Anthropic** — obtenir sur [console.anthropic.com](https://console.anthropic.com)

---

## Installation (première fois)

### 1. Copier le dossier projet

Copiez le dossier `projet-qualite-ia` sur le nouveau PC, par exemple dans :
```
C:\Users\VotreNom\Desktop\projet-qualite-ia\
```

### 2. Créer le fichier de configuration `.env`

Dans le dossier du projet, créez un fichier nommé `.env` (pas `.env.txt`) avec ce contenu :
```
ANTHROPIC_API_KEY=sk-ant-VOTRE_CLE_ICI
CLAUDE_MODEL=claude-sonnet-4-6
```

Remplacez `sk-ant-VOTRE_CLE_ICI` par votre vraie clé API.

> **Comment créer un fichier `.env` ?**
> Ouvrez le Bloc-notes → Fichier → Enregistrer sous → dans "Nom du fichier" tapez `.env` → dans "Type" choisissez "Tous les fichiers (*.*)" → Enregistrer.

### 3. Installer les dépendances Python

Ouvrez une invite de commande dans le dossier du projet (clic droit → "Ouvrir dans le terminal") et tapez :
```
pip install -r requirements.txt
```

### 4. Lancer l'application

Double-cliquez sur **`Lancer_IA_Qualite.bat`**.

L'application s'ouvre automatiquement dans votre navigateur sur `http://localhost:8501`.

---

## Utilisation quotidienne

### Générer un dossier qualité

1. **Sélectionner la catégorie** dans le menu de gauche (Couches minces, Glace nue, Céramique…)
2. **Remplir le brief client** : type de produit, matière, traitements, dimensions
3. Cliquer **"Analyser la similarité"** — le système trouve la référence la plus proche
4. Vérifier la référence source proposée, puis cliquer **"Générer les documents"**
5. **Relire et corriger** les 3 documents dans les tableaux éditables
6. **Exporter en Excel** et/ou **Enregistrer en base** pour enrichir la bibliothèque

### Gérer la base de références

- Aller dans **"Gestion de la base"** dans la navigation
- Consulter, modifier ou supprimer des références existantes
- Les modifications sont sauvegardées directement dans les fichiers JSON

---

## Sauvegardes automatiques

À chaque démarrage de l'application, une copie complète de la base est créée dans `backups/auto/YYYY-MM-DD/`.

Les sauvegardes de plus de **30 jours** sont supprimées automatiquement.

Pour **restaurer une sauvegarde** : aller dans "Gestion de la base" → onglet "Sauvegardes".

---

## Structure du projet

```
projet-qualite-ia/
├── Lancer_IA_Qualite.bat       ← Double-cliquer pour démarrer
├── .env                         ← Clé API (ne jamais partager)
├── requirements.txt
├── frontend/
│   └── app.py                   ← Interface Streamlit
├── backend/
│   ├── similarity_engine.py     ← Moteur de similarité
│   ├── document_generator.py    ← Génération via Claude API
│   ├── category_manager.py      ← Gestion des catégories
│   ├── reference_manager.py     ← Lecture/écriture des références
│   ├── reference_saver.py       ← Enregistrement nouvelles références
│   ├── backup_manager.py        ← Sauvegardes automatiques
│   └── excel_exporter.py        ← Export Excel
├── categories/
│   ├── couches_minces/
│   │   ├── config.json          ← Config + vocabulaire + poids similarité
│   │   └── references/          ← Base de données des références
│   ├── glace_nue/
│   └── ceramique/
├── templates/
│   └── Templates_AMDEC_Gamme.xlsx
├── exports/                     ← Fichiers Excel générés
└── backups/                     ← Sauvegardes automatiques
```

---

## Transférer sur un autre ordinateur

1. Copier tout le dossier `projet-qualite-ia/` (clé USB, réseau, OneDrive…)
2. Installer Python sur le nouveau PC (si pas déjà fait)
3. Créer le fichier `.env` avec la clé API
4. Double-cliquer sur `Lancer_IA_Qualite.bat` — il installe automatiquement les dépendances

> La base de données (dossier `categories/`) voyage avec le projet. Toutes les références et configurations sont incluses.

---

## Ajouter une nouvelle catégorie

Dans l'interface → "Gestion de la base" → onglet "Catégories" → "Créer une catégorie".

Ou manuellement : créer un dossier `categories/<code>/` avec un `config.json` (voir les exemples existants).

---

## Résolution de problèmes

| Problème | Solution |
|----------|----------|
| "Clé API manquante" | Vérifier que le fichier `.env` existe et contient `ANTHROPIC_API_KEY=sk-ant-...` |
| L'app ne s'ouvre pas | Vérifier que Python est installé : ouvrir cmd et taper `python --version` |
| "Module not found" | Ouvrir cmd dans le dossier projet et relancer `pip install -r requirements.txt` |
| Page blanche dans le navigateur | Attendre 5-10 secondes puis rafraîchir (F5) |
| Erreur JSON de Claude | Réessayer la génération — peut être transitoire |

---

## Contact et support

Pour toute question sur l'utilisation, contacter le responsable qualité ou l'équipe IT.
