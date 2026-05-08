"""
Lecture automatique d'un plan technique (PDF ou image) via Claude Vision.

Extrait les informations dimensionnelles et produit pour pré-remplir le brief.
"""

import base64
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from backend.config import get_secret

load_dotenv(override=True)

MODEL = get_secret("CLAUDE_MODEL", "claude-sonnet-4-6")

_SYSTEM = (
    "Tu es un expert en lecture de plans techniques industriels. "
    "Tu sais lire les cartouches, les vues, les cotations et les tolérances "
    "de plans de pièces mécaniques, horlogers, optiques ou céramiques."
)

_DIMS_PAR_DEFAUT = [
    {"cle": "diametre_mm", "label": "dimension principale (mm)"},
    {"cle": "epaisseur_mm", "label": "épaisseur (mm)"},
]

_PROMPT_BASE = """Analyse ce plan technique et extrais les informations suivantes.

Réponds UNIQUEMENT avec un objet JSON valide, sans commentaire ni markdown, avec exactement ces clés :

{dims_schema}
  "designation": "désignation ou titre du plan (chaîne vide si absent)",
  "type_produit": "snake_case, vide si incertain",
  "matiere": "snake_case, vide si incertain",
  "traitements": ["liste", "de", "traitements", "détectés"],
  "notes": "toute autre information utile visible sur le plan"
}}

Règles :
- Si une cote est ambiguë (plusieurs valeurs), retourne la valeur nominale principale.
- Convertis toutes les cotes en millimètres (sauf si la cle indique autre unité).
- Si une information est absente ou illisible, mets null ou liste/chaîne vide — ne suppose rien.
"""


def _build_prompt_extraction(categorie=None) -> tuple[str, list[str]]:
    """Retourne (prompt, liste des clés numériques à normaliser en float)."""
    if categorie is not None and hasattr(categorie, "parametres_numeriques"):
        params = categorie.parametres_numeriques()
    else:
        params = _DIMS_PAR_DEFAUT

    dims_lines = []
    float_keys = []
    for p in params:
        cle = p["cle"]
        label = p.get("label", cle)
        dims_lines.append(f'  "{cle}": null ou nombre flottant ({label}),')
        dims_lines.append(f'  "tolerance_{cle}": null ou nombre flottant (tolérance ±),')
        float_keys.extend([cle, f"tolerance_{cle}"])

    dims_schema = "{{\n" + "\n".join(dims_lines) + "\n"
    return _PROMPT_BASE.format(dims_schema=dims_schema), float_keys


def _media_type(nom_fichier: str) -> str:
    ext = Path(nom_fichier).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")


def analyser_plan(fichier_bytes: bytes, nom_fichier: str, categorie=None) -> dict:
    """
    Analyse un plan technique et retourne un dict structuré pour pré-remplir le brief.

    Paramètres
    ----------
    fichier_bytes : contenu binaire du fichier
    nom_fichier   : nom original (utilisé pour détecter le type MIME)
    categorie     : CategorieConfig optionnel (pour adapter le prompt au domaine)

    Retourne
    --------
    dict avec les clés : designation, type_produit, matiere, traitements,
    diametre_mm, tolerance_diametre_mm, epaisseur_mm, tolerance_epaisseur_mm, notes
    """
    api_key = get_secret("ANTHROPIC_API_KEY")

    media_type = _media_type(nom_fichier)
    if media_type == "application/octet-stream":
        raise ValueError(f"Format non supporté : {Path(nom_fichier).suffix}. Utilise PDF, PNG, JPG ou WEBP.")

    data_b64 = base64.standard_b64encode(fichier_bytes).decode("utf-8")

    # Construction du contenu du message selon le type
    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": data_b64,
            },
        }
    else:
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data_b64,
            },
        }

    # Construire le prompt dynamiquement selon la catégorie
    prompt, float_keys = _build_prompt_extraction(categorie)
    if categorie is not None and hasattr(categorie, "vocabulaire"):
        vocab = categorie.vocabulaire()
        types_dispo = list(vocab.get("types_produit", {}).keys())
        matieres_dispo = list(vocab.get("matieres", {}).keys())
        traitements_dispo = list(vocab.get("traitements", {}).keys())
        if types_dispo or matieres_dispo or traitements_dispo:
            prompt += (
                f"\n\nValeurs attendues pour cette catégorie ({categorie.nom}) :"
                f"\n- types_produit possibles : {types_dispo}"
                f"\n- matieres possibles : {matieres_dispo}"
                f"\n- traitements possibles : {traitements_dispo}"
                "\nUtilise ces valeurs si elles correspondent à ce que tu vois."
            )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Nettoyage défensif si Claude a quand même mis du markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Réponse Claude non parseable : {e}\n---\n{raw}") from e

    # Normalisation des types numériques (clés dynamiques selon catégorie)
    for float_key in float_keys:
        val = result.get(float_key)
        if val is not None:
            try:
                result[float_key] = float(val)
            except (TypeError, ValueError):
                result[float_key] = None

    if not isinstance(result.get("traitements"), list):
        result["traitements"] = []

    return result
