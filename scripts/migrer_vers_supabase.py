"""
Migration des references JSON locales vers Supabase.
Utilise l'API REST Supabase directement via requests (pas de client supabase).

Usage :
    python scripts/migrer_vers_supabase.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

try:
    import requests
except ImportError:
    print("ERREUR : pip install requests")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERREUR : SUPABASE_URL et SUPABASE_KEY doivent etre definis dans .env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

ENDPOINT = f"{SUPABASE_URL}/rest/v1/dossiers"


def upsert(categorie: str, code: str, metadata: dict, data: dict) -> bool:
    meta_clean = {k: v for k, v in metadata.items() if not k.startswith("_")}
    payload = {
        "categorie": categorie,
        "code": code,
        "metadata": meta_clean,
        "data": data,
    }
    r = requests.post(ENDPOINT, headers=HEADERS, json=payload, timeout=15)
    return r.status_code in (200, 201)


def migrer():
    from backend.category_manager import lister_categories
    categories = lister_categories()

    if not categories:
        print("ERREUR : Aucune categorie trouvee dans categories/")
        sys.exit(1)

    total_ok = total_err = 0

    for cat in categories:
        if not cat.references_dir.exists():
            continue

        print(f"\nCategorie : {cat.nom} ({cat.code})")

        for ref_path in sorted(cat.references_dir.glob("*/metadata.json")):
            code = ref_path.parent.name
            ref_dir = ref_path.parent

            try:
                metadata = json.loads(ref_path.read_text(encoding="utf-8"))
                data = {}
                for nom, fichier in [
                    ("amdec_produit",  "data/amdec_produit.json"),
                    ("amdec_process",  "data/amdec_process.json"),
                    ("gamme",          "data/gamme.json"),
                    ("plan_controle",  "data/plan_controle.json"),
                ]:
                    chemin = ref_dir / fichier
                    if chemin.exists():
                        data[nom] = json.loads(chemin.read_text(encoding="utf-8"))

                ok = upsert(cat.code, code, metadata, data)
                if ok:
                    print(f"  OK : {code}")
                    total_ok += 1
                else:
                    print(f"  ERREUR HTTP : {code}")
                    total_err += 1

            except Exception as e:
                print(f"  ERREUR : {code} -- {e}")
                total_err += 1

    print(f"\n{'='*40}")
    print(f"Migration terminee : {total_ok} OK  |  {total_err} erreur(s)")


if __name__ == "__main__":
    migrer()
