"""
Sauvegarde d'un dossier validé comme nouvelle référence — multi-catégories.

Toute sauvegarde initialise automatiquement le workflow en `brouillon`.
Une référence n'est utilisable comme source de similarité qu'après validation
complète du workflow (statut `libere` ou `approuve`).
"""

import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from backend.category_manager import Categorie, charger_categorie
from backend.workflow_manager import initialiser_workflow


def _resoudre_categorie(categorie) -> Categorie:
    if isinstance(categorie, str):
        cat = charger_categorie(categorie)
        if cat is None:
            raise ValueError(f"Catégorie inconnue : {categorie}")
        return cat
    return categorie


def _slug_reference(code: str) -> str:
    code = code.strip().upper().replace(" ", "-")
    return re.sub(r"[^A-Z0-9-]", "", code)


# ─── Versioning ───────────────────────────────────────────────────────────────

def archiver_version(ref_dir: Path) -> Path | None:
    """
    Archive la version actuelle d'une référence avant écrasement.

    Copie metadata.json et data/ dans un sous-dossier :
      historique/{YYYY-MM-DDTHH-MM-SS}/

    Retourne le chemin de l'archive créée, ou None si rien à archiver.
    """
    metadata_path = ref_dir / "metadata.json"
    data_dir = ref_dir / "data"
    if not metadata_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    archive_dir = ref_dir / "historique" / timestamp
    archive_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(metadata_path, archive_dir / "metadata.json")
    if data_dir.exists():
        shutil.copytree(data_dir, archive_dir / "data", dirs_exist_ok=True)

    return archive_dir


def lister_historique(categorie, code: str) -> list[dict]:
    """
    Retourne la liste des versions archivées d'une référence, de la plus récente à la plus ancienne.
    Chaque entrée : {"timestamp": str, "chemin": str, "indice_revision": str, "statut": str}
    """
    cat = _resoudre_categorie(categorie)
    historique_dir = cat.references_dir / _slug_reference(code) / "historique"
    if not historique_dir.exists():
        return []

    versions = []
    for version_dir in sorted(historique_dir.iterdir(), reverse=True):
        if not version_dir.is_dir():
            continue
        meta_path = version_dir / "metadata.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        except Exception:
            meta = {}
        versions.append({
            "timestamp": version_dir.name,
            "chemin": str(version_dir),
            "indice_revision": meta.get("indice_revision", "?"),
            "statut": meta.get("statut", "?"),
            "redige_par": meta.get("redige_par", "?"),
        })
    return versions


def proposer_code_reference(categorie, brief: dict) -> str:
    """Génère un code de référence par défaut basé sur le brief et la catégorie."""
    cat = _resoudre_categorie(categorie)

    matiere_initiale = (brief.get("matiere", "")[:1] or "X").upper()
    type_str = brief.get("type_produit", "")
    if "spherique" in type_str:
        type_initiale = "S"
    elif "box" in type_str:
        type_initiale = "B"
    elif "ronde" in type_str:
        type_initiale = "R"
    elif "tonneau" in type_str:
        type_initiale = "T"
    elif "rectangulaire" in type_str:
        type_initiale = "C"
    elif "ovale" in type_str:
        type_initiale = "O"
    else:
        type_initiale = "X"

    diametre = int(round(brief.get("dimensions", {}).get("diametre_mm", 0)))

    # Préfixe basé sur la catégorie : couches_minces → CM, glace_nue → GN, ceramique → CE
    cat_prefix = "".join(part[0].upper() for part in cat.code.split("_"))[:2]
    prefixe = f"REF-{cat_prefix}{type_initiale}{matiere_initiale}-{diametre:03d}"

    if not (cat.references_dir / prefixe).exists():
        return prefixe

    for suffixe in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = f"{prefixe}-{suffixe}"
        if not (cat.references_dir / candidate).exists():
            return candidate
    return prefixe


def _get_sb():
    try:
        from backend.supabase_client import get_supabase
        return get_supabase()
    except Exception:
        return None


def _sb_upsert(sb, cat_code: str, code: str, metadata: dict, data: dict) -> None:
    meta_clean = {k: v for k, v in metadata.items() if not k.startswith("_")}
    sb.table("dossiers").upsert({
        "categorie": cat_code,
        "code": code,
        "metadata": meta_clean,
        "data": data,
    }).execute()


def reference_existe(categorie, code: str) -> bool:
    cat = _resoudre_categorie(categorie)
    sb = _get_sb()
    if sb:
        try:
            res = sb.table("dossiers").select("code").eq("categorie", cat.code).eq("code", _slug_reference(code)).execute()
            if res.data is not None:
                return bool(res.data)
        except Exception:
            pass
    return (cat.references_dir / _slug_reference(code)).exists()


def enregistrer_reference(
    categorie,
    code: str,
    brief: dict,
    dossier: dict,
    acteur: str,
    commentaire_creation: str = "",
    overwrite: bool = False,
) -> Path:
    """
    Enregistre un dossier comme nouvelle référence et initialise automatiquement
    son workflow en `brouillon`.

    La référence ne sera utilisable comme source de similarité qu'une fois
    libérée (statut `libere` ou `approuve` dans le workflow).
    """
    cat = _resoudre_categorie(categorie)
    code = _slug_reference(code)
    if not code:
        raise ValueError("Code de référence vide ou invalide.")
    if not acteur or not acteur.strip():
        raise ValueError("Le nom de l'acteur (rédacteur) est obligatoire.")

    ref_dir = cat.references_dir / code
    if ref_dir.exists() and not overwrite:
        raise FileExistsError(f"La référence {code} existe déjà dans {cat.code}. Cocher 'Écraser' pour la remplacer.")

    # Archiver l'ancienne version avant écrasement
    if ref_dir.exists() and overwrite:
        archiver_version(ref_dir)

    ref_dir.mkdir(parents=True, exist_ok=True)
    data_dir = ref_dir / "data"
    data_dir.mkdir(exist_ok=True)

    dimensions = brief.get("dimensions", {})
    # Compatibilité multi-catégories : chercher la première dimension disponible
    diametre = dimensions.get("diametre_mm") or dimensions.get("dim1") or 0

    # Générer une désignation lisible à partir du vocabulaire de la catégorie
    vocab = cat.vocabulaire()
    type_label = vocab.get("types_produit", {}).get(brief.get("type_produit", ""), brief.get("type_produit", ""))
    matiere_label = vocab.get("matieres", {}).get(brief.get("matiere", ""), brief.get("matiere", ""))

    def _label_traitement(t):
        # t peut être un str (ancien format) ou dict {"code": ..., "typologie": ...}
        if isinstance(t, dict):
            code = t.get("code", "")
            typo = t.get("typologie")
            base = vocab.get("traitements", {}).get(code, code)
            return f"{base} [{typo}]" if typo else base
        return vocab.get("traitements", {}).get(t, t)

    traitements_str = " + ".join(_label_traitement(t) for t in brief.get("traitements", []))
    if diametre:
        designation = f"{type_label} {matiere_label} Ø{float(diametre):.2f}mm"
    else:
        designation = f"{type_label} {matiere_label}"
    if traitements_str:
        designation += f" — {traitements_str}"
    if brief.get("designation_client"):
        designation = brief["designation_client"]

    metadata = {
        "reference": code,
        "categorie": cat.code,
        "designation": designation,
        "type_produit": brief.get("type_produit"),
        "matiere": brief.get("matiere"),
        "traitements": brief.get("traitements", []),
        "dimensions": {
            k: v for k, v in dimensions.items()
        },
        "exigences_speciales": brief.get("exigences_speciales", ""),
        "documents": {
            "AMDEC_produit": "data/amdec_produit.json",
            "AMDEC_process": "data/amdec_process.json",
            "gamme": "data/gamme.json",
            "plan_controle": "data/plan_controle.json",
        },
        "infor_reference": None,
        "date_creation": date.today().isoformat(),
        "statut": "brouillon",
        "redige_par": acteur,
        "approuve_par": None,
        "indice_revision": "A",
        "reference_source": dossier.get("metadonnees_generation", {}).get("reference_source"),
        "score_similarite_origine": dossier.get("metadonnees_generation", {}).get("score_similarite"),
        # Garde qualité niveau 2 : flag procédé extrapolé (score similarité 30-60%)
        "premiere_fabrication": dossier.get("metadonnees_generation", {}).get("premiere_fabrication", False),
        "score_reference": dossier.get("metadonnees_generation", {}).get("score_reference"),
    }

    amdec_produit = dict(dossier.get("amdec_produit", {}))
    amdec_produit["reference"] = code
    amdec_produit["designation"] = designation

    amdec_process = dict(dossier.get("amdec_process", {}))
    amdec_process["reference"] = code
    amdec_process["designation"] = designation

    gamme = dict(dossier.get("gamme", {}))
    gamme["reference"] = code
    gamme["designation"] = designation

    plan_controle = dict(dossier.get("plan_controle", {}))
    plan_controle["reference"] = code
    plan_controle["designation"] = designation

    # Initialise le workflow AVANT de sauver — la nouvelle ref démarre en brouillon
    data_workflow = {
        "amdec_produit": amdec_produit,
        "amdec_process": amdec_process,
        "gamme": gamme,
        "plan_controle": plan_controle,
    }
    initialiser_workflow(
        metadata, data_workflow,
        acteur=acteur,
        commentaire=commentaire_creation or f"Création de la référence {code}",
    )

    (ref_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "amdec_produit.json").write_text(json.dumps(amdec_produit, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "amdec_process.json").write_text(json.dumps(amdec_process, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "gamme.json").write_text(json.dumps(gamme, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "plan_controle.json").write_text(json.dumps(plan_controle, ensure_ascii=False, indent=2), encoding="utf-8")

    # Persistance Supabase
    sb = _get_sb()
    if sb:
        try:
            _sb_upsert(sb, cat.code, code, metadata, {
                "amdec_produit": amdec_produit,
                "amdec_process": amdec_process,
                "gamme": gamme,
                "plan_controle": plan_controle,
            })
        except Exception:
            pass

    return ref_dir


def enregistrer_variantes(
    categorie,
    resultats_variantes: dict,
    brief_base: dict,
    acteur: str,
    overwrite: bool = False,
) -> list[Path]:
    """
    Enregistre N variantes générées par generer_dossier_variantes() en une seule opération.
    Chaque variante démarre en brouillon avec workflow initialisé au nom de `acteur`.
    """
    if not acteur or not acteur.strip():
        raise ValueError("Le nom de l'acteur (rédacteur) est obligatoire.")

    chemins = []
    for article, dossier in resultats_variantes.items():
        variante = dossier.get("variante", {})
        brief_variante = dict(brief_base)
        brief_variante["traitements"] = variante.get("traitements", brief_base.get("traitements", []))
        if variante.get("designation"):
            brief_variante["designation_client"] = variante["designation"]

        chemin = enregistrer_reference(
            categorie=categorie,
            code=article,
            brief=brief_variante,
            dossier=dossier,
            acteur=acteur,
            commentaire_creation=f"Variante {article} — base {brief_base.get('designation_client', '')}",
            overwrite=overwrite,
        )
        chemins.append(chemin)
    return chemins
