"""
Script utilitaire — crée 4 références horlogères de démo dans la base.

Crée :
  - REF-GSS-032 : Glace sphérique saphir Ø32mm — Or + AR double face
  - REF-GBS-030 : Glace box saphir 30x30mm — Chrome clair + AR simple face
  - REF-GPS-036 : Glace plate saphir Ø36mm — AR double face uniquement
  - REF-GPS-040 : Glace plate saphir Ø40mm — AR double face uniquement
"""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = ROOT / "base_references"


def construire_amdec_produit(reference, designation, modes_specifiques):
    """Construit l'AMDEC Produit avec un socle commun + modes spécifiques au produit."""
    # Modes communs à toutes les glaces (géométrique, traçabilité)
    modes_communs = [
        {
            "no": "01", "famille": "geometrique",
            "fonction_exigence": "Conformité dimensionnelle",
            "caracteristique_critique": "Diamètre / dimensions",
            "mode_defaillance": "Cote hors tolérance",
            "effets_defaillance": "Impossibilité de montage / jeu excessif",
            "G": 9, "causes_defaillance": "Dérive machine usinage, usure outil",
            "O": 2, "controles_existants": "Mesure pied à coulisse digital 100% réception",
            "D": 2, "classe_criticite": "Action corrective",
            "actions_correctives": "SPC dimension lot entrant, certificat fournisseur obligatoire",
            "responsable": "BT Qualité", "delai": "J+7"
        },
        {
            "no": "02", "famille": "esthetique",
            "fonction_exigence": "Aspect surface",
            "caracteristique_critique": "Absence de rayures",
            "mode_defaillance": "Rayures post-traitement",
            "effets_defaillance": "Refus qualité, rebut pièce",
            "G": 7, "causes_defaillance": "Contact inadapté lors conditionnement / manutention",
            "O": 4, "controles_existants": "Inspection 100% sous éclairage rasant x20",
            "D": 2, "classe_criticite": "Action corrective",
            "actions_correctives": "Film protecteur individuel, poste de conditionnement dédié",
            "responsable": "Resp. Méthodes", "delai": "J+7"
        },
        {
            "no": "03", "famille": "esthetique",
            "fonction_exigence": "Intégrité bordure",
            "caracteristique_critique": "Absence d'éclats bordure",
            "mode_defaillance": "Éclats / microfissures en bordure",
            "effets_defaillance": "Risque blessure, étanchéité compromise",
            "G": 8, "causes_defaillance": "Choc lors manutention, usinage trop agressif matière brute",
            "O": 3, "controles_existants": "Inspection 100% bordure au microscope x50",
            "D": 2, "classe_criticite": "Action corrective",
            "actions_correctives": "Contrôle entrée matière + protocole manutention renforcé",
            "responsable": "BT Qualité", "delai": "J+15"
        },
        {
            "no": "04", "famille": "etancheite",
            "fonction_exigence": "Zone d'appui joint",
            "caracteristique_critique": "Planéité zone joint",
            "mode_defaillance": "Planéité zone joint hors tolérance",
            "effets_defaillance": "Fuite étanchéité montre, retour SAV",
            "G": 9, "causes_defaillance": "Contamination surface appui, défaut polissage",
            "O": 3, "controles_existants": "Mesure rugosimètre zone annulaire 100% lot",
            "D": 3, "classe_criticite": "Action corrective",
            "actions_correctives": "Contrôle dédié zone joint, nettoyage plasmatique avant mesure",
            "responsable": "BT Qualité", "delai": "J+15"
        },
        {
            "no": "05", "famille": "tracabilite",
            "fonction_exigence": "Identification produit",
            "caracteristique_critique": "Référence correcte",
            "mode_defaillance": "Confusion de référence",
            "effets_defaillance": "Livraison produit non-conforme, crise client",
            "G": 9, "causes_defaillance": "Mélange lots en production, étiquetage défaillant",
            "O": 2, "controles_existants": "Scan code-barres à chaque étape de production",
            "D": 2, "classe_criticite": "Action corrective",
            "actions_correctives": "Kanban physique + scan obligatoire avant conditionnement",
            "responsable": "Resp. Qualité", "delai": "J+7"
        },
    ]
    # Renuméroter les modes spécifiques
    for i, m in enumerate(modes_specifiques, start=6):
        m["no"] = f"{i:02d}"
    return {
        "reference": reference,
        "document": "AMDEC Produit",
        "designation": designation,
        "modes_defaillance": modes_communs + modes_specifiques,
    }


def construire_amdec_process(reference, designation, modes_specifiques):
    """AMDEC Process avec modes communs + modes spécifiques au process du produit."""
    modes_communs = [
        {
            "no": "01", "operation_process": "OP-10 Réception matière",
            "etape_poste": "Zone réception",
            "mode_defaillance": "Pièces non-conformes acceptées",
            "effets_produit": "Défaut propagé en production, rebut en aval",
            "G": 8, "causes_process": "Contrôle insuffisant, plan de contrôle incomplet",
            "O": 3, "controles_process": "Contrôle dimensionnel + visuel 100% réception",
            "D": 3, "classe_criticite": "Action corrective",
            "actions_correctives": "Renforcer plan de contrôle réception, certificat fournisseur obligatoire",
            "responsable": "BT Qualité", "delai": "J+15",
            "parametre_cle": "Dimensions + aspect", "valeur_cible": "Selon plan"
        },
        {
            "no": "02", "operation_process": "OP-30 Nettoyage ultrason",
            "etape_poste": "Cuve US",
            "mode_defaillance": "Nettoyage insuffisant",
            "effets_produit": "Contamination résiduelle → défaut adhérence couches",
            "G": 9, "causes_process": "Température bain incorrecte, durée cycle trop courte",
            "O": 4, "controles_process": "Inspection UV 365nm avant passage en salle blanche",
            "D": 2, "classe_criticite": "Action corrective",
            "actions_correctives": "Enregistrement auto température/durée, alarme dérive",
            "responsable": "Resp. Process", "delai": "J+7",
            "parametre_cle": "Température bain US", "valeur_cible": "50°C ± 5°C"
        },
        {
            "no": "03", "operation_process": "OP-100 Contrôle final",
            "etape_poste": "Table qualité",
            "mode_defaillance": "Défaut non détecté au contrôle final",
            "effets_produit": "Livraison pièce non-conforme au client",
            "G": 9, "causes_process": "Fatigue opérateur, éclairage inadapté, critères ambigus",
            "O": 3, "controles_process": "Inspection 100% selon gamme de contrôle + spectrophotomètre",
            "D": 3, "classe_criticite": "Action corrective",
            "actions_correctives": "Critères visuels illustrés (référentiels), rotation opérateurs 2h max",
            "responsable": "Resp. Qualité", "delai": "J+15",
            "parametre_cle": "Transmission optique", "valeur_cible": "≥ 92%"
        },
    ]
    for i, m in enumerate(modes_specifiques, start=4):
        m["no"] = f"{i:02d}"
    return {
        "reference": reference,
        "document": "AMDEC Process",
        "designation": designation,
        "modes_defaillance": modes_communs + modes_specifiques,
    }


def construire_gamme(reference, designation, operations_specifiques):
    """Gamme = opérations communes + opérations spécifiques au produit, dans l'ordre."""
    return {
        "reference": reference,
        "document": "Gamme de Production",
        "designation": designation,
        "operations": operations_specifiques,
    }


def op_reception(diametre):
    return {
        "no_op": "10", "designation": "Réception matière",
        "description_detaillee": "Contrôle visuel et dimensionnel entrant",
        "poste_machine": "Zone réception",
        "outillage_fixture": "Pied à coulisse digital + micromètre",
        "parametre_1": "Dimensions", "valeur_1": f"Ø{diametre} ±0.05mm",
        "parametre_2": "Aspect", "valeur_2": "Aucun défaut visible",
        "parametre_3": "—", "temps_min": 15,
        "point_controle": "Cotes + aspect", "moyen_controle": "Pied à coulisse + visuel",
        "frequence": "100%", "critere_acceptation": "Conforme plan + certificat",
        "ref_dit": "DIT-010", "ref_infor": "OP-10",
    }


def op_marquage():
    return {
        "no_op": "20", "designation": "Marquage traçabilité",
        "description_detaillee": "Attribution numéro de lot, marquage discret, enregistrement ERP",
        "poste_machine": "Bureau réception",
        "outillage_fixture": "Imprimante étiquettes code-barres",
        "parametre_1": "Format étiquette", "valeur_1": "REF + LOT + DATE",
        "parametre_2": "Lisibilité", "valeur_2": "Scan OK 100%",
        "parametre_3": "—", "temps_min": 10,
        "point_controle": "Traçabilité", "moyen_controle": "Scan code-barres",
        "frequence": "100%", "critere_acceptation": "Référence + lot + date corrects",
        "ref_dit": "DIT-020", "ref_infor": "OP-20",
    }


def op_nettoyage_us():
    return {
        "no_op": "30", "designation": "Nettoyage ultrason",
        "description_detaillee": "Nettoyage US avec détergent neutre avant dépôt sous vide",
        "poste_machine": "Cuve ultrason",
        "outillage_fixture": "Panier US inox anti-rayure",
        "parametre_1": "Température bain", "valeur_1": "50°C ± 5°C",
        "parametre_2": "Durée cycle", "valeur_2": "8 min ± 1 min",
        "parametre_3": "Fréquence US", "temps_min": 20,
        "point_controle": "Propreté surface", "moyen_controle": "Inspection UV 365nm",
        "frequence": "100%", "critere_acceptation": "Classe ≤ ISO 5",
        "ref_dit": "DIT-030", "ref_infor": "OP-30",
    }


def op_inspection_predepot():
    return {
        "no_op": "40", "designation": "Inspection pré-dépôt",
        "description_detaillee": "Contrôle visuel et propreté avant entrée salle blanche",
        "poste_machine": "Sas salle blanche",
        "outillage_fixture": "Microscope x10/x50 + éclairage rasant",
        "parametre_1": "Aspect surface", "valeur_1": "0 défaut > 0.05mm",
        "parametre_2": "Propreté", "valeur_2": "≤ ISO 5",
        "parametre_3": "—", "temps_min": 15,
        "point_controle": "Aspect + propreté", "moyen_controle": "Visuel x50 + UV",
        "frequence": "100%", "critere_acceptation": "0 rayure, 0 poussière, ≤ ISO 5",
        "ref_dit": "DIT-040", "ref_infor": "OP-40",
    }


def op_controle_final():
    return {
        "no_op": "100", "designation": "Contrôle final 100%",
        "description_detaillee": "Contrôle 100% tous critères avant libération lot",
        "poste_machine": "Table qualité éclairage rasant",
        "outillage_fixture": "Microscope x50 + spectrophotomètre",
        "parametre_1": "Transmission optique", "valeur_1": "≥ 92%",
        "parametre_2": "Réflexion AR", "valeur_2": "Selon spec",
        "parametre_3": "Aspect x50", "temps_min": 25,
        "point_controle": "Tous critères plan + spec", "moyen_controle": "Spectro + visuel x50",
        "frequence": "100%", "critere_acceptation": "Tous critères conformes",
        "ref_dit": "DIT-100", "ref_infor": "OP-100",
    }


def op_liberation_conditionnement():
    return [
        {
            "no_op": "110", "designation": "Libération lot",
            "description_detaillee": "Vérification dossier, signature libération, enregistrement ERP",
            "poste_machine": "Bureau qualité",
            "outillage_fixture": "Check-list + ERP Infor",
            "parametre_1": "Complétude dossier", "valeur_1": "100% rubriques OK",
            "parametre_2": "—", "valeur_2": "—",
            "parametre_3": "—", "temps_min": 10,
            "point_controle": "Dossier qualité", "moyen_controle": "Check-list signée",
            "frequence": "1/lot", "critere_acceptation": "Dossier complet + visa qualité",
            "ref_dit": "DIT-110", "ref_infor": "OP-110",
        },
        {
            "no_op": "120", "designation": "Conditionnement",
            "description_detaillee": "Emballage individuel film ESD + boîte rigide étiquetée",
            "poste_machine": "Poste emballage",
            "outillage_fixture": "Film ESD + boîte rigide",
            "parametre_1": "Film protecteur", "valeur_1": "ESD anti-rayure obligatoire",
            "parametre_2": "Étiquetage", "valeur_2": "REF + LOT + DATE + QTE",
            "parametre_3": "—", "temps_min": 10,
            "point_controle": "Étiquetage + traçabilité", "moyen_controle": "Vérif visuelle + scan",
            "frequence": "100%", "critere_acceptation": "Référence + lot corrects",
            "ref_dit": "DIT-120", "ref_infor": "OP-120",
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# DÉFINITION DES 4 RÉFÉRENCES
# ═══════════════════════════════════════════════════════════════════════════════

REFERENCES = [
    # ─── 1. Sphérique saphir Or + AR double face ─────────────────────────────
    {
        "reference": "REF-GSS-032",
        "designation": "Glace sphérique saphir Ø32mm — Or + AR double face",
        "type_produit": "glace_spherique",
        "matiere": "saphir",
        "traitements": ["metallisation_or", "antireflet_double_face"],
        "dimensions": {"diametre_mm": 32.0, "tolerance_diametre_mm": 0.05,
                       "epaisseur_mm": 1.5, "tolerance_epaisseur_mm": 0.03,
                       "rayon_courbure_mm": 15.0},
        "modes_p_specifiques": [
            {"famille": "geometrique", "fonction_exigence": "Forme sphérique",
             "caracteristique_critique": "Rayon de courbure",
             "mode_defaillance": "Rayon de courbure hors tolérance",
             "effets_defaillance": "Aspect optique non-conforme, distorsion image",
             "G": 8, "causes_defaillance": "Dérive process polissage sphérique fournisseur",
             "O": 3, "controles_existants": "Mesure profilomètre 3D zone centrale",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Contrôle profil 3D 100% réception, gabarit de référence",
             "responsable": "BT Qualité", "delai": "J+15"},
            {"famille": "optique", "fonction_exigence": "Métallisation décorative Or",
             "caracteristique_critique": "Couleur Or stable",
             "mode_defaillance": "Variation teinte Or (jaune → rosé)",
             "effets_defaillance": "Refus esthétique client, lots non-uniformes",
             "G": 7, "causes_defaillance": "Dérive composition cible Au, contamination chambre",
             "O": 4, "controles_existants": "Mesure colorimétrie L*a*b* 1/lot",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "SPC colorimétrie, étalonnage cible Au mensuel",
             "responsable": "Resp. Process", "delai": "J+15"},
            {"famille": "optique", "fonction_exigence": "Adhérence Or",
             "caracteristique_critique": "Tenue couche Or",
             "mode_defaillance": "Délaminage couche Or sur surface courbe",
             "effets_defaillance": "Décollement progressif, retour SAV",
             "G": 9, "causes_defaillance": "Mauvaise prépa surface zone courbe, tensions internes",
             "O": 3, "controles_existants": "Test adhérence cross-cut + thermal cycling",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Sous-couche d'accrochage Cr-NiCr avant Or, nettoyage plasma",
             "responsable": "Resp. Process", "delai": "J+30"},
            {"famille": "optique", "fonction_exigence": "Antireflet double face",
             "caracteristique_critique": "Réflexion résiduelle",
             "mode_defaillance": "Réflexion hors spec sur zone courbe",
             "effets_defaillance": "Reflet gênant en périphérie, non-conformité",
             "G": 8, "causes_defaillance": "Variation épaisseur AR liée à courbure",
             "O": 4, "controles_existants": "Mesure spectrophotomètre multi-zones",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Adapter géométrie porte-pièces, masque dynamique",
             "responsable": "Resp. Process", "delai": "J+30"},
        ],
        "modes_pr_specifiques": [
            {"operation_process": "OP-50 Métallisation Or",
             "etape_poste": "Évaporateur thermique Au",
             "mode_defaillance": "Épaisseur couche Or non-uniforme",
             "effets_produit": "Variation colorimétrique sur la pièce",
             "G": 7, "causes_process": "Géométrie sphérique → flux non uniforme",
             "O": 5, "controles_process": "Mesure 5 zones spectrophotomètre",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Porte-pièces rotatif planétaire, masque correction",
             "responsable": "Resp. Process", "delai": "J+15",
             "parametre_cle": "Vitesse rotation porte-pièces",
             "valeur_cible": "20 RPM ± 2"},
            {"operation_process": "OP-70 AR Face 1 sur courbe",
             "etape_poste": "Évaporateur PVD",
             "mode_defaillance": "Dépôt AR non-uniforme sur zone courbe",
             "effets_produit": "Iridescence visible en périphérie",
             "G": 7, "causes_process": "Angle d'incidence variable selon position pièce",
             "O": 4, "controles_process": "Spectro multi-points (centre + 4 périphérie)",
             "D": 3, "classe_criticite": "Surveillance",
             "actions_correctives": "Optimiser hauteur source, correction par calcul vectoriel",
             "responsable": "Resp. Process", "delai": "J+45",
             "parametre_cle": "Distance source-substrat",
             "valeur_cible": "350mm ± 10mm"},
        ],
        "operations_gamme_specifiques": [
            op_reception(32.0), op_marquage(), op_nettoyage_us(), op_inspection_predepot(),
            {"no_op": "45", "designation": "Activation plasma Ar",
             "description_detaillee": "Activation surface saphir par plasma Ar avant dépôt Or",
             "poste_machine": "Plasma cleaner",
             "outillage_fixture": "Support spécifique courbe",
             "parametre_1": "Puissance plasma", "valeur_1": "150W ± 10W",
             "parametre_2": "Durée", "valeur_2": "60s ± 5s",
             "parametre_3": "Pression Ar", "temps_min": 10,
             "point_controle": "Mouillage surface", "moyen_controle": "Test goutte d'eau",
             "frequence": "1/lot", "critere_acceptation": "Angle contact < 10°",
             "ref_dit": "DIT-045", "ref_infor": "OP-45"},
            {"no_op": "50", "designation": "Métallisation Or",
             "description_detaillee": "Dépôt couche Or 24K par évaporation thermique",
             "poste_machine": "Évaporateur thermique Au",
             "outillage_fixture": "Porte-pièces planétaire courbe",
             "parametre_1": "Épaisseur Or", "valeur_1": "120nm ± 10nm",
             "parametre_2": "Vitesse dépôt", "valeur_2": "5 Å/s",
             "parametre_3": "Vitesse rotation", "temps_min": 50,
             "point_controle": "Épaisseur + colorimétrie",
             "moyen_controle": "Profilomètre + spectro L*a*b*",
             "frequence": "1/lot",
             "critere_acceptation": "120nm ± 10nm, L* > 88, b* dans tolérance",
             "ref_dit": "DIT-050", "ref_infor": "OP-50"},
            {"no_op": "70", "designation": "Antireflet Face 1 PVD",
             "description_detaillee": "Dépôt AR multicouche face 1 adapté courbure",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 1 sphérique",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Distance source", "temps_min": 60,
             "point_controle": "Réflexion F1 multi-zones",
             "moyen_controle": "Spectrophotomètre 5 points",
             "frequence": "1/lot", "critere_acceptation": "R ≤ 0.2% à 550nm tous points",
             "ref_dit": "DIT-070", "ref_infor": "OP-70"},
            {"no_op": "80", "designation": "Retournement F1→F2",
             "description_detaillee": "Retournement délicat sur support concave adapté",
             "poste_machine": "Poste assemblage",
             "outillage_fixture": "Support concave Shore A 25",
             "parametre_1": "Dureté support", "valeur_1": "Shore A ≤ 30",
             "parametre_2": "Forme support", "valeur_2": "Concave R15 ± 1",
             "parametre_3": "—", "temps_min": 10,
             "point_controle": "Aspect F1 après retournement",
             "moyen_controle": "Inspection visuelle x20",
             "frequence": "100%", "critere_acceptation": "0 rayure, 0 contact métal",
             "ref_dit": "DIT-080", "ref_infor": "OP-80"},
            {"no_op": "90", "designation": "Antireflet Face 2 PVD",
             "description_detaillee": "Dépôt AR multicouche face 2 adapté courbure",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 2 sphérique",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Distance source", "temps_min": 60,
             "point_controle": "Réflexion F2 multi-zones",
             "moyen_controle": "Spectrophotomètre 5 points",
             "frequence": "1/lot", "critere_acceptation": "R ≤ 0.2% à 550nm tous points",
             "ref_dit": "DIT-090", "ref_infor": "OP-90"},
            op_controle_final(),
            *op_liberation_conditionnement(),
        ],
    },
    # ─── 2. Box saphir Chrome clair + AR simple face ─────────────────────────
    {
        "reference": "REF-GBS-030",
        "designation": "Glace box saphir 30x30mm — Chrome clair + AR simple face",
        "type_produit": "glace_box",
        "matiere": "saphir",
        "traitements": ["metallisation_chrome_clair", "antireflet_simple_face"],
        "dimensions": {"diametre_mm": 30.0, "tolerance_diametre_mm": 0.05,
                       "epaisseur_mm": 2.0, "tolerance_epaisseur_mm": 0.03,
                       "hauteur_box_mm": 1.2},
        "modes_p_specifiques": [
            {"famille": "geometrique", "fonction_exigence": "Forme box",
             "caracteristique_critique": "Hauteur de box (rebord surélevé)",
             "mode_defaillance": "Hauteur box hors tolérance",
             "effets_defaillance": "Problème montage boîtier, jeu visible",
             "G": 8, "causes_defaillance": "Dérive usinage zone surélevée",
             "O": 3, "controles_existants": "Mesure micromètre profondeur 4 angles",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "Contrôle 100% hauteur box réception, gabarit de mesure",
             "responsable": "BT Qualité", "delai": "J+15"},
            {"famille": "geometrique", "fonction_exigence": "Angles box",
             "caracteristique_critique": "Angularité 90°",
             "mode_defaillance": "Angles box non-conformes",
             "effets_defaillance": "Difficulté montage, étanchéité compromise aux coins",
             "G": 7, "causes_defaillance": "Usure outil usinage, bridage incorrect",
             "O": 4, "controles_existants": "Mesure projecteur de profil",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Contrôle systématique projecteur, plan SPC angularité",
             "responsable": "BT Qualité", "delai": "J+30"},
            {"famille": "esthetique", "fonction_exigence": "Décor Chrome clair",
             "caracteristique_critique": "Brillance Chrome",
             "mode_defaillance": "Manque de brillance / aspect terne",
             "effets_defaillance": "Refus esthétique, aspect bas de gamme",
             "G": 6, "causes_defaillance": "Cible Cr usée, vide insuffisant",
             "O": 4, "controles_existants": "Mesure brillancemètre + comparaison référence",
             "D": 3, "classe_criticite": "Surveillance",
             "actions_correctives": "Maintenance cible mensuelle, contrôle vide systématique",
             "responsable": "Resp. Process", "delai": "J+30"},
            {"famille": "esthetique", "fonction_exigence": "Tranches box",
             "caracteristique_critique": "Aspect tranches",
             "mode_defaillance": "Tranches mates au lieu de polies",
             "effets_defaillance": "Aspect non-conforme, refus esthétique",
             "G": 5, "causes_defaillance": "Polissage tranches insuffisant fournisseur",
             "O": 5, "controles_existants": "Inspection visuelle x20 tranches",
             "D": 2, "classe_criticite": "Surveillance",
             "actions_correctives": "Spec polissage tranches dans cahier des charges fournisseur",
             "responsable": "Achats", "delai": "J+45"},
        ],
        "modes_pr_specifiques": [
            {"operation_process": "OP-50 Métallisation Chrome clair",
             "etape_poste": "Sputtéring Cr",
             "mode_defaillance": "Couche Cr trop fine (manque brillance)",
             "effets_produit": "Aspect terne, brillance insuffisante",
             "G": 6, "causes_process": "Puissance cathode insuffisante, vitesse rotation trop élevée",
             "O": 4, "controles_process": "Profilomètre + brillancemètre",
             "D": 3, "classe_criticite": "Surveillance",
             "actions_correctives": "SPC épaisseur Cr, étalonnage brillancemètre",
             "responsable": "Resp. Process", "delai": "J+15",
             "parametre_cle": "Épaisseur Cr", "valeur_cible": "180nm ± 15nm"},
            {"operation_process": "OP-55 Bridage spécifique box",
             "etape_poste": "Salle blanche",
             "mode_defaillance": "Marques de bridage sur surface décor",
             "effets_produit": "Empreintes visibles après dépôt, rebut",
             "G": 7, "causes_process": "Outillage de bridage inadapté forme box",
             "O": 4, "controles_process": "Inspection visuelle x20 zones de contact",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "Bridage par les tranches (jamais sur faces décor)",
             "responsable": "Méthodes", "delai": "J+15",
             "parametre_cle": "Zone de bridage", "valeur_cible": "Tranches uniquement"},
        ],
        "operations_gamme_specifiques": [
            op_reception(30.0), op_marquage(), op_nettoyage_us(), op_inspection_predepot(),
            {"no_op": "50", "designation": "Métallisation Chrome clair",
             "description_detaillee": "Dépôt Chrome clair par sputtéring magnétron",
             "poste_machine": "Sputtéring ALS-450",
             "outillage_fixture": "Bridage par tranches box",
             "parametre_1": "Puissance cathode", "valeur_1": "X W ± 10W",
             "parametre_2": "Pression enceinte", "valeur_2": "≤ 5×10⁻⁶ mbar",
             "parametre_3": "Épaisseur Cr", "temps_min": 40,
             "point_controle": "Épaisseur + brillance",
             "moyen_controle": "Profilomètre + brillancemètre",
             "frequence": "1/lot", "critere_acceptation": "180nm ± 15nm, brillance > 80 GU",
             "ref_dit": "DIT-050", "ref_infor": "OP-50"},
            {"no_op": "60", "designation": "Contrôle post-Cr",
             "description_detaillee": "Contrôle aspect Chrome + brillance + dimensions box",
             "poste_machine": "Table contrôle salle blanche",
             "outillage_fixture": "Microscope x50 + brillancemètre",
             "parametre_1": "Brillance Chrome", "valeur_1": "≥ 80 GU à 60°",
             "parametre_2": "Aspect", "valeur_2": "0 défaut > 0.1mm",
             "parametre_3": "—", "temps_min": 20,
             "point_controle": "Aspect + brillance Chrome",
             "moyen_controle": "Visuel x50 + brillancemètre",
             "frequence": "100%", "critere_acceptation": "Brillance OK, 0 défaut visible",
             "ref_dit": "DIT-060", "ref_infor": "OP-60"},
            {"no_op": "70", "designation": "Antireflet face supérieure (simple face)",
             "description_detaillee": "Dépôt AR multicouche uniquement face dessus (face client)",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque protection face arrière",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Nb couches", "temps_min": 50,
             "point_controle": "Réflexion face sup",
             "moyen_controle": "Spectrophotomètre",
             "frequence": "1/lot", "critere_acceptation": "R ≤ 0.4% à 550nm",
             "ref_dit": "DIT-070", "ref_infor": "OP-70"},
            op_controle_final(),
            *op_liberation_conditionnement(),
        ],
    },
    # ─── 3. Plat saphir Ø36mm AR double face uniquement ──────────────────────
    {
        "reference": "REF-GPS-036",
        "designation": "Glace plate saphir Ø36mm — AR double face uniquement",
        "type_produit": "glace_ronde",
        "matiere": "saphir",
        "traitements": ["antireflet_double_face"],
        "dimensions": {"diametre_mm": 36.0, "tolerance_diametre_mm": 0.05,
                       "epaisseur_mm": 1.5, "tolerance_epaisseur_mm": 0.03},
        "modes_p_specifiques": [
            {"famille": "optique", "fonction_exigence": "Transmission optique",
             "caracteristique_critique": "Taux de transmission",
             "mode_defaillance": "Transmission insuffisante (< 92%)",
             "effets_defaillance": "Lisibilité cadran réduite",
             "G": 7, "causes_defaillance": "AR mal calibré, contamination surface",
             "O": 3, "controles_existants": "Mesure spectrophotomètre 100%",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "Contrôle systématique transmission, recalibrage AR mensuel",
             "responsable": "Resp. Qualité", "delai": "J+15"},
            {"famille": "optique", "fonction_exigence": "Antireflet double face",
             "caracteristique_critique": "Réflexion résiduelle",
             "mode_defaillance": "Réflexion hors spec (> 0.4%)",
             "effets_defaillance": "Reflet visible, refus client",
             "G": 8, "causes_defaillance": "Dérive paramètres dépôt PVD",
             "O": 3, "controles_existants": "Spectrophotomètre 1/lot",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "SPC épaisseur couches, étalonnage QCM mensuel",
             "responsable": "Resp. Process", "delai": "J+15"},
            {"famille": "optique", "fonction_exigence": "Adhérence AR",
             "caracteristique_critique": "Tenue couche AR",
             "mode_defaillance": "Délaminage couche AR",
             "effets_defaillance": "Aspect inacceptable, retour client",
             "G": 9, "causes_defaillance": "Mauvaise prépa surface saphir",
             "O": 3, "controles_existants": "Test cross-cut + thermal cycling",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Renforcer protocole nettoyage US, contrôle UV",
             "responsable": "Resp. Process", "delai": "J+30"},
        ],
        "modes_pr_specifiques": [
            {"operation_process": "OP-70 AR Face 1 PVD",
             "etape_poste": "Évaporateur PVD",
             "mode_defaillance": "Délaminage AR Face 1",
             "effets_produit": "Réflexion hors spec, refus contrôle final",
             "G": 9, "causes_process": "Contamination surface, vide insuffisant",
             "O": 3, "controles_process": "Cross-cut + spectrophotomètre",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "Vérification vide avant lancement, nettoyage US strict",
             "responsable": "Resp. Qualité", "delai": "J+7",
             "parametre_cle": "Propreté surface", "valeur_cible": "≤ ISO 5"},
            {"operation_process": "OP-80 Retournement F1→F2",
             "etape_poste": "Poste assemblage",
             "mode_defaillance": "Rayure Face 1 lors retournement",
             "effets_produit": "Refus contrôle final, rebut pièce traitée",
             "G": 7, "causes_process": "Support inadapté",
             "O": 5, "controles_process": "Inspection visuelle x20 100%",
             "D": 4, "classe_criticite": "Action corrective",
             "actions_correctives": "Support Shore A ≤ 30, gabarit dédié",
             "responsable": "Méthodes", "delai": "J+30",
             "parametre_cle": "Dureté support", "valeur_cible": "Shore A ≤ 30"},
        ],
        "operations_gamme_specifiques": [
            op_reception(36.0), op_marquage(), op_nettoyage_us(), op_inspection_predepot(),
            {"no_op": "70", "designation": "Antireflet Face 1 PVD",
             "description_detaillee": "Dépôt AR multicouche face 1",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 1",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Nb couches", "temps_min": 60,
             "point_controle": "Réflexion F1", "moyen_controle": "Spectrophotomètre",
             "frequence": "1/lot", "critere_acceptation": "R ≤ 0.2% à 550nm",
             "ref_dit": "DIT-070", "ref_infor": "OP-70"},
            {"no_op": "80", "designation": "Retournement F1→F2",
             "description_detaillee": "Retournement délicat sans rayure",
             "poste_machine": "Poste assemblage",
             "outillage_fixture": "Support souple Shore A ≤ 30",
             "parametre_1": "Dureté support", "valeur_1": "Shore A ≤ 30",
             "parametre_2": "—", "valeur_2": "—",
             "parametre_3": "—", "temps_min": 10,
             "point_controle": "Aspect F1", "moyen_controle": "Visuel x20",
             "frequence": "100%", "critere_acceptation": "0 rayure",
             "ref_dit": "DIT-080", "ref_infor": "OP-80"},
            {"no_op": "90", "designation": "Antireflet Face 2 PVD",
             "description_detaillee": "Dépôt AR multicouche face 2",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 2",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Nb couches", "temps_min": 60,
             "point_controle": "Réflexion F2", "moyen_controle": "Spectrophotomètre",
             "frequence": "1/lot", "critere_acceptation": "R ≤ 0.2% à 550nm",
             "ref_dit": "DIT-090", "ref_infor": "OP-90"},
            op_controle_final(),
            *op_liberation_conditionnement(),
        ],
    },
    # ─── 4. Plat saphir Ø40mm AR double face uniquement ──────────────────────
    {
        "reference": "REF-GPS-040",
        "designation": "Glace plate saphir Ø40mm — AR double face uniquement",
        "type_produit": "glace_ronde",
        "matiere": "saphir",
        "traitements": ["antireflet_double_face"],
        "dimensions": {"diametre_mm": 40.0, "tolerance_diametre_mm": 0.05,
                       "epaisseur_mm": 1.8, "tolerance_epaisseur_mm": 0.03},
        "modes_p_specifiques": [
            {"famille": "optique", "fonction_exigence": "Transmission optique",
             "caracteristique_critique": "Taux de transmission",
             "mode_defaillance": "Transmission insuffisante (< 92%)",
             "effets_defaillance": "Lisibilité cadran réduite",
             "G": 7, "causes_defaillance": "AR mal calibré sur grand diamètre",
             "O": 4, "controles_existants": "Mesure spectrophotomètre multi-zones",
             "D": 2, "classe_criticite": "Action corrective",
             "actions_correctives": "SPC transmission, calibration multi-zones",
             "responsable": "Resp. Qualité", "delai": "J+15"},
            {"famille": "optique", "fonction_exigence": "Uniformité AR",
             "caracteristique_critique": "Uniformité couche sur grand Ø",
             "mode_defaillance": "Variation épaisseur centre/bord",
             "effets_defaillance": "Effet arc-en-ciel visible en bordure",
             "G": 6, "causes_defaillance": "Géométrie source/substrat inadaptée Ø40",
             "O": 5, "controles_existants": "Inspection sous lumière blanche diffuse",
             "D": 3, "classe_criticite": "Surveillance",
             "actions_correctives": "Optimiser hauteur source pour grand Ø, masque correction",
             "responsable": "Resp. Process", "delai": "J+45"},
            {"famille": "geometrique", "fonction_exigence": "Planéité",
             "caracteristique_critique": "Planéité grand diamètre",
             "mode_defaillance": "Planéité hors tolérance (Ø40 plus sensible)",
             "effets_defaillance": "Problème montage boîtier, contraintes",
             "G": 7, "causes_defaillance": "Contrainte interne matière sur grand Ø",
             "O": 4, "controles_existants": "Mesure marbre + comparateur",
             "D": 3, "classe_criticite": "Action corrective",
             "actions_correctives": "Plan SPC planéité 100% Ø ≥ 38mm",
             "responsable": "BT Qualité", "delai": "J+15"},
        ],
        "modes_pr_specifiques": [
            {"operation_process": "OP-70 AR Face 1 PVD grand Ø",
             "etape_poste": "Évaporateur PVD",
             "mode_defaillance": "AR non-uniforme centre/bord",
             "effets_produit": "Iridescence en bordure",
             "G": 6, "causes_process": "Distance source insuffisante pour Ø40",
             "O": 5, "controles_process": "Spectro 5 points (centre + 4 périphérie)",
             "D": 3, "classe_criticite": "Surveillance",
             "actions_correctives": "Augmenter distance source, masque correction",
             "responsable": "Resp. Process", "delai": "J+45",
             "parametre_cle": "Distance source-substrat",
             "valeur_cible": "400mm ± 10mm (vs 350 standard)"},
            {"operation_process": "OP-80 Retournement Ø40",
             "etape_poste": "Poste assemblage",
             "mode_defaillance": "Rayure Face 1 (surface plus grande)",
             "effets_produit": "Refus contrôle final, perte valeur",
             "G": 7, "causes_process": "Support standard inadapté grand Ø",
             "O": 5, "controles_process": "Inspection x20 100%",
             "D": 4, "classe_criticite": "Action corrective",
             "actions_correctives": "Support spécifique Ø40, manipulation deux opérateurs",
             "responsable": "Méthodes", "delai": "J+30",
             "parametre_cle": "Diamètre support", "valeur_cible": "Ø40 ± 1mm"},
        ],
        "operations_gamme_specifiques": [
            op_reception(40.0), op_marquage(), op_nettoyage_us(), op_inspection_predepot(),
            {"no_op": "70", "designation": "Antireflet Face 1 PVD",
             "description_detaillee": "Dépôt AR multicouche face 1 — paramètres adaptés Ø40",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 1 grand Ø",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Distance source", "temps_min": 70,
             "point_controle": "Réflexion F1 multi-zones",
             "moyen_controle": "Spectro 5 points", "frequence": "1/lot",
             "critere_acceptation": "R ≤ 0.2% tous points à 550nm",
             "ref_dit": "DIT-070", "ref_infor": "OP-70"},
            {"no_op": "80", "designation": "Retournement F1→F2",
             "description_detaillee": "Retournement avec support spécifique Ø40",
             "poste_machine": "Poste assemblage",
             "outillage_fixture": "Support souple Ø40 Shore A 25",
             "parametre_1": "Dureté support", "valeur_1": "Shore A ≤ 30",
             "parametre_2": "Diamètre support", "valeur_2": "Ø40 ± 1mm",
             "parametre_3": "—", "temps_min": 12,
             "point_controle": "Aspect F1", "moyen_controle": "Visuel x20",
             "frequence": "100%", "critere_acceptation": "0 rayure",
             "ref_dit": "DIT-080", "ref_infor": "OP-80"},
            {"no_op": "90", "designation": "Antireflet Face 2 PVD",
             "description_detaillee": "Dépôt AR multicouche face 2 — paramètres adaptés Ø40",
             "poste_machine": "Évaporateur thermique PVD",
             "outillage_fixture": "Masque face 2 grand Ø",
             "parametre_1": "Couche SiO2", "valeur_1": "λ/4 ± 2nm",
             "parametre_2": "Couche TiO2", "valeur_2": "λ/4 ± 2nm",
             "parametre_3": "Distance source", "temps_min": 70,
             "point_controle": "Réflexion F2 multi-zones",
             "moyen_controle": "Spectro 5 points", "frequence": "1/lot",
             "critere_acceptation": "R ≤ 0.2% tous points à 550nm",
             "ref_dit": "DIT-090", "ref_infor": "OP-90"},
            op_controle_final(),
            *op_liberation_conditionnement(),
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# CRÉATION DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════

def creer_reference(spec):
    code = spec["reference"]
    designation = spec["designation"]
    ref_dir = BASE / code
    data_dir = ref_dir / "data"
    ref_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # metadata.json
    metadata = {
        "reference": code,
        "designation": designation,
        "type_produit": spec["type_produit"],
        "matiere": spec["matiere"],
        "traitements": spec["traitements"],
        "dimensions": spec["dimensions"],
        "documents": {
            "AMDEC_produit": "data/amdec_produit.json",
            "AMDEC_process": "data/amdec_process.json",
            "gamme": "data/gamme.json",
        },
        "infor_reference": None,
        "date_creation": date.today().isoformat(),
        "statut": "valide",
        "redige_par": "Bureau Technique",
        "approuve_par": None,
        "indice_revision": "A",
    }
    (ref_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # AMDEC Produit
    amdec_p = construire_amdec_produit(code, designation, spec["modes_p_specifiques"])
    (data_dir / "amdec_produit.json").write_text(
        json.dumps(amdec_p, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # AMDEC Process
    amdec_pr = construire_amdec_process(code, designation, spec["modes_pr_specifiques"])
    (data_dir / "amdec_process.json").write_text(
        json.dumps(amdec_pr, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Gamme
    gamme = construire_gamme(code, designation, spec["operations_gamme_specifiques"])
    (data_dir / "gamme.json").write_text(
        json.dumps(gamme, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return code, len(amdec_p["modes_defaillance"]), len(amdec_pr["modes_defaillance"]), len(gamme["operations"])


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Creation des references de demo...\n")
    for spec in REFERENCES:
        code, n_p, n_pr, n_op = creer_reference(spec)
        print(f"  [OK] {code} : {n_p} modes produit | {n_pr} modes process | {n_op} operations")
    print(f"\n{len(REFERENCES)} references creees dans {BASE}")
