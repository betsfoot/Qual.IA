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

# ─── Routing des notifications par événement ─────────────────────────────────
#
# Pour chaque événement, liste des rôles qui reçoivent la notification (in-app + email).
# Modifier ici pour ajouter/retirer des destinataires selon votre organisation.
#
ROLES_PAR_STATUT = {
    # Nouveau dossier créé → toute l'équipe concernée est informée
    "creation":    ["admin", "qualite", "methodes", "bt", "indus", "outillage", "prod"],

    # Dossier soumis en revue → les validateurs de la gate courante
    "en_revue":    ["bt", "methodes", "qualite", "direction", "admin"],

    # Corrections demandées → le rédacteur doit agir
    "corrections": ["redacteur", "admin"],

    # Dossier approuvé (toutes gates) → le rédacteur est informé
    "approuve":    ["redacteur", "qualite", "methodes", "admin"],

    # Dossier libéré en production → production + qualité informées
    "libere":      ["redacteur", "qualite", "methodes", "prod", "indus", "outillage", "admin"],

    # Dossier rendu obsolète → admin uniquement
    "obsolete":    ["admin", "qualite"],
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
    designation: str = "",
    commentaire: str = "",
    gate: str = "",
    role_requis: str = "",
) -> None:
    """
    Ajoute une notification in-app et envoie un email aux utilisateurs concernés.

    Paramètres additionnels pour enrichir les emails :
      designation      : désignation humaine de la référence
      commentaire      : commentaire libre (affiché dans l'email validation)
      gate             : gate à valider (pour statut en_revue)
      role_requis      : rôle requis pour la gate (pour statut en_revue)
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
    except Exception as e:
        logger.warning("Supabase notification échouée (%s), fallback JSON.", e)
        notifs = _lire_fichier()
        notifs.append(notif)
        _ecrire_fichier(notifs)
        logger.info("Notification JSON ajoutée pour %s — statut %s", ref, statut)
        return

    # ── Envoi email ────────────────────────────────────────────────────────────
    try:
        _envoyer_email_notification(
            notif,
            designation=designation,
            commentaire=commentaire,
            gate=gate,
            role_requis=role_requis,
        )
    except Exception as e:
        logger.warning("Envoi email notification echoue (%s)", e)


def _envoyer_email_notification(
    notif: dict,
    designation: str = "",
    commentaire: str = "",
    gate: str = "",
    role_requis: str = "",
) -> None:
    """Sélectionne le bon template email et envoie aux destinataires concernés."""
    from backend.email_notifier import (
        email_configure, get_emails_par_roles,
        notifier_nouveau_dossier, notifier_validation_requise, notifier_transition,
    )

    if not email_configure():
        return

    ref       = notif["ref"]
    categorie = notif["categorie"]
    statut    = notif["statut"]
    acteur    = notif["acteur"]
    message   = notif["message"]
    roles     = notif.get("roles_destinataires", ["admin"])

    destinataires = get_emails_par_roles(roles)
    if not destinataires:
        return

    if statut == "creation":
        notifier_nouveau_dossier(ref, designation, categorie, acteur, destinataires)

    elif statut == "en_revue":
        notifier_validation_requise(
            reference=ref,
            designation=designation,
            categorie=categorie,
            soumis_par=acteur,
            gate=gate or "Vérification BT",
            role_requis=role_requis or "bt",
            destinataires=destinataires,
            commentaire=commentaire,
        )

    else:
        notifier_transition(ref, designation, categorie, statut, acteur, message, destinataires)


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
