"""
Moteur de workflow de validation des dossiers qualité.

États : brouillon → en_revue → approuve → libere → obsolete
        en_revue → corrections → en_revue (boucle correction)

Les gates requises sont calculées automatiquement selon l'IPR max du dossier.
"""

from datetime import datetime
from pathlib import Path
import json

# ─── États et libellés ───────────────────────────────────────────────────────

STATUTS = {
    "brouillon":    {"label": "📝 Brouillon",           "couleur": "gray"},
    "en_revue":     {"label": "👁️ En revue",            "couleur": "blue"},
    "corrections":  {"label": "🔄 Corrections demandées","couleur": "orange"},
    "approuve":     {"label": "✅ Approuvé",             "couleur": "green"},
    "libere":       {"label": "🚀 Libéré",               "couleur": "green"},
    "obsolete":     {"label": "🗄️ Obsolète",            "couleur": "gray"},
}

TRANSITIONS = {
    # (statut_actuel, action) → nouveau_statut
    ("brouillon",   "soumettre"):           "en_revue",
    ("corrections", "resoumettre"):         "en_revue",
    ("en_revue",    "approuver_gate_bt"):   None,   # géré dynamiquement
    ("en_revue",    "corrections"):         "corrections",
    ("en_revue",    "approuver"):           "approuve",
    ("approuve",    "liberer"):             "libere",
    ("libere",      "rendre_obsolete"):     "obsolete",
    ("approuve",    "rendre_obsolete"):     "obsolete",
    ("brouillon",   "rendre_obsolete"):     "obsolete",
}

ACTIONS_LABELS = {
    "soumettre":        "Soumettre pour revue",
    "resoumettre":      "Resoumettre après corrections",
    "corrections":      "Demander des corrections",
    "approuver":        "Approuver",
    "liberer":          "Libérer en production",
    "rendre_obsolete":  "Rendre obsolète",
}


# ─── Calcul des gates selon IPR ──────────────────────────────────────────────

def calculer_ipr_max(data: dict) -> int:
    """Retourne l'IPR maximum trouvé dans l'AMDEC Produit ET l'AMDEC Process du dossier."""
    ipr_max = 0
    modes_produit = data.get("amdec_produit", {}).get("modes_defaillance", [])
    modes_process = data.get("amdec_process", {}).get("modes_defaillance", [])
    for m in modes_produit + modes_process:
        try:
            g = int(m.get("G", 0) or 0)
            o = int(m.get("O", 0) or 0)
            d = int(m.get("D", 0) or 0)
            ipr = g * o * d
            if ipr > ipr_max:
                ipr_max = ipr
        except (TypeError, ValueError):
            pass
    return ipr_max


def calculer_gates_requises(ipr_max: int) -> list[str]:
    """Retourne la liste des gates requises selon l'IPR max."""
    if ipr_max > 100:
        return ["Vérification BT", "Approbation Qualité", "Validation Direction"]
    elif ipr_max > 40:
        return ["Vérification BT", "Approbation Qualité"]
    else:
        return ["Vérification BT"]


# ─── Initialisation du workflow ──────────────────────────────────────────────

def initialiser_workflow(metadata: dict, data: dict, acteur: str = "Système", commentaire: str = "") -> dict:
    """
    Ajoute la structure workflow à un metadata existant.
    Appelé à la création ou à la première soumission d'un dossier.
    """
    ipr_max = calculer_ipr_max(data)
    gates = calculer_gates_requises(ipr_max)

    workflow = {
        "statut": "brouillon",
        "ipr_max": ipr_max,
        "gates_requises": gates,
        "gates_completees": [],
        "historique": [
            _entree(
                action="creation",
                acteur=acteur,
                commentaire=commentaire or f"Dossier créé — IPR max détecté : {ipr_max}",
            )
        ],
    }
    metadata["workflow"] = workflow
    return metadata


# ─── Transitions ─────────────────────────────────────────────────────────────

def faire_transition(
    metadata: dict,
    action: str,
    acteur: str,
    commentaire: str = "",
    data: dict | None = None,
) -> dict:
    """
    Applique une transition sur le workflow du dossier.

    Modifie `metadata` en place et retourne-le.
    Lève ValueError si la transition n'est pas permise.
    """
    wf = metadata.setdefault("workflow", {})
    statut_actuel = wf.get("statut", "brouillon")
    gates_requises = wf.get("gates_requises", ["Vérification BT"])
    gates_completees = wf.get("gates_completees", [])

    # Recalcul IPR si données fournies (après modification BT)
    if data and action == "soumettre":
        ipr_max = calculer_ipr_max(data)
        wf["ipr_max"] = ipr_max
        wf["gates_requises"] = calculer_gates_requises(ipr_max)
        gates_requises = wf["gates_requises"]

    # ── Validation de la transition ──
    if action == "soumettre" and statut_actuel not in ("brouillon", "corrections"):
        raise ValueError(f"Impossible de soumettre depuis l'état '{statut_actuel}'.")

    if action == "resoumettre" and statut_actuel != "corrections":
        raise ValueError("Resoumettre n'est possible que depuis l'état 'corrections'.")

    if action == "corrections" and statut_actuel != "en_revue":
        raise ValueError("Impossible de demander des corrections depuis cet état.")

    if action == "approuver" and statut_actuel != "en_revue":
        raise ValueError("Impossible d'approuver depuis cet état.")

    if action == "liberer" and statut_actuel != "approuve":
        raise ValueError("Impossible de libérer depuis cet état.")

    # ── Appliquer la transition ──
    if action in ("soumettre", "resoumettre"):
        nouveau_statut = "en_revue"
        wf["gates_completees"] = []  # reset gates à chaque nouvelle soumission

    elif action == "corrections":
        nouveau_statut = "corrections"

    elif action == "approuver":
        # Trouver la prochaine gate non complétée
        prochaine_gate = next(
            (g for g in gates_requises if g not in gates_completees), None
        )
        if prochaine_gate:
            gates_completees.append(prochaine_gate)
            wf["gates_completees"] = gates_completees
            commentaire_gate = f"Gate '{prochaine_gate}' validée par {acteur}. " + commentaire

            # Toutes les gates complétées → approuvé
            if set(gates_requises) <= set(gates_completees):
                nouveau_statut = "approuve"
                commentaire_gate += " — Toutes les gates complétées."
            else:
                # Gates restantes
                restantes = [g for g in gates_requises if g not in gates_completees]
                nouveau_statut = "en_revue"
                commentaire_gate += f" — Gate(s) restante(s) : {', '.join(restantes)}"
            commentaire = commentaire_gate
        else:
            nouveau_statut = "approuve"

    elif action == "liberer":
        nouveau_statut = "libere"

    elif action == "rendre_obsolete":
        nouveau_statut = "obsolete"

    else:
        raise ValueError(f"Action inconnue : '{action}'")

    wf["statut"] = nouveau_statut
    wf["historique"] = wf.get("historique", []) + [
        _entree(action=action, acteur=acteur, commentaire=commentaire)
    ]

    # Conserver aussi le statut principal pour compatibilité
    metadata["statut"] = nouveau_statut
    metadata["workflow"] = wf
    return metadata


# ─── Lecture de l'état ───────────────────────────────────────────────────────

def lire_workflow(metadata: dict) -> dict:
    """Retourne le workflow du dossier, initialisé si absent."""
    wf = metadata.get("workflow")
    if not wf:
        return {
            "statut": metadata.get("statut", "brouillon"),
            "ipr_max": 0,
            "gates_requises": ["Vérification BT"],
            "gates_completees": [],
            "historique": [],
        }
    return wf


def actions_disponibles(metadata: dict) -> list[str]:
    """Retourne la liste des actions possibles depuis l'état actuel."""
    wf = lire_workflow(metadata)
    statut = wf.get("statut", "brouillon")

    mapping = {
        "brouillon":   ["soumettre", "rendre_obsolete"],
        "en_revue":    ["approuver", "corrections"],
        "corrections": ["resoumettre", "rendre_obsolete"],
        "approuve":    ["liberer", "rendre_obsolete"],
        "libere":      ["rendre_obsolete"],
        "obsolete":    [],
    }
    return mapping.get(statut, [])


def prochaine_gate(metadata: dict) -> str | None:
    """Retourne le nom de la prochaine gate à valider, ou None si toutes faites."""
    wf = lire_workflow(metadata)
    gates_req = wf.get("gates_requises", [])
    gates_ok = wf.get("gates_completees", [])
    return next((g for g in gates_req if g not in gates_ok), None)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _entree(action: str, acteur: str, commentaire: str = "") -> dict:
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "action": action,
        "acteur": acteur,
        "commentaire": commentaire,
    }


def label_statut(statut: str) -> str:
    return STATUTS.get(statut, {}).get("label", statut)


def label_action(action: str) -> str:
    return ACTIONS_LABELS.get(action, action)


# ─── Mapping gate → rôle requis ──────────────────────────────────────────────

GATE_ROLES = {
    "Vérification BT": "bt",
    "Approbation Qualité": "qualite",
    "Validation Direction": "direction",
}


def role_pour_gate(gate: str) -> str:
    """Retourne le code rôle requis pour valider une gate donnée."""
    return GATE_ROLES.get(gate, "admin")
