"""
Gestionnaire de catégories métier.

Une catégorie = un secteur d'activité avec ses propres :
  - références (base de données isolée)
  - critères de similarité + poids
  - vocabulaire (types, matières, traitements)
  - prompts spécialisés Claude

Chaque catégorie vit dans categories/<code>/ avec un config.json à la racine.
"""

import json
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CATEGORIES_DIR = BASE_DIR / "categories"


@dataclass
class Categorie:
    code: str
    nom: str
    icone: str
    description: str
    config: dict
    chemin: Path

    @property
    def references_dir(self) -> Path:
        return self.chemin / "references"

    @property
    def prompts_dir(self) -> Path:
        return self.chemin / "prompts"

    def label_complet(self) -> str:
        return f"{self.icone} {self.nom}"

    def criteres_similarite(self) -> dict:
        return self.config.get("criteres_similarite", {})

    def vocabulaire(self) -> dict:
        return self.config.get("vocabulaire", {})

    def expert_prompt(self) -> str:
        return self.config.get("expert_prompt", "")

    def champs_brief(self) -> dict:
        return self.config.get("champs_brief", {})

    def parametres_numeriques(self) -> list[dict]:
        """Retourne la liste des paramètres numériques du brief.

        Nouveau format : "parametres_numeriques" dans config.json.
        Fallback : génère depuis l'ancien "champs_brief" pour la rétrocompatibilité.
        """
        if "parametres_numeriques" in self.config:
            return self.config["parametres_numeriques"]
        champs = self.config.get("champs_brief", {})
        params = []
        if "diametre_min" in champs or "diametre_obligatoire" in champs:
            params.append({
                "cle": "diametre_mm",
                "label": champs.get("diametre_label", "Diamètre (mm)"),
                "obligatoire": champs.get("diametre_obligatoire", True),
                "min": float(champs.get("diametre_min", 1.0)),
                "max": float(champs.get("diametre_max", 200.0)),
                "tolerance_default": float(champs.get("tolerance_diametre_default", 0.05)),
                "step": 0.1,
                "format": "%.2f",
            })
        if "epaisseur_min" in champs or "epaisseur_obligatoire" in champs:
            params.append({
                "cle": "epaisseur_mm",
                "label": champs.get("epaisseur_label", "Épaisseur (mm)"),
                "obligatoire": champs.get("epaisseur_obligatoire", False),
                "min": float(champs.get("epaisseur_min", 0.0)),
                "max": float(champs.get("epaisseur_max", 50.0)),
                "tolerance_default": float(champs.get("tolerance_epaisseur_default", 0.03)),
                "step": 0.1,
                "format": "%.2f",
            })
        return params


def lister_categories() -> list[Categorie]:
    """Retourne toutes les catégories disponibles, triées par nom."""
    categories = []
    if not CATEGORIES_DIR.exists():
        return categories

    for cat_dir in sorted(CATEGORIES_DIR.iterdir()):
        config_path = cat_dir / "config.json"
        if not (cat_dir.is_dir() and config_path.exists()):
            continue
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # Ignorer les catégories explicitement désactivées
            if config.get("disabled", False):
                continue
            categories.append(Categorie(
                code=config.get("code", cat_dir.name),
                nom=config.get("nom", cat_dir.name),
                icone=config.get("icone", "📁"),
                description=config.get("description", ""),
                config=config,
                chemin=cat_dir,
            ))
        except Exception:
            continue
    return categories


def charger_categorie(code: str) -> Categorie | None:
    """Charge une catégorie par son code."""
    for cat in lister_categories():
        if cat.code == code:
            return cat
    return None


def categorie_par_defaut() -> Categorie | None:
    """Retourne la première catégorie disponible (par défaut au démarrage)."""
    cats = lister_categories()
    return cats[0] if cats else None


def creer_categorie(code: str, nom: str, icone: str = "📁", description: str = "") -> Categorie:
    """
    Crée une nouvelle catégorie vide avec un config minimal.
    À compléter ensuite manuellement ou via l'UI.
    """
    cat_dir = CATEGORIES_DIR / code
    if cat_dir.exists():
        raise FileExistsError(f"La catégorie '{code}' existe déjà.")

    cat_dir.mkdir(parents=True)
    (cat_dir / "references").mkdir()
    (cat_dir / "prompts").mkdir()

    config = {
        "code": code,
        "nom": nom,
        "icone": icone,
        "description": description,
        "expert_prompt": f"Tu es un expert qualité industrielle pour le métier : {nom}.",
        "criteres_similarite": {
            "type_produit": {
                "poids": 0.30,
                "type_comparaison": "exact_match",
                "description": "Type de produit",
            },
            "matiere": {
                "poids": 0.30,
                "type_comparaison": "exact_match",
                "description": "Matière",
            },
            "gamme_dimension": {
                "poids": 0.25,
                "type_comparaison": "diameter_range",
                "cle_dimension": "dim1",
                "description": "Gamme dimensionnelle principale",
            },
            "dim2": {
                "poids": 0.15,
                "type_comparaison": "numeric_proximity",
                "cle_dimension": "dim2",
                "description": "Dimension secondaire",
            },
        },
        "vocabulaire": {
            "types_produit": {},
            "matieres": {},
            "traitements": {},
            "familles_defaillance": ["geometrique", "structurel", "tracabilite"],
        },
        "parametres_numeriques": [
            {
                "cle": "dim1",
                "label": "Dimension principale (mm)",
                "obligatoire": True,
                "min": 1.0,
                "max": 500.0,
                "tolerance_default": 0.05,
                "step": 0.1,
                "format": "%.2f",
            },
            {
                "cle": "dim2",
                "label": "Dimension secondaire (mm)",
                "obligatoire": False,
                "min": 0.0,
                "max": 100.0,
                "tolerance_default": 0.03,
                "step": 0.1,
                "format": "%.2f",
            },
        ],
    }
    (cat_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return charger_categorie(code)
