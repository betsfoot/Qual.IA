"""
Gestion des notifications in-app pour les transitions de workflow.

Le fichier config/notifications.json stocke une liste de notifications :
  {ref, categorie, statut, acteur, date, message, roles_destinataires, lue_par}

Fonctions publiques :
  ajouter_notification(ref, categorie, statut, acteur, message, roles_destinataires)
  lire_notifications(role) → liste des notifications non lues pour ce rôle
  marquer_lues(role)       → vide les notifications du rôle
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

    notifs = _lire_fichier()
    notifs.append({
        "ref": ref,
        "categorie": categorie,
        "statut": statut,
        "acteur": acteur,
        "date": datetime.now().isoformat(timespec="seconds"),
        "message": message,
        "roles_destinataires": roles_destinataires,
        "lue_par": [],
    })
    _ecrire_fichier(notifs)
    logger.info("Notification ajoutée pour %s — statut %s", ref, statut)


def lire_notifications(role: str) -> list[dict]:
    """
    Retourne les notifications non lues pour un rôle donné,
    de la plus récente à la plus ancienne.
    """
    notifs = _lire_fichier()
    non_lues = [
        n for n in notifs
        if role in n.get("roles_destinataires", [])
        and role not in n.get("lue_par", [])
    ]
    return list(reversed(non_lues))


def marquer_lues(role: str) -> None:
    """Marque toutes les notifications destinées à ce rôle comme lues."""
    notifs = _lire_fichier()
    modifie = False
    for n in notifs:
        if role in n.get("roles_destinataires", []) and role not in n.get("lue_par", []):
            n["lue_par"].append(role)
            modifie = True
    if modifie:
        _ecrire_fichier(notifs)
