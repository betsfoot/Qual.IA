"""
Moteur de similarité multi-catégories.

Compare un brief client avec les références d'une catégorie donnée.
Les critères et poids sont définis dans le config.json de la catégorie.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from backend.category_manager import Categorie, charger_categorie
from backend.typologie_manager import normaliser_traitement, codes_traitements

SEUIL_AUTO = float(os.getenv("SEUIL_AUTO", "0.85"))
SEUIL_AVERTISSEMENT = float(os.getenv("SEUIL_AVERTISSEMENT", "0.60"))


@dataclass
class ResultatSimilarite:
    reference: str
    designation: str
    score: float
    detail_scores: dict
    mode: str          # "automatique" | "avertissement" | "manuelle"
    avertissements: list[str]
    metadata: dict
    categorie: str


# ─── Fonctions de score (génériques, choisies via type_comparaison) ─────────

def _score_exact_match(brief_val, ref_val) -> float:
    if brief_val is None or ref_val is None:
        return 0.5
    return 1.0 if brief_val == ref_val else 0.0


def _trouver_traitement(traitements: list, prefixe: str = None, code: str = None):
    """Retourne (code, typologie) du premier traitement matchant prefixe ou code."""
    for t in traitements:
        c, typo = normaliser_traitement(t)
        if code and c == code:
            return c, typo
        if prefixe and c.startswith(prefixe):
            return c, typo
    return None, None


def _score_traitement_avec_typologie(brief_pair, ref_pair) -> float:
    """
    Score un couple (code, typologie) entre brief et référence.

    1.0 = même code ET même typologie (ou typologie absente des deux côtés)
    0.5 = même code mais typologie différente (mêmes risques mais outillage et méthode différents)
    0.0 = codes différents
    """
    brief_code, brief_typo = brief_pair
    ref_code, ref_typo = ref_pair

    if brief_code != ref_code:
        return 0.0
    # Codes identiques
    if brief_typo == ref_typo:
        return 1.0
    # Une seule des deux a une typologie déclarée → on considère qu'on ne sait pas
    if brief_typo is None or ref_typo is None:
        return 0.7
    # Typologies différentes : risques similaires mais outillage/méthode différents
    return 0.5


def _score_metallisation_match(brief: dict, ref_meta: dict) -> float:
    """Score sur la métallisation : présence, type, et typologie (composition).

    1.0 = même code métallisation ET même typologie (composition cible)
    0.7 = même code, typologie inconnue d'un côté
    0.5 = même code, typologies différentes (même procédé mais stack différent)
    0.3 = un seul côté a une métallisation
    0.0 = codes différents (CN ≠ Or ≠ Chrome…) — critère ÉLIMINATOIRE.
          CN et Or sont des procédés, chimies et contrôles entièrement différents.
    """
    brief_pair = _trouver_traitement(brief.get("traitements", []), prefixe="metallisation_")
    ref_pair = _trouver_traitement(ref_meta.get("traitements", []), prefixe="metallisation_")

    brief_code, _ = brief_pair
    ref_code, _ = ref_pair

    # Aucune métallisation des deux côtés → équivalent parfait
    if brief_code is None and ref_code is None:
        return 1.0
    # Présence d'un seul côté → pénalité forte (processus différents)
    if brief_code is None or ref_code is None:
        return 0.3
    # Codes différents (ex: CN vs Or) → score 0.0 ÉLIMINATOIRE.
    # La chimie de dépôt, l'outillage, les contrôles spectro et l'aspect final
    # sont entièrement incompatibles : aucun crédit partiel accordé.
    if brief_code != ref_code:
        return 0.0
    # Même code : comparaison des typologies (stack de couches)
    return _score_traitement_avec_typologie(brief_pair, ref_pair)


def _score_ar_levels(brief: dict, ref_meta: dict) -> float:
    """
    Score AR : absent / simple / double face + typologie (composition de couches).

    1.0 = même type AR ET même typologie (composition)
    0.7 = même type AR, typologie inconnue d'un côté
    0.5 = même type AR (ex: double face) mais typologies différentes (autre stack/outillage)
    0.3 = un seul a un AR
    0.0 = aucun AR vs AR (ou simple vs double face) — critère ÉLIMINATOIRE.
          Simple face ≠ double face : nombre de passes, outillage et programme
          de dépôt entièrement différents.
    """
    def trouver_ar(traitements):
        for t in traitements:
            code, typo = normaliser_traitement(t)
            if code in ("antireflet_double_face", "antireflet_simple_face"):
                return code, typo
        return None, None

    brief_pair = trouver_ar(brief.get("traitements", []))
    ref_pair = trouver_ar(ref_meta.get("traitements", []))

    brief_code, _ = brief_pair
    ref_code, _ = ref_pair

    if brief_code is None and ref_code is None:
        return 1.0
    if brief_code is None or ref_code is None:
        return 0.3
    if brief_code != ref_code:
        # simple face ≠ double face : processus incompatibles — score ÉLIMINATOIRE.
        return 0.0
    # Même type AR : on compare les typologies
    return _score_traitement_avec_typologie(brief_pair, ref_pair)


def _score_diameter_range(brief: dict, ref_meta: dict, cle: str = "diametre_mm") -> float:
    def tranche(d):
        if d is None:
            return None
        if d < 30:
            return "small"
        if d <= 40:
            return "medium"
        return "large"

    brief_d = brief.get("dimensions", {}).get(cle)
    ref_d = ref_meta.get("dimensions", {}).get(cle)

    if brief_d is None or ref_d is None:
        return 0.5
    if tranche(brief_d) == tranche(ref_d):
        diff_pct = abs(brief_d - ref_d) / ref_d
        if diff_pct < 0.05:
            return 1.0
        if diff_pct < 0.15:
            return 0.8
        return 0.6
    return 0.0


def _score_numeric_proximity(brief: dict, ref_meta: dict, cle: str = "epaisseur_mm") -> float:
    brief_v = brief.get("dimensions", {}).get(cle)
    ref_v = ref_meta.get("dimensions", {}).get(cle)
    if brief_v is None or ref_v is None:
        return 0.5
    if ref_v == 0:
        return 0.5
    diff_pct = abs(brief_v - ref_v) / ref_v
    if diff_pct < 0.05:
        return 1.0
    if diff_pct < 0.15:
        return 0.7
    if diff_pct < 0.30:
        return 0.4
    return 0.0


# Mapping nom de comparaison → fonction (signature: brief, ref_meta, nom_critere, params)
COMPARATEURS = {
    "exact_match":        lambda b, r, k, p: _score_exact_match(b.get(k), r.get(k)),
    "metallisation_match": lambda b, r, k, p: _score_metallisation_match(b, r),
    "ar_levels":          lambda b, r, k, p: _score_ar_levels(b, r),
    "diameter_range":     lambda b, r, k, p: _score_diameter_range(b, r, p.get("cle_dimension", "diametre_mm")),
    "numeric_proximity":  lambda b, r, k, p: _score_numeric_proximity(b, r, p.get("cle_dimension", "epaisseur_mm")),
}


# ─── Calcul du score global ──────────────────────────────────────────────────

def _calculer_score(brief: dict, ref_meta: dict, criteres: dict) -> tuple[float, dict]:
    scores = {}
    score_total = 0.0
    poids_total = 0.0

    for nom_critere, params in criteres.items():
        type_comp = params.get("type_comparaison", "exact_match")
        poids = params.get("poids", 0.0)

        comparateur = COMPARATEURS.get(type_comp)
        if comparateur is None:
            scores[nom_critere] = 0.0
            continue

        score = comparateur(brief, ref_meta, nom_critere, params)
        scores[nom_critere] = score
        score_total += score * poids
        poids_total += poids

    if poids_total > 0:
        score_total = score_total / poids_total  # normalisation si poids ≠ 1.0

    return round(score_total, 4), scores


def _generer_avertissements(brief: dict, ref_meta: dict, detail: dict, criteres: dict) -> list[str]:
    avertissements = []
    for nom_critere, score in detail.items():
        if score >= 0.95:
            continue
        params = criteres.get(nom_critere, {})
        description = params.get("description", nom_critere)
        if score < 0.3:
            avertissements.append(f"❌ {description} : forte divergence (score {score:.0%})")
        elif score < 0.7:
            avertissements.append(f"⚠️ {description} : différence notable (score {score:.0%})")
    return avertissements


# Statuts qui rendent une référence utilisable comme SOURCE de similarité.
# Une référence en brouillon, en revue ou en corrections ne doit JAMAIS servir
# de base à un nouveau dossier — elle peut contenir des erreurs non détectées.
STATUTS_UTILISABLES = ("libere", "approuve")
STATUTS_LEGACY = ("valide",)  # Références importées avant l'introduction du workflow


def est_utilisable_comme_source(metadata: dict) -> bool:
    """Une référence n'est utilisable comme source que si elle est libérée/approuvée."""
    wf = metadata.get("workflow") or {}
    statut_wf = wf.get("statut")
    if statut_wf:
        return statut_wf in STATUTS_UTILISABLES
    # Compatibilité : références créées avant l'introduction du workflow
    return metadata.get("statut") in STATUTS_LEGACY + STATUTS_UTILISABLES


def charger_references(categorie: Categorie, inclure_non_validees: bool = False) -> list[dict]:
    """
    Charge les metadata.json d'une catégorie.

    Par défaut, ne retourne que les références **libérées ou approuvées** —
    une référence en brouillon ou en revue ne peut pas servir de source à un
    nouveau dossier (elle pourrait contenir des erreurs non validées).
    """
    references = []
    for metadata_file in categorie.references_dir.glob("*/metadata.json"):
        try:
            with open(metadata_file, encoding="utf-8") as f:
                meta = json.load(f)
            if inclure_non_validees or est_utilisable_comme_source(meta):
                references.append(meta)
        except Exception:
            pass
    return references


def traitements_inconnus(brief: dict, references: list[dict]) -> list[str]:
    """
    Retourne la liste des codes de traitement présents dans le brief mais qui
    n'existent dans AUCUNE référence libérée/approuvée de la base.
    Utilisé pour bloquer la génération si le procédé est totalement inconnu.
    """
    from backend.typologie_manager import normaliser_traitement

    codes_brief = {normaliser_traitement(t)[0] for t in brief.get("traitements", []) if t}
    codes_brief.discard("")
    codes_base = set()
    for ref in references:
        for t in ref.get("traitements", []):
            code, _ = normaliser_traitement(t)
            if code:
                codes_base.add(code)
    return sorted(codes_brief - codes_base)


def trouver_meilleure_reference(brief: dict, categorie: Categorie | str) -> ResultatSimilarite | None:
    """
    Compare le brief avec toutes les références de la catégorie.
    `categorie` peut être un objet Categorie ou un code (str).
    """
    if isinstance(categorie, str):
        categorie = charger_categorie(categorie)
    if categorie is None:
        return None

    criteres = categorie.criteres_similarite()
    references = charger_references(categorie)  # filtre auto : libere/approuve uniquement
    if not references:
        return None


    meilleure = None
    meilleur_score = -1.0
    meilleur_detail = {}

    for ref_meta in references:
        score, detail = _calculer_score(brief, ref_meta, criteres)
        if score > meilleur_score:
            meilleur_score = score
            meilleure = ref_meta
            meilleur_detail = detail

    if meilleure is None:
        return None

    if meilleur_score >= SEUIL_AUTO:
        mode = "automatique"
    elif meilleur_score >= SEUIL_AVERTISSEMENT:
        mode = "avertissement"
    else:
        mode = "manuelle"

    return ResultatSimilarite(
        reference=meilleure["reference"],
        designation=meilleure["designation"],
        score=meilleur_score,
        detail_scores=meilleur_detail,
        mode=mode,
        avertissements=_generer_avertissements(brief, meilleure, meilleur_detail, criteres),
        metadata=meilleure,
        categorie=categorie.code,
    )


def brief_depuis_formulaire(
    type_produit: str,
    matiere: str,
    traitements: list[str],
    dimensions: dict,
) -> dict:
    """Construit le dict brief à partir des champs du formulaire."""
    return {
        "type_produit": type_produit,
        "matiere": matiere,
        "traitements": traitements,
        "dimensions": dimensions,
    }


if __name__ == "__main__":
    # Test : trouver REF-GRS-001 pour brief Ø31mm CN+AR dans couches_minces
    brief_test = brief_depuis_formulaire(
        type_produit="glace_ronde",
        matiere="saphir",
        traitements=["metallisation_CN", "antireflet_double_face"],
        dimensions={"diametre_mm": 31.0, "tolerance_diametre_mm": 0.05},
    )
    res = trouver_meilleure_reference(brief_test, categorie="couches_minces")
    if res:
        print(f"Référence trouvée : {res.reference}")
        print(f"Score : {res.score:.2%}")
        print(f"Mode : {res.mode}")
        print(f"Catégorie : {res.categorie}")
    else:
        print("Aucune référence trouvée.")
