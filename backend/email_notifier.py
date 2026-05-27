"""
Notifications par email — Qual.IA.

Configuration dans .env (ou Streamlit Secrets) :
  SMTP_HOST      = smtp.gmail.com          (défaut Gmail)
  SMTP_PORT      = 587                     (TLS)
  SMTP_USER      = votre.email@gmail.com
  SMTP_PASSWORD  = xxxx xxxx xxxx xxxx    (mot de passe d'application Gmail)
  EMAIL_FROM     = Qual.IA <votre.email@gmail.com>   (optionnel)
  EMAIL_ADMIN    = destinataire@entreprise.com        (email de secours global)

Avec Gmail : activer l'authentification 2FA puis générer un
"Mot de passe d'application" sur https://myaccount.google.com/apppasswords
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

def _cfg() -> dict:
    return {
        "host":     os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port":     int(os.environ.get("SMTP_PORT", "587")),
        "user":     os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from":     os.environ.get("EMAIL_FROM", ""),
        "admin":    os.environ.get("EMAIL_ADMIN", ""),
    }


def email_configure() -> bool:
    """Retourne True si SMTP_USER et SMTP_PASSWORD sont définis."""
    cfg = _cfg()
    return bool(cfg["user"] and cfg["password"])


def get_emails_par_roles(roles: list[str]) -> list[str]:
    """
    Collecte les adresses email des utilisateurs dont le rôle est dans `roles`.
    Ajoute EMAIL_ADMIN comme destinataire de secours si aucun email trouvé.
    """
    emails = set()

    # Chercher les emails des utilisateurs par rôle
    try:
        from backend.auth_manager import lister_utilisateurs
        for u in lister_utilisateurs():
            if u.get("role") in roles and u.get("email"):
                emails.add(u["email"].strip())
    except Exception:
        pass

    # Fallback : email admin global
    admin_email = os.environ.get("EMAIL_ADMIN", "").strip()
    if admin_email:
        emails.add(admin_email)

    return [e for e in emails if e and "@" in e]


# ── Envoi bas niveau ──────────────────────────────────────────────────────────

def envoyer_email(
    destinataires: list[str],
    sujet: str,
    corps_html: str,
    corps_texte: str = "",
) -> bool:
    """
    Envoie un email HTML à une liste de destinataires via SMTP/TLS.
    Retourne True si l'envoi a réussi, False sinon (sans lever d'exception).
    """
    if not email_configure():
        logger.debug("Email non configuré (SMTP_USER/SMTP_PASSWORD absents) — envoi ignoré.")
        return False

    destinataires = [d.strip() for d in destinataires if d and "@" in d]
    if not destinataires:
        logger.debug("Aucun destinataire valide — envoi ignoré.")
        return False

    cfg = _cfg()
    expediteur = cfg["from"] or cfg["user"]

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sujet
        msg["From"]    = expediteur
        msg["To"]      = ", ".join(destinataires)

        if corps_texte:
            msg.attach(MIMEText(corps_texte, "plain", "utf-8"))
        msg.attach(MIMEText(corps_html, "html", "utf-8"))

        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=12) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(expediteur, destinataires, msg.as_string())

        logger.info("Email envoye a %s — sujet : %s", destinataires, sujet)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP : erreur d'authentification — verifiez SMTP_USER et SMTP_PASSWORD.")
        return False
    except smtplib.SMTPException as e:
        logger.warning("SMTP echec (%s)", e)
        return False
    except Exception as e:
        logger.warning("Envoi email echec (%s)", e)
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


# ── Templates métier ──────────────────────────────────────────────────────────

def notifier_nouveau_dossier(
    reference: str,
    designation: str,
    categorie: str,
    redacteur: str,
    destinataires: list[str],
) -> bool:
    """Email envoyé à l'admin/qualité à la création d'un nouveau dossier."""
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


def notifier_validation_requise(
    reference: str,
    designation: str,
    categorie: str,
    soumis_par: str,
    gate: str,
    role_requis: str,
    destinataires: list[str],
    commentaire: str = "",
) -> bool:
    """Email envoyé aux validateurs quand un dossier passe en_revue."""
    sujet = f"[Qual.IA] Validation requise : {reference} — {gate}"
    role_labels = {
        "bt":        "Bureau Technique",
        "qualite":   "Responsable Qualité",
        "direction": "Direction",
        "admin":     "Administrateur",
    }
    role_label = role_labels.get(role_requis, role_requis.capitalize())
    commentaire_html = (
        f'<p style="font-size:13px;background:#fffbeb;padding:12px 14px;border-radius:6px;'
        f'margin:16px 0 0;border-left:3px solid #f59e0b;">'
        f'<strong>Commentaire :</strong> {commentaire}</p>'
        if commentaire else ""
    )
    corps = f"""
    <p style="font-size:15px;margin:0 0 20px;color:#1e293b;">
      Un dossier qualité est <strong>en attente de votre validation</strong>.
    </p>
    <table style="border-collapse:collapse;width:100%;background:#f8fafc;border-radius:8px;padding:8px;">
      {_row("Référence", f"<strong>{reference}</strong>")}
      {_row("Désignation", designation or "—")}
      {_row("Catégorie", categorie)}
      {_row("Gate à valider", f'<strong style="color:#1d4ed8;">{gate}</strong>')}
      {_row("Rôle requis", role_label)}
      {_row("Soumis par", soumis_par)}
      {_row("Statut", _badge_html("en_revue"))}
    </table>
    {commentaire_html}
    <p style="font-size:13px;color:#64748b;margin:20px 0 0;">
      Connectez-vous à <strong>Qual.IA</strong> pour consulter le dossier et effectuer la validation.
    </p>"""
    html = _html_wrap(f"Validation requise : {reference}", corps, "en_revue")
    texte = (
        f"Validation requise — Qual.IA\n\n"
        f"Reference : {reference}\n"
        f"Gate : {gate}\n"
        f"Soumis par : {soumis_par}\n"
        f"Role requis : {role_label}"
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
    """Email générique pour les autres transitions de workflow (corrections, approuvé, libéré…)."""
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
