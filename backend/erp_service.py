"""
Service ERP — Connexion Infor / SAP pour récupérer les infos d'un Ordre de Fabrication.

Pour brancher sur un vrai ERP :
  1. Renseigner ERP_TYPE, ERP_URL, ERP_USER, ERP_PASSWORD dans le .env
  2. Implémenter _fetch_infor() ou _fetch_sap() ci-dessous
  3. La fonction publique chercher_of() reste identique pour le reste du code

Sans ERP configuré : retourne des données mock pour les tests.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

ERP_TYPE     = os.getenv("ERP_TYPE", "")          # "infor" | "sap" | ""
ERP_URL      = os.getenv("ERP_URL", "")           # ex. https://erp.entreprise.fr/api
ERP_USER     = os.getenv("ERP_USER", "")
ERP_PASSWORD = os.getenv("ERP_PASSWORD", "")
ERP_TOKEN    = os.getenv("ERP_TOKEN", "")         # si authentification par token


# ── Interface publique ────────────────────────────────────────────────────────

def chercher_of(numero_of: str) -> dict | None:
    """
    Retourne les informations d'un OF ou None si introuvable.

    Structure retournée :
    {
        "numero_of":       "OF-2026-001",
        "designation":     "Vis M6 inox",
        "reference_piece": "VS-M6-316L",
        "client":          "Client SA",
        "matiere":         "Inox 316L",
        "quantite":        500,
        "date_lancement":  "2026-08-01",
        "responsable":     "dupont",
        "source":          "erp" | "mock",
    }
    """
    if not numero_of or not numero_of.strip():
        return None

    numero_of = numero_of.strip().upper()

    if ERP_TYPE == "infor" and ERP_URL:
        return _fetch_infor(numero_of)
    elif ERP_TYPE == "sap" and ERP_URL:
        return _fetch_sap(numero_of)
    else:
        # Pas d'ERP configuré — données de démonstration
        return _mock_of(numero_of)


def erp_configure() -> bool:
    """Retourne True si un ERP est configuré."""
    return bool(ERP_TYPE and ERP_URL)


# ── Connecteurs ERP ───────────────────────────────────────────────────────────

def _fetch_infor(numero_of: str) -> dict | None:
    """
    Connecteur Infor LN / Infor M3 — à adapter selon votre version.
    Documentation API : https://docs.infor.com/
    """
    try:
        # Exemple endpoint Infor M3 (OIS300 / MWOPTR)
        endpoint = f"{ERP_URL}/M3/m3api-rest/v2/execute/OIS300/GetOrderInfo"
        headers = {
            "Authorization": f"Bearer {ERP_TOKEN}" if ERP_TOKEN else "",
            "Content-Type":  "application/json",
        }
        params = {"ORNO": numero_of}
        r = requests.get(endpoint, params=params, headers=headers, timeout=5,
                         auth=(ERP_USER, ERP_PASSWORD) if not ERP_TOKEN else None)
        r.raise_for_status()
        data = r.json()

        # ⚠️  Adapter le mapping selon la structure réelle de votre ERP
        return {
            "numero_of":       numero_of,
            "designation":     data.get("ITDS", ""),
            "reference_piece": data.get("ITNO", ""),
            "client":          data.get("CUNM", ""),
            "matiere":         data.get("MATE", ""),
            "quantite":        int(data.get("ORQT", 0)),
            "date_lancement":  data.get("PLDT", ""),
            "responsable":     data.get("RESP", ""),
            "source":          "infor",
        }
    except Exception as e:
        logger.warning("Infor ERP — OF %s : %s", numero_of, e)
        return None


def _fetch_sap(numero_of: str) -> dict | None:
    """
    Connecteur SAP — utilise l'OData API (PP/PI Production Orders).
    Documentation : https://api.sap.com/
    """
    try:
        # Exemple SAP S/4HANA OData
        endpoint = f"{ERP_URL}/sap/opu/odata/sap/API_PRODUCTION_ORDER_2_SRV/A_ProductionOrder('{numero_of}')"
        headers = {
            "Authorization": f"Bearer {ERP_TOKEN}" if ERP_TOKEN else "",
            "Accept":        "application/json",
        }
        r = requests.get(endpoint, headers=headers, timeout=5,
                         auth=(ERP_USER, ERP_PASSWORD) if not ERP_TOKEN else None)
        r.raise_for_status()
        data = r.json().get("d", {})

        # ⚠️  Adapter le mapping selon votre configuration SAP
        return {
            "numero_of":       numero_of,
            "designation":     data.get("ProductionOrderType", ""),
            "reference_piece": data.get("Material", ""),
            "client":          data.get("SalesOrder", ""),
            "matiere":         data.get("MaterialName", ""),
            "quantite":        int(data.get("TotalQuantity", 0)),
            "date_lancement":  data.get("PlannedStartDate", ""),
            "responsable":     data.get("ResponsiblePerson", ""),
            "source":          "sap",
        }
    except Exception as e:
        logger.warning("SAP ERP — OF %s : %s", numero_of, e)
        return None


def _mock_of(numero_of: str) -> dict:
    """Données de démonstration quand aucun ERP n'est configuré."""
    mocks = {
        "OF-2026-001": {
            "designation": "Vis M6 inox",
            "reference_piece": "VS-M6-316L",
            "client": "Client Démo SA",
            "matiere": "Inox 316L",
            "quantite": 500,
            "date_lancement": "2026-08-01",
            "responsable": "martin",
        },
        "OF-2026-002": {
            "designation": "Axe de transmission",
            "reference_piece": "AX-TR-42",
            "client": "Industrie Démo",
            "matiere": "Acier 42CrMo4",
            "quantite": 50,
            "date_lancement": "2026-07-15",
            "responsable": "dupont",
        },
    }
    base = mocks.get(numero_of, {
        "designation": f"Pièce {numero_of}",
        "reference_piece": numero_of,
        "client": "",
        "matiere": "",
        "quantite": 0,
        "date_lancement": "",
        "responsable": "",
    })
    return {"numero_of": numero_of, "source": "mock", **base}
