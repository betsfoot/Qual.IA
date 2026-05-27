"""
Gestion des notifications in-app pour les transitions de workflow.

Stockage prioritaire : Supabase (table `notifications`) si configuré.
Fallback                : config/notifications.json (comportement original).

Structure d'une notification :
  {ref, categorie, statut, acteur, date, message, roles_destinataires, lue_par}
"""

import json
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTIF_FILE = ROOT / "config" / "notifications.json"

logger = logging.getLogger(__name__)

# Rôles notifiés pour chaque statut de transition
ROLES_PAR_STATUT = {
    "en_revue":    ["bt", "qualite", "direction", "admin"],
    "corrections": ["redacteur", "admin"],
    "approuve":    ["redacteur", "admin"],
    "libere":      ["redacteur", "qualite", "admin"],
    "obsolete":    ["admin"],
}


# ─── Persistence locale (fallback JSON) ──────────────────────────────────────

def _lire_fichier() -> list[dict]:
    if not NOTIF_FILE.exists():
        return []
    try:
        with open(NOTIF_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _ecrire_fichier(notifs: list[dict]) -> None:
    NOTIF_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(notifs, f, ensure_ascii=False, indent=2)


# ─── Persistence Supabase ─────────────────────────────────────────────────────

def _sb_ajouter(sb, notif: dict) -> None:
    sb.table("notifications").insert({
        "ref":                  notif["ref"],
        "categorie":            notif["categorie"],
        "statut":               notif["statut"],
        "acteur":               notif["acteur"],
        "date":                 notif["date"],
        "message":              notif["message"],
        "roles_destinataires":  notif["roles_destinataires"],
        "lue_par":              notif["lue_par"],
    }).execute()


def _sb_lire_non_lues(sb, role: str) -> list[dict]:
    """Retourne les notifications non lues pour un rôle, de la plus récente à la plus ancienne."""
    res = sb.table("notifications").select("*").order("date", desc=True).execute()
    return [
        n for n in (res.data or [])
        if role in (n.get("roles_destinataires") or [])
        and role not in (n.get("lue_par") or [])
    ]


def _sb_marquer_lues(sb, role: str) -> None:
    """Marque toutes les notifications non lues du rôle comme lues."""
    res = sb.table("notifications").select("id, lue_par").execute()
    for row in (res.data or []):
        lue_par = row.get("lue_par") or []
        if role not in lue_par:
            lue_par.append(role)
            sb.table("notifications").update({"lue_par": lue_par}).eq("id", row["id"]).execute()


# ─── API publique ─────────────────────────────────────────────────────────────

def ajouter_notification(
    ref: str,
    categorie: str,
    statut: str,
    acteur: str,
    message: str,
    roles_destinataires: list[str] | None = None,
) -> None:
    """
    Ajoute une notification pour les rôles concernés par la transition de statut.
    Si roles_destinataires n'est pas fourni, les rôles par défaut du statut sont utilisés.
    """
    if roles_destinataires is None:
        roles_destinataires = ROLES_PAR_STATUT.get(statut, ["admin"])

    notif = {
        "ref":                 ref,
        "categorie":           categorie,
        "statut":              statut,
        "acteur":              acteur,
        "date":                datetime.now().isoformat(timespec="seconds"),
        "message":             message,
        "roles_destinataires": roles_destinataires,
        "lue_par":             [],
    }

    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            _sb_ajouter(sb, notif)
            logger.info("Notification Supabase ajoutée pour %s — statut %s", ref, statut)
            return
    except Exception as e:
        logger.warning("Supabase notification échouée (%s), fallback JSON.", e)

    notifs = _lire_fichier()
    notifs.append(notif)
    _ecrire_fichier(notifs)
    logger.info("Notification JSON ajoutée pour %s — statut %s", ref, statut)


def lire_notifications(role: str) -> list[dict]:
    """
    Retourne les notifications non lues pour un rôle donné,
    de la plus récente à la plus ancienne.
    """
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            return _sb_lire_non_lues(sb, role)
    except Exception:
        pass

    notifs = _lire_fichier()
    non_lues = [
        n for n in notifs
        if role in n.get("roles_destinataires", [])
        and role not in n.get("lue_par", [])
    ]
    return list(reversed(non_lues))


def marquer_lues(role: str) -> None:
    """Marque toutes les notifications destinées à ce rôle comme lues."""
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            _sb_marquer_lues(sb, role)
            return
    except Exception:
        pass

    notifs = _lire_fichier()
    modifie = False
    for n in notifs:
        if role in n.get("roles_destinataires", []) and role not in n.get("lue_par", []):
            n["lue_par"].append(role)
            modifie = True
    if modifie:
        _ecrire_fichier(notifs)
