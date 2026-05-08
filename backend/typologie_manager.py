"""
Gestion des typologies de traitements.

Une **typologie** est une variante nommée d'un traitement (ex: "BBAR-5L" pour
un AR double face avec un stack SiO2/TiO2/SiO2/TiO2/SiO2). Chaque typologie a
son propre outillage, sa méthodologie de production, et son stack de couches.

Stockage : `categories/{cat}/typologies.json`
Format :
{
  "antireflet_double_face": {
    "BBAR-5L": {
      "nom": "BBAR Standard 5 couches",
      "stack": ["SiO2", "TiO2", "SiO2", "TiO2", "SiO2"],
      "outillage": "OUT-AR-BBAR-5L",
      "methodologie": "PVD basse température, manipulation gants nitrile",
      "gamme_application": "VIS 400-700nm",
      "notes": ""
    },
    ...
  },
  ...
}
"""

import json
from pathlib import Path

from backend.category_manager import Categorie, charger_categorie


def _resoudre_categorie(categorie) -> Categorie:
    if isinstance(categorie, str):
        cat = charger_categorie(categorie)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {categorie}")
        return cat
    return categorie


def _typologies_path(categorie) -> Path:
    cat = _resoudre_categorie(categorie)
    return cat.chemin / "typologies.json"


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def charger_typologies(categorie) -> dict:
    """Charge le catalogue de typologies de la catégorie. Retourne {} si absent."""
    p = _typologies_path(categorie)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sauvegarder_typologies(categorie, typologies: dict) -> None:
    p = _typologies_path(categorie)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(typologies, ensure_ascii=False, indent=2), encoding="utf-8")


def lister_typologies(categorie, code_traitement: str) -> list[dict]:
    """Liste des typologies disponibles pour un traitement donné."""
    catalog = charger_typologies(categorie)
    typo_dict = catalog.get(code_traitement, {})
    return [
        {"code": code, **details}
        for code, details in typo_dict.items()
    ]


def get_typologie(categorie, code_traitement: str, code_typologie: str) -> dict | None:
    catalog = charger_typologies(categorie)
    return catalog.get(code_traitement, {}).get(code_typologie)


def creer_ou_maj_typologie(
    categorie,
    code_traitement: str,
    code_typologie: str,
    nom: str,
    stack: list[str] | None = None,
    outillage: str = "",
    methodologie: str = "",
    gamme_application: str = "",
    notes: str = "",
) -> None:
    """Crée ou met à jour une typologie pour un traitement."""
    if not code_traitement or not code_typologie:
        raise ValueError("code_traitement et code_typologie sont obligatoires.")
    catalog = charger_typologies(categorie)
    catalog.setdefault(code_traitement, {})
    catalog[code_traitement][code_typologie] = {
        "nom": nom,
        "stack": stack or [],
        "outillage": outillage,
        "methodologie": methodologie,
        "gamme_application": gamme_application,
        "notes": notes,
    }
    sauvegarder_typologies(categorie, catalog)


def supprimer_typologie(categorie, code_traitement: str, code_typologie: str) -> None:
    catalog = charger_typologies(categorie)
    if code_traitement in catalog and code_typologie in catalog[code_traitement]:
        del catalog[code_traitement][code_typologie]
        if not catalog[code_traitement]:
            del catalog[code_traitement]
        sauvegarder_typologies(categorie, catalog)


# ─── Helpers pour la similarité et l'affichage ────────────────────────────────

def traitement_a_typologies(categorie, code_traitement: str) -> bool:
    """True si le traitement a au moins une typologie définie dans la catégorie."""
    return bool(charger_typologies(categorie).get(code_traitement))


def normaliser_traitement(traitement) -> tuple[str, str | None]:
    """
    Accepte un traitement sous forme `str` (ancien format) OU `dict` (nouveau format).
    Retourne (code_traitement, code_typologie_ou_None).
    """
    if isinstance(traitement, dict):
        return traitement.get("code", ""), traitement.get("typologie") or None
    return str(traitement), None


def codes_traitements(traitements: list) -> list[str]:
    """Extrait uniquement les codes des traitements (sans les typologies)."""
    return [normaliser_traitement(t)[0] for t in traitements]


def format_traitements_str(traitements: list, separateur: str = ", ") -> str:
    """Formatte une liste de traitements (mix str/dict) en chaîne lisible."""
    parts = []
    for t in traitements:
        code, typo = normaliser_traitement(t)
        parts.append(f"{code} [{typo}]" if typo else code)
    return separateur.join(parts)
