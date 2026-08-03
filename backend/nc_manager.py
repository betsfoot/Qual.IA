"""
Gestionnaire des Non-Conformités — Qual.IA Streamlit.
Stockage : data/nc/<id>.json  +  data/nc_index.json
"""
import json
import logging
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Chemins ───────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
NC_DIR    = _ROOT / "data" / "nc"
NC_INDEX  = _ROOT / "data" / "nc_index.json"
PHOTOS_DIR = _ROOT / "data" / "nc_photos"

NC_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# ── Constantes métier ─────────────────────────────────────────────────────────
TYPES_DEFAUT = [
    "Dimensionnel",
    "Visuel / Aspect",
    "Fonctionnel",
    "Documentation",
    "Matière / Matériau",
    "Traitement de surface",
    "Autre",
]

PHASES_DETECTION = [
    "Réception matière",
    "Fabrication",
    "Contrôle final",
    "Expédition",
    "Retour client",
    "Audit interne",
]

NIVEAUX_GRAVITE = ["Mineure", "Majeure", "Critique"]

STATUTS_NC = {
    "ouverte":    "🟠 Ouverte",
    "en_cours":   "🔵 En cours",
    "fermee":     "🟢 Fermée",
    "abandonnee": "⚫ Abandonnée",
}


# ── Index ─────────────────────────────────────────────────────────────────────

def _lire_index() -> list[dict]:
    if NC_INDEX.exists():
        try:
            return json.loads(NC_INDEX.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _ecrire_index(index: list[dict]) -> None:
    NC_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _entree_index(nc: dict) -> dict:
    return {
        "id":              nc["id"],
        "numero_of":       nc.get("numero_of", ""),
        "dossier_ref":     nc.get("dossier_ref", ""),
        "type_defaut":     nc.get("type_defaut", ""),
        "gravite":         nc.get("gravite", ""),
        "statut":          nc.get("statut", "ouverte"),
        "detecte_par":     nc.get("detecte_par", ""),
        "phase_detection": nc.get("phase_detection", ""),
        "created_at":      nc.get("created_at", ""),
        "updated_at":      nc.get("updated_at", ""),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _generer_id() -> str:
    annee = datetime.now().year
    index = _lire_index()
    seq = len([e for e in index if e["id"].startswith(f"NC-{annee}-")]) + 1
    return f"NC-{annee}-{seq:04d}"


# ── CRUD ──────────────────────────────────────────────────────────────────────

def lister_nc(statut: str | None = None) -> list[dict]:
    index = _lire_index()
    if statut:
        index = [e for e in index if e.get("statut") == statut]
    return sorted(index, key=lambda x: x.get("created_at", ""), reverse=True)


def charger_nc(nc_id: str) -> dict | None:
    chemin = NC_DIR / f"{nc_id}.json"
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Erreur lecture NC %s : %s", nc_id, e)
        return None


def creer_nc(data: dict, auteur: str) -> dict:
    nc_id = _generer_id()
    maintenant = _maintenant()
    nc = {
        "id": nc_id,
        "numero_of":        data.get("numero_of", ""),
        "info_of":          data.get("info_of", {}),
        "dossier_ref":      data.get("dossier_ref", ""),
        "date_detection":   data.get("date_detection", maintenant[:10]),
        "detecte_par":      auteur,
        "phase_detection":  data.get("phase_detection", ""),
        "type_defaut":      data.get("type_defaut", ""),
        "description":      data.get("description", ""),
        "gravite":          data.get("gravite", "Mineure"),
        "piece_reference":  data.get("piece_reference", "") or data.get("info_of", {}).get("reference_piece", ""),
        "quantite_affectee": int(data.get("quantite_affectee", 1) or data.get("info_of", {}).get("quantite", 1) or 1),
        "photos": [],
        "statut": "ouverte",
        "huit_d": {
            "d1_equipe":              "",
            "d2_description":         data.get("description", ""),
            "d3_confinement":         "",
            "d4_causes_racines":      "",
            "d5_actions_correctives": "",
            "d6_mise_en_oeuvre":      "",
            "d7_prevention":          "",
            "d8_cloture":             "",
            "suggestions_ia":         [],
        },
        "created_at": maintenant,
        "updated_at": maintenant,
    }
    (NC_DIR / f"{nc_id}.json").write_text(
        json.dumps(nc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    index = _lire_index()
    index.append(_entree_index(nc))
    _ecrire_index(index)
    logger.info("NC créée : %s par %s", nc_id, auteur)
    return nc


def sauvegarder_nc(nc_id: str, nc: dict) -> bool:
    nc["updated_at"] = _maintenant()
    try:
        (NC_DIR / f"{nc_id}.json").write_text(
            json.dumps(nc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        index = _lire_index()
        for i, e in enumerate(index):
            if e["id"] == nc_id:
                index[i] = _entree_index(nc)
                break
        _ecrire_index(index)
        return True
    except Exception as e:
        logger.error("Erreur sauvegarde NC %s : %s", nc_id, e)
        return False


# ── Photos ────────────────────────────────────────────────────────────────────

def sauvegarder_photo(nc_id: str, nom_fichier: str, contenu: bytes) -> str:
    """Enregistre une photo sur disque et retourne le nom définitif."""
    nom_def = f"{nc_id}_{nom_fichier}"
    (PHOTOS_DIR / nom_def).write_bytes(contenu)
    nc = charger_nc(nc_id)
    if nc and nom_def not in nc["photos"]:
        nc["photos"].append(nom_def)
        sauvegarder_nc(nc_id, nc)
    return nom_def


def supprimer_photo(nc_id: str, nom_fichier: str) -> bool:
    chemin = PHOTOS_DIR / nom_fichier
    if chemin.exists():
        chemin.unlink()
    nc = charger_nc(nc_id)
    if nc:
        nc["photos"] = [p for p in nc["photos"] if p != nom_fichier]
        sauvegarder_nc(nc_id, nc)
    return True


# ── KPI ───────────────────────────────────────────────────────────────────────

def kpi_nc() -> dict:
    index = _lire_index()
    par_mois:   dict[str, int] = defaultdict(int)
    par_type:   dict[str, int] = defaultdict(int)
    par_gravite: dict[str, int] = defaultdict(int)

    for e in index:
        mois = e.get("created_at", "")[:7]
        if mois:
            par_mois[mois] += 1
        par_type[e.get("type_defaut", "Autre")] += 1
        par_gravite[e.get("gravite", "Mineure")] += 1

    mois_tries = sorted(par_mois.keys())[-12:]
    return {
        "total":           len(index),
        "ouvertes":        sum(1 for e in index if e.get("statut") == "ouverte"),
        "en_cours":        sum(1 for e in index if e.get("statut") == "en_cours"),
        "fermees":         sum(1 for e in index if e.get("statut") == "fermee"),
        "par_mois_labels": mois_tries,
        "par_mois_data":   [par_mois[m] for m in mois_tries],
        "par_type":        dict(par_type),
        "par_gravite":     dict(par_gravite),
    }


# ── KPI filtré ───────────────────────────────────────────────────────────────

def kpi_nc_filtre(periode: str = "mois", annee: int | None = None, mois: int | None = None) -> dict:
    """
    KPI NC filtré.
    periode = "mois"   → toutes les données groupées par mois (pour l'année sélectionnée)
    periode = "annee"  → toutes les données groupées par année
    """
    index = _lire_index()
    from datetime import datetime as dt
    annee_courante = dt.now().year

    par_periode: dict[str, int] = defaultdict(int)
    par_type:    dict[str, int] = defaultdict(int)
    par_gravite: dict[str, int] = defaultdict(int)
    par_statut:  dict[str, int] = defaultdict(int)

    for e in index:
        created = e.get("created_at", "")
        if not created:
            continue
        e_annee = int(created[:4]) if len(created) >= 4 else 0
        e_mois  = int(created[5:7]) if len(created) >= 7 else 0

        # Filtre
        if periode == "mois":
            cible_annee = annee or annee_courante
            if e_annee != cible_annee:
                continue
            cle = f"{e_mois:02d}/{cible_annee}"
        else:  # par année
            cle = str(e_annee)

        par_periode[cle] += 1
        par_type[e.get("type_defaut", "Autre")] += 1
        par_gravite[e.get("gravite", "Mineure")] += 1
        par_statut[e.get("statut", "ouverte")] += 1

    labels = sorted(par_periode.keys())
    return {
        "labels":      labels,
        "data":        [par_periode[l] for l in labels],
        "par_type":    dict(sorted(par_type.items(), key=lambda x: -x[1])),
        "par_gravite": dict(par_gravite),
        "par_statut":  dict(par_statut),
        "total_filtre": sum(par_periode.values()),
    }


def annees_disponibles() -> list[int]:
    """Retourne les années pour lesquelles des NC existent."""
    index = _lire_index()
    annees = set()
    for e in index:
        c = e.get("created_at", "")
        if c and len(c) >= 4:
            annees.add(int(c[:4]))
    from datetime import datetime as dt
    annees.add(dt.now().year)
    return sorted(annees, reverse=True)


# ── IA (Claude) ───────────────────────────────────────────────────────────────

def suggerer_8d_ia(nc: dict) -> dict | None:
    """
    Génère des suggestions 8D via Claude API.
    Retourne un dict de suggestions ou None si la clé n'est pas configurée.
    """
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("Package 'anthropic' non installé.")
        return None

    # Cherche des NC similaires fermées
    similaires_txt = ""
    index = _lire_index()
    similaires = []
    for e in index:
        if e["id"] == nc["id"] or e.get("statut") != "fermee":
            continue
        score = (2 if e.get("type_defaut") == nc.get("type_defaut") else 0) + \
                (1 if e.get("phase_detection") == nc.get("phase_detection") else 0)
        if score > 0:
            s_nc = charger_nc(e["id"])
            if s_nc and s_nc.get("huit_d", {}).get("d4_causes_racines"):
                similaires.append((score, s_nc))
    similaires.sort(key=lambda x: -x[0])
    for _, s in similaires[:4]:
        d = s.get("huit_d", {})
        similaires_txt += (
            f"\n--- {s['id']} ---\n"
            f"Type: {s.get('type_defaut')}\n"
            f"D4 causes: {d.get('d4_causes_racines')}\n"
            f"D5 actions: {d.get('d5_actions_correctives')}\n"
        )

    prompt = f"""Tu es un expert qualité industrielle en méthode 8D.

NC À ANALYSER :
- Type défaut : {nc.get('type_defaut')}
- Phase : {nc.get('phase_detection')}
- Gravité : {nc.get('gravite')}
- Description : {nc.get('description')}
- Pièce : {nc.get('piece_reference')}
- Qté affectée : {nc.get('quantite_affectee')}

HISTORIQUE NC SIMILAIRES RÉSOLUES :
{similaires_txt or "Aucune NC similaire fermée dans la base."}

Réponds uniquement avec un JSON brut (pas de markdown) :
{{
  "d1_suggestion": "Équipe recommandée",
  "d3_suggestion": "Action de confinement immédiate",
  "d4_suggestions": ["Cause racine 1", "Cause racine 2", "Cause racine 3"],
  "d5_suggestions": ["Action corrective 1", "Action corrective 2"],
  "d7_suggestion": "Mesure de prévention",
  "confiance": "haute|moyenne|faible",
  "rationale": "Explication courte"
}}"""

    try:
        msg = client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-opus-4-5"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        contenu = msg.content[0].text.strip()
        if contenu.startswith("```"):
            contenu = contenu.split("```")[1]
            if contenu.startswith("json"):
                contenu = contenu[4:]
        return json.loads(contenu)
    except Exception as e:
        logger.error("Erreur IA suggestions 8D : %s", e)
        return None
