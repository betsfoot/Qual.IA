"""
Gestion des utilisateurs, rôles et authentification.

Stockage prioritaire : Supabase (table `users`) si SUPABASE_URL + SUPABASE_KEY sont définis.
Fallback                : config/users.json (comportement original, aucun changement).

Le basculement est automatique — aucune intervention nécessaire.
Hachage : PBKDF2-SHA256 (stdlib uniquement, aucune dépendance externe).
"""

import hashlib
import json
import secrets
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
USERS_FILE = CONFIG_DIR / "users.json"

# ─── Définition des rôles ─────────────────────────────────────────────────────
#
# Chaque rôle déclare :
#   label            : nom affiché dans l'interface
#   description      : courte description métier
#   groupe           : famille (validation / metier / admin)
#   gates            : gates de workflow que ce rôle peut valider
#   peut_soumettre   : peut soumettre un dossier en revue
#   peut_corrections : peut demander des corrections
#   peut_liberer     : peut libérer un dossier en production
#
ROLES = {
    # ── Administration ──────────────────────────────────────────────────────
    "admin": {
        "label":          "Administrateur",
        "description":    "Accès complet — gère les utilisateurs et tous les workflows",
        "groupe":         "admin",
        "gates":          ["Vérification BT", "Approbation Qualité", "Validation Direction", "Validation Méthodes"],
        "peut_soumettre":  True,
        "peut_corrections":True,
        "peut_liberer":    True,
    },
    "direction": {
        "label":          "Direction",
        "description":    "Valide les dossiers à fort enjeu (IPR > 100)",
        "groupe":         "validation",
        "gates":          ["Validation Direction"],
        "peut_soumettre":  False,
        "peut_corrections":False,
        "peut_liberer":    True,
    },

    # ── Validation technique ────────────────────────────────────────────────
    "bt": {
        "label":          "Bureau Technique",
        "description":    "Vérifie la cohérence technique AMDEC / Gamme",
        "groupe":         "validation",
        "gates":          ["Vérification BT"],
        "peut_soumettre":  True,
        "peut_corrections":False,
        "peut_liberer":    False,
    },
    "qualite": {
        "label":          "Responsable Qualité",
        "description":    "Approuve les dossiers qualité et peut demander des corrections",
        "groupe":         "validation",
        "gates":          ["Approbation Qualité"],
        "peut_soumettre":  False,
        "peut_corrections":True,
        "peut_liberer":    False,
    },
    "methodes": {
        "label":          "Responsable Méthodes",
        "description":    "Valide les procédés et gammes de fabrication",
        "groupe":         "validation",
        "gates":          ["Validation Méthodes"],
        "peut_soumettre":  True,
        "peut_corrections":True,
        "peut_liberer":    False,
    },

    # ── Métiers notifiés (pas de gate, informés en lecture) ─────────────────
    "indus": {
        "label":          "Responsable Industrialisation",
        "description":    "Reçoit les notifications — suit la mise en production",
        "groupe":         "metier",
        "gates":          [],
        "peut_soumettre":  False,
        "peut_corrections":False,
        "peut_liberer":    False,
    },
    "outillage": {
        "label":          "Responsable Outillage",
        "description":    "Reçoit les notifications — gère les outillages et fixtures",
        "groupe":         "metier",
        "gates":          [],
        "peut_soumettre":  False,
        "peut_corrections":False,
        "peut_liberer":    False,
    },
    "prod": {
        "label":          "Responsable Production",
        "description":    "Reçoit les notifications — responsable de la ligne de production",
        "groupe":         "metier",
        "gates":          [],
        "peut_soumettre":  False,
        "peut_corrections":False,
        "peut_liberer":    False,
    },

    # ── Rédaction ───────────────────────────────────────────────────────────
    "redacteur": {
        "label":          "Chef de Projet / Rédacteur",
        "description":    "Crée et soumet les dossiers qualité",
        "groupe":         "redaction",
        "gates":          [],
        "peut_soumettre":  True,
        "peut_corrections":False,
        "peut_liberer":    False,
    },
    "viewer": {
        "label":          "Lecteur",
        "description":    "Consultation uniquement — aucune action possible",
        "groupe":         "autre",
        "gates":          [],
        "peut_soumettre":  False,
        "peut_corrections":False,
        "peut_liberer":    False,
    },
}

# Groupes de rôles pour l'affichage dans l'admin
GROUPES_ROLES = {
    "validation": "🔐 Validation workflow",
    "metier":     "📣 Métiers notifiés",
    "redaction":  "✏️ Rédaction",
    "admin":      "⚙️ Administration",
    "autre":      "👁️ Lecture seule",
}

# Comptes créés automatiquement au premier démarrage
_UTILISATEURS_DEFAUT = [
    ("admin",     "Administrateur",    "admin",     "Admin123!"),
    ("bt",        "Bureau Technique",  "bt",        "BT123!"),
    ("qualite",   "Resp. Qualité",     "qualite",   "Qualite123!"),
    ("methodes",  "Resp. Méthodes",    "methodes",  "Methodes123!"),
    ("direction", "Direction",         "direction", "Direction123!"),
    ("redacteur", "Chef de Projet",    "redacteur", "ChefProjet123!"),
]


# ─── Hachage ─────────────────────────────────────────────────────────────────

def _hasher(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()


# ─── Persistence locale (fallback JSON) ──────────────────────────────────────

def _charger_local() -> dict:
    if not USERS_FILE.exists():
        _initialiser_defaut_local()
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _sauvegarder_local(data: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _initialiser_defaut_local() -> None:
    data = {"users": {}}
    for username, nom, role, password in _UTILISATEURS_DEFAUT:
        salt = secrets.token_hex(16)
        data["users"][username] = {
            "nom": nom,
            "role": role,
            "salt": salt,
            "password_hash": _hasher(password, salt),
        }
    _sauvegarder_local(data)


# ─── Persistence Supabase ─────────────────────────────────────────────────────

def _sb_initialiser_defaut(sb) -> None:
    """Insère les comptes par défaut dans Supabase s'ils n'existent pas."""
    for username, nom, role, password in _UTILISATEURS_DEFAUT:
        existing = sb.table("users").select("username").eq("username", username).execute()
        if not existing.data:
            salt = secrets.token_hex(16)
            sb.table("users").insert({
                "username": username,
                "nom": nom,
                "role": role,
                "salt": salt,
                "password_hash": _hasher(password, salt),
            }).execute()


def _sb_charger_tous(sb) -> dict:
    """Charge tous les utilisateurs depuis Supabase."""
    res = sb.table("users").select("*").execute()
    users = {}
    for row in (res.data or []):
        users[row["username"]] = {
            "nom":           row["nom"],
            "role":          row["role"],
            "salt":          row["salt"],
            "password_hash": row["password_hash"],
            "email":         row.get("email", ""),
        }
    # Initialisation au premier démarrage si vide
    if not users:
        _sb_initialiser_defaut(sb)
        res = sb.table("users").select("*").execute()
        for row in (res.data or []):
            users[row["username"]] = {
                "nom": row["nom"],
                "role": row["role"],
                "salt": row["salt"],
                "password_hash": row["password_hash"],
            }
    return {"users": users}


# ─── Routage automatique (Supabase si dispo, JSON sinon) ─────────────────────

def _charger() -> dict:
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            return _sb_charger_tous(sb)
    except Exception:
        pass
    return _charger_local()


def _sauvegarder(data: dict) -> None:
    """Persiste dans Supabase OU dans le JSON local selon la config."""
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            # Supabase : upsert de chaque utilisateur (insert ou update)
            for username, info in data.get("users", {}).items():
                sb.table("users").upsert({
                    "username":     username,
                    "nom":          info["nom"],
                    "role":         info["role"],
                    "salt":         info["salt"],
                    "password_hash":info["password_hash"],
                    "email":        info.get("email", ""),
                }).execute()
            return
    except Exception:
        pass
    _sauvegarder_local(data)


def _supprimer_supabase(username: str) -> bool:
    """Supprime un utilisateur dans Supabase. Retourne True si réussi."""
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            sb.table("users").delete().eq("username", username).execute()
            return True
    except Exception:
        pass
    return False


# ─── API publique (inchangée) ─────────────────────────────────────────────────

def verifier_credentials(username: str, password: str) -> dict | None:
    """Retourne le profil utilisateur si les credentials sont valides, None sinon."""
    data = _charger()
    user = data["users"].get(username)
    if not user:
        return None
    if _hasher(password, user["salt"]) == user["password_hash"]:
        return {"username": username, "nom": user["nom"], "role": user["role"]}
    return None


def lister_utilisateurs() -> list[dict]:
    data = _charger()
    return [
        {"username": k, "nom": v["nom"], "role": v["role"], "email": v.get("email", "")}
        for k, v in data["users"].items()
    ]


def creer_utilisateur(username: str, nom: str, role: str, password: str, email: str = "") -> None:
    if role not in ROLES:
        raise ValueError(f"Rôle inconnu : '{role}'. Valeurs acceptées : {list(ROLES)}")
    data = _charger()
    if username in data["users"]:
        raise ValueError(f"L'utilisateur '{username}' existe déjà.")
    salt = secrets.token_hex(16)
    data["users"][username] = {
        "nom":           nom,
        "role":          role,
        "salt":          salt,
        "password_hash": _hasher(password, salt),
        "email":         email.strip().lower() if email else "",
    }
    _sauvegarder(data)


def mettre_a_jour_email(username: str, email: str) -> None:
    """Met à jour l'adresse email d'un utilisateur."""
    data = _charger()
    if username not in data["users"]:
        raise ValueError(f"Utilisateur introuvable : '{username}'")
    data["users"][username]["email"] = email.strip().lower() if email else ""
    _sauvegarder(data)


def changer_mot_de_passe(username: str, nouveau_mdp: str) -> None:
    data = _charger()
    if username not in data["users"]:
        raise ValueError(f"Utilisateur introuvable : '{username}'")
    salt = secrets.token_hex(16)
    data["users"][username]["salt"] = salt
    data["users"][username]["password_hash"] = _hasher(nouveau_mdp, salt)
    _sauvegarder(data)


def supprimer_utilisateur(username: str) -> None:
    data = _charger()
    if username not in data["users"]:
        raise ValueError(f"Utilisateur introuvable : '{username}'")
    # Supabase : suppression directe
    if not _supprimer_supabase(username):
        # Fallback JSON
        del data["users"][username]
        _sauvegarder_local(data)


# ─── Helpers de droits ────────────────────────────────────────────────────────

def peut_valider_gate(role: str, gate: str) -> bool:
    return gate in ROLES.get(role, {}).get("gates", [])


def peut_soumettre(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_soumettre", False)


def peut_demander_corrections(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_corrections", False)


def peut_liberer(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_liberer", False)
