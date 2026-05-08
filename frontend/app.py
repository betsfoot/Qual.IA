"""
Interface Streamlit — Qual.IA
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from backend.config import get_secret
from backend.similarity_engine import brief_depuis_formulaire, trouver_meilleure_reference
from backend.document_generator import generer_dossier_complet, generer_dossier_variantes
from backend.reference_manager import (
    lister_references,
    charger_reference_complete,
    supprimer_reference,
    sauvegarder_modifications,
    calculer_stats,
)
from backend.category_manager import lister_categories, categorie_par_defaut, charger_categorie
from backend.backup_manager import demarrage_app, lister_sauvegardes, restaurer_sauvegarde, faire_sauvegarde
from backend.notification_manager import ajouter_notification, lire_notifications, marquer_lues
from backend.workflow_manager import (
    initialiser_workflow, faire_transition, lire_workflow,
    actions_disponibles, prochaine_gate, label_statut, label_action,
    STATUTS, calculer_ipr_max, calculer_gates_requises, role_pour_gate,
)
from backend.auth_manager import (
    verifier_credentials, ROLES,
    peut_valider_gate, peut_soumettre, peut_demander_corrections, peut_liberer,
    lister_utilisateurs, creer_utilisateur, supprimer_utilisateur, changer_mot_de_passe,
)
from backend.dit_manager import (
    lister_dits, charger_dit, sauvegarder_dit, supprimer_dit,
    dit_existe, nouveau_dit, generer_dit_ia,
)
from backend.pdf_exporter import exporter_dossier_pdf
from backend.typologie_manager import (
    charger_typologies, sauvegarder_typologies, lister_typologies,
    creer_ou_maj_typologie, supprimer_typologie, format_traitements_str,
)

st.set_page_config(
    page_title="Qual.IA",
    page_icon="⌚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Authentification ─────────────────────────────────────────────────────────

if "user" not in st.session_state:
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("# ⌚ Qual.IA")
        st.markdown("**Connectez-vous pour accéder à l'application.**")
        st.divider()
        _username = st.text_input("Identifiant", placeholder="admin")
        _password = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", type="primary", use_container_width=True):
            _result = verifier_credentials(_username.strip(), _password)
            if _result:
                st.session_state["user"] = _result
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
        st.divider()
        st.caption("Contactez votre administrateur si vous avez oublié vos identifiants.")
    st.stop()

user = st.session_state["user"]

# ─── Sauvegarde automatique au démarrage (une fois par jour) ─────────────────
if "backup_demarrage_fait" not in st.session_state:
    rapport_backup = demarrage_app()
    st.session_state["backup_demarrage_fait"] = True
    st.session_state["rapport_backup"] = rapport_backup

# ─── Sidebar — Catégorie + Navigation ────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⌚ Qual.IA")
    st.caption("MVP v1.1 — multi-catégories")
    st.divider()

    # ── Utilisateur connecté ──
    role_label = ROLES.get(user["role"], {}).get("label", user["role"])
    st.markdown(f"👤 **{user['nom']}**")
    st.caption(f"Rôle : {role_label}")
    if st.button("Déconnexion", use_container_width=True, key="logout_btn"):
        del st.session_state["user"]
        st.rerun()

    with st.expander("🔑 Changer mon mot de passe"):
        mdp_actuel  = st.text_input("Mot de passe actuel", type="password", key="chg_mdp_actuel")
        mdp_nouveau = st.text_input("Nouveau mot de passe", type="password", key="chg_mdp_nouveau")
        mdp_confirm = st.text_input("Confirmer", type="password", key="chg_mdp_confirm")
        if st.button("Mettre à jour", key="btn_chg_mdp"):
            if not verifier_credentials(user["username"], mdp_actuel):
                st.error("Mot de passe actuel incorrect.")
            elif len(mdp_nouveau) < 8:
                st.error("Minimum 8 caractères.")
            elif mdp_nouveau != mdp_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                try:
                    changer_mot_de_passe(user["username"], mdp_nouveau)
                    st.success("Mot de passe mis à jour.")
                except Exception as e:
                    st.error(str(e))
    st.divider()

    # ── Sélecteur de catégorie métier ──
    categories_disponibles = lister_categories()
    if not categories_disponibles:
        st.error("Aucune catégorie n'est définie. Crée au moins une catégorie dans `categories/`.")
        st.stop()

    st.markdown("**🏷️ Catégorie active**")
    code_par_defaut = st.session_state.get("categorie_active", categories_disponibles[0].code)
    codes_options = [c.code for c in categories_disponibles]
    try:
        idx_default = codes_options.index(code_par_defaut)
    except ValueError:
        idx_default = 0
    cat_code_selectionne = st.selectbox(
        "Catégorie",
        options=codes_options,
        index=idx_default,
        format_func=lambda c: next((f"{cat.icone} {cat.nom}" for cat in categories_disponibles if cat.code == c), c),
        label_visibility="collapsed",
    )

    # Reset de la session si la catégorie change
    if st.session_state.get("categorie_active") != cat_code_selectionne:
        st.session_state["categorie_active"] = cat_code_selectionne
        st.session_state["resultat_similarite"] = None
        st.session_state["brief"] = None
        st.session_state["dossier_genere"] = None

    categorie_active = charger_categorie(cat_code_selectionne)
    st.caption(categorie_active.description)

    st.divider()

    # ── Badge notifications ──
    _notifs_non_lues = lire_notifications(user["role"])
    _nb_notifs = len(_notifs_non_lues)
    if _nb_notifs > 0:
        st.markdown(f"🔔 **{_nb_notifs} notification(s) non lue(s)**")

    pages_disponibles = ["🏭 Nouveau produit", "📥 Importer un Excel", "📋 Workflow", "🔔 Notifications", "📚 Gestion de la base", "🔧 Retouches"]
    if user["role"] == "admin":
        pages_disponibles.append("🎨 Typologies")
        pages_disponibles.append("👥 Utilisateurs")

    # Navigation programmatique depuis le workflow (goto_page posé par un bouton de carte)
    if st.session_state.get("goto_page") in pages_disponibles:
        st.session_state["nav_page"] = st.session_state.pop("goto_page")

    page = st.radio(
        "Navigation",
        options=pages_disponibles,
        label_visibility="collapsed",
        key="nav_page",
    )

    st.divider()
    refs = lister_references(categorie_active)
    st.metric(f"Références — {categorie_active.nom}", len(refs))
    for r in refs[:8]:
        st.caption(f"`{r['reference']}` — {r.get('designation', '')[:40]}…")
    if len(refs) > 8:
        st.caption(f"… et {len(refs) - 8} autres")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 : GESTION DE LA BASE — rendue en premier puis st.stop() si sélectionnée
# ═════════════════════════════════════════════════════════════════════════════

if page == "📥 Importer un Excel":
    import pandas as pd
    from scripts.importer_excel import (
        COLONNES_AMDEC_PRODUIT, COLONNES_AMDEC_PROCESS, COLONNES_GAMME,
        _mapper_colonnes_auto, _appliquer_mapping, _detecter_ligne_header,
    )
    from backend.reference_saver import proposer_code_reference, enregistrer_reference, reference_existe

    st.title(f"📥 Importer un fichier Excel — {categorie_active.icone} {categorie_active.nom}")
    st.caption("Importe les AMDEC et Gamme d'un client directement depuis leur fichier Excel.")

    st.divider()

    # ── Étape 1 : Upload ──
    st.subheader("① Choisir le fichier Excel")
    fichier = st.file_uploader("Glisser-déposer ou parcourir", type=["xlsx", "xls"])

    if fichier is not None:
        import openpyxl
        wb = openpyxl.load_workbook(fichier, data_only=True)
        sheets = wb.sheetnames
        st.success(f"Fichier chargé : **{fichier.name}** — {len(sheets)} onglet(s) : {', '.join(sheets)}")

        st.divider()

        # ── Étape 2 : Identifier les onglets ──
        st.subheader("② Identifier les onglets")
        st.caption("Indique quel onglet contient chaque document.")

        options_sheets = ["— Aucun —"] + sheets

        def _auto_detect(mots):
            for s in sheets:
                for m in mots:
                    if m.lower() in s.lower():
                        return s
            return "— Aucun —"

        col1, col2, col3 = st.columns(3)
        with col1:
            sheet_ap = st.selectbox("AMDEC Produit",  options_sheets,
                index=options_sheets.index(_auto_detect(["produit", "ap", "amdec p"])))
        with col2:
            sheet_apr = st.selectbox("AMDEC Process", options_sheets,
                index=options_sheets.index(_auto_detect(["process", "apr", "amdec pr"])))
        with col3:
            sheet_g = st.selectbox("Gamme", options_sheets,
                index=options_sheets.index(_auto_detect(["gamme", "production", "game"])))

        st.divider()

        # ── Étape 3 : Aperçu + mapping colonnes ──
        st.subheader("③ Vérifier le mapping des colonnes")

        mapping_final = {}
        lignes_finales = {}

        for doc_type, sheet_name, colonnes_cibles, cle in [
            ("AMDEC Produit",  sheet_ap,  COLONNES_AMDEC_PRODUIT,  "amdec_produit"),
            ("AMDEC Process",  sheet_apr, COLONNES_AMDEC_PROCESS,  "amdec_process"),
            ("Gamme",          sheet_g,   COLONNES_GAMME,          "gamme"),
        ]:
            if sheet_name == "— Aucun —":
                lignes_finales[cle] = []
                continue

            ws = wb[sheet_name]
            ligne_h = _detecter_ligne_header(ws)
            data = list(ws.values)
            if len(data) <= ligne_h:
                st.warning(f"{doc_type} : onglet vide.")
                lignes_finales[cle] = []
                continue

            headers = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(data[ligne_h - 1])]
            rows = data[ligne_h:]
            df = pd.DataFrame(rows, columns=headers).dropna(how="all")

            colonnes_excel = [c for c in df.columns if c and not str(c).startswith("col_")]
            auto = _mapper_colonnes_auto(colonnes_excel, colonnes_cibles)

            with st.expander(f"**{doc_type}** — {len(df)} lignes détectées ({sheet_name})", expanded=True):
                st.caption("Vérifie et corrige le mapping si besoin.")
                cols_display = st.columns(2)
                mapping_corr = {}
                for i, cible in enumerate(colonnes_cibles):
                    col_widget = cols_display[i % 2]
                    options_col = ["— Ignorer —"] + colonnes_excel
                    val_auto = auto.get(cible, "— Ignorer —")
                    idx_auto = options_col.index(val_auto) if val_auto in options_col else 0
                    choix = col_widget.selectbox(
                        f"`{cible}`",
                        options_col,
                        index=idx_auto,
                        key=f"map_{cle}_{cible}",
                    )
                    if choix != "— Ignorer —":
                        mapping_corr[cible] = choix

                mapping_final[cle] = mapping_corr
                lignes = _appliquer_mapping(df, mapping_corr, colonnes_cibles)
                lignes_finales[cle] = lignes
                st.caption(f"→ {len(lignes)} lignes prêtes à importer")

                if lignes:
                    st.dataframe(pd.DataFrame(lignes[:5]), use_container_width=True, hide_index=True)

        st.divider()

        # ── Étape 4 : Métadonnées ──
        st.subheader("④ Informations sur la référence")

        vocab = categorie_active.vocabulaire()
        type_labels = vocab.get("types_produit", {})
        matiere_labels = vocab.get("matieres", {})
        traitements_dispo = vocab.get("traitements", {})

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            designation = st.text_input("Désignation complète *", placeholder="Ex: Glace ronde saphir Ø34mm CN+AR")
            type_produit = st.selectbox("Type produit", list(type_labels.keys()),
                format_func=lambda x: type_labels.get(x, x)) if type_labels else st.text_input("Type produit")
            matiere = st.selectbox("Matière", list(matiere_labels.keys()),
                format_func=lambda x: matiere_labels.get(x, x)) if matiere_labels else st.text_input("Matière")
            traitements = st.multiselect("Traitements", list(traitements_dispo.keys()),
                format_func=lambda x: traitements_dispo.get(x, x)) if traitements_dispo else []

        with col_m2:
            params_num_imp = categorie_active.parametres_numeriques()
            valeurs_dim_imp = {}
            tolerances_dim_imp = {}
            for p in params_num_imp:
                cle = p["cle"]
                label = p["label"]
                obligatoire = p.get("obligatoire", True)
                p_min = float(p.get("min", 0.0))
                p_max = float(p.get("max", 1000.0))
                tol_default = float(p.get("tolerance_default", 0.05))
                suffix = " *" if obligatoire else " — 0 si inconnu"
                valeurs_dim_imp[cle] = st.number_input(
                    f"{label}{suffix}",
                    min_value=0.0 if not obligatoire else p_min,
                    max_value=p_max,
                    value=p_min if obligatoire else 0.0,
                    step=float(p.get("step", 0.1)),
                    format=p.get("format", "%.2f"),
                    key=f"imp_dim_{cle}_{cat_code_selectionne}",
                )
                tolerances_dim_imp[cle] = st.number_input(
                    f"Tolérance {label} (±)",
                    min_value=0.001, max_value=50.0,
                    value=tol_default, step=0.001, format="%.3f",
                    key=f"imp_tol_{cle}_{cat_code_selectionne}",
                )
            statut = st.selectbox("Statut", ["valide", "brouillon"],
                format_func=lambda x: {"valide": "✅ Validé", "brouillon": "📝 Brouillon"}[x])
            approuve_par = st.text_input("Approuvé par", placeholder="Nom du valideur")

        dims_imp = {}
        for p in params_num_imp:
            cle = p["cle"]
            v = valeurs_dim_imp[cle]
            dims_imp[cle] = v if (p.get("obligatoire", True) or v > 0) else None
            dims_imp[f"tolerance_{cle}"] = tolerances_dim_imp[cle]

        brief_import = {
            "type_produit": type_produit if isinstance(type_produit, str) else list(type_labels.keys())[0],
            "matiere": matiere if isinstance(matiere, str) else list(matiere_labels.keys())[0],
            "traitements": traitements,
            "dimensions": dims_imp,
            "designation_client": designation,
            "exigences_speciales": "",
        }

        code_propose = proposer_code_reference(categorie_active, brief_import)
        code_ref = st.text_input("Code de référence", value=code_propose,
            help="Modifiable — format conseillé : REF-XXX-NNN")

        if reference_existe(categorie_active, code_ref):
            st.warning(f"La référence `{code_ref}` existe déjà.")
            overwrite = st.checkbox("Écraser la référence existante")
        else:
            overwrite = False

        st.divider()

        # ── Étape 5 : Import ──
        st.subheader("⑤ Lancer l'import")

        total_lignes = sum(len(v) for v in lignes_finales.values())
        st.info(f"Prêt à importer : **{len(lignes_finales.get('amdec_produit',[]))}** modes AMDEC Produit · "
                f"**{len(lignes_finales.get('amdec_process',[]))}** modes AMDEC Process · "
                f"**{len(lignes_finales.get('gamme',[]))}** opérations Gamme")

        if st.button("📥 Importer dans la base", type="primary", use_container_width=True,
                     disabled=not designation):
            dossier_import = {
                "amdec_produit": {
                    "reference": code_ref, "document": "AMDEC Produit",
                    "designation": designation,
                    "modes_defaillance": lignes_finales.get("amdec_produit", []),
                    "confiance_globale": 1.0,
                    "avertissements_generateur": ["Importé depuis Excel client"],
                },
                "amdec_process": {
                    "reference": code_ref, "document": "AMDEC Process",
                    "designation": designation,
                    "modes_defaillance": lignes_finales.get("amdec_process", []),
                    "confiance_globale": 1.0,
                    "avertissements_generateur": ["Importé depuis Excel client"],
                },
                "gamme": {
                    "reference": code_ref, "document": "Gamme de Production",
                    "designation": designation,
                    "operations": lignes_finales.get("gamme", []),
                    "confiance_globale": 1.0,
                    "avertissements_generateur": ["Importé depuis Excel client"],
                },
                "metadonnees_generation": {
                    "reference_source": "import_excel",
                    "score_similarite": 1.0,
                    "mode_generation": "import",
                },
            }
            try:
                ref_dir = enregistrer_reference(
                    categorie=categorie_active, code=code_ref,
                    brief=brief_import, dossier=dossier_import,
                    acteur=user["nom"],
                    commentaire_creation=f"Import Excel — fichier client",
                    overwrite=overwrite,
                )
                st.success(
                    f"✅ Référence **{code_ref}** importée — workflow initialisé en brouillon. "
                    f"Va dans **📋 Workflow** pour la soumettre à validation."
                )
            except FileExistsError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.stop()

if page == "📋 Workflow":
    role_user = user["role"]
    nom_user = user["nom"]

    st.title("📋 Suivi du workflow qualité")
    st.caption(
        f"Connecté en tant que **{nom_user}** — "
        f"{ROLES.get(role_user, {}).get('label', role_user)}"
    )
    st.divider()

    toutes_refs = lister_references(categorie_active)
    if not toutes_refs:
        st.info("Aucune référence dans cette catégorie.")
        st.stop()

    def _statut_ref(r: dict) -> str:
        return r.get("workflow", {}).get("statut", r.get("statut", "brouillon"))

    refs_a_soumettre  = [r for r in toutes_refs if _statut_ref(r) in ("brouillon", "corrections")]
    refs_en_validation = [r for r in toutes_refs if _statut_ref(r) == "en_revue"]
    refs_termines      = [r for r in toutes_refs if _statut_ref(r) in ("approuve", "libere", "obsolete")]

    # ── Compteurs rapides ──────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📝 À soumettre",   len(refs_a_soumettre))
    m2.metric("👁️ En validation", len(refs_en_validation))
    m3.metric("✅ Terminés",       len(refs_termines))
    attente_moi = sum(
        1 for r in refs_en_validation
        if peut_valider_gate(
            role_user,
            next((g for g in r.get("workflow", {}).get("gates_requises", [])
                  if g not in r.get("workflow", {}).get("gates_completees", [])), ""),
        )
    )
    m4.metric("✋ En attente de vous", attente_moi)

    st.divider()

    # ── Vue Kanban 3 colonnes ─────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown(f"### 📝 À soumettre ({len(refs_a_soumettre)})")
        if not refs_a_soumettre:
            st.caption("Aucun dossier.")
        for r in refs_a_soumettre:
            wf = r.get("workflow", {})
            statut = _statut_ref(r)
            last = (wf.get("historique") or [{}])[-1]
            with st.container(border=True):
                st.markdown(f"**`{r['reference']}`**")
                st.caption(r.get("designation", "")[:50])
                st.caption(f"IPR max : {wf.get('ipr_max', '—')}")
                if statut == "corrections":
                    st.warning("🔄 Corrections demandées")
                    if last.get("commentaire"):
                        st.caption(f"💬 {last['commentaire'][:70]}")
                else:
                    st.info("📝 Brouillon")
                if st.button("📄 Voir AMDEC/Gamme", key=f"goto_base_a_{r['reference']}", use_container_width=True):
                    st.session_state["goto_page"] = "📚 Gestion de la base"
                    st.session_state["goto_ref"] = r["reference"]
                    st.rerun()

    with col_b:
        st.markdown(f"### 👁️ En validation ({len(refs_en_validation)})")
        if not refs_en_validation:
            st.caption("Aucun dossier.")
        for r in refs_en_validation:
            wf = r.get("workflow", {})
            gates_req = wf.get("gates_requises", [])
            gates_ok  = wf.get("gates_completees", [])
            gate_courante = next((g for g in gates_req if g not in gates_ok), None)
            role_requis   = role_pour_gate(gate_courante) if gate_courante else ""
            je_peux_agir  = peut_valider_gate(role_user, gate_courante) if gate_courante else False
            with st.container(border=True):
                kb1, kb2 = st.columns([3, 1])
                kb1.markdown(f"**`{r['reference']}`**")
                ipr_max = wf.get("ipr_max")
                if ipr_max and ipr_max != "—":
                    try:
                        ipr_val = int(ipr_max)
                        badge = "🔴" if ipr_val >= 100 else ("🟠" if ipr_val >= 50 else "🟢")
                        kb2.markdown(f"{badge} **IPR {ipr_val}**")
                    except (ValueError, TypeError):
                        kb2.caption(f"IPR {ipr_max}")
                st.caption(r.get("designation", "")[:50])
                for g in gates_req:
                    if g in gates_ok:
                        st.caption(f"✅ {g}")
                    elif g == gate_courante:
                        st.caption(f"👉 **{g}**")
                    else:
                        st.caption(f"⏳ {g}")
                # Résumé rapide des défaillances critiques (IPR ≥ 100)
                ref_data = charger_reference_complete(categorie_active, r["reference"])
                def _top_critiques(amdec):
                    return sorted(
                        [m for m in amdec.get("modes_defaillance", [])
                         if (m.get("G",0)*m.get("O",0)*m.get("D",0)) >= 100],
                        key=lambda m: -(m.get("G",0)*m.get("O",0)*m.get("D",0))
                    )[:3]
                critiques = (
                    _top_critiques(ref_data["data"].get("amdec_produit", {})) +
                    _top_critiques(ref_data["data"].get("amdec_process", {}))
                )
                if critiques:
                    st.caption("🔴 **Défaillances critiques (IPR ≥ 100) :**")
                    for m in critiques:
                        ipr = m.get("G",0)*m.get("O",0)*m.get("D",0)
                        st.caption(f"  · IPR {ipr} — {m.get('mode_defaillance','')[:45]}")
                if je_peux_agir:
                    st.success("✋ En attente de votre validation")
                elif gate_courante:
                    requis_label = ROLES.get(role_requis, {}).get("label", role_requis)
                    st.caption(f"Nécessite : {requis_label}")
                if st.button("📄 Voir AMDEC/Gamme", key=f"goto_base_b_{r['reference']}", use_container_width=True):
                    st.session_state["goto_page"] = "📚 Gestion de la base"
                    st.session_state["goto_ref"] = r["reference"]
                    st.rerun()

    with col_c:
        st.markdown(f"### ✅ Terminés ({len(refs_termines)})")
        if not refs_termines:
            st.caption("Aucun dossier.")
        for r in refs_termines:
            wf   = r.get("workflow", {})
            last = (wf.get("historique") or [{}])[-1]
            with st.container(border=True):
                st.markdown(f"**`{r['reference']}`**")
                st.caption(r.get("designation", "")[:50])
                st.markdown(label_statut(_statut_ref(r)))
                if last.get("date"):
                    st.caption(f"Le {last['date'][:10]} — {last.get('acteur', '—')}")
                if st.button("📄 Voir AMDEC/Gamme", key=f"goto_base_c_{r['reference']}", use_container_width=True):
                    st.session_state["goto_page"] = "📚 Gestion de la base"
                    st.session_state["goto_ref"] = r["reference"]
                    st.rerun()

    st.divider()

    # ── Panel d'action ────────────────────────────────────────────────────────
    st.subheader("⚡ Effectuer une action")

    codes_actifs = [r["reference"] for r in toutes_refs if _statut_ref(r) != "obsolete"]
    if not codes_actifs:
        st.info("Aucun dossier actif.")
        st.stop()

    code_wf = st.selectbox("Sélectionner un dossier", codes_actifs)
    ref_wf   = charger_reference_complete(categorie_active, code_wf)
    meta_wf  = ref_wf["metadata"]
    data_wf  = ref_wf["data"]

    wf_actuel     = lire_workflow(meta_wf)
    statut_actuel = wf_actuel.get("statut", "brouillon")
    gate_suivante = prochaine_gate(meta_wf)

    inf1, inf2, inf3, inf4 = st.columns(4)
    inf1.metric("Statut", label_statut(statut_actuel))
    inf2.metric("IPR max", wf_actuel.get("ipr_max", "—"))
    inf3.metric("Gates", f"{len(wf_actuel.get('gates_completees',[]))}/{len(wf_actuel.get('gates_requises',[]))}")
    inf4.metric("Prochaine gate", gate_suivante or "Toutes validées ✅")

    # Progression visuelle des gates
    gates_req = wf_actuel.get("gates_requises", [])
    gates_ok  = wf_actuel.get("gates_completees", [])
    if gates_req:
        st.markdown("**Progression des signatures :**")
        pcols = st.columns(len(gates_req))
        for i, g in enumerate(gates_req):
            if g in gates_ok:
                pcols[i].success(f"✅ {g}")
            elif g == gate_suivante:
                pcols[i].warning(f"👉 {g}")
            else:
                pcols[i].info(f"⏳ {g}")

    # ── Récapitulatif des défaillances majeures ───────────────────────────────
    def _extraire_defaillances_majeures(amdec: dict, seuil_ipr: int = 50) -> list[dict]:
        modes = amdec.get("modes_defaillance", [])
        result = []
        for m in modes:
            ipr = (m.get("G") or 0) * (m.get("O") or 0) * (m.get("D") or 0)
            if ipr >= seuil_ipr:
                result.append({
                    "ipr": ipr,
                    "mode": m.get("mode_defaillance") or m.get("mode_defaillance", ""),
                    "effet": m.get("effets_defaillance") or m.get("effets_produit", ""),
                    "G": m.get("G", "?"), "O": m.get("O", "?"), "D": m.get("D", "?"),
                    "classe": m.get("classe_criticite", ""),
                    "action": m.get("actions_correctives", ""),
                    "contexte": m.get("operation_process") or m.get("famille", ""),
                })
        return sorted(result, key=lambda x: -x["ipr"])

    ap_data  = data_wf.get("amdec_produit", {})
    apr_data = data_wf.get("amdec_process", {})
    def_produit  = _extraire_defaillances_majeures(ap_data)
    def_process  = _extraire_defaillances_majeures(apr_data)
    toutes_def   = sorted(def_produit + def_process, key=lambda x: -x["ipr"])

    if toutes_def:
        with st.expander(
            f"🚨 **{len(toutes_def)} défaillance(s) majeure(s)** (IPR ≥ 50) — cliquer pour vérifier avant validation",
            expanded=(statut_actuel == "en_revue"),
        ):
            tab_prod, tab_proc = st.tabs([
                f"AMDEC Produit ({len(def_produit)})",
                f"AMDEC Process ({len(def_process)})",
            ])
            with tab_prod:
                if not def_produit:
                    st.success("Aucune défaillance produit à IPR ≥ 50.")
                for d in def_produit:
                    couleur = "🔴" if d["ipr"] >= 100 else "🟠"
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"{couleur} **{d['mode']}**")
                        c2.metric("IPR", d["ipr"])
                        if d["effet"]:
                            st.caption(f"Effet : {d['effet']}")
                        if d["contexte"]:
                            st.caption(f"Famille : {d['contexte']}")
                        st.caption(f"G={d['G']} · O={d['O']} · D={d['D']} | {d['classe']}")
                        if d["action"]:
                            st.caption(f"✅ Action : {d['action']}")
            with tab_proc:
                if not def_process:
                    st.success("Aucune défaillance process à IPR ≥ 50.")
                for d in def_process:
                    couleur = "🔴" if d["ipr"] >= 100 else "🟠"
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"{couleur} **{d['mode']}**")
                        c2.metric("IPR", d["ipr"])
                        if d["effet"]:
                            st.caption(f"Effet : {d['effet']}")
                        if d["contexte"]:
                            st.caption(f"Opération : {d['contexte']}")
                        st.caption(f"G={d['G']} · O={d['O']} · D={d['D']} | {d['classe']}")
                        if d["action"]:
                            st.caption(f"✅ Action : {d['action']}")
    else:
        st.success("✅ Aucune défaillance majeure (IPR ≥ 50) dans ce dossier.")

    # ── Calcul des actions autorisées pour ce rôle ──
    actions_brutes     = actions_disponibles(meta_wf)
    actions_autorisees = []
    for action in actions_brutes:
        if action == "approuver":
            if gate_suivante and (peut_valider_gate(role_user, gate_suivante) or role_user == "admin"):
                actions_autorisees.append(action)
        elif action in ("soumettre", "resoumettre"):
            if peut_soumettre(role_user):
                actions_autorisees.append(action)
        elif action == "corrections":
            if peut_demander_corrections(role_user):
                actions_autorisees.append(action)
        elif action == "liberer":
            if peut_liberer(role_user):
                actions_autorisees.append(action)
        elif action == "rendre_obsolete":
            if role_user == "admin":
                actions_autorisees.append(action)

    if not actions_autorisees:
        if actions_brutes:
            if gate_suivante:
                requis_label = ROLES.get(role_pour_gate(gate_suivante), {}).get("label", "?")
                st.warning(
                    f"⛔ La prochaine action sur ce dossier requiert le rôle **{requis_label}**. "
                    f"Vous êtes connecté en tant que *{ROLES.get(role_user, {}).get('label', '')}*."
                )
            else:
                st.info("Aucune action disponible pour votre rôle sur ce dossier.")
        else:
            st.success("✅ Ce dossier est dans un état final — aucune action possible.")
    else:
        ac1, ac2 = st.columns([2, 3])
        with ac1:
            action_choisie = st.selectbox(
                "Action",
                options=actions_autorisees,
                format_func=label_action,
                label_visibility="collapsed",
            )
        with ac2:
            st.text_input("Signataire", value=nom_user, disabled=True, key="signataire_affiche")

        commentaire_wf = st.text_area(
            "Commentaire" + (" *" if action_choisie == "corrections" else " (optionnel)"),
            placeholder="Ex: IPR de l'op. Sputtering à revoir…",
            height=80,
            key="commentaire_wf",
        )

        if action_choisie == "approuver" and gate_suivante:
            st.info(f"✍️ Vous allez apposer votre signature sur : **{gate_suivante}**")

        btn_disabled = action_choisie == "corrections" and not commentaire_wf.strip()

        if st.button(f"▶ {label_action(action_choisie)}", type="primary", disabled=btn_disabled):
            try:
                faire_transition(
                    metadata=meta_wf,
                    action=action_choisie,
                    acteur=nom_user,
                    commentaire=commentaire_wf.strip(),
                    data=data_wf,
                )
                sauvegarder_modifications(categorie_active, code_wf, meta_wf)
                ajouter_notification(
                    ref=code_wf,
                    categorie=cat_code_selectionne,
                    statut=meta_wf["statut"],
                    acteur=nom_user,
                    message=f"{nom_user} a effectué l'action '{label_action(action_choisie)}' sur `{code_wf}` — statut : {label_statut(meta_wf['statut'])}",
                )
                st.success(
                    f"✅ **{label_action(action_choisie)}** enregistré — "
                    f"Signataire : **{nom_user}** — "
                    f"Statut : {label_statut(meta_wf['statut'])}"
                )
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erreur inattendue : {e}")

    # ── Export PDF ────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("📄 Exporter ce dossier en PDF"):
        if st.button("Générer le PDF", key=f"wf_pdf_{code_wf}"):
            try:
                pdf_bytes = exporter_dossier_pdf(
                    metadata=meta_wf,
                    amdec_produit=data_wf.get("amdec_produit", {}),
                    amdec_process=data_wf.get("amdec_process", {}),
                    gamme=data_wf.get("gamme", {}),
                )
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"dossier_qualite_{code_wf}.pdf",
                    mime="application/pdf",
                    key=f"wf_dl_pdf_{code_wf}",
                )
            except Exception as e:
                st.error(f"Erreur PDF : {e}")

    # ── Historique des signatures ─────────────────────────────────────────────
    st.divider()
    st.subheader("📜 Historique des signatures")
    historique = wf_actuel.get("historique", [])
    if not historique:
        st.info("Aucune action enregistrée — workflow non initialisé.")
        if st.button("Initialiser le workflow"):
            initialiser_workflow(meta_wf, data_wf, acteur=nom_user, commentaire="Initialisation manuelle")
            sauvegarder_modifications(categorie_active, code_wf, meta_wf)
            st.success("Workflow initialisé.")
            st.rerun()
    else:
        for entree in reversed(historique):
            date_str = entree.get("date", "")[:16].replace("T", " à ")
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{label_action(entree.get('action', ''))}** — ✍️ {entree.get('acteur', '—')}")
                c2.caption(date_str)
                if entree.get("commentaire"):
                    st.caption(f"💬 {entree['commentaire']}")

    st.stop()

if page == "🎨 Typologies":
    st.title(f"🎨 Typologies de traitement — {categorie_active.icone} {categorie_active.nom}")
    st.caption(
        "Définis les variantes nommées de chaque traitement (composition, outillage, méthode). "
        "Quand un utilisateur sélectionnera ce traitement dans un brief, il pourra choisir la typologie. "
        "Le moteur de similarité matche sur (traitement + typologie)."
    )
    st.divider()

    typologies_actuelles = charger_typologies(categorie_active)

    # ── Tableau des typologies existantes ──
    if typologies_actuelles:
        st.subheader("📋 Typologies existantes")
        for code_traitement, typo_dict in typologies_actuelles.items():
            label_t = categorie_active.vocabulaire().get("traitements", {}).get(code_traitement, code_traitement)
            with st.expander(f"**{label_t}** ({code_traitement}) — {len(typo_dict)} typologie(s)"):
                for code_typo, details in typo_dict.items():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**`{code_typo}`** — {details.get('nom', '')}")
                            if details.get("stack"):
                                st.caption(f"🧱 Stack : {' / '.join(details['stack'])}")
                            if details.get("outillage"):
                                st.caption(f"🔧 Outillage : {details['outillage']}")
                            if details.get("methodologie"):
                                st.caption(f"📋 Méthode : {details['methodologie']}")
                            if details.get("gamme_application"):
                                st.caption(f"🎯 Gamme : {details['gamme_application']}")
                            if details.get("notes"):
                                st.caption(f"📝 Notes : {details['notes']}")
                        with c2:
                            if st.button("🗑️ Supprimer", key=f"del_{code_traitement}_{code_typo}"):
                                supprimer_typologie(categorie_active, code_traitement, code_typo)
                                st.success(f"Typologie {code_typo} supprimée.")
                                st.rerun()
    else:
        st.info("Aucune typologie définie pour cette catégorie.")

    st.divider()

    # ── Création / mise à jour ──
    st.subheader("➕ Créer ou modifier une typologie")

    with st.form("form_typologie"):
        traitements_dispo = categorie_active.vocabulaire().get("traitements", {})
        col_a, col_b = st.columns(2)
        with col_a:
            if traitements_dispo:
                code_traitement_input = st.selectbox(
                    "Traitement *",
                    options=list(traitements_dispo.keys()),
                    format_func=lambda x: f"{x} — {traitements_dispo.get(x, x)}",
                )
            else:
                code_traitement_input = st.text_input(
                    "Code traitement *",
                    placeholder="Ex: antireflet_double_face",
                )
        with col_b:
            code_typologie_input = st.text_input(
                "Code typologie *",
                placeholder="Ex: BBAR-5L",
                help="Code court unique pour cette composition.",
            )

        nom_typo = st.text_input(
            "Nom complet *",
            placeholder="Ex: BBAR Standard 5 couches",
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            stack_str = st.text_input(
                "Stack des couches",
                placeholder="Ex: SiO2, TiO2, SiO2, TiO2, SiO2",
                help="Liste des matériaux de chaque couche, séparés par virgule.",
            )
        with col_s2:
            outillage_input = st.text_input(
                "Référence outillage",
                placeholder="Ex: OUT-AR-BBAR-5L",
            )

        methodologie_input = st.text_area(
            "Méthodologie de production",
            placeholder="Ex: PVD basse température, manipulation gants nitrile",
            height=70,
        )
        gamme_app_input = st.text_input(
            "Gamme d'application",
            placeholder="Ex: VIS 400-700nm",
        )
        notes_input = st.text_area(
            "Notes (optionnel)",
            placeholder="Précisions, contraintes, références internes…",
            height=70,
        )

        valide = st.form_submit_button("💾 Enregistrer la typologie", type="primary")

    if valide:
        if not code_traitement_input or not code_typologie_input or not nom_typo:
            st.error("Les champs Traitement, Code typologie et Nom sont obligatoires.")
        else:
            try:
                stack_list = [s.strip() for s in stack_str.split(",") if s.strip()] if stack_str else []
                creer_ou_maj_typologie(
                    categorie_active,
                    code_traitement=code_traitement_input,
                    code_typologie=code_typologie_input,
                    nom=nom_typo,
                    stack=stack_list,
                    outillage=outillage_input,
                    methodologie=methodologie_input,
                    gamme_application=gamme_app_input,
                    notes=notes_input,
                )
                st.success(f"✅ Typologie `{code_typologie_input}` enregistrée pour `{code_traitement_input}`.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.stop()

# ─── PAGE : Gestion des utilisateurs (admin uniquement) ──────────────────────
if page == "👥 Utilisateurs":
    if user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    st.title("👥 Gestion des utilisateurs")
    st.caption("Créer, modifier et supprimer les comptes utilisateurs de l'application.")

    utilisateurs = lister_utilisateurs()

    # ── Tableau des utilisateurs existants ────────────────────────────────────
    st.subheader("Comptes actifs")
    for u in utilisateurs:
        role_label = ROLES.get(u["role"], {}).get("label", u["role"])
        with st.container(border=True):
            uc1, uc2, uc3, uc4 = st.columns([2, 2, 2, 1])
            uc1.markdown(f"**`{u['username']}`**")
            uc2.write(u["nom"])
            uc3.write(role_label)
            with uc4:
                if u["username"] != user["username"]:
                    if st.button("🗑️", key=f"del_user_{u['username']}",
                                 help=f"Supprimer {u['username']}"):
                        try:
                            supprimer_utilisateur(u["username"])
                            st.success(f"Utilisateur `{u['username']}` supprimé.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.caption("(vous)")

    # ── Réinitialisation mot de passe ────────────────────────────────────────
    st.divider()
    st.subheader("🔑 Réinitialiser un mot de passe")
    usernames = [u["username"] for u in utilisateurs]
    col_r1, col_r2, col_r3 = st.columns([2, 2, 1])
    with col_r1:
        cible_reset = st.selectbox("Utilisateur", usernames, key="reset_user_select")
    with col_r2:
        nouveau_mdp_admin = st.text_input("Nouveau mot de passe", type="password", key="reset_mdp_admin")
    with col_r3:
        st.write("")
        st.write("")
        if st.button("Réinitialiser", key="btn_reset_admin"):
            if not nouveau_mdp_admin.strip():
                st.error("Le mot de passe ne peut pas être vide.")
            elif len(nouveau_mdp_admin) < 8:
                st.error("Minimum 8 caractères.")
            else:
                try:
                    changer_mot_de_passe(cible_reset, nouveau_mdp_admin)
                    st.success(f"Mot de passe de `{cible_reset}` réinitialisé.")
                except Exception as e:
                    st.error(str(e))

    # ── Créer un nouvel utilisateur ───────────────────────────────────────────
    st.divider()
    st.subheader("➕ Créer un utilisateur")
    with st.form("form_creer_user"):
        fc1, fc2 = st.columns(2)
        with fc1:
            new_username = st.text_input("Identifiant *", placeholder="prenom.nom")
            new_nom = st.text_input("Nom affiché *", placeholder="Jean Dupont")
        with fc2:
            new_role = st.selectbox(
                "Rôle *",
                options=list(ROLES.keys()),
                format_func=lambda r: ROLES[r]["label"],
            )
            new_mdp = st.text_input("Mot de passe *", type="password",
                                    placeholder="Min. 8 caractères")
            new_mdp2 = st.text_input("Confirmer le mot de passe *", type="password")

        if st.form_submit_button("Créer le compte", type="primary"):
            if not new_username.strip() or not new_nom.strip() or not new_mdp:
                st.error("Tous les champs sont obligatoires.")
            elif new_mdp != new_mdp2:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(new_mdp) < 8:
                st.error("Le mot de passe doit faire au moins 8 caractères.")
            else:
                try:
                    creer_utilisateur(new_username.strip(), new_nom.strip(), new_role, new_mdp)
                    st.success(f"✅ Compte `{new_username}` créé avec le rôle **{ROLES[new_role]['label']}**.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.stop()

if page == "🔔 Notifications":
    st.title("🔔 Notifications")
    st.caption("Alertes liées aux transitions de workflow qui vous concernent.")

    _role = user["role"]
    _notifs = lire_notifications(_role)

    if not _notifs:
        st.info("Aucune notification non lue.")
    else:
        if st.button("✅ Marquer tout comme lu", key="notif_marquer_lues"):
            marquer_lues(_role)
            st.success("Toutes les notifications ont été marquées comme lues.")
            st.rerun()

        for _n in _notifs:
            with st.container(border=True):
                col_n1, col_n2 = st.columns([3, 1])
                col_n1.markdown(f"**{_n['message']}**")
                col_n2.caption(_n["date"].replace("T", " ")[:16])
                st.caption(
                    f"Référence : `{_n['ref']}` — Catégorie : {_n['categorie']} "
                    f"— Statut : {_n['statut']} — Par : {_n['acteur']}"
                )

    st.stop()

if page == "📚 Gestion de la base":
    import pandas as pd

    st.title(f"📚 Gestion de la base — {categorie_active.icone} {categorie_active.nom}")
    st.caption("Visualiser, filtrer, éditer et supprimer les références de la catégorie active")

    references = lister_references(categorie_active)

    if not references:
        st.info("Aucune référence dans la base. Crée-en une via la page **🏭 Nouveau produit**.")
        st.stop()

    # ─── Statistiques globales ──────────────────────────────────────────────
    _params_num_stats = categorie_active.parametres_numeriques()
    _dim_key_stats = _params_num_stats[0]["cle"] if _params_num_stats else "diametre_mm"
    _dim_label_stats = _params_num_stats[0]["label"].split("(")[0].strip() if _params_num_stats else "Dim."
    stats = calculer_stats(references, dim_key=_dim_key_stats)
    st.divider()
    st.subheader("📊 Vue d'ensemble")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Références totales", stats["total"])
    c2.metric("Modes AMDEC Produit", stats.get("nb_modes_produit_total", 0))
    c3.metric("Modes AMDEC Process", stats.get("nb_modes_process_total", 0))
    c4.metric("Opérations Gamme", stats.get("nb_operations_total", 0))

    if stats.get("dim_prim_moy"):
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{_dim_label_stats} min", f"{stats['dim_prim_min']:.1f}")
        c2.metric(f"{_dim_label_stats} moy.", f"{stats['dim_prim_moy']:.1f}")
        c3.metric(f"{_dim_label_stats} max", f"{stats['dim_prim_max']:.1f}")

    with st.expander("Répartition par catégorie"):
        rep1, rep2, rep3 = st.columns(3)
        with rep1:
            st.markdown("**Par type produit**")
            for k, v in sorted(stats.get("types", {}).items(), key=lambda x: -x[1]):
                st.markdown(f"- `{k}` : {v}")
        with rep2:
            st.markdown("**Par matière**")
            for k, v in sorted(stats.get("matieres", {}).items(), key=lambda x: -x[1]):
                st.markdown(f"- `{k}` : {v}")
        with rep3:
            st.markdown("**Par traitement**")
            for k, v in sorted(stats.get("traitements", {}).items(), key=lambda x: -x[1]):
                st.markdown(f"- `{k}` : {v}")

    # ─── Tableau filtrable ──────────────────────────────────────────────────
    st.divider()
    st.subheader("🔍 Liste des références")

    filt_c1, filt_c2, filt_c3, filt_c4 = st.columns(4)
    with filt_c1:
        f_type = st.multiselect("Type", sorted(stats.get("types", {}).keys()))
    with filt_c2:
        f_matiere = st.multiselect("Matière", sorted(stats.get("matieres", {}).keys()))
    with filt_c3:
        f_traitement = st.multiselect("Traitement", sorted(stats.get("traitements", {}).keys()))
    with filt_c4:
        f_statut = st.multiselect("Statut", sorted(stats.get("statuts", {}).keys()))

    filtered = references
    if f_type:
        filtered = [r for r in filtered if r.get("type_produit") in f_type]
    if f_matiere:
        filtered = [r for r in filtered if r.get("matiere") in f_matiere]
    if f_traitement:
        filtered = [r for r in filtered if any(t in r.get("traitements", []) for t in f_traitement)]
    if f_statut:
        filtered = [r for r in filtered if r.get("statut") in f_statut]

    st.caption(f"**{len(filtered)}** référence(s) sur {len(references)}")

    # Tableau récap
    if filtered:
        _col_dim_label = _dim_label_stats
        df = pd.DataFrame([{
            "Référence": r.get("reference", ""),
            "Désignation": r.get("designation", ""),
            "Type": r.get("type_produit", ""),
            "Matière": r.get("matiere", ""),
            _col_dim_label: r.get("dimensions", {}).get(_dim_key_stats),
            "Traitements": format_traitements_str(r.get("traitements", [])),
            "Statut": r.get("statut", ""),
            "Modes P": r.get("_nb_modes_produit", 0),
            "Modes Pr": r.get("_nb_modes_process", 0),
            "Ops": r.get("_nb_operations", 0),
            "Créée le": r.get("date_creation", ""),
        } for r in filtered])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── Détail / Édition / Suppression d'une référence ─────────────────────
    st.divider()
    st.subheader("✏️ Éditer ou supprimer une référence")

    codes_refs = [r["reference"] for r in filtered]
    if not codes_refs:
        st.info("Aucune référence ne correspond aux filtres.")
        st.stop()

    # Pré-sélection depuis un clic workflow (goto_ref posé par un bouton de carte)
    _goto_ref = st.session_state.pop("goto_ref", None)
    _idx_ref = codes_refs.index(_goto_ref) if _goto_ref and _goto_ref in codes_refs else 0
    code_selectionne = st.selectbox("Sélectionner une référence", codes_refs, index=_idx_ref)
    ref_complete = charger_reference_complete(categorie_active, code_selectionne)
    meta = ref_complete["metadata"]
    data = ref_complete["data"]

    tab_meta, tab_p, tab_pr, tab_g, tab_dit, tab_zone = st.tabs([
        "📋 Métadonnées", "AMDEC Produit", "AMDEC Process", "Gamme", "📄 DIT", "⚙️ Actions"
    ])

    # Vérification verrou : une référence libérée/approuvée est en lecture seule
    _statut_wf = meta.get("workflow", {}).get("statut", meta.get("statut", "brouillon"))
    _est_verrouille = _statut_wf in ("libere", "approuve") and user["role"] != "admin"
    _est_verrouille_admin = _statut_wf in ("libere", "approuve")

    with tab_meta:
        st.json(meta)

    if _est_verrouille_admin:
        _msg_verrou = (
            "Un administrateur peut forcer la modification."
            if user["role"] != "admin"
            else "En tant qu'administrateur, vous pouvez modifier, mais cela brisera la traçabilité du workflow."
        )
        st.warning(
            f"🔒 Cette référence est **{_statut_wf.upper()}** — les documents qualité sont en **lecture seule**. {_msg_verrou}"
        )
    else:
        st.info(
            "✏️ **Mode édition activé** : modifie les cellules directement, ajoute des lignes "
            "via la dernière ligne grise en bas, ou coche une ligne et touche `Suppr` pour la "
            "supprimer. **Clique sur 💾 Enregistrer en bas de chaque onglet** pour sauver dans la base."
        )

    # ─── Onglet AMDEC Produit (éditable) ────────────────────────────────────
    with tab_p:
        modes = data.get("amdec_produit", {}).get("modes_defaillance", [])
        if not modes:
            modes = []
            st.caption("Pas d'AMDEC Produit existant — tu peux en créer une de zéro.")

        colonnes_p = ["no", "famille", "fonction_exigence", "caracteristique_critique",
                      "mode_defaillance", "effets_defaillance", "G", "causes_defaillance",
                      "O", "controles_existants", "D", "classe_criticite",
                      "actions_correctives", "responsable", "delai"]
        df_p = pd.DataFrame(modes)
        for c in colonnes_p:
            if c not in df_p.columns:
                df_p[c] = ""
        df_p = df_p[colonnes_p]

        edited_p = st.data_editor(
            df_p, num_rows="dynamic" if not _est_verrouille else "fixed",
            use_container_width=True, disabled=_est_verrouille,
            key=f"editor_p_{code_selectionne}",
            column_config={
                "no": st.column_config.TextColumn("N°", width="small"),
                "famille": st.column_config.SelectboxColumn(
                    "Famille",
                    options=["optique", "esthetique", "geometrique", "etancheite", "tracabilite"],
                    width="small",
                ),
                "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
            },
        )

        if st.button("💾 Enregistrer AMDEC Produit", key=f"save_p_{code_selectionne}", type="primary", disabled=_est_verrouille):
            data["amdec_produit"] = data.get("amdec_produit", {"reference": code_selectionne, "document": "AMDEC Produit"})
            data["amdec_produit"]["modes_defaillance"] = edited_p.fillna("").to_dict("records")
            sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
            st.success(f"✅ AMDEC Produit de `{code_selectionne}` enregistrée ({len(edited_p)} modes).")

        st.divider()
        with st.expander("➕ Ajouter une défaillance produit", expanded=False) if not _est_verrouille else st.expander("🔒 Ajout désactivé — référence verrouillée", expanded=False):
            familles_p = ["optique", "esthetique", "geometrique", "etancheite", "tracabilite"]
            ap1, ap2 = st.columns(2)
            with ap1:
                nf_famille = st.selectbox("Famille", familles_p, key=f"nf_famille_{code_selectionne}")
                nf_fonction = st.text_input("Fonction / exigence", placeholder="Ex: Conformité dimensionnelle", key=f"nf_fonction_{code_selectionne}")
                nf_carac = st.text_input("Caractéristique critique", placeholder="Ex: Diamètre / dimensions", key=f"nf_carac_{code_selectionne}")
                nf_mode = st.text_input("Mode de défaillance *", placeholder="Ex: Cote hors tolérance", key=f"nf_mode_{code_selectionne}")
                nf_effet = st.text_input("Effet sur le produit *", placeholder="Ex: Impossibilité de montage", key=f"nf_effet_{code_selectionne}")
            with ap2:
                nf_cause = st.text_input("Cause(s)", placeholder="Ex: Dérive machine, usure outil", key=f"nf_cause_{code_selectionne}")
                nf_controle = st.text_input("Contrôles existants", placeholder="Ex: Mesure 100% réception", key=f"nf_controle_{code_selectionne}")
                nf_action = st.text_input("Action corrective", placeholder="Ex: SPC dimension lot entrant", key=f"nf_action_{code_selectionne}")
                nf_resp = st.text_input("Responsable", value="BT Qualité", key=f"nf_resp_{code_selectionne}")
                gc1, gc2, gc3 = st.columns(3)
                nf_G = gc1.number_input("G (gravité)", 1, 10, 5, key=f"nf_G_{code_selectionne}")
                nf_O = gc2.number_input("O (occurence)", 1, 10, 3, key=f"nf_O_{code_selectionne}")
                nf_D = gc3.number_input("D (détection)", 1, 10, 3, key=f"nf_D_{code_selectionne}")
                nf_ipr = nf_G * nf_O * nf_D
                nf_classe = "🔴 Critique" if nf_ipr >= 100 else ("🟠 Action corrective" if nf_ipr >= 50 else "🟢 Acceptable")
                st.metric("IPR calculé", nf_ipr, help="G × O × D")
                st.caption(f"Criticité : {nf_classe}")

            if st.button("Ajouter cette défaillance", type="primary", key=f"btn_add_p_{code_selectionne}"):
                if not nf_mode.strip() or not nf_effet.strip():
                    st.error("Le mode de défaillance et l'effet sont obligatoires.")
                else:
                    amdec_p = data.get("amdec_produit", {"reference": code_selectionne, "document": "AMDEC Produit", "modes_defaillance": []})
                    modes_actuels = edited_p.fillna("").to_dict("records")
                    no_suivant = str(len(modes_actuels) + 1).zfill(2)
                    classe_clean = nf_classe.split(" ", 1)[-1]
                    modes_actuels.append({
                        "no": no_suivant,
                        "famille": nf_famille,
                        "fonction_exigence": nf_fonction,
                        "caracteristique_critique": nf_carac,
                        "mode_defaillance": nf_mode.strip(),
                        "effets_defaillance": nf_effet.strip(),
                        "G": nf_G, "causes_defaillance": nf_cause,
                        "O": nf_O, "controles_existants": nf_controle,
                        "D": nf_D, "classe_criticite": classe_clean,
                        "actions_correctives": nf_action,
                        "responsable": nf_resp, "delai": "",
                    })
                    amdec_p["modes_defaillance"] = modes_actuels
                    data["amdec_produit"] = amdec_p
                    sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
                    st.success(f"✅ Défaillance ajoutée (IPR {nf_ipr} — {classe_clean}).")
                    st.rerun()

    # ─── Onglet AMDEC Process (éditable) ────────────────────────────────────
    with tab_pr:
        modes_pr = data.get("amdec_process", {}).get("modes_defaillance", [])
        if not modes_pr:
            modes_pr = []
            st.caption("Pas d'AMDEC Process existant — tu peux en créer une de zéro.")

        colonnes_pr = ["no", "operation_process", "etape_poste", "mode_defaillance",
                       "effets_produit", "G", "causes_process", "O", "controles_process",
                       "D", "classe_criticite", "actions_correctives", "responsable",
                       "delai", "parametre_cle", "valeur_cible"]
        df_pr = pd.DataFrame(modes_pr)
        for c in colonnes_pr:
            if c not in df_pr.columns:
                df_pr[c] = ""
        df_pr = df_pr[colonnes_pr]

        edited_pr = st.data_editor(
            df_pr, num_rows="dynamic", use_container_width=True,
            key=f"editor_pr_{code_selectionne}",
            column_config={
                "no": st.column_config.TextColumn("N°", width="small"),
                "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
            },
        )

        if st.button("💾 Enregistrer AMDEC Process", key=f"save_pr_{code_selectionne}", type="primary", disabled=_est_verrouille):
            data["amdec_process"] = data.get("amdec_process", {"reference": code_selectionne, "document": "AMDEC Process"})
            data["amdec_process"]["modes_defaillance"] = edited_pr.fillna("").to_dict("records")
            sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
            st.success(f"✅ AMDEC Process de `{code_selectionne}` enregistrée ({len(edited_pr)} modes).")

        st.divider()
        with st.expander("➕ Ajouter une défaillance process", expanded=False) if not _est_verrouille else st.expander("🔒 Ajout désactivé — référence verrouillée", expanded=False):
            # Récupérer les opérations de la gamme pour pré-remplir l'opération
            ops_gamme_pr = data.get("gamme", {}).get("operations", [])
            options_ops = ["(saisie libre)"] + [
                f"{op.get('no_op','')} — {op.get('designation','')}"
                for op in ops_gamme_pr if op.get("designation")
            ]
            apr1, apr2 = st.columns(2)
            with apr1:
                op_choisie = st.selectbox(
                    "Opération (depuis la gamme)",
                    options=options_ops,
                    key=f"npr_op_select_{code_selectionne}",
                )
                if op_choisie == "(saisie libre)":
                    npr_op = st.text_input("Nom de l'opération *", placeholder="Ex: Sputtering AR double face", key=f"npr_op_{code_selectionne}")
                    npr_etape = st.text_input("Étape / poste", placeholder="Ex: Poste PVD", key=f"npr_etape_{code_selectionne}")
                else:
                    idx_op = options_ops.index(op_choisie) - 1
                    op_data = ops_gamme_pr[idx_op]
                    npr_op = op_data.get("designation", "")
                    npr_etape = op_data.get("poste_machine", "")
                    st.caption(f"Opération : **{npr_op}** | Poste : {npr_etape}")

                npr_mode = st.text_input("Mode de défaillance *", placeholder="Ex: Délaminement couche AR", key=f"npr_mode_{code_selectionne}")
                npr_effet = st.text_input("Effet sur le produit *", placeholder="Ex: Réflexion hors spec", key=f"npr_effet_{code_selectionne}")
            with apr2:
                npr_cause = st.text_input("Cause process", placeholder="Ex: Température sputtering trop élevée", key=f"npr_cause_{code_selectionne}")
                npr_controle = st.text_input("Contrôles process", placeholder="Ex: Contrôle réflectivité 100%", key=f"npr_controle_{code_selectionne}")
                npr_action = st.text_input("Action corrective", placeholder="Ex: Ajuster paramètre puissance RF", key=f"npr_action_{code_selectionne}")
                npr_param = st.text_input("Paramètre clé", placeholder="Ex: Puissance RF (W)", key=f"npr_param_{code_selectionne}")
                npr_valeur = st.text_input("Valeur cible", placeholder="Ex: 800 ± 50 W", key=f"npr_valeur_{code_selectionne}")
                gc1, gc2, gc3 = st.columns(3)
                npr_G = gc1.number_input("G (gravité)", 1, 10, 5, key=f"npr_G_{code_selectionne}")
                npr_O = gc2.number_input("O (occurrence)", 1, 10, 3, key=f"npr_O_{code_selectionne}")
                npr_D = gc3.number_input("D (détection)", 1, 10, 3, key=f"npr_D_{code_selectionne}")
                npr_ipr = npr_G * npr_O * npr_D
                npr_classe = "🔴 Critique" if npr_ipr >= 100 else ("🟠 Action corrective" if npr_ipr >= 50 else "🟢 Acceptable")
                st.metric("IPR calculé", npr_ipr, help="G × O × D")
                st.caption(f"Criticité : {npr_classe}")

            if st.button("Ajouter cette défaillance", type="primary", key=f"btn_add_pr_{code_selectionne}"):
                if not npr_mode.strip() or not npr_effet.strip() or not npr_op.strip():
                    st.error("L'opération, le mode de défaillance et l'effet sont obligatoires.")
                else:
                    amdec_pr = data.get("amdec_process", {"reference": code_selectionne, "document": "AMDEC Process", "modes_defaillance": []})
                    modes_pr_actuels = edited_pr.fillna("").to_dict("records")
                    no_suivant = str(len(modes_pr_actuels) + 1).zfill(2)
                    classe_clean = npr_classe.split(" ", 1)[-1]
                    modes_pr_actuels.append({
                        "no": no_suivant,
                        "operation_process": npr_op.strip(),
                        "etape_poste": npr_etape,
                        "mode_defaillance": npr_mode.strip(),
                        "effets_produit": npr_effet.strip(),
                        "G": npr_G, "causes_process": npr_cause,
                        "O": npr_O, "controles_process": npr_controle,
                        "D": npr_D, "classe_criticite": classe_clean,
                        "actions_correctives": npr_action,
                        "responsable": "BT Qualité", "delai": "",
                        "parametre_cle": npr_param, "valeur_cible": npr_valeur,
                    })
                    amdec_pr["modes_defaillance"] = modes_pr_actuels
                    data["amdec_process"] = amdec_pr
                    sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
                    st.success(f"✅ Défaillance ajoutée sur « {npr_op} » (IPR {npr_ipr} — {classe_clean}).")
                    st.rerun()

    # ─── Onglet Gamme (éditable) ────────────────────────────────────────────
    with tab_g:
        ops = data.get("gamme", {}).get("operations", [])
        if not ops:
            ops = []
            st.caption("Pas de Gamme existante — tu peux en créer une de zéro.")

        colonnes_g = ["no_op", "designation", "description_detaillee", "poste_machine",
                      "outillage_fixture", "parametre_1", "valeur_1", "parametre_2",
                      "valeur_2", "parametre_3", "temps_min", "point_controle",
                      "moyen_controle", "frequence", "critere_acceptation",
                      "ref_dit", "ref_infor"]
        df_g = pd.DataFrame(ops)
        for c in colonnes_g:
            if c not in df_g.columns:
                df_g[c] = ""
        df_g = df_g[colonnes_g]

        edited_g = st.data_editor(
            df_g, num_rows="dynamic", use_container_width=True,
            key=f"editor_g_{code_selectionne}",
            column_config={
                "no_op": st.column_config.TextColumn("N° Op", width="small"),
                "temps_min": st.column_config.NumberColumn("Temps (min)", min_value=0, width="small"),
            },
        )

        if not edited_g.empty and "temps_min" in edited_g:
            temps_total = pd.to_numeric(edited_g["temps_min"], errors="coerce").fillna(0).sum()
            st.caption(f"⏱️ Temps total gamme : **{int(temps_total)} min**")

        if st.button("💾 Enregistrer Gamme", key=f"save_g_{code_selectionne}", type="primary", disabled=_est_verrouille):
            data["gamme"] = data.get("gamme", {"reference": code_selectionne, "document": "Gamme de Production"})
            data["gamme"]["operations"] = edited_g.fillna("").to_dict("records")
            sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
            st.success(f"✅ Gamme de `{code_selectionne}` enregistrée ({len(edited_g)} opérations).")

    # ─── Onglet DIT ─────────────────────────────────────────────────────────
    with tab_dit:
        st.markdown("### 📄 Documents d'Instruction de Travail")
        st.caption(
            "Chaque opération de la gamme peut avoir un DIT. "
            "Clique sur une opération pour voir, créer ou modifier son instruction."
        )

        ops_gamme = data.get("gamme", {}).get("operations", [])
        if not ops_gamme:
            st.info("Aucune opération dans la gamme. Ajoute des opérations dans l'onglet **Gamme** d'abord.")
        else:
            # ── Tableau de bord DIT ──
            dits_existants = {d["code"] for d in lister_dits(categorie_active, code_selectionne)}
            nb_ok = sum(1 for op in ops_gamme if op.get("ref_dit", "") in dits_existants)
            nb_total = len(ops_gamme)
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Opérations totales", nb_total)
            col_b.metric("DIT rédigés", nb_ok)
            col_c.metric("DIT manquants", nb_total - nb_ok)

            st.divider()

            # ── Sélection de l'opération ──
            op_options = {
                f"Op {op.get('no_op','?')} — {op.get('designation','')} [{op.get('ref_dit','')}]": op
                for op in ops_gamme
                if op.get("no_op") or op.get("designation")
            }
            if not op_options:
                st.info("Les opérations n'ont pas de numéro ou de désignation.")
            else:
                op_label = st.selectbox(
                    "Choisir une opération",
                    list(op_options.keys()),
                    key=f"dit_op_select_{code_selectionne}",
                )
                op_choisie = op_options[op_label]
                dit_code = op_choisie.get("ref_dit", "").strip()

                if not dit_code:
                    st.warning("Cette opération n'a pas de code DIT dans la gamme (colonne `ref_dit` vide).")
                else:
                    existe = dit_code in dits_existants
                    st.markdown(f"**Code DIT :** `{dit_code}` — {'✅ DIT existant' if existe else '⚪ Pas encore rédigé'}")

                    dit_actuel = charger_dit(categorie_active, code_selectionne, dit_code) if existe else None

                    # ── Bouton génération IA ──
                    col_gen, col_del = st.columns([3, 1])
                    with col_gen:
                        if st.button(
                            f"🤖 Générer le DIT par IA" if not existe else "🤖 Régénérer par IA",
                            key=f"gen_dit_{code_selectionne}_{dit_code}",
                            type="primary" if not existe else "secondary",
                        ):
                            with st.spinner(f"Génération du DIT {dit_code} en cours…"):
                                try:
                                    ia_result = generer_dit_ia(
                                        operation=op_choisie,
                                        reference=code_selectionne,
                                        designation=meta.get("designation", ""),
                                    )
                                    if dit_actuel is None:
                                        dit_actuel = nouveau_dit(dit_code, op_choisie)
                                    dit_actuel.update(ia_result)
                                    sauvegarder_dit(categorie_active, code_selectionne, dit_code, dit_actuel)
                                    st.success(f"✅ DIT {dit_code} généré et enregistré ({len(ia_result.get('etapes', []))} étapes).")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur génération IA : {e}")

                    with col_del:
                        if existe and st.button("🗑️ Supprimer", key=f"del_dit_{code_selectionne}_{dit_code}"):
                            supprimer_dit(categorie_active, code_selectionne, dit_code)
                            st.success(f"DIT {dit_code} supprimé.")
                            st.rerun()

                    st.divider()

                    # ── Formulaire DIT ──
                    if dit_actuel is None:
                        dit_actuel = nouveau_dit(dit_code, op_choisie)

                    with st.form(key=f"form_dit_{code_selectionne}_{dit_code}"):
                        st.markdown(f"#### ✏️ Édition — {dit_code}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            titre = st.text_input("Titre", value=dit_actuel.get("titre", ""), key=f"dit_titre_{dit_code}")
                        with col2:
                            revision = st.text_input("Révision", value=dit_actuel.get("revision", "A"), key=f"dit_rev_{dit_code}")
                        with col3:
                            redige_par = st.text_input("Rédigé par", value=dit_actuel.get("redige_par", ""), key=f"dit_red_{dit_code}")

                        col4, col5 = st.columns(2)
                        with col4:
                            epi_str = st.text_area(
                                "EPI requis (1 par ligne)",
                                value="\n".join(dit_actuel.get("epi_requis", [])),
                                height=80,
                                key=f"dit_epi_{dit_code}",
                            )
                        with col5:
                            outillage_str = st.text_area(
                                "Outillage requis (1 par ligne)",
                                value="\n".join(dit_actuel.get("outillage_requis", [])),
                                height=80,
                                key=f"dit_out_{dit_code}",
                            )

                        st.markdown("**Étapes de l'instruction**")
                        etapes = dit_actuel.get("etapes", [])
                        df_etapes = pd.DataFrame(etapes) if etapes else pd.DataFrame(
                            columns=["no", "instruction", "point_vigilance"]
                        )
                        for c in ["no", "instruction", "point_vigilance"]:
                            if c not in df_etapes.columns:
                                df_etapes[c] = ""
                        edited_etapes = st.data_editor(
                            df_etapes[["no", "instruction", "point_vigilance"]],
                            num_rows="dynamic",
                            use_container_width=True,
                            key=f"dit_etapes_{code_selectionne}_{dit_code}",
                            column_config={
                                "no": st.column_config.NumberColumn("N°", width="small", min_value=1),
                                "instruction": st.column_config.TextColumn("Instruction", width="large"),
                                "point_vigilance": st.column_config.TextColumn("Point de vigilance", width="medium"),
                            },
                        )

                        criteres = st.text_area(
                            "Critères d'acceptation",
                            value=dit_actuel.get("criteres_acceptation", ""),
                            height=60,
                            key=f"dit_crit_{dit_code}",
                        )
                        securite = st.text_area(
                            "Notes de sécurité",
                            value=dit_actuel.get("notes_securite", ""),
                            height=60,
                            key=f"dit_sec_{dit_code}",
                        )

                        submitted = st.form_submit_button("💾 Enregistrer le DIT", type="primary")
                        if submitted:
                            dit_sauvegarde = {
                                **dit_actuel,
                                "titre": titre,
                                "revision": revision,
                                "redige_par": redige_par,
                                "epi_requis": [l.strip() for l in epi_str.splitlines() if l.strip()],
                                "outillage_requis": [l.strip() for l in outillage_str.splitlines() if l.strip()],
                                "etapes": edited_etapes.fillna("").to_dict("records"),
                                "criteres_acceptation": criteres,
                                "notes_securite": securite,
                            }
                            sauvegarder_dit(categorie_active, code_selectionne, dit_code, dit_sauvegarde)
                            st.success(f"✅ DIT {dit_code} enregistré ({len(edited_etapes)} étapes).")

    with tab_zone:
        # ── Export PDF ────────────────────────────────────────────────────────
        st.markdown("### 📄 Export PDF")
        st.caption("Génère un PDF complet du dossier qualité prêt à imprimer ou archiver.")

        sections_dispo = {
            "garde": "Fiche de garde",
            "amdec_produit": "AMDEC Produit",
            "amdec_process": "AMDEC Process",
            "gamme": "Gamme de production",
        }
        sections_choisies = st.multiselect(
            "Sections à inclure",
            options=list(sections_dispo.keys()),
            default=list(sections_dispo.keys()),
            format_func=lambda x: sections_dispo[x],
            key=f"pdf_sections_{code_selectionne}",
        )
        if st.button("📄 Générer le PDF", key=f"btn_pdf_{code_selectionne}"):
            try:
                pdf_bytes = exporter_dossier_pdf(
                    metadata=meta,
                    amdec_produit=data.get("amdec_produit", {}),
                    amdec_process=data.get("amdec_process", {}),
                    gamme=data.get("gamme", {}),
                    sections=sections_choisies or None,
                )
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"dossier_qualite_{code_selectionne}.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{code_selectionne}",
                )
                st.success(f"PDF prêt — {len(pdf_bytes):,} octets.")
            except Exception as e:
                st.error(f"Erreur génération PDF : {e}")

        st.divider()
        st.markdown("### Modifier le statut")
        nouveau_statut = st.selectbox(
            "Statut",
            options=["valide", "brouillon", "obsolete"],
            index=["valide", "brouillon", "obsolete"].index(meta.get("statut", "valide"))
                if meta.get("statut") in ("valide", "brouillon", "obsolete") else 0,
            key="edit_statut",
        )
        nouveau_approuve = st.text_input("Approuvé par", value=meta.get("approuve_par") or "", key="edit_approuve")

        if st.button("💾 Enregistrer les modifications"):
            meta["statut"] = nouveau_statut
            meta["approuve_par"] = nouveau_approuve or None
            sauvegarder_modifications(categorie_active, code_selectionne, meta)
            st.success(f"Référence `{code_selectionne}` mise à jour.")

        st.divider()
        st.markdown("### ⚠️ Zone dangereuse")
        st.warning(
            "La suppression est définitive depuis l'app, mais une **sauvegarde** est créée "
            "automatiquement dans `backups/AAAA-MM-JJ/`."
        )
        confirm = st.text_input(
            f"Pour confirmer, taper le code exact `{code_selectionne}` :",
            key="confirm_delete",
        )
        if st.button("🗑️ Supprimer définitivement", type="primary", disabled=(confirm != code_selectionne)):
            try:
                backup = supprimer_reference(categorie_active, code_selectionne, sauvegarde=True)
                st.success(
                    f"Référence `{code_selectionne}` supprimée. "
                    f"Sauvegarde : `{backup.relative_to(ROOT) if backup else 'aucune'}`"
                )
                st.info("Recharge la page pour rafraîchir la liste.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ─── Section Sauvegardes (en dehors des tabs de référence) ─────────────────
    st.divider()
    st.subheader("💾 Sauvegardes automatiques")

    col_backup_left, col_backup_right = st.columns([3, 1])
    with col_backup_left:
        sauvegardes = lister_sauvegardes()
        if not sauvegardes:
            st.info("Aucune sauvegarde trouvée. Le premier démarrage crée automatiquement une sauvegarde.")
        else:
            rapport = st.session_state.get("rapport_backup", {})
            if rapport.get("sauvegarde_creee"):
                st.success(f"Sauvegarde créée aujourd'hui.")
            elif rapport.get("erreur"):
                st.error(f"Erreur sauvegarde : {rapport['erreur']}")

            import pandas as pd
            df_bk = pd.DataFrame([{
                "Date": s["date"],
                "Taille (Mo)": s["taille_mo"],
            } for s in sauvegardes])
            st.dataframe(df_bk, use_container_width=True, hide_index=True)

    with col_backup_right:
        if st.button("💾 Forcer une sauvegarde maintenant"):
            try:
                chemin = faire_sauvegarde(force=True)
                st.success(f"Sauvegarde créée : `{chemin.name}`")
            except Exception as e:
                st.error(f"Erreur : {e}")

    if sauvegardes:
        st.markdown("**Restaurer une sauvegarde**")
        st.warning(
            "La restauration remplace l'intégralité de la base actuelle. "
            "L'état courant est sauvegardé dans `backups/restauration/` avant l'opération."
        )
        date_restore = st.selectbox(
            "Choisir la date de restauration",
            [s["date"] for s in sauvegardes],
            key="select_restauration",
        )
        confirm_restore = st.text_input(
            "Taper **RESTAURER** pour confirmer :", key="confirm_restauration"
        )
        if st.button("♻️ Restaurer", type="primary", disabled=(confirm_restore != "RESTAURER")):
            try:
                restaurer_sauvegarde(date_restore)
                st.success(f"Base restaurée depuis le {date_restore}. Rechargez l'application.")
                st.session_state["backup_demarrage_fait"] = False
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.stop()  # Ne pas exécuter la page Nouveau produit en dessous

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 : NOUVEAU PRODUIT (par défaut)
# ═════════════════════════════════════════════════════════════════════════════

st.title(f"Qual.IA — {categorie_active.icone} {categorie_active.nom}")
st.caption(f"Catégorie active : {categorie_active.description}")
st.divider()

# ─── Session state ───────────────────────────────────────────────────────────

for key, default in [
    ("resultat_similarite", None),
    ("brief", None),
    ("dossier_genere", None),
    ("plan_prefill", {}),
    ("plan_nom", None),
    ("variantes_config", []),
    ("dossiers_variantes", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Bandeau reprise brouillon ────────────────────────────────────────────────

def _chemin_brouillon(cat_code: str, username: str) -> Path:
    return ROOT / "brouillons" / cat_code / f"{username}.json"

def _sauvegarder_brouillon(cat_code: str, username: str, brief: dict, dossier: dict, resultat) -> None:
    import dataclasses
    chemin = _chemin_brouillon(cat_code, username)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "brief": brief,
        "dossier": dossier,
        "resultat": {
            "reference": resultat.reference,
            "designation": resultat.designation,
            "score": resultat.score,
            "mode": resultat.mode,
            "detail_scores": resultat.detail_scores,
            "avertissements": resultat.avertissements,
            "metadata": resultat.metadata,
            "categorie": getattr(resultat, "categorie", cat_code),
        },
        "sauvegarde_le": __import__("datetime").datetime.now().isoformat(),
    }
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def _charger_brouillon(cat_code: str, username: str) -> dict | None:
    chemin = _chemin_brouillon(cat_code, username)
    if not chemin.exists():
        return None
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)

def _supprimer_brouillon(cat_code: str, username: str) -> None:
    chemin = _chemin_brouillon(cat_code, username)
    if chemin.exists():
        chemin.unlink()

brouillon_existant = _charger_brouillon(cat_code_selectionne, user["username"])
if brouillon_existant and st.session_state.dossier_genere is None:
    date_bk = brouillon_existant.get("sauvegarde_le", "")[:16].replace("T", " à ")
    with st.container(border=True):
        col_bk1, col_bk2, col_bk3 = st.columns([4, 1, 1])
        col_bk1.markdown(f"**📝 Brouillon en cours** — sauvegardé le {date_bk}  \n"
                         f"Brief : {brouillon_existant['brief'].get('designation_client', '—')}")
        if col_bk2.button("↩️ Reprendre", use_container_width=True, type="primary"):
            from backend.similarity_engine import ResultatSimilarite
            r = brouillon_existant["resultat"]
            res_restore = ResultatSimilarite(
                reference=r["reference"],
                designation=r["designation"],
                score=r["score"],
                mode=r["mode"],
                detail_scores=r["detail_scores"],
                avertissements=r["avertissements"],
                metadata=r["metadata"],
                categorie=r.get("categorie", cat_code_selectionne),
            )
            st.session_state.brief = brouillon_existant["brief"]
            st.session_state.dossier_genere = brouillon_existant["dossier"]
            st.session_state.resultat_similarite = res_restore
        if col_bk3.button("🗑️ Ignorer", use_container_width=True):
            _supprimer_brouillon(cat_code_selectionne, user["username"])
            st.rerun()

# ─── ÉTAPE 0 : Import plan technique (optionnel) ─────────────────────────────

with st.expander("📐 Importer un plan technique (optionnel — pré-remplit le formulaire)", expanded=bool(st.session_state.plan_prefill)):
    st.caption("Glisse un plan PDF ou une image (PNG, JPG) — le système extrait automatiquement les dimensions.")

    plan_col1, plan_col2 = st.columns([3, 1])
    with plan_col1:
        plan_upload = st.file_uploader(
            "Plan technique",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key=f"plan_upload_{cat_code_selectionne}",
            label_visibility="collapsed",
        )
    with plan_col2:
        analyser_plan_btn = st.button(
            "Analyser le plan →",
            type="primary",
            use_container_width=True,
            disabled=(plan_upload is None),
        )

    if analyser_plan_btn and plan_upload is not None:
        from backend.plan_reader import analyser_plan as _analyser_plan
        try:
            api_key = get_secret("ANTHROPIC_API_KEY")
        except ValueError as e:
            st.error(str(e))
            api_key = ""
        if api_key:
            with st.spinner("Lecture du plan en cours…"):
                try:
                    prefill = _analyser_plan(
                        plan_upload.read(),
                        plan_upload.name,
                        categorie=categorie_active,
                    )
                    st.session_state.plan_prefill = prefill
                    st.session_state.plan_nom = plan_upload.name
                    st.success(f"Plan analysé : **{plan_upload.name}** — données extraites ci-dessous.")
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

    if st.session_state.plan_prefill:
        pf = st.session_state.plan_prefill
        st.divider()
        plan_r1, plan_r2, plan_r3 = st.columns(3)
        plan_r1.markdown(
            f"**Désignation :** {pf.get('designation') or '—'}  \n"
            f"**Type :** `{pf.get('type_produit') or '—'}`  \n"
            f"**Matière :** `{pf.get('matiere') or '—'}`"
        )
        plan_r2.markdown(
            "  \n".join(
                f"**{p['label']} :** {pf.get(p['cle']) or '—'} (±{pf.get('tolerance_' + p['cle']) or '?'})"
                for p in categorie_active.parametres_numeriques()
            ) or "—"
        )
        traitements_plan = pf.get("traitements") or []
        plan_r3.markdown(
            f"**Traitements :** {', '.join(traitements_plan) if traitements_plan else '—'}  \n"
            f"**Notes :** {(pf.get('notes') or '—')[:120]}"
        )
        st.caption("Ces valeurs pré-remplissent le formulaire ci-dessous — modifiable à tout moment.")
        if st.button("Effacer les données du plan", key="clear_plan"):
            st.session_state.plan_prefill = {}
            st.session_state.plan_nom = None
            st.rerun()

# ─── ÉTAPE 1 : Brief ─────────────────────────────────────────────────────────

st.header("① Brief client")

with st.form("brief_form"):
    col1, col2 = st.columns(2)

    # Récupérer les données extraites du plan (si disponibles)
    pf = st.session_state.get("plan_prefill", {})

    with col1:
        st.subheader(f"Caractéristiques produit — {categorie_active.icone} {categorie_active.nom}")

        if pf:
            st.caption(f"📐 Pré-rempli depuis : `{st.session_state.get('plan_nom', 'plan importé')}`")

        vocab = categorie_active.vocabulaire()
        type_labels = vocab.get("types_produit", {})
        matiere_labels = vocab.get("matieres", {})
        traitements_disponibles = vocab.get("traitements", {})

        # ── Type de produit ──
        type_plan = pf.get("type_produit", "")
        if type_labels:
            idx_type = 0
            if type_plan and type_plan in type_labels:
                idx_type = list(type_labels.keys()).index(type_plan)
            type_choisi = st.selectbox(
                "Type de produit (liste prédéfinie pour cette catégorie)",
                options=list(type_labels.keys()),
                index=idx_type,
                format_func=lambda x: type_labels.get(x, x),
            )
        else:
            type_choisi = ""
            st.caption("ℹ️ Aucun type prédéfini pour cette catégorie — saisis ci-dessous.")
        type_libre = st.text_input(
            "→ ou saisir un type personnalisé (prioritaire si rempli)",
            placeholder="Ex: glace_carree, glace_polygonale…",
            value=type_plan if type_plan and type_plan not in type_labels else "",
            key=f"type_libre_{cat_code_selectionne}",
        )
        type_produit = type_libre.strip().lower().replace(" ", "_") if type_libre.strip() else type_choisi

        st.markdown("---")

        # ── Matière ──
        matiere_plan = pf.get("matiere", "")
        if matiere_labels:
            idx_matiere = 0
            if matiere_plan and matiere_plan in matiere_labels:
                idx_matiere = list(matiere_labels.keys()).index(matiere_plan)
            matiere_choisie = st.selectbox(
                "Matière (liste prédéfinie pour cette catégorie)",
                options=list(matiere_labels.keys()),
                index=idx_matiere,
                format_func=lambda x: matiere_labels.get(x, x),
            )
        else:
            matiere_choisie = ""
            st.caption("ℹ️ Aucune matière prédéfinie pour cette catégorie — saisis ci-dessous.")
        matiere_libre = st.text_input(
            "→ ou saisir une matière personnalisée (prioritaire si rempli)",
            placeholder="Ex: zircone, céramique…",
            value=matiere_plan if matiere_plan and matiere_plan not in matiere_labels else "",
            key=f"matiere_libre_{cat_code_selectionne}",
        )
        matiere = matiere_libre.strip().lower().replace(" ", "_") if matiere_libre.strip() else matiere_choisie

        st.markdown("---")

        # ── Traitements ──
        traitements_plan = [t for t in (pf.get("traitements") or []) if t in traitements_disponibles]
        traitements_plan_libres = [t for t in (pf.get("traitements") or []) if t not in traitements_disponibles]
        if traitements_disponibles:
            default_traitements = traitements_plan if traitements_plan else []
            traitements_selectionnes = st.multiselect(
                "Traitements (liste — sélection multiple)",
                options=list(traitements_disponibles.keys()),
                default=default_traitements,
                format_func=lambda x: traitements_disponibles.get(x, x),
            )
        else:
            traitements_selectionnes = []
            st.caption("ℹ️ Aucun traitement prédéfini pour cette catégorie.")
        traitements_autres_str = st.text_input(
            "→ Ajouter d'autres traitements (séparer par virgule)",
            placeholder="Ex: depot_DLC, gravure_laser",
            value=", ".join(traitements_plan_libres),
            key=f"traitements_autres_{cat_code_selectionne}",
        )

        # ── Typologies (compositions/variantes) par traitement ──
        typologies_catalogue = charger_typologies(categorie_active)
        if typologies_catalogue:
            st.markdown("**🎨 Composition / typologie** (sélectionner si applicable)")
            st.caption(
                "Chaque traitement peut avoir plusieurs compositions différentes "
                "(stack de couches, outillage et méthode différents). "
                "Sélectionnez uniquement pour les traitements que vous avez cochés."
            )
            for code_t, typo_dict in typologies_catalogue.items():
                label_t = traitements_disponibles.get(code_t, code_t)
                options_typo = ["(aucune)"] + list(typo_dict.keys())

                def _fmt_typo(x, _typo_dict=typo_dict):
                    if x == "(aucune)":
                        return "(aucune — non spécifiée)"
                    nom = _typo_dict.get(x, {}).get("nom", x)
                    return f"{x} — {nom}"

                st.selectbox(
                    f"Typologie pour : {label_t}",
                    options=options_typo,
                    format_func=_fmt_typo,
                    key=f"typo_{cat_code_selectionne}_{code_t}",
                )

        st.markdown("---")

        designation_client = st.text_input(
            "Désignation client (texte libre)",
            placeholder="Ex: Glace saphir Ø31mm CN+AR — Montre XY",
            value=pf.get("designation", ""),
        )

    with col2:
        st.subheader("Dimensions")
        params_num = categorie_active.parametres_numeriques()
        valeurs_dim = {}
        tolerances_dim = {}
        for p in params_num:
            cle = p["cle"]
            label = p["label"]
            obligatoire = p.get("obligatoire", True)
            p_min = float(p.get("min", 0.0))
            p_max = float(p.get("max", 1000.0))
            tol_default = float(p.get("tolerance_default", 0.05))
            step = float(p.get("step", 0.1))
            fmt = p.get("format", "%.2f")

            val_plan = pf.get(cle)
            if obligatoire:
                default_val = float(max(p_min, min(p_max, val_plan))) if val_plan else p_min
            else:
                default_val = float(max(0.0, min(p_max, val_plan))) if val_plan else 0.0

            suffix = " *" if obligatoire else " — 0 si inconnu"
            valeurs_dim[cle] = st.number_input(
                f"{label}{suffix}",
                min_value=0.0 if not obligatoire else p_min,
                max_value=p_max,
                value=default_val,
                step=step,
                format=fmt,
                key=f"dim_{cle}_{cat_code_selectionne}",
            )
            tol_plan = pf.get(f"tolerance_{cle}")
            val_tol = float(max(0.001, min(50.0, tol_plan))) if tol_plan else tol_default
            tolerances_dim[cle] = st.number_input(
                f"Tolérance {label} (±)",
                min_value=0.001,
                max_value=50.0,
                value=val_tol,
                step=0.001,
                format="%.3f",
                key=f"tol_{cle}_{cat_code_selectionne}",
            )

    st.subheader("Exigences spéciales")
    exigences_speciales = st.text_area(
        "Exigences particulières (optionnel)",
        placeholder="Ex: Transmission ≥ 94%…",
        value=pf.get("notes", "") or "",
        height=80,
    )

    submitted = st.form_submit_button("Analyser la similarité →", type="primary", use_container_width=True)

# ─── Traitement formulaire ────────────────────────────────────────────────────

if submitted:
    # Fusionner traitements cochés + traitements libres saisis
    traitements_libres = [
        t.strip().lower().replace(" ", "_")
        for t in (traitements_autres_str or "").split(",")
        if t.strip()
    ]
    codes_uniques = list(dict.fromkeys(traitements_selectionnes + traitements_libres))

    # Associer la typologie sélectionnée (le cas échéant) à chaque traitement
    traitements_finaux = []
    for code in codes_uniques:
        typo_key = f"typo_{cat_code_selectionne}_{code}"
        typo_choisie = st.session_state.get(typo_key)
        if typo_choisie and typo_choisie != "(aucune)":
            traitements_finaux.append({"code": code, "typologie": typo_choisie})
        else:
            traitements_finaux.append(code)

    erreurs = []
    if not type_produit:
        erreurs.append("Type de produit obligatoire (saisir si 'Autre').")
    if not matiere:
        erreurs.append("Matière obligatoire (saisir si 'Autre').")
    if not traitements_finaux:
        erreurs.append("Au moins un traitement requis (liste ou champ libre).")

    if erreurs:
        for e in erreurs:
            st.error(e)
    else:
        dimensions = {}
        for p in params_num:
            cle = p["cle"]
            v = valeurs_dim[cle]
            dimensions[cle] = v if (p.get("obligatoire", True) or v > 0) else None
            dimensions[f"tolerance_{cle}"] = tolerances_dim[cle]

        # ── Validation des dimensions ──────────────────────────────────────
        erreurs_dim = []
        for p in params_num:
            cle = p["cle"]
            val = valeurs_dim[cle]
            label_dim = p["label"]
            obligatoire_dim = p.get("obligatoire", True)
            # Diamètre : obligatoire, entre 0 (exclu) et 200 mm
            if "diametre" in cle or "diam" in cle:
                if val <= 0:
                    erreurs_dim.append(f"{label_dim} doit être supérieur à 0 mm.")
                elif val >= 200:
                    erreurs_dim.append(f"{label_dim} doit être inférieur à 200 mm (valeur : {val} mm).")
            # Épaisseur : optionnelle, mais si saisie doit être entre 0 (exclu) et 50 mm
            if "epaisseur" in cle:
                if val > 0 and val >= 50:
                    erreurs_dim.append(f"{label_dim} doit être inférieure à 50 mm si saisie (valeur : {val} mm).")
            # Tolérance : doit être > 0
            tol_val = tolerances_dim.get(cle, 0)
            if tol_val <= 0:
                erreurs_dim.append(f"La tolérance de {label_dim} doit être supérieure à 0.")

        if erreurs_dim:
            for e in erreurs_dim:
                st.error(e)
        else:
            brief = brief_depuis_formulaire(
                type_produit=type_produit,
                matiere=matiere,
                traitements=traitements_finaux,
                dimensions=dimensions,
            )
            brief["designation_client"] = designation_client
            brief["exigences_speciales"] = exigences_speciales

            with st.spinner("Analyse de similarité…"):
                resultat = trouver_meilleure_reference(brief, categorie_active)

            st.session_state.brief = brief
            st.session_state.resultat_similarite = resultat
            st.session_state.dossier_genere = None
            st.session_state.dossiers_variantes = None

# ─── VARIANTES : configuration dans le brief ─────────────────────────────────

st.divider()
st.subheader("🔀 Variantes (optionnel)")
st.caption("Le client veut la même pièce avec **plusieurs revêtements différents** ? Coche la case ci-dessous et ajoute une ligne par article.")

mode_variantes = st.checkbox(
    "Générer plusieurs variantes pour ce brief",
    value=bool(st.session_state.variantes_config),
    key="mode_variantes_actif",
)

if mode_variantes:
    vocab_v = categorie_active.vocabulaire()
    traitements_v = vocab_v.get("traitements", {})
    variantes_cfg = list(st.session_state.variantes_config)

    nb_v = st.number_input("Nombre de variantes", min_value=2, max_value=10,
                           value=max(len(variantes_cfg), 2), step=1, key="nb_variantes")
    while len(variantes_cfg) < nb_v:
        variantes_cfg.append({"article": "", "traitements": [], "designation": ""})
    variantes_cfg = variantes_cfg[:nb_v]

    for i, var in enumerate(variantes_cfg):
        with st.container(border=True):
            vc1, vc2, vc3 = st.columns([2, 3, 3])
            with vc1:
                variantes_cfg[i]["article"] = st.text_input(
                    f"N° article — variante {i+1}",
                    value=var.get("article", ""),
                    placeholder="Ex: MA696.361",
                    key=f"var_article_{i}",
                )
            with vc2:
                opts_t = list(traitements_v.keys())
                default_t = [t for t in var.get("traitements", []) if t in opts_t]
                variantes_cfg[i]["traitements"] = st.multiselect(
                    "Traitement(s) spécifique à cette variante",
                    options=opts_t,
                    default=default_t,
                    format_func=lambda x: traitements_v.get(x, x),
                    key=f"var_traitements_{i}",
                )
            with vc3:
                variantes_cfg[i]["designation"] = st.text_input(
                    "Désignation libre (optionnel)",
                    value=var.get("designation", ""),
                    placeholder="Ex: Glace Ø31mm MET CN",
                    key=f"var_designation_{i}",
                )

    st.session_state.variantes_config = variantes_cfg

    variantes_valides = [v for v in variantes_cfg if v.get("article", "").strip() and v.get("traitements")]
    articles_uniques = len({v["article"] for v in variantes_valides}) == len(variantes_valides)

    if not articles_uniques:
        st.warning("Deux variantes ont le même N° article.")
    elif len(variantes_valides) < nb_v:
        st.warning(f"{nb_v - len(variantes_valides)} variante(s) incomplète(s) — remplis le N° article et au moins un traitement.")
    else:
        st.success(f"✅ {len(variantes_valides)} variantes configurées. Clique sur **Analyser la similarité →** ci-dessus pour continuer.")
else:
    st.session_state.variantes_config = []

# ─── ÉTAPE 2 : Similarité ────────────────────────────────────────────────────

if st.session_state.resultat_similarite is not None:
    st.divider()
    st.header("② Résultat de l'analyse")

    res = st.session_state.resultat_similarite
    brief = st.session_state.brief
    score_pct = f"{res.score:.0%}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Référence source :** `{res.reference}` — {res.designation}")

    # Affichage du score avec composants natifs
    if res.mode == "automatique":
        st.success(f"Score de similarité : **{score_pct}** — Adaptation automatique possible")
    elif res.mode == "avertissement":
        st.warning(f"Score de similarité : **{score_pct}** — Vérification recommandée avant validation")
    else:
        st.error(
            f"Score de similarité : **{score_pct}** — Trop bas pour une adaptation directe. "
            "Tu peux quand même utiliser cette référence comme **trame de structure** : "
            "l'IA proposera un dossier à compléter, à éditer fortement à l'étape ④."
        )

    with st.expander("Détail des scores par critère"):
        criteres_config = categorie_active.criteres_similarite()
        lignes = ["| Critère | Poids | Score | Contribution |", "|---|---|---|---|"]
        for critere, params_c in criteres_config.items():
            score_critere = res.detail_scores.get(critere, 0)
            poids = params_c.get("poids", 0)
            label = params_c.get("description", critere)
            lignes.append(f"| {label} | {poids:.0%} | {score_critere:.0%} | {score_critere * poids:.2%} |")
        st.markdown("\n".join(lignes))

    if res.avertissements:
        for a in res.avertissements:
            st.warning(a)

    # ── Bouton variantes si configurées ──
    variantes_pretes = [v for v in st.session_state.variantes_config if v.get("article", "").strip() and v.get("traitements")]
    if variantes_pretes and len({v["article"] for v in variantes_pretes}) == len(variantes_pretes):
        st.divider()
        st.info(f"**{len(variantes_pretes)} variante(s) configurées dans le brief** → {', '.join(v['article'] for v in variantes_pretes)}")
        if st.button(f"⚡ Générer les {len(variantes_pretes)} variantes →", type="primary", use_container_width=True, key="btn_variantes"):
            try:
                api_key = get_secret("ANTHROPIC_API_KEY")
            except ValueError as e:
                st.error(str(e))
                api_key = ""
            if api_key:
                ph_v = st.empty()
                ph_v.info(f"Génération de {len(variantes_pretes)} variantes… (30–90 secondes)")
                try:
                    dossiers = generer_dossier_variantes(
                        brief_base=st.session_state.brief,
                        variantes=variantes_pretes,
                        resultat_similarite=st.session_state.resultat_similarite,
                        categorie=categorie_active,
                    )
                    st.session_state.dossiers_variantes = dossiers
                    ph_v.success(f"✅ {len(dossiers)} variantes générées !")
                    st.rerun()
                except Exception as e:
                    ph_v.error(f"Erreur : {e}")

# ─── ÉTAPE 3 : Génération ────────────────────────────────────────────────────

if (
    st.session_state.resultat_similarite is not None
    and st.session_state.dossier_genere is None
    and st.session_state.dossiers_variantes is None
):
    st.divider()
    st.header("③ Génération des documents")
    res = st.session_state.resultat_similarite
    brief = st.session_state.brief

    if res.mode == "manuelle":
        st.warning(
            f"⚠️ **Mode création assistée** — Score {score_pct} faible. "
            f"`{res.reference}` ne sera utilisée que comme **trame structurelle** "
            f"(colonnes, format, type d'opérations). Les contenus métier devront être "
            f"largement révisés à l'étape ④. La confiance globale sera basse."
        )
    else:
        _pn = categorie_active.parametres_numeriques()
        _dim_info = f"{_pn[0]['label']}={brief['dimensions'].get(_pn[0]['cle'], '?')}" if _pn else ""
        st.info(
            f"Prêt à générer **AMDEC Produit + AMDEC Process + Gamme** "
            f"en adaptant `{res.reference}` ({_dim_info})."
        )

    label_btn = "Générer en mode création assistée →" if res.mode == "manuelle" else "Générer les documents IA →"
    if st.button(label_btn, type="primary"):
        try:
            api_key = get_secret("ANTHROPIC_API_KEY")
        except ValueError as e:
            st.error(str(e))
            api_key = ""
        if api_key:
            placeholder = st.empty()
            placeholder.info("Génération en cours… (30–90 secondes). En cas de surcharge API, jusqu'à 3 tentatives automatiques.")
            try:
                dossier = generer_dossier_complet(
                    brief=st.session_state.brief,
                    resultat_similarite=res,
                    categorie=categorie_active,
                )
                st.session_state.dossier_genere = dossier
                placeholder.success("Documents générés avec succès !")
            except Exception as e:
                err_str = str(e)
                if "overloaded" in err_str.lower() or "529" in err_str:
                    placeholder.error(
                        "Les serveurs Claude sont momentanément surchargés (erreur 529). "
                        "Patiente 1–2 minutes puis réessaie."
                    )
                elif "rate_limit" in err_str.lower() or "429" in err_str:
                    placeholder.error(
                        "Limite de requêtes API atteinte (erreur 429). "
                        "Patiente quelques secondes puis réessaie."
                    )
                else:
                    placeholder.error(f"Erreur lors de la génération : {e}")

# ─── ÉTAPE 4 : Validation BT ─────────────────────────────────────────────────

if st.session_state.dossier_genere is not None:
    dossier = st.session_state.dossier_genere
    meta_gen = dossier.get("metadonnees_generation", {})
    brief = st.session_state.brief

    st.divider()
    st.header("④ Validation Bureau Technique")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Similarité source", f"{meta_gen.get('score_similarite', 0):.0%}")
    col2.metric("Confiance AMDEC Produit", f"{meta_gen.get('confiance_amdec_produit', 0):.0%}")
    col3.metric("Confiance AMDEC Process", f"{meta_gen.get('confiance_amdec_process', 0):.0%}")
    col4.metric("Confiance Gamme", f"{meta_gen.get('confiance_gamme', 0):.0%}")

    tous_avertissements = (
        meta_gen.get("avertissements_similarite", [])
        + meta_gen.get("avertissements_amdec_produit", [])
        + meta_gen.get("avertissements_amdec_process", [])
        + meta_gen.get("avertissements_gamme", [])
    )
    if tous_avertissements:
        with st.expander(f"⚠️ {len(tous_avertissements)} point(s) à vérifier avant validation"):
            for a in tous_avertissements:
                st.warning(a)

    st.info("✏️ **Mode édition** : modifie les cellules directement, ajoute des lignes via la dernière ligne vide ou supprime via la corbeille à gauche. Les changements sont pris en compte à l'export.")

    import pandas as pd

    tab1, tab2, tab3 = st.tabs(["AMDEC Produit", "AMDEC Process", "Gamme de Production"])

    # ─── AMDEC Produit ───────────────────────────────────────────────────────
    with tab1:
        amdec_p = dossier.get("amdec_produit", {})
        st.caption(f"Référence : {amdec_p.get('reference', '')} | {amdec_p.get('designation', '')}")
        modes = amdec_p.get("modes_defaillance", [])
        df_p = pd.DataFrame(modes)

        colonnes_p = ["no", "famille", "fonction_exigence", "caracteristique_critique",
                      "mode_defaillance", "effets_defaillance", "G", "causes_defaillance",
                      "O", "controles_existants", "D", "classe_criticite",
                      "actions_correctives", "responsable", "delai"]
        for c in colonnes_p:
            if c not in df_p.columns:
                df_p[c] = ""
        df_p = df_p[colonnes_p]

        edited_p = st.data_editor(
            df_p,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_amdec_produit",
            column_config={
                "no": st.column_config.TextColumn("N°", width="small"),
                "famille": st.column_config.SelectboxColumn(
                    "Famille",
                    options=["optique", "esthetique", "geometrique", "etancheite", "tracabilite"],
                    width="small",
                ),
                "fonction_exigence": st.column_config.TextColumn("Fonction / Exigence"),
                "caracteristique_critique": st.column_config.TextColumn("Caract. critique"),
                "mode_defaillance": st.column_config.TextColumn("Mode défaillance"),
                "effets_defaillance": st.column_config.TextColumn("Effets"),
                "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                "causes_defaillance": st.column_config.TextColumn("Causes"),
                "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                "controles_existants": st.column_config.TextColumn("Contrôles"),
                "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
                "classe_criticite": st.column_config.TextColumn("Criticité"),
                "actions_correctives": st.column_config.TextColumn("Actions correctives"),
                "responsable": st.column_config.TextColumn("Responsable", width="small"),
                "delai": st.column_config.TextColumn("Délai", width="small"),
            },
        )
        st.session_state.dossier_genere["amdec_produit"]["modes_defaillance"] = edited_p.fillna("").to_dict("records")

        # Calculer IPR récap
        if not edited_p.empty and "G" in edited_p and "O" in edited_p and "D" in edited_p:
            df_calc = edited_p.dropna(subset=["G", "O", "D"]).copy()
            if not df_calc.empty:
                df_calc["IPR"] = df_calc["G"].astype(int) * df_calc["O"].astype(int) * df_calc["D"].astype(int)
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("🔴 IPR > 100 (action obligatoire)", (df_calc["IPR"] > 100).sum())
                col_r2.metric("🟠 IPR 41–100 (surveillance)", ((df_calc["IPR"] > 40) & (df_calc["IPR"] <= 100)).sum())
                col_r3.metric("🟢 IPR ≤ 40 (acceptable)", (df_calc["IPR"] <= 40).sum())

    # ─── AMDEC Process ───────────────────────────────────────────────────────
    with tab2:
        amdec_pr = dossier.get("amdec_process", {})
        st.caption(f"Référence : {amdec_pr.get('reference', '')} | {amdec_pr.get('designation', '')}")
        modes_pr = amdec_pr.get("modes_defaillance", [])
        df_pr = pd.DataFrame(modes_pr)

        colonnes_pr = ["no", "operation_process", "etape_poste", "mode_defaillance",
                       "effets_produit", "G", "causes_process", "O", "controles_process",
                       "D", "classe_criticite", "actions_correctives", "responsable",
                       "delai", "parametre_cle", "valeur_cible"]
        for c in colonnes_pr:
            if c not in df_pr.columns:
                df_pr[c] = ""
        df_pr = df_pr[colonnes_pr]

        edited_pr = st.data_editor(
            df_pr,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_amdec_process",
            column_config={
                "no": st.column_config.TextColumn("N°", width="small"),
                "operation_process": st.column_config.TextColumn("Opération process"),
                "etape_poste": st.column_config.TextColumn("Étape / Poste"),
                "mode_defaillance": st.column_config.TextColumn("Mode défaillance"),
                "effets_produit": st.column_config.TextColumn("Effets produit"),
                "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                "causes_process": st.column_config.TextColumn("Causes process"),
                "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                "controles_process": st.column_config.TextColumn("Contrôles"),
                "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
                "classe_criticite": st.column_config.TextColumn("Criticité"),
                "actions_correctives": st.column_config.TextColumn("Actions"),
                "responsable": st.column_config.TextColumn("Responsable", width="small"),
                "delai": st.column_config.TextColumn("Délai", width="small"),
                "parametre_cle": st.column_config.TextColumn("Paramètre clé"),
                "valeur_cible": st.column_config.TextColumn("Valeur cible"),
            },
        )
        st.session_state.dossier_genere["amdec_process"]["modes_defaillance"] = edited_pr.fillna("").to_dict("records")

    # ─── Gamme de Production ─────────────────────────────────────────────────
    with tab3:
        gamme = dossier.get("gamme", {})
        st.caption(f"Référence : {gamme.get('reference', '')} | {gamme.get('designation', '')}")
        operations = gamme.get("operations", [])
        df_g = pd.DataFrame(operations)

        colonnes_g = ["no_op", "designation", "description_detaillee", "poste_machine",
                      "outillage_fixture", "parametre_1", "valeur_1", "parametre_2",
                      "valeur_2", "parametre_3", "temps_min", "point_controle",
                      "moyen_controle", "frequence", "critere_acceptation",
                      "ref_dit", "ref_infor"]
        for c in colonnes_g:
            if c not in df_g.columns:
                df_g[c] = ""
        df_g = df_g[colonnes_g]

        edited_g = st.data_editor(
            df_g,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_gamme",
            column_config={
                "no_op": st.column_config.TextColumn("N° Op", width="small"),
                "designation": st.column_config.TextColumn("Désignation"),
                "description_detaillee": st.column_config.TextColumn("Description"),
                "poste_machine": st.column_config.TextColumn("Poste / Machine"),
                "outillage_fixture": st.column_config.TextColumn("Outillage"),
                "parametre_1": st.column_config.TextColumn("Paramètre 1"),
                "valeur_1": st.column_config.TextColumn("Valeur 1"),
                "parametre_2": st.column_config.TextColumn("Paramètre 2"),
                "valeur_2": st.column_config.TextColumn("Valeur 2"),
                "parametre_3": st.column_config.TextColumn("Paramètre 3"),
                "temps_min": st.column_config.NumberColumn("Temps (min)", min_value=0, width="small"),
                "point_controle": st.column_config.TextColumn("Point contrôle"),
                "moyen_controle": st.column_config.TextColumn("Moyen contrôle"),
                "frequence": st.column_config.TextColumn("Fréquence", width="small"),
                "critere_acceptation": st.column_config.TextColumn("Critère acceptation"),
                "ref_dit": st.column_config.TextColumn("Réf. DIT", width="small"),
                "ref_infor": st.column_config.TextColumn("Réf. Infor", width="small"),
            },
        )
        st.session_state.dossier_genere["gamme"]["operations"] = edited_g.fillna("").to_dict("records")

        if not edited_g.empty and "temps_min" in edited_g:
            temps_total = pd.to_numeric(edited_g["temps_min"], errors="coerce").fillna(0).sum()
            st.metric("⏱️ Temps total gamme", f"{int(temps_total)} min")

    # ─── Sauvegarde brouillon ─────────────────────────────────────────────────

    st.divider()
    col_brd1, col_brd2 = st.columns([3, 1])
    with col_brd1:
        st.caption("Tu peux sauvegarder ton travail en cours et reprendre plus tard sans tout reperdre.")
    with col_brd2:
        if st.button("💾 Sauvegarder en brouillon", use_container_width=True):
            try:
                _sauvegarder_brouillon(
                    cat_code_selectionne,
                    user["username"],
                    st.session_state.brief,
                    st.session_state.dossier_genere,
                    st.session_state.resultat_similarite,
                )
                st.success("Brouillon sauvegardé — tu peux fermer et reprendre plus tard.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    # ─── ÉTAPE 5 : Export Excel ───────────────────────────────────────────────

    # ── Enregistrer + soumettre au workflow (UNIQUE chemin de sauvegarde) ──
    st.divider()
    st.subheader("📋 Enregistrer et soumettre pour validation")
    st.caption(
        "Toute sauvegarde dans la base démarre obligatoirement le workflow de validation. "
        "La référence ne sera utilisable comme source pour de futurs dossiers qu'une fois libérée."
    )

    from backend.reference_saver import proposer_code_reference, enregistrer_reference, reference_existe

    code_propose_wf = proposer_code_reference(categorie_active, brief)

    wf_c1, wf_c2 = st.columns([2, 2])
    with wf_c1:
        code_wf_gen = st.text_input(
            "Code de la référence",
            value=code_propose_wf,
            help="Modifiable. Format conseillé : REF-XXX-NNN.",
            key="code_wf_gen_input",
        )
    with wf_c2:
        wf_commentaire = st.text_input(
            "Commentaire (optionnel)",
            placeholder="Ex: Généré depuis REF-GRS-001",
            key="wf_comment_gen",
        )

    overwrite_wf = False
    if reference_existe(categorie_active, code_wf_gen):
        st.warning(f"⚠️ La référence `{code_wf_gen}` existe déjà dans la catégorie {categorie_active.nom}.")
        overwrite_wf = st.checkbox("Écraser la référence existante", key="overwrite_wf_gen")

    st.caption(f"✍️ Signataire : **{user['nom']}**")

    if st.button("📋 Enregistrer et soumettre pour revue →", type="primary", use_container_width=True):
        try:
            ref_dir_wf = enregistrer_reference(
                categorie=categorie_active,
                code=code_wf_gen,
                brief=brief,
                dossier=dossier,
                acteur=user["nom"],
                commentaire_creation=f"Dossier généré depuis {meta_gen.get('reference_source', '?')}",
                overwrite=overwrite_wf,
            )
            # La ref démarre en brouillon avec workflow initialisé. On la soumet pour revue.
            ref_complete_wf = charger_reference_complete(categorie_active, code_wf_gen)
            meta_wf_gen = ref_complete_wf["metadata"]
            data_wf_gen = ref_complete_wf["data"]
            faire_transition(
                meta_wf_gen,
                action="soumettre",
                acteur=user["nom"],
                commentaire=wf_commentaire.strip() or "Soumis après génération IA",
                data=data_wf_gen,
            )
            sauvegarder_modifications(categorie_active, code_wf_gen, meta_wf_gen)
            _supprimer_brouillon(cat_code_selectionne, user["username"])
            ajouter_notification(
                ref=code_wf_gen,
                categorie=cat_code_selectionne,
                statut="en_revue",
                acteur=user["nom"],
                message=f"Nouveau dossier `{code_wf_gen}` soumis pour revue par {user['nom']}.",
            )
            gates_info = meta_wf_gen.get("workflow", {}).get("gates_requises", [])
            st.success(
                f"✅ `{code_wf_gen}` enregistré et soumis pour revue. "
                f"Gates requises : {' → '.join(gates_info)}. "
                f"Va dans **📋 Workflow** pour suivre la validation."
            )
        except FileExistsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Erreur : {e}")

    st.divider()
    st.header("⑤ Export Excel")

    _pn_exp = categorie_active.parametres_numeriques()
    _cle_exp = _pn_exp[0]["cle"] if _pn_exp else "diametre_mm"
    _val_exp = brief.get("dimensions", {}).get(_cle_exp, 0) or 0
    prefixe = f"NOUVEAU-{_val_exp:.0f}"
    exports_dir = ROOT / "exports"
    exports_dir.mkdir(exist_ok=True)

    col_e1, col_e2, col_e3 = st.columns(3)

    with col_e1:
        if st.button("Générer AMDEC Produit", use_container_width=True):
            from backend.excel_exporter import exporter_amdec_produit
            chemin = exporter_amdec_produit(dossier["amdec_produit"], f"{prefixe}_AMDEC_Produit.xlsx", exports_dir)
            with open(chemin, "rb") as f:
                st.download_button("Télécharger AMDEC Produit", f.read(), file_name=chemin.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_amdec_p")

    with col_e2:
        if st.button("Générer AMDEC Process", use_container_width=True):
            from backend.excel_exporter import exporter_amdec_process
            chemin = exporter_amdec_process(dossier["amdec_process"], f"{prefixe}_AMDEC_Process.xlsx", exports_dir)
            with open(chemin, "rb") as f:
                st.download_button("Télécharger AMDEC Process", f.read(), file_name=chemin.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_amdec_pr")

    with col_e3:
        if st.button("Générer Gamme", use_container_width=True):
            from backend.excel_exporter import exporter_gamme
            chemin = exporter_gamme(dossier["gamme"], f"{prefixe}_Gamme.xlsx", exports_dir)
            with open(chemin, "rb") as f:
                st.download_button("Télécharger Gamme", f.read(), file_name=chemin.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_gamme")

    st.divider()
    if st.button("Nouveau brief →"):
        _supprimer_brouillon(cat_code_selectionne, user["username"])
        st.session_state.resultat_similarite = None
        st.session_state.brief = None
        st.session_state.dossier_genere = None
        st.session_state.dossiers_variantes = None
        st.session_state.variantes_config = []

# ═════════════════════════════════════════════════════════════════════════════
# RÉSULTATS VARIANTES
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.dossiers_variantes is not None:
    import pandas as pd
    from backend.excel_exporter import exporter_amdec_produit, exporter_amdec_process, exporter_gamme
    from backend.reference_saver import enregistrer_variantes, reference_existe

    dossiers_v = st.session_state.dossiers_variantes
    brief_base_v = st.session_state.brief
    articles = list(dossiers_v.keys())

    st.divider()
    st.header(f"④ Validation — {len(articles)} variantes générées")
    st.caption("Chaque onglet correspond à une variante. Édite les cellules directement avant d'exporter.")

    # ── Métriques globales ──
    mc = st.columns(len(articles))
    for i, article in enumerate(articles):
        meta_v = dossiers_v[article]["metadonnees_generation"]
        mc[i].metric(
            article,
            f"Conf. moy. {(meta_v['confiance_amdec_produit'] + meta_v['confiance_amdec_process'] + meta_v['confiance_gamme']) / 3:.0%}",
            delta=f"source : {meta_v['reference_source']}",
        )

    # ── Tabs par variante ──
    tabs_v = st.tabs([f"🏷️ {a}" for a in articles])

    for tab, article in zip(tabs_v, articles):
        dossier_v = dossiers_v[article]
        variante_info = dossier_v.get("variante", {})

        with tab:
            st.caption(f"Traitements : {format_traitements_str(variante_info.get('traitements', []))} | {variante_info.get('designation', '')}")

            meta_v = dossier_v["metadonnees_generation"]
            mv1, mv2, mv3 = st.columns(3)
            mv1.metric("Confiance AMDEC Produit", f"{meta_v['confiance_amdec_produit']:.0%}")
            mv2.metric("Confiance AMDEC Process", f"{meta_v['confiance_amdec_process']:.0%}")
            mv3.metric("Confiance Gamme", f"{meta_v['confiance_gamme']:.0%}")

            avertissements_v = (
                meta_v.get("avertissements_similarite", [])
                + meta_v.get("avertissements_amdec_produit", [])
                + meta_v.get("avertissements_amdec_process", [])
                + meta_v.get("avertissements_gamme", [])
            )
            if avertissements_v:
                with st.expander(f"⚠️ {len(avertissements_v)} point(s) à vérifier"):
                    for aw in avertissements_v:
                        st.warning(aw)

            subtab_ap, subtab_apr, subtab_g = st.tabs(["AMDEC Produit", "AMDEC Process", "Gamme"])

            # ── AMDEC Produit ──
            with subtab_ap:
                colonnes_p = ["no", "famille", "fonction_exigence", "caracteristique_critique",
                              "mode_defaillance", "effets_defaillance", "G", "causes_defaillance",
                              "O", "controles_existants", "D", "classe_criticite",
                              "actions_correctives", "responsable", "delai"]
                modes_vp = dossier_v["amdec_produit"].get("modes_defaillance", [])
                df_vp = pd.DataFrame(modes_vp)
                for c in colonnes_p:
                    if c not in df_vp.columns:
                        df_vp[c] = ""
                df_vp = df_vp[colonnes_p]
                edited_vp = st.data_editor(df_vp, num_rows="dynamic", use_container_width=True,
                    key=f"veditor_p_{article}",
                    column_config={
                        "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                        "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                        "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
                        "famille": st.column_config.SelectboxColumn("Famille",
                            options=["optique", "esthetique", "geometrique", "etancheite", "tracabilite"], width="small"),
                    })
                st.session_state.dossiers_variantes[article]["amdec_produit"]["modes_defaillance"] = edited_vp.fillna("").to_dict("records")
                if not edited_vp.empty and {"G", "O", "D"}.issubset(edited_vp.columns):
                    df_ipr = edited_vp.dropna(subset=["G", "O", "D"]).copy()
                    if not df_ipr.empty:
                        df_ipr["IPR"] = df_ipr["G"].astype(int) * df_ipr["O"].astype(int) * df_ipr["D"].astype(int)
                        ci1, ci2, ci3 = st.columns(3)
                        ci1.metric("🔴 IPR > 100", (df_ipr["IPR"] > 100).sum())
                        ci2.metric("🟠 IPR 41–100", ((df_ipr["IPR"] > 40) & (df_ipr["IPR"] <= 100)).sum())
                        ci3.metric("🟢 IPR ≤ 40", (df_ipr["IPR"] <= 40).sum())

            # ── AMDEC Process ──
            with subtab_apr:
                colonnes_pr = ["no", "operation_process", "etape_poste", "mode_defaillance",
                               "effets_produit", "G", "causes_process", "O", "controles_process",
                               "D", "classe_criticite", "actions_correctives", "responsable",
                               "delai", "parametre_cle", "valeur_cible"]
                modes_vpr = dossier_v["amdec_process"].get("modes_defaillance", [])
                df_vpr = pd.DataFrame(modes_vpr)
                for c in colonnes_pr:
                    if c not in df_vpr.columns:
                        df_vpr[c] = ""
                df_vpr = df_vpr[colonnes_pr]
                edited_vpr = st.data_editor(df_vpr, num_rows="dynamic", use_container_width=True,
                    key=f"veditor_pr_{article}",
                    column_config={
                        "G": st.column_config.NumberColumn("G", min_value=1, max_value=10, width="small"),
                        "O": st.column_config.NumberColumn("O", min_value=1, max_value=10, width="small"),
                        "D": st.column_config.NumberColumn("D", min_value=1, max_value=10, width="small"),
                    })
                st.session_state.dossiers_variantes[article]["amdec_process"]["modes_defaillance"] = edited_vpr.fillna("").to_dict("records")

            # ── Gamme ──
            with subtab_g:
                colonnes_g = ["no_op", "designation", "description_detaillee", "poste_machine",
                              "outillage_fixture", "parametre_1", "valeur_1", "parametre_2",
                              "valeur_2", "parametre_3", "temps_min", "point_controle",
                              "moyen_controle", "frequence", "critere_acceptation",
                              "ref_dit", "ref_infor"]
                ops_vg = dossier_v["gamme"].get("operations", [])
                df_vg = pd.DataFrame(ops_vg)
                for c in colonnes_g:
                    if c not in df_vg.columns:
                        df_vg[c] = ""
                df_vg = df_vg[colonnes_g]
                edited_vg = st.data_editor(df_vg, num_rows="dynamic", use_container_width=True,
                    key=f"veditor_g_{article}",
                    column_config={
                        "temps_min": st.column_config.NumberColumn("Temps (min)", min_value=0, width="small"),
                    })
                st.session_state.dossiers_variantes[article]["gamme"]["operations"] = edited_vg.fillna("").to_dict("records")
                if not edited_vg.empty and "temps_min" in edited_vg:
                    temps_v = pd.to_numeric(edited_vg["temps_min"], errors="coerce").fillna(0).sum()
                    st.metric("⏱️ Temps total", f"{int(temps_v)} min")

            # ── Export Excel par variante ──
            st.markdown("**Export Excel**")
            exports_dir_v = ROOT / "exports"
            exports_dir_v.mkdir(exist_ok=True)
            ev1, ev2, ev3 = st.columns(3)
            with ev1:
                if st.button("AMDEC Produit", key=f"exp_ap_{article}", use_container_width=True):
                    ch = exporter_amdec_produit(dossier_v["amdec_produit"], f"{article}_AMDEC_Produit.xlsx", exports_dir_v)
                    with open(ch, "rb") as f:
                        st.download_button("⬇️ Télécharger", f.read(), file_name=ch.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_vap_{article}")
            with ev2:
                if st.button("AMDEC Process", key=f"exp_apr_{article}", use_container_width=True):
                    ch = exporter_amdec_process(dossier_v["amdec_process"], f"{article}_AMDEC_Process.xlsx", exports_dir_v)
                    with open(ch, "rb") as f:
                        st.download_button("⬇️ Télécharger", f.read(), file_name=ch.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_vapr_{article}")
            with ev3:
                if st.button("Gamme", key=f"exp_g_{article}", use_container_width=True):
                    ch = exporter_gamme(dossier_v["gamme"], f"{article}_Gamme.xlsx", exports_dir_v)
                    with open(ch, "rb") as f:
                        st.download_button("⬇️ Télécharger", f.read(), file_name=ch.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_vg_{article}")

    # ── Enregistrement en lot ──
    st.divider()
    st.header("⑥ Enregistrer les variantes et soumettre au workflow")
    st.caption(
        "Chaque variante devient une référence distincte avec son propre workflow de validation. "
        "Toutes démarrent en brouillon puis sont soumises pour revue BT."
    )

    overwrite_var = False
    articles_existants = [a for a in articles if reference_existe(categorie_active, a)]
    if articles_existants:
        st.warning(f"Articles déjà existants : {', '.join(articles_existants)}")
        overwrite_var = st.checkbox("Écraser les références existantes", key="overwrite_variantes")

    st.caption(f"✍️ Signataire : **{user['nom']}**")

    if st.button(f"📋 Enregistrer + soumettre les {len(articles)} variantes", type="primary", use_container_width=True):
        try:
            chemins = enregistrer_variantes(
                categorie=categorie_active,
                resultats_variantes=st.session_state.dossiers_variantes,
                brief_base=brief_base_v,
                acteur=user["nom"],
                overwrite=overwrite_var,
            )
            # Soumettre chaque variante pour revue
            for article in articles:
                try:
                    ref_v = charger_reference_complete(categorie_active, article)
                    meta_v = ref_v["metadata"]
                    data_v = ref_v["data"]
                    faire_transition(
                        meta_v, action="soumettre",
                        acteur=user["nom"],
                        commentaire=f"Variante {article} soumise après génération IA",
                        data=data_v,
                    )
                    sauvegarder_modifications(categorie_active, article, meta_v)
                except Exception:
                    pass
            for article in articles:
                ajouter_notification(
                    ref=article,
                    categorie=cat_code_selectionne,
                    statut="en_revue",
                    acteur=user["nom"],
                    message=f"Variante `{article}` soumise pour revue par {user['nom']}.",
                )
            st.success(
                f"✅ {len(chemins)} variante(s) enregistrées et soumises pour revue : {', '.join(articles)}. "
                f"Va dans **📋 Workflow** pour suivre la validation."
            )
        except FileExistsError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Erreur : {e}")

    st.divider()
    if st.button("Nouveau brief →", key="nouveau_brief_variantes"):
        st.session_state.resultat_similarite = None
        st.session_state.brief = None
        st.session_state.dossier_genere = None
        st.session_state.dossiers_variantes = None
        st.session_state.variantes_config = []
        st.rerun()


# ─── PAGE : Retouches articles ────────────────────────────────────────────────
if page == "🔧 Retouches":
    from backend.retouche_manager import (
        creer_retouche, lister_retouches, supprimer_retouche,
        stats_retouches, lister_articles_avec_retouches,
        retouches_vers_lignes_excel, RESULTATS,
    )
    from backend.excel_exporter import exporter_retouches

    st.header("🔧 Gestion des retouches")
    st.caption(
        "Documentez les opérations de reprise effectuées sur les pièces non conformes. "
        "Chaque fiche est rattachée à une référence article."
    )

    # ── Sélection de la référence article ────────────────────────────────────
    refs_dispo = lister_references(categorie_active)
    articles_existants = lister_articles_avec_retouches()

    col_ref, col_new = st.columns([3, 1])
    with col_ref:
        refs_codes = [r["reference"] for r in refs_dispo]
        if refs_codes:
            ref_choisie = st.selectbox(
                "Référence article",
                options=refs_codes,
                help="Sélectionner la référence pour laquelle consulter ou saisir des retouches.",
            )
        else:
            ref_choisie = st.text_input(
                "Référence article (saisie libre)",
                placeholder="REF-GRS-001",
            )

    if not ref_choisie:
        st.info("Sélectionner ou saisir une référence article pour commencer.")
        st.stop()

    retouches = lister_retouches(ref_choisie)
    stats = stats_retouches(ref_choisie)

    # ── Métriques rapides ─────────────────────────────────────────────────────
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total retouches", stats["total"])
    m2.metric("✅ Conformes", stats["conformes"])
    m3.metric("❌ Non conformes / Rebuts", stats["non_conformes"] + stats["rebuts"])
    taux_pct = f"{stats['taux_conformite']:.0%}" if stats["total"] > 0 else "—"
    m4.metric("Taux conformité après retouche", taux_pct)

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab_liste, tab_saisie, tab_stats = st.tabs(
        ["📋 Liste des retouches", "➕ Nouvelle retouche", "📊 Statistiques"]
    )

    # ── Onglet 1 : Liste ──────────────────────────────────────────────────────
    with tab_liste:
        if not retouches:
            st.info(f"Aucune retouche enregistrée pour **{ref_choisie}**.")
        else:
            # Export Excel
            col_dl, _ = st.columns([2, 4])
            with col_dl:
                if st.button("📥 Exporter en Excel", key="export_retouches_xl"):
                    try:
                        from pathlib import Path as _Path
                        chemin_xl = exporter_retouches(ref_choisie)
                        st.success(f"Fichier créé : `{chemin_xl.name}`")
                    except Exception as e_xl:
                        st.error(f"Erreur export : {e_xl}")

            st.divider()

            COULEUR_RES = {
                "conforme":     ("green",  "✅"),
                "non_conforme": ("orange", "⚠️"),
                "rebut":        ("red",    "🗑️"),
            }

            for r in retouches:
                res = r.get("resultat", "")
                couleur, icone = COULEUR_RES.get(res, ("gray", "❓"))
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 4, 1])
                    with c1:
                        st.markdown(f"**{r['id']}**  ·  `{r['date']}`")
                        st.caption(f"👤 {r['operateur']}  ·  🏭 {r['poste_travail']}")
                    with c2:
                        st.markdown(f"**Défaut :** {r['defaut_constate']}")
                        st.markdown(f"**Opération :** {r['operation']}")
                        if r.get("commentaire"):
                            st.caption(f"💬 {r['commentaire']}")
                    with c3:
                        st.markdown(f":{couleur}[{icone} **{RESULTATS.get(res, res)}**]")
                        if user.get("role") in ("admin", "bt") and st.button(
                            "🗑️", key=f"del_ret_{r['id']}", help="Supprimer cette fiche"
                        ):
                            supprimer_retouche(ref_choisie, r["id"])
                            st.success("Fiche supprimée.")
                            st.rerun()

    # ── Onglet 2 : Nouvelle retouche ──────────────────────────────────────────
    with tab_saisie:
        st.subheader("Saisir une nouvelle retouche")

        with st.form("form_retouche", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                date_ret = st.date_input(
                    "Date de la retouche *",
                    value=None,
                    help="Date à laquelle la retouche a été effectuée.",
                )
                operateur_ret = st.text_input(
                    "Opérateur *",
                    placeholder="Prénom Nom",
                    value=user.get("nom", ""),
                )
                poste_ret = st.text_input(
                    "Poste de travail *",
                    placeholder="Ex: PO-01, AR-02, CN-03",
                )
            with fc2:
                resultat_ret = st.selectbox(
                    "Résultat après retouche *",
                    options=list(RESULTATS.keys()),
                    format_func=lambda k: RESULTATS[k],
                )
                commentaire_ret = st.text_area(
                    "Commentaire (optionnel)",
                    placeholder="Note libre, conditions particulières…",
                    height=88,
                )

            defaut_ret = st.text_area(
                "Défaut constaté *",
                placeholder="Décrire précisément le défaut observé (ex: rayure fine face avant Ø3mm à 6h)",
                height=80,
            )
            operation_ret = st.text_area(
                "Opération de retouche effectuée *",
                placeholder="Ex: Reprise polissage grain 3000 + contrôle Ra, Reprise métallisation CN…",
                height=80,
            )

            submitted = st.form_submit_button("✅ Enregistrer la retouche", type="primary", use_container_width=True)

        if submitted:
            erreurs_form = []
            if not date_ret:
                erreurs_form.append("La date est obligatoire.")
            if not operateur_ret.strip():
                erreurs_form.append("L'opérateur est obligatoire.")
            if not poste_ret.strip():
                erreurs_form.append("Le poste de travail est obligatoire.")
            if not defaut_ret.strip():
                erreurs_form.append("La description du défaut est obligatoire.")
            if not operation_ret.strip():
                erreurs_form.append("L'opération de retouche est obligatoire.")

            if erreurs_form:
                for e in erreurs_form:
                    st.error(e)
            else:
                try:
                    fiche = creer_retouche(
                        ref_article=ref_choisie,
                        date_retouche=str(date_ret),
                        operateur=operateur_ret.strip(),
                        poste_travail=poste_ret.strip(),
                        defaut_constate=defaut_ret.strip(),
                        operation=operation_ret.strip(),
                        resultat=resultat_ret,
                        commentaire=commentaire_ret.strip(),
                    )
                    st.success(f"✅ Retouche **{fiche['id']}** enregistrée !")
                    st.rerun()
                except Exception as e_creer:
                    st.error(f"Erreur : {e_creer}")

    # ── Onglet 3 : Statistiques ───────────────────────────────────────────────
    with tab_stats:
        if stats["total"] == 0:
            st.info("Aucune retouche enregistrée — les statistiques apparaîtront ici.")
        else:
            import pandas as pd

            st.subheader("Résultats globaux")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.metric("Taux de conformité après retouche",
                           f"{stats['taux_conformite']:.1%}")
                df_res = pd.DataFrame(
                    [{"Résultat": RESULTATS.get(k, k), "Nombre": v}
                     for k, v in stats["par_resultat"].items()]
                )
                st.dataframe(df_res, use_container_width=True, hide_index=True)

            with col_g2:
                if stats["par_operateur"]:
                    st.subheader("Par opérateur")
                    df_op = pd.DataFrame(
                        [{"Opérateur": op, "Retouches": cnt}
                         for op, cnt in sorted(stats["par_operateur"].items(), key=lambda x: -x[1])]
                    )
                    st.dataframe(df_op, use_container_width=True, hide_index=True)
