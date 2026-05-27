"""
Client Supabase — persistance cloud pour les utilisateurs et notifications.

Si SUPABASE_URL et SUPABASE_KEY sont définis (dans .env ou secrets Streamlit),
auth_manager et notification_manager utilisent Supabase automatiquement.
Sinon, ils tombent en fallback sur les fichiers JSON locaux (comportement inchangé).

Usage :
    from backend.supabase_client import get_supabase
    sb = get_supabase()
    if sb:
        # utiliser Supabase
    else:
        # utiliser le fichier JSON local

SQL à exécuter dans Supabase → SQL Editor avant première utilisation :

    CREATE TABLE IF NOT EXISTS users (
        username    TEXT PRIMARY KEY,
        nom         TEXT NOT NULL,
        role        TEXT NOT NULL,
        salt        TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ref         TEXT NOT NULL,
        categorie   TEXT NOT NULL,
        statut      TEXT NOT NULL,
        acteur      TEXT NOT NULL,
        date        TIMESTAMPTZ NOT NULL,
        message     TEXT NOT NULL,
        roles_destinataires JSONB NOT NULL DEFAULT '[]',
        lue_par     JSONB NOT NULL DEFAULT '[]'
    );

    -- Désactiver RLS (Row Level Security) pour un accès serveur direct
    ALTER TABLE users DISABLE ROW LEVEL SECURITY;
    ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase():
    """
    Retourne un client Supabase si les credentials sont configurés, None sinon.
    Le résultat est mis en cache — l'initialisation ne se fait qu'une seule fois.
    """
    try:
        from backend.config import get_secret
        url = get_secret("SUPABASE_URL", "")
        key = get_secret("SUPABASE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client
        client = create_client(url, key)
        logger.info("Supabase connecté : %s", url)
        return client
    except ImportError:
        logger.warning("Package 'supabase' non installé — fallback JSON local.")
        return None
    except Exception as e:
        logger.warning("Supabase non disponible (%s) — fallback JSON local.", e)
        return None


def supabase_disponible() -> bool:
    """Retourne True si Supabase est configuré et accessible."""
    return get_supabase() is not None
