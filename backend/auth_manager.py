"""
Gestion des utilisateurs, rôles et authentification.

Stockage : config/users.json (auto-créé avec utilisateurs par défaut).
Hachage  : PBKDF2-SHA256 (stdlib uniquement, aucune dépendance externe).
"""

import hashlib
import json
import secrets
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
USERS_FILE = CONFIG_DIR / "users.json"

# ─── Définition des rôles ─────────────────────────────────────────────────────

ROLES = {
    "admin": {
        "label": "Administrateur",
        "gates": ["Vérification BT", "Approbation Qualité", "Validation Direction"],
        "peut_soumettre": True,
        "peut_corrections": True,
        "peut_liberer": True,
    },
    "bt": {
        "label": "Bureau Technique",
        "gates": ["Vérification BT"],
        "peut_soumettre": True,
        "peut_corrections": False,
        "peut_liberer": False,
    },
    "qualite": {
        "label": "Responsable Qualité",
        "gates": ["Approbation Qualité"],
        "peut_soumettre": False,
        "peut_corrections": True,
        "peut_liberer": False,
    },
    "direction": {
        "label": "Direction",
        "gates": ["Validation Direction"],
        "peut_soumettre": False,
        "peut_corrections": False,
        "peut_liberer": True,
    },
    "viewer": {
        "label": "Lecteur",
        "gates": [],
        "peut_soumettre": False,
        "peut_corrections": False,
        "peut_liberer": False,
    },
}

# Comptes créés automatiquement au premier démarrage
_UTILISATEURS_DEFAUT = [
    ("admin",     "Administrateur",    "admin",     "Admin123!"),
    ("bt",        "Bureau Technique",  "bt",        "BT123!"),
    ("qualite",   "Resp. Qualité",     "qualite",   "Qualite123!"),
    ("direction", "Direction",         "direction", "Direction123!"),
]


# ─── Hachage ─────────────────────────────────────────────────────────────────

def _hasher(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()


# ─── Persistence ──────────────────────────────────────────────────────────────

def _charger() -> dict:
    if not USERS_FILE.exists():
        _initialiser_defaut()
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _sauvegarder(data: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _initialiser_defaut() -> None:
    data = {"users": {}}
    for username, nom, role, password in _UTILISATEURS_DEFAUT:
        salt = secrets.token_hex(16)
        data["users"][username] = {
            "nom": nom,
            "role": role,
            "salt": salt,
            "password_hash": _hasher(password, salt),
        }
    _sauvegarder(data)


# ─── API publique ─────────────────────────────────────────────────────────────

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
        {"username": k, "nom": v["nom"], "role": v["role"]}
        for k, v in data["users"].items()
    ]


def creer_utilisateur(username: str, nom: str, role: str, password: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Rôle inconnu : '{role}'. Valeurs acceptées : {list(ROLES)}")
    data = _charger()
    if username in data["users"]:
        raise ValueError(f"L'utilisateur '{username}' existe déjà.")
    salt = secrets.token_hex(16)
    data["users"][username] = {
        "nom": nom,
        "role": role,
        "salt": salt,
        "password_hash": _hasher(password, salt),
    }
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
    del data["users"][username]
    _sauvegarder(data)


# ─── Helpers de droits ────────────────────────────────────────────────────────

def peut_valider_gate(role: str, gate: str) -> bool:
    return gate in ROLES.get(role, {}).get("gates", [])


def peut_soumettre(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_soumettre", False)


def peut_demander_corrections(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_corrections", False)


def peut_liberer(role: str) -> bool:
    return ROLES.get(role, {}).get("peut_liberer", False)
