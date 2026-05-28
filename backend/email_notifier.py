"""
Notifications par email — Qual.IA.
Utilise l'API Resend (https://resend.com) pour l'envoi transactionnel.

Configuration dans .env (ou Streamlit Secrets) :
  RESEND_API_KEY = re_xxxxxxxxxxxx     (clé API Resend)
  RESEND_FROM    = Qual.IA <notifications@qualia-saas.app>   (optionnel)

Seule notification active : "nouveau dossier créé"
envoyée à tous les utilisateurs ayant un email renseigné avec le rôle admin/qualite.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

def email_configure() -> bool:
    """Retourne True si RESEND_API_KEY est défini."""
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def get_emails_par_roles(roles: list[str]) -> list[str]:
    """
    Collecte les adresses email des utilisateurs dont le rôle est dans `roles`.
    """
    emails = set()
    try:
        from backend.auth_manager import lister_utilisateurs
        for u in lister_utilisateurs():
            if u.get("role") in roles and u.get("email"):
                emails.add(u["email"].strip())
    except Exception:
        pass
    return [e for e in emails if e and "@" in e]


# ── Envoi via Resend ──────────────────────────────────────────────────────────

def envoyer_email(
    destinataires: list[str],
    sujet: str,
    corps_html: str,
    corps_texte: str = "",
) -> bool:
    """
    Envoie un email HTML via l'API Resend.
    Retourne True si l'envoi a réussi, False sinon (sans lever d'exception).
    """
    if not email_configure():
        logger.debug("Resend non configuré (RESEND_API_KEY absent) — envoi ignoré.")
        return False

    destinataires = [d.strip() for d in destinataires if d and "@" in d]
    if not destinataires:
        logger.debug("Aucun destinataire valide — envoi ignoré.")
        return False

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    expediteur = os.environ.get("RESEND_FROM", "Qual.IA <notifications@qualia-saas.app>")

    try:
        import resend
        resend.api_key = api_key

        params = {
            "from": expediteur,
            "to": destinataires,
            "subject": sujet,
            "html": corps_html,
        }
        if corps_texte:
            params["text"] = corps_texte

        resend.Emails.send(params)
        logger.info("Email envoyé via Resend à %s — sujet : %s", destinataires, sujet)
        return True

    except ImportError:
        logger.error("Package 'resend' non installé. Lancez : pip install resend")
        return False
    except Exception as e:
        logger.warning("Resend — envoi échoué (%s)", e)
        return False


# ── Palette & layout HTML ─────────────────────────────────────────────────────

_COULEURS_STATUT = {
    "creation":   ("#7c3aed", "#ede9fe"),
    "en_revue":   ("#1d4ed8", "#dbeafe"),
    "corrections":("#c2410c", "#ffedd5"),
    "approuve":   ("#15803d", "#dcfce7"),
    "libere":     ("#0f766e", "#ccfbf1"),
    "obsolete":   ("#6b7280", "#f3f4f6"),
    "brouillon":  ("#475569", "#f1f5f9"),
}

def _badge_html(statut: str) -> str:
    c_text, c_bg = _COULEURS_STATUT.get(statut, ("#475569", "#f1f5f9"))
    labels = {
        "creation": "NOUVEAU",
        "en_revue": "EN REVUE",
        "corrections": "CORRECTIONS",
        "approuve": "APPROUVE",
        "libere": "LIBERE",
        "obsolete": "OBSOLETE",
        "brouillon": "BROUILLON",
    }
    label = labels.get(statut, statut.upper().replace("_", " "))
    return (
        f'<span style="background:{c_bg};color:{c_text};'
        f'padding:3px 10px;border-radius:4px;font-size:12px;'
        f'font-weight:700;letter-spacing:0.5px;">{label}</span>'
    )

def _row(label: str, valeur: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:7px 14px 7px 0;color:#64748b;font-size:13px;'
        f'font-weight:600;white-space:nowrap;vertical-align:top;">{label}</td>'
        f'<td style="padding:7px 0;color:#1e293b;font-size:13px;">{valeur}</td>'
        f'</tr>'
    )

def _html_wrap(titre: str, corps: str, statut: str = "") -> str:
    c_text, _ = _COULEURS_STATUT.get(statut, ("#1B3A6B", "#f1f5f9"))
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>{titre}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <!-- EN-TÊTE -->
        <tr>
          <td style="background:linear-gradient(135deg,#1B3A6B 0%,#2563eb 100%);padding:22px 32px;">
            <p style="margin:0;color:#bfdbfe;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">QUAL.IA — Gestion Qualité Industrielle</p>
            <p style="margin:6px 0 0;color:#ffffff;font-size:20px;font-weight:700;line-height:1.3;">{titre}</p>
          </td>
        </tr>
        <!-- CORPS -->
        <tr>
          <td style="padding:28px 32px;">
            {corps}
          </td>
        </tr>
        <!-- PIED -->
        <tr>
          <td style="padding:16px 32px 24px;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:11px;color:#94a3b8;">
              Qual.IA — Notification automatique — Envoyé le {now}<br>
              Ne pas répondre à cet email.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Notification : nouveau dossier créé ──────────────────────────────────────

def notifier_nouveau_dossier(
    reference: str,
    designation: str,
    categorie: str,
    redacteur: str,
    destinataires: list[str],
) -> bool:
    """Email envoyé à la création d'un nouveau dossier."""
    sujet = f"[Qual.IA] Nouveau dossier créé : {reference}"
    corps = f"""
    <p style="font-size:15px;margin:0 0 20px;color:#1e293b;">
      Un nouveau dossier qualité vient d'être enregistré dans la base.
    </p>
    <table style="border-collapse:collapse;width:100%;background:#f8fafc;border-radius:8px;padding:8px;">
      {_row("Référence", f"<strong>{reference}</strong>")}
      {_row("Désignation", designation or "—")}
      {_row("Catégorie", categorie)}
      {_row("Rédacteur", redacteur)}
      {_row("Statut", _badge_html("creation"))}
    </table>
    <p style="font-size:13px;color:#64748b;margin:20px 0 0;padding:12px;background:#f8fafc;border-radius:6px;border-left:3px solid #1B3A6B;">
      Ce dossier démarre en <strong>brouillon</strong>. Il sera soumis au workflow de validation par le rédacteur.
    </p>"""
    html = _html_wrap(f"Nouveau dossier : {reference}", corps, "creation")
    texte = (
        f"Nouveau dossier Qual.IA\n\n"
        f"Reference : {reference}\n"
        f"Designation : {designation}\n"
        f"Redacteur : {redacteur}\n"
        f"Categorie : {categorie}\n"
        f"Statut : Brouillon"
    )
    return envoyer_email(destinataires, sujet, html, texte)


def notifier_transition(
    reference: str,
    designation: str,
    categorie: str,
    statut: str,
    acteur: str,
    message: str,
    destinataires: list[str],
) -> bool:
    """Email générique pour les transitions de workflow (corrections, approuvé, libéré…)."""
    statut_labels = {
        "corrections": "Corrections demandées",
        "approuve":    "Approuvé",
        "libere":      "Libéré en production",
        "obsolete":    "Rendu obsolète",
    }
    statut_label = statut_labels.get(statut, statut.replace("_", " ").capitalize())
    sujet = f"[Qual.IA] {statut_label} : {reference}"
    corps = f"""
    <p style="font-size:15px;margin:0 0 20px;color:#1e293b;">{message}</p>
    <table style="border-collapse:collapse;width:100%;background:#f8fafc;border-radius:8px;padding:8px;">
      {_row("Référence", f"<strong>{reference}</strong>")}
      {_row("Désignation", designation or "—")}
      {_row("Catégorie", categorie)}
      {_row("Action par", acteur)}
      {_row("Nouveau statut", _badge_html(statut))}
    </table>"""
    html = _html_wrap(f"{statut_label} : {reference}", corps, statut)
    texte = (
        f"{statut_label} — Qual.IA\n\n"
        f"Reference : {reference}\n"
        f"Action par : {acteur}\n"
        f"{message}"
    )
    return envoyer_email(destinataires, sujet, html, texte)
