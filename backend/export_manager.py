"""
Gestion de la purge automatique des exports générés.

Le dossier exports/ peut grossir indéfiniment si aucune purge n'est faite.
Ce module supprime les fichiers exportés plus vieux que N jours (défaut : 30).
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "exports"

logger = logging.getLogger(__name__)


def purger_exports_anciens(jours: int = 30) -> list[Path]:
    """
    Supprime les fichiers du dossier exports/ plus vieux que `jours` jours.
    Retourne la liste des fichiers supprimés.
    """
    if not EXPORTS_DIR.exists():
        return []

    limite = datetime.now() - timedelta(days=jours)
    supprimes = []

    for fichier in EXPORTS_DIR.rglob("*"):
        if not fichier.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(fichier.stat().st_mtime)
        except OSError:
            continue
        if mtime < limite:
            try:
                fichier.unlink()
                supprimes.append(fichier)
                logger.info("Export purgé : %s", fichier)
            except OSError as exc:
                logger.warning("Impossible de supprimer %s : %s", fichier, exc)

    return supprimes
