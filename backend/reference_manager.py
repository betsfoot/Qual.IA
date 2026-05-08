"""
Gestion CRUD de la base de références — multi-catégories.

Toutes les fonctions prennent un objet Categorie (ou son code).
"""

import json
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

from backend.category_manager import Categorie, charger_categorie

BASE_DIR = Path(__file__).parent.parent
BACKUPS_DIR = BASE_DIR / "backups"

_CODE_RE = re.compile(r'^[A-Za-z0-9_\-\.]+$')


def _valider_code(code: str, nom: str = "code") -> None:
    if not code or not _CODE_RE.match(code):
        raise ValueError(
            f"{nom} invalide : '{code}'. "
            "Seuls les caractères alphanumériques, tirets, underscores et points sont autorisés."
        )


def _resoudre_categorie(categorie) -> Categorie:
    if isinstance(categorie, str):
        cat = charger_categorie(categorie)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {categorie}")
        return cat
    return categorie


def lister_references(categorie) -> list[dict]:
    """Retourne la liste de toutes les références de la catégorie avec compteurs."""
    cat = _resoudre_categorie(categorie)
    references = []

    for ref_path in sorted(cat.references_dir.glob("*/metadata.json")):
        try:
            with open(ref_path, encoding="utf-8") as f:
                meta = json.load(f)

            ref_dir = ref_path.parent
            nb_modes_p = nb_modes_pr = nb_ops = 0
            try:
                p = ref_dir / "data" / "amdec_produit.json"
                if p.exists():
                    nb_modes_p = len(json.loads(p.read_text(encoding="utf-8")).get("modes_defaillance", []))
            except Exception:
                pass
            try:
                p = ref_dir / "data" / "amdec_process.json"
                if p.exists():
                    nb_modes_pr = len(json.loads(p.read_text(encoding="utf-8")).get("modes_defaillance", []))
            except Exception:
                pass
            try:
                p = ref_dir / "data" / "gamme.json"
                if p.exists():
                    nb_ops = len(json.loads(p.read_text(encoding="utf-8")).get("operations", []))
            except Exception:
                pass

            meta["_chemin"] = str(ref_dir)
            meta["_categorie"] = cat.code
            meta["_nb_modes_produit"] = nb_modes_p
            meta["_nb_modes_process"] = nb_modes_pr
            meta["_nb_operations"] = nb_ops
            references.append(meta)
        except Exception as e:
            references.append({
                "reference": ref_path.parent.name,
                "designation": f"⚠️ Métadonnées illisibles ({e})",
                "_chemin": str(ref_path.parent),
                "_categorie": cat.code,
                "statut": "erreur",
            })
    return references


def charger_reference_complete(categorie, code: str) -> dict:
    _valider_code(code, "code référence")
    cat = _resoudre_categorie(categorie)
    ref_dir = cat.references_dir / code
    if not ref_dir.exists():
        raise FileNotFoundError(f"Référence introuvable : {code} dans {cat.code}")

    metadata = json.loads((ref_dir / "metadata.json").read_text(encoding="utf-8"))
    data = {}
    for nom, fichier in [
        ("amdec_produit", "data/amdec_produit.json"),
        ("amdec_process", "data/amdec_process.json"),
        ("gamme", "data/gamme.json"),
    ]:
        chemin = ref_dir / fichier
        if chemin.exists():
            data[nom] = json.loads(chemin.read_text(encoding="utf-8"))

    return {"metadata": metadata, "data": data}


def supprimer_reference(categorie, code: str, sauvegarde: bool = True) -> Path | None:
    _valider_code(code, "code référence")
    cat = _resoudre_categorie(categorie)
    ref_dir = cat.references_dir / code
    if not ref_dir.exists():
        raise FileNotFoundError(f"Référence introuvable : {code}")

    backup_path = None
    if sauvegarde:
        BACKUPS_DIR.mkdir(exist_ok=True)
        date_str = date.today().isoformat()
        backup_dir = BACKUPS_DIR / date_str / cat.code
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / code
        if backup_path.exists():
            from datetime import datetime
            ts = datetime.now().strftime("%H%M%S")
            backup_path = backup_dir / f"{code}_{ts}"
        shutil.copytree(ref_dir, backup_path)

    shutil.rmtree(ref_dir)
    return backup_path


def sauvegarder_modifications(categorie, code: str, metadata: dict, data: dict | None = None) -> None:
    _valider_code(code, "code référence")
    cat = _resoudre_categorie(categorie)
    ref_dir = cat.references_dir / code
    if not ref_dir.exists():
        raise FileNotFoundError(f"Référence introuvable : {code}")

    (ref_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if data:
        data_dir = ref_dir / "data"
        data_dir.mkdir(exist_ok=True)
        for nom, fichier in [
            ("amdec_produit", "amdec_produit.json"),
            ("amdec_process", "amdec_process.json"),
            ("gamme", "gamme.json"),
        ]:
            if nom in data:
                (data_dir / fichier).write_text(
                    json.dumps(data[nom], ensure_ascii=False, indent=2), encoding="utf-8"
                )


def calculer_stats(references: list[dict], dim_key: str = "diametre_mm") -> dict:
    total = len(references)
    if total == 0:
        return {"total": 0}

    types = Counter(r.get("type_produit", "inconnu") for r in references)
    matieres = Counter(r.get("matiere", "inconnu") for r in references)
    statuts = Counter(r.get("statut", "inconnu") for r in references)
    traitements = Counter()
    for r in references:
        for t in r.get("traitements", []):
            cle = t.get("code", "") if isinstance(t, dict) else str(t)
            if cle:
                traitements[cle] += 1
    dims_prim = [
        r.get("dimensions", {}).get(dim_key)
        for r in references
        if r.get("dimensions", {}).get(dim_key) is not None
    ]
    return {
        "total": total,
        "types": dict(types),
        "matieres": dict(matieres),
        "statuts": dict(statuts),
        "traitements": dict(traitements),
        "dim_prim_min": min(dims_prim) if dims_prim else None,
        "dim_prim_max": max(dims_prim) if dims_prim else None,
        "dim_prim_moy": sum(dims_prim) / len(dims_prim) if dims_prim else None,
        "nb_modes_produit_total": sum(r.get("_nb_modes_produit", 0) for r in references),
        "nb_modes_process_total": sum(r.get("_nb_modes_process", 0) for r in references),
        "nb_operations_total": sum(r.get("_nb_operations", 0) for r in references),
    }
