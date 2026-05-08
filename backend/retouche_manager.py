"""
Gestion des retouches articles.

Une retouche = une opération de reprise/correction effectuée sur une pièce
non-conforme, documentée par rapport à une référence article.

Stockage : config/retouches/{ref_article}.json
Format   : liste de fiches retouche, chacune identifiée par un id unique.

Chaque fiche retouche contient :
  - id             : identifiant unique (RETO-{ref}-{n})
  - ref_article    : code de la référence article concernée
  - date           : date de la retouche (ISO 8601)
  - operateur      : nom de l'opérateur
  - poste_travail  : poste de travail (ex: PO-01, AR-02, CN-03)
  - defaut_constate: description libre du défaut constaté
  - operation      : opération de retouche effectuée
  - resultat       : "conforme" | "non_conforme" | "rebut"
  - commentaire    : note libre optionnelle
  - created_at     : timestamp de création de la fiche
"""

import json
import uuid
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RETOUCHES_DIR = BASE_DIR / "config" / "retouches"

# ─── Résultats possibles ─────────────────────────────────────────────────────

RESULTATS = {
    "conforme":     "✅ Conforme",
    "non_conforme": "❌ Non conforme",
    "rebut":        "🗑️ Mis au rebut",
}

# ─── Helpers internes ────────────────────────────────────────────────────────

def _chemin_fichier(ref_article: str) -> Path:
    """Retourne le chemin du JSON de retouches pour une référence article."""
    RETOUCHES_DIR.mkdir(parents=True, exist_ok=True)
    # Nettoie le nom pour éviter les traversées de répertoire
    slug = ref_article.strip().replace("/", "_").replace("\\", "_")
    return RETOUCHES_DIR / f"{slug}.json"


def _charger_fichier(ref_article: str) -> list[dict]:
    """Charge la liste des retouches d'une référence. Retourne [] si inexistant."""
    p = _chemin_fichier(ref_article)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _sauvegarder_fichier(ref_article: str, retouches: list[dict]) -> None:
    """Persiste la liste des retouches sur disque."""
    p = _chemin_fichier(ref_article)
    p.write_text(json.dumps(retouches, ensure_ascii=False, indent=2, default=str),
                 encoding="utf-8")


def _generer_id(ref_article: str, retouches: list[dict]) -> str:
    """Génère un identifiant lisible et unique pour une nouvelle fiche retouche."""
    slug = ref_article.strip().upper().replace("-", "").replace(" ", "")[:10]
    n = len(retouches) + 1
    return f"RETO-{slug}-{n:04d}"


# ─── CRUD ────────────────────────────────────────────────────────────────────

def lister_retouches(ref_article: str) -> list[dict]:
    """Retourne toutes les retouches d'un article, triées par date décroissante."""
    retouches = _charger_fichier(ref_article)
    return sorted(retouches, key=lambda r: r.get("date", ""), reverse=True)


def get_retouche(ref_article: str, retouche_id: str) -> dict | None:
    """Retourne une fiche retouche par son id. None si introuvable."""
    for r in _charger_fichier(ref_article):
        if r.get("id") == retouche_id:
            return r
    return None


def creer_retouche(
    ref_article: str,
    date_retouche: str | date,
    operateur: str,
    poste_travail: str,
    defaut_constate: str,
    operation: str,
    resultat: str,
    commentaire: str = "",
) -> dict:
    """
    Crée et persiste une nouvelle fiche retouche.

    Paramètres
    ----------
    ref_article    : code de référence de l'article (ex: REF-GRS-001)
    date_retouche  : date de la retouche (str ISO ou objet date)
    operateur      : prénom/nom de l'opérateur
    poste_travail  : identifiant du poste (ex: PO-01)
    defaut_constate: description du défaut observé
    operation      : opération de reprise effectuée
    resultat       : "conforme" | "non_conforme" | "rebut"
    commentaire    : note libre (optionnel)

    Retourne la fiche créée.
    """
    if resultat not in RESULTATS:
        raise ValueError(
            f"Résultat invalide : '{resultat}'. "
            f"Valeurs acceptées : {list(RESULTATS.keys())}"
        )
    if not ref_article.strip():
        raise ValueError("La référence article est obligatoire.")
    if not operateur.strip():
        raise ValueError("L'opérateur est obligatoire.")
    if not defaut_constate.strip():
        raise ValueError("La description du défaut est obligatoire.")
    if not operation.strip():
        raise ValueError("L'opération de retouche est obligatoire.")

    retouches = _charger_fichier(ref_article)
    fiche = {
        "id":              _generer_id(ref_article, retouches),
        "ref_article":     ref_article.strip(),
        "date":            str(date_retouche),
        "operateur":       operateur.strip(),
        "poste_travail":   poste_travail.strip(),
        "defaut_constate": defaut_constate.strip(),
        "operation":       operation.strip(),
        "resultat":        resultat,
        "commentaire":     commentaire.strip(),
        "created_at":      datetime.now().isoformat(timespec="seconds"),
    }
    retouches.append(fiche)
    _sauvegarder_fichier(ref_article, retouches)
    return fiche


def supprimer_retouche(ref_article: str, retouche_id: str) -> bool:
    """Supprime une fiche retouche. Retourne True si trouvée et supprimée."""
    retouches = _charger_fichier(ref_article)
    nouvelles = [r for r in retouches if r.get("id") != retouche_id]
    if len(nouvelles) == len(retouches):
        return False
    _sauvegarder_fichier(ref_article, nouvelles)
    return True


# ─── Statistiques ─────────────────────────────────────────────────────────────

def stats_retouches(ref_article: str) -> dict:
    """
    Calcule les statistiques de retouche pour un article.

    Retourne un dict avec :
      - total           : nombre total de retouches
      - conformes       : nombre de retouches aboutissant à une conformité
      - non_conformes   : nombre de retouches non concluantes
      - rebuts          : nombre de pièces mises au rebut
      - taux_conformite : % de retouches conformes / total (0.0 si aucune)
      - par_resultat    : {resultat: count}
      - par_operateur   : {operateur: count}
      - par_poste       : {poste: count}
    """
    retouches = _charger_fichier(ref_article)
    total = len(retouches)
    if total == 0:
        return {
            "total": 0,
            "conformes": 0,
            "non_conformes": 0,
            "rebuts": 0,
            "taux_conformite": 0.0,
            "par_resultat": {},
            "par_operateur": {},
            "par_poste": {},
        }

    par_resultat: dict[str, int] = {}
    par_operateur: dict[str, int] = {}
    par_poste: dict[str, int] = {}

    for r in retouches:
        res = r.get("resultat", "inconnu")
        par_resultat[res] = par_resultat.get(res, 0) + 1
        op = r.get("operateur", "—")
        par_operateur[op] = par_operateur.get(op, 0) + 1
        po = r.get("poste_travail", "—")
        par_poste[po] = par_poste.get(po, 0) + 1

    conformes = par_resultat.get("conforme", 0)
    return {
        "total":           total,
        "conformes":       conformes,
        "non_conformes":   par_resultat.get("non_conforme", 0),
        "rebuts":          par_resultat.get("rebut", 0),
        "taux_conformite": round(conformes / total, 4) if total else 0.0,
        "par_resultat":    par_resultat,
        "par_operateur":   par_operateur,
        "par_poste":       par_poste,
    }


def lister_articles_avec_retouches() -> list[str]:
    """Retourne la liste des références article qui ont au moins une retouche."""
    if not RETOUCHES_DIR.exists():
        return []
    return sorted(
        p.stem for p in RETOUCHES_DIR.glob("*.json") if p.is_file()
    )


# ─── Export données brutes ────────────────────────────────────────────────────

def retouches_vers_lignes_excel(ref_article: str) -> list[dict]:
    """
    Transforme les retouches d'un article en liste de dicts plats,
    prêts pour l'export Excel (une ligne par retouche).
    """
    retouches = lister_retouches(ref_article)
    lignes = []
    for r in retouches:
        lignes.append({
            "ID Retouche":       r.get("id", ""),
            "Référence article": r.get("ref_article", ""),
            "Date":              r.get("date", ""),
            "Opérateur":         r.get("operateur", ""),
            "Poste de travail":  r.get("poste_travail", ""),
            "Défaut constaté":   r.get("defaut_constate", ""),
            "Opération retouche":r.get("operation", ""),
            "Résultat":          RESULTATS.get(r.get("resultat", ""), r.get("resultat", "")),
            "Commentaire":       r.get("commentaire", ""),
            "Créé le":           r.get("created_at", ""),
        })
    return lignes
