"""
Gestion des sauvegardes automatiques de la base de références.

Sauvegarde quotidienne du dossier categories/ au démarrage de l'app.
Rétention : 30 jours glissants.
"""

import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from backend.export_manager import purger_exports_anciens

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES_DIR = ROOT / "categories"
BACKUP_ROOT = ROOT / "backups"

logger = logging.getLogger(__name__)


def _date_tag() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _backup_existe_aujourd_hui() -> bool:
    """Vérifie si une sauvegarde a déjà été faite aujourd'hui."""
    tag = _date_tag()
    backup_dir = BACKUP_ROOT / "auto" / tag
    # Considère comme faite si le dossier existe et contient au moins un fichier
    return backup_dir.exists() and any(backup_dir.rglob("*.json"))


def faire_sauvegarde(force: bool = False) -> Path | None:
    """
    Copie intégrale de categories/ dans backups/auto/YYYY-MM-DD/.
    Ne sauvegarde qu'une fois par jour sauf si force=True.
    Retourne le chemin du backup créé, ou None si saut.
    """
    if not force and _backup_existe_aujourd_hui():
        logger.info("Sauvegarde déjà effectuée aujourd'hui — saut.")
        return None

    tag = _date_tag()
    dest = BACKUP_ROOT / "auto" / tag

    if dest.exists():
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CATEGORIES_DIR, dest)
    logger.info("Sauvegarde automatique créée : %s", dest)
    return dest


def purger_anciennes_sauvegardes(retention_jours: int = 30) -> list[Path]:
    """
    Supprime les sauvegardes auto de plus de `retention_jours` jours.
    Retourne la liste des dossiers supprimés.
    """
    auto_dir = BACKUP_ROOT / "auto"
    if not auto_dir.exists():
        return []

    limite = datetime.now() - timedelta(days=retention_jours)
    supprimes = []

    for dossier in sorted(auto_dir.iterdir()):
        if not dossier.is_dir():
            continue
        try:
            date_backup = datetime.strptime(dossier.name, "%Y-%m-%d")
        except ValueError:
            continue
        if date_backup < limite:
            shutil.rmtree(dossier)
            supprimes.append(dossier)
            logger.info("Sauvegarde purgée : %s", dossier)

    return supprimes


def lister_sauvegardes() -> list[dict]:
    """
    Retourne la liste des sauvegardes disponibles, du plus récent au plus ancien.
    Chaque entrée : {"date": "YYYY-MM-DD", "chemin": Path, "taille_mo": float}
    """
    auto_dir = BACKUP_ROOT / "auto"
    if not auto_dir.exists():
        return []

    resultats = []
    for dossier in sorted(auto_dir.iterdir(), reverse=True):
        if not dossier.is_dir():
            continue
        try:
            datetime.strptime(dossier.name, "%Y-%m-%d")
        except ValueError:
            continue

        taille = sum(f.stat().st_size for f in dossier.rglob("*") if f.is_file())
        resultats.append({
            "date": dossier.name,
            "chemin": dossier,
            "taille_mo": round(taille / 1_048_576, 2),
        })

    return resultats


def restaurer_sauvegarde(date_str: str) -> bool:
    """
    Restaure la base categories/ depuis la sauvegarde du jour indiqué.
    Fait d'abord un backup de sécurité de l'état actuel.
    Retourne True si succès.
    """
    source = BACKUP_ROOT / "auto" / date_str
    if not source.exists():
        raise FileNotFoundError(f"Aucune sauvegarde trouvée pour {date_str}")

    # Sauvegarde de sécurité avant restauration
    securite = BACKUP_ROOT / "restauration" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if CATEGORIES_DIR.exists():
        shutil.copytree(CATEGORIES_DIR, securite)
        logger.info("Backup de sécurité avant restauration : %s", securite)

    # Restauration
    if CATEGORIES_DIR.exists():
        shutil.rmtree(CATEGORIES_DIR)
    shutil.copytree(source, CATEGORIES_DIR)
    logger.info("Base restaurée depuis : %s", source)
    return True


def demarrage_app() -> dict:
    """
    À appeler au démarrage de l'application Streamlit.
    Lance sauvegarde + purge et retourne un rapport.
    """
    rapport = {
        "sauvegarde_creee": None,
        "backup_purges": [],
        "exports_purges": [],
        "erreur": None,
    }
    try:
        chemin = faire_sauvegarde()
        rapport["sauvegarde_creee"] = str(chemin) if chemin else None
        rapport["backup_purges"] = [str(p) for p in purger_anciennes_sauvegardes(30)]
        rapport["exports_purges"] = [str(p) for p in purger_exports_anciens(30)]
    except Exception as exc:
        rapport["erreur"] = str(exc)
        logger.error("Erreur sauvegarde démarrage : %s", exc)
    return rapport
