"""
Gestion centralisée des secrets pour Qual.IA.

Priorité de résolution :
  1. os.getenv(key)          → fonctionne en local avec .env (via python-dotenv)
  2. st.secrets.get(key)     → fonctionne sur Streamlit Community Cloud
  3. default                 → valeur par défaut optionnelle
  4. Exception claire        → si aucune valeur trouvée

Utilisation :
    from backend.config import get_secret
    api_key = get_secret("ANTHROPIC_API_KEY")
    model   = get_secret("CLAUDE_MODEL", "claude-sonnet-4-6")
"""

import os
from typing import Optional


def get_secret(key: str, default: Optional[str] = None) -> str:
    """
    Résout un secret dans cet ordre :
      1. Variable d'environnement (os.getenv) — local via .env
      2. st.secrets — Streamlit Community Cloud
      3. Valeur par défaut si fournie
      4. Exception explicite

    Args:
        key:     Nom de la variable / secret à lire.
        default: Valeur de repli si aucune source ne contient la clé.

    Returns:
        La valeur du secret sous forme de chaîne.

    Raises:
        ValueError: Si le secret est introuvable et qu'aucun default n'est fourni.
    """
    # 1. Variable d'environnement (local .env ou vars système)
    value = os.getenv(key)
    if value and value.strip() and not value.startswith("sk-ant-VOTRE"):
        return value.strip()

    # 2. st.secrets (Streamlit Cloud) — import optionnel pour éviter
    #    les erreurs si streamlit n'est pas installé (scripts CLI, tests)
    try:
        import streamlit as st
        cloud_value = st.secrets.get(key)
        if cloud_value and str(cloud_value).strip():
            return str(cloud_value).strip()
    except Exception:
        # streamlit non disponible, ou secrets non configurés — on continue
        pass

    # 3. Valeur par défaut
    if default is not None:
        return default

    # 4. Aucune source → exception explicite
    raise ValueError(
        f"Secret '{key}' introuvable.\n"
        f"  • En local : ajoutez '{key}=<valeur>' dans le fichier .env à la racine du projet.\n"
        f"  • Sur Streamlit Cloud : ajoutez '{key}' dans Settings → Secrets (format TOML).\n"
        f"    Exemple : {key} = \"sk-ant-api...\""
    )
