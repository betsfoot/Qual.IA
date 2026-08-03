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
from backend.similarity_engine import brief_depuis_formulaire, trouver_meilleure_reference, extraire_valeurs_comparaison, trouver_references_composites
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
    verifier_credentials, ROLES, MODULES_DISPONIBLES,
    peut_valider_gate, peut_soumettre, peut_demander_corrections, peut_liberer,
    lister_utilisateurs, creer_utilisateur, supprimer_utilisateur, changer_mot_de_passe,
    mettre_a_jour_email, modifier_acces_utilisateur,
)
try:
    from backend.auth_manager import GROUPES_ROLES
except ImportError:
    GROUPES_ROLES = {
        "validation": "🔐 Validation workflow",
        "metier":     "📣 Métiers notifiés",
        "redaction":  "✏️ Rédaction",
        "admin":      "⚙️ Administration",
        "autre":      "👁️ Lecture seule",
    }
from backend.dit_manager import (
    lister_dits, charger_dit, sauvegarder_dit, supprimer_dit,
    dit_existe, nouveau_dit, generer_dit_ia,
)
from backend.pdf_exporter import exporter_dossier_pdf
from backend.nc_manager import (
    lister_nc, charger_nc, creer_nc, sauvegarder_nc,
    sauvegarder_photo, supprimer_photo, kpi_nc, kpi_nc_filtre,
    annees_disponibles, suggerer_8d_ia,
    TYPES_DEFAUT as NC_TYPES_DEFAUT,
    PHASES_DETECTION as NC_PHASES,
    NIVEAUX_GRAVITE as NC_GRAVITES,
    CATEGORIES_NC, STATUTS_NC, PHOTOS_DIR as NC_PHOTOS_DIR,
)
from backend.erp_service import chercher_of, erp_configure
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

st.markdown("""
<style>
/* ── Masquer éléments Streamlit génériques ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

/* ── Typographie globale ── */
html, body, [class*="css"] {
    font-family: "Inter", "Segoe UI", sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #1B3A6B !important;
    border-right: none;
}
[data-testid="stSidebar"] * {
    color: #E8EFF8 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #E8EFF8 !important;
    font-weight: 500;
}
[data-testid="stSidebar"] .stCaption p {
    color: #A8BDD8 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #2E5499 !important;
}
[data-testid="stSidebar"] .stMetric label {
    color: #A8BDD8 !important;
}
[data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 1.1rem !important;
}
/* Boutons sidebar */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255,255,255,0.22) !important;
}
/* Selectbox sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.25) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #FFFFFF !important;
}
/* Expander sidebar */
[data-testid="stSidebar"] .streamlit-expanderHeader {
    color: #E8EFF8 !important;
}
/* Input sidebar */
[data-testid="stSidebar"] input {
    background-color: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
    border-color: rgba(255,255,255,0.25) !important;
}
/* Codes de référence (backticks) dans la sidebar */
[data-testid="stSidebar"] code {
    background-color: rgba(255,255,255,0.18) !important;
    color: #FFFFFF !important;
    padding: 1px 5px !important;
    border-radius: 4px !important;
    font-size: 0.78rem !important;
}
/* Metric sidebar */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background-color: rgba(255,255,255,0.10) !important;
    border-left: 3px solid rgba(255,255,255,0.4) !important;
}

/* ── Titres de page ── */
h1 {
    color: #1B3A6B !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px;
    border-bottom: 3px solid #1B3A6B;
    padding-bottom: 0.4rem;
    margin-bottom: 0.5rem;
}
h2, h3 {
    color: #1B3A6B !important;
    font-weight: 600 !important;
}

/* ── Métriques ── */
[data-testid="stMetric"] {
    background-color: #EEF2F7;
    border-radius: 10px;
    padding: 12px 16px;
    border-left: 4px solid #1B3A6B;
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #4A5568 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #1B3A6B !important;
}

/* ── Boutons primaires ── */
.stButton > button[kind="primary"] {
    background-color: #1B3A6B !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    padding: 0.5rem 1.2rem;
    transition: background-color 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background-color: #142d52 !important;
}

/* ── Containers (cards) ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    border: 1px solid #D6E0EE !important;
    box-shadow: 0 1px 4px rgba(27,58,107,0.07);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #D6E0EE;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    color: #4A5568;
}
.stTabs [aria-selected="true"] {
    color: #1B3A6B !important;
    border-bottom: 2px solid #1B3A6B !important;
}

/* ── Divider ── */
hr {
    border-color: #D6E0EE !important;
}

/* ── Page de login ── */
.login-header {
    background: linear-gradient(135deg, #1B3A6B 0%, #2E5499 100%);
    padding: 3rem 2rem 2.5rem 2rem;
    text-align: center;
    margin: -1rem -1rem 2rem -1rem;
    border-radius: 0 0 16px 16px;
}
.login-header h1 {
    color: #FFFFFF !important;
    font-size: 2.8rem !important;
    font-weight: 800 !important;
    letter-spacing: -1px;
    border-bottom: none !important;
    padding-bottom: 0 !important;
    margin-bottom: 0.3rem !important;
}
.login-header p {
    color: #A8BDD8;
    font-size: 1.05rem;
    margin: 0;
    letter-spacing: 0.5px;
}
.login-card {
    background: #FFFFFF;
    border: 1px solid #D6E0EE;
    border-radius: 14px;
    padding: 2rem 1.8rem;
    box-shadow: 0 4px 20px rgba(27,58,107,0.10);
}
</style>
""", unsafe_allow_html=True)

# ─── Authentification ─────────────────────────────────────────────────────────

if "user" not in st.session_state:
    st.markdown("""
    <div class="login-header">
        <h1>Qual.IA</h1>
        <p>Gestion Qualité Industrielle — Optique &amp; Horlogerie</p>
    </div>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("##### Connexion à votre espace")
        _username = st.text_input("Identifiant", placeholder="Votre identifiant", label_visibility="visible")
        _password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
        st.write("")
        if st.button("Se connecter →", type="primary", use_container_width=True):
            _result = verifier_credentials(_username.strip(), _password)
            if _result:
                st.session_state["user"] = _result
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.write("")
        st.caption("Contactez votre administrateur si vous avez oublié vos identifiants.")
    st.stop()

user = st.session_state["user"]

# ─── Sélection de module (écran d'accueil) ───────────────────────────────────

_modules_user = user.get("modules", list(MODULES_DISPONIBLES.keys()))

if "module_actif" not in st.session_state:
    # Si un seul module autorisé → accès direct sans écran de sélection
    if len(_modules_user) == 1:
        st.session_state["module_actif"] = _modules_user[0]
    else:
        st.markdown(f"## Bonjour **{user.get('nom', user['username'])}** 👋")
        if user.get("entreprise"):
            st.caption(f"🏢 {user['entreprise']}")
        st.markdown("### Quel module souhaitez-vous ouvrir ?")
        st.write("")

        cols = st.columns(len(_modules_user), gap="large")
        module_labels = {
            "dev": ("⚙️ Qualité Développement", "AMDEC · Gamme · Plan de Contrôle · Workflow", "Création et validation des dossiers techniques produit"),
            "nc":  ("⚠️ Qualité Documentaire",  "NC · 8D · Suggestions IA · KPI alertes",      "Gestion des alertes qualité et résolution de problèmes"),
        }
        for i, mod in enumerate(_modules_user):
            titre, sous_titre, caption = module_labels.get(mod, (mod, "", ""))
            with cols[i]:
                if st.button(
                    f"{titre}\n\n{sous_titre}",
                    use_container_width=True,
                    key=f"btn_module_{mod}",
                ):
                    st.session_state["module_actif"] = mod
                    st.rerun()
                st.caption(caption)

        st.stop()

# Bouton retour accueil dans sidebar (ajouté plus bas)

# ─── Sauvegarde automatique au démarrage (une fois par jour) ─────────────────
if "backup_demarrage_fait" not in st.session_state:
    rapport_backup = demarrage_app()
    st.session_state["backup_demarrage_fait"] = True
    st.session_state["rapport_backup"] = rapport_backup

# ─── Sidebar — Catégorie + Navigation ────────────────────────────────────────

with st.sidebar:
    st.markdown("### Qual.IA")
    st.caption("Gestion Qualité Industrielle")

    module_actif = st.session_state.get("module_actif", "dev")
    if module_actif == "dev":
        st.info("⚙️ Qualité Développement")
    else:
        st.warning("⚠️ Qualité Documentaire")

    if len(_modules_user) > 1:
        if st.button("← Changer de module", use_container_width=True, key="btn_changer_module"):
            del st.session_state["module_actif"]
            if "nav_page" in st.session_state:
                del st.session_state["nav_page"]
            st.rerun()

    st.divider()
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
        format_func=lambda c: next((cat.nom for cat in categories_disponibles if cat.code == c), c),
        label_visibility="collapsed",
    )

    # Reset de la session si la catégorie change
    if st.session_state.get("categorie_active") != cat_code_selectionne:
        st.session_state["categorie_active"] = cat_code_selectionne
        st.session_state["resultat_similarite"] = None
        st.session_state["brief"] = None
        st.session_state["dossier_genere"] = None
        st.session_state["refs_composites"] = None

    categorie_active = charger_categorie(cat_code_selectionne)
    st.caption(categorie_active.description)

    st.divider()

    # ── Badge notifications ──
    _notifs_non_lues = lire_notifications(user["role"])
    _nb_notifs = len(_notifs_non_lues)
    if _nb_notifs > 0:
        st.markdown(f"🔔 **{_nb_notifs} notification(s) non lue(s)**")

    _module = st.session_state.get("module_actif", "dev")
    if _module == "nc":
        pages_disponibles = ["⚠️ Non-Conformités"]
    else:
        pages_disponibles = ["📊 Tableau de bord", "🏭 Nouveau produit", "📥 Importer un Excel", "📋 Workflow", "🔔 Notifications", "📚 Gestion de la base", "🔧 Retouches"]
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
        st.caption(f"`{r.get('reference', '?')}` — {r.get('designation', '')[:40]}…")
    if len(refs) > 8:
        st.caption(f"… et {len(refs) - 8} autres")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 : GESTION DE LA BASE — rendue en premier puis st.stop() si sélectionnée
# ═════════════════════════════════════════════════════════════════════════════

if page == "📊 Tableau de bord":
    import pandas as pd
    from datetime import datetime

    from backend.retouche_manager import lister_articles_avec_retouches, stats_retouches

    st.title("📊 Tableau de bord qualité")
    st.caption(f"Vue synthétique — {categorie_active.nom}")

    toutes_refs = lister_references(categorie_active)

    if not toutes_refs:
        st.info("Aucune référence dans cette catégorie.")
        st.stop()

    def _statut_ref(r: dict) -> str:
        return r.get("workflow", {}).get("statut", r.get("statut", "brouillon"))

    def _derniere_date(r: dict) -> str:
        hist = r.get("workflow", {}).get("historique", [])
        return hist[-1].get("date", "") if hist else ""

    def _ipr_int(r: dict) -> int:
        try:
            return int(r.get("workflow", {}).get("ipr_max", 0) or 0)
        except (TypeError, ValueError):
            return 0

    # ── Calculs globaux ──────────────────────────────────────────────────────────
    par_statut: dict[str, int] = {}
    for r in toutes_refs:
        s = _statut_ref(r)
        par_statut[s] = par_statut.get(s, 0) + 1

    SEUIL_BLOQUE = 7
    maintenant = datetime.now()
    bloques = []
    for r in toutes_refs:
        if _statut_ref(r) == "en_revue":
            d = _derniere_date(r)
            if d:
                try:
                    delta = (maintenant - datetime.fromisoformat(d[:19])).days
                    if delta >= SEUIL_BLOQUE:
                        bloques.append({
                            "ref": r["reference"],
                            "designation": r.get("designation", "")[:45],
                            "jours": delta,
                            "ipr_max": r.get("workflow", {}).get("ipr_max", "—"),
                        })
                except Exception:
                    pass
    bloques.sort(key=lambda x: -x["jours"])

    ipr_rouge  = sum(1 for r in toutes_refs if _ipr_int(r) > 100)
    ipr_orange = sum(1 for r in toutes_refs if 40 < _ipr_int(r) <= 100)
    ipr_vert   = sum(1 for r in toutes_refs if _ipr_int(r) <= 40)

    # ── KPI ──────────────────────────────────────────────────────────────────────
    st.subheader("Vue globale")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📋 Total", len(toutes_refs))
    k2.metric("📝 Brouillons", par_statut.get("brouillon", 0) + par_statut.get("corrections", 0))
    k3.metric("👁️ En revue", par_statut.get("en_revue", 0))
    k4.metric("🚀 Libérés", par_statut.get("libere", 0))
    k5.metric(
        f"🚨 Bloqués > {SEUIL_BLOQUE}j",
        len(bloques),
        delta=f"{bloques[0]['jours']}j max" if bloques else None,
        delta_color="inverse",
    )

    st.divider()

    # ── IPR + Bloqués ─────────────────────────────────────────────────────────────
    col_ipr, col_bloque = st.columns(2)

    with col_ipr:
        st.subheader("🎯 Distribution des risques")
        ci1, ci2, ci3 = st.columns(3)
        ci1.metric("🔴 Critique", ipr_rouge, help="IPR > 100")
        ci2.metric("🟠 Élevé", ipr_orange, help="IPR 41–100")
        ci3.metric("🟢 Acceptable", ipr_vert, help="IPR ≤ 40")
        df_ipr = pd.DataFrame({
            "Zone": ["🔴 Critique", "🟠 Élevé", "🟢 Acceptable"],
            "Dossiers": [ipr_rouge, ipr_orange, ipr_vert],
        }).set_index("Zone")
        st.bar_chart(df_ipr)

    with col_bloque:
        st.subheader(f"🚨 En revue > {SEUIL_BLOQUE} jours")
        if not bloques:
            st.success("Aucun dossier bloqué.")
        else:
            for b in bloques[:6]:
                with st.container(border=True):
                    bc1, bc2 = st.columns([4, 1])
                    bc1.markdown(f"**`{b['ref']}`**  {b['designation']}")
                    bc1.caption(f"IPR max : {b['ipr_max']}")
                    bc2.metric("Jours", b["jours"])

    st.divider()

    # ── Top modes de défaillance ──────────────────────────────────────────────────
    st.subheader("🔍 Top 10 modes de défaillance (IPR les plus élevés)")

    top_modes = []
    for r in toutes_refs:
        try:
            ref_data = charger_reference_complete(categorie_active, r["reference"])
            for doc_key, doc_label in [("amdec_produit", "Produit"), ("amdec_process", "Process")]:
                for m in ref_data["data"].get(doc_key, {}).get("modes_defaillance", []):
                    try:
                        ipr = int(m.get("G") or 0) * int(m.get("O") or 0) * int(m.get("D") or 0)
                        if ipr > 0:
                            top_modes.append({
                                "Référence": r["reference"],
                                "Document": doc_label,
                                "Mode de défaillance": (m.get("mode_defaillance") or "")[:55],
                                "G": m.get("G", ""),
                                "O": m.get("O", ""),
                                "D": m.get("D", ""),
                                "IPR": ipr,
                            })
                    except (TypeError, ValueError):
                        pass
        except Exception:
            pass

    top_modes.sort(key=lambda x: -x["IPR"])
    if top_modes:
        df_top = pd.DataFrame(top_modes[:10])
        st.dataframe(
            df_top, use_container_width=True, hide_index=True,
            column_config={"IPR": st.column_config.NumberColumn("IPR", format="%d")},
        )
    else:
        st.info("Pas encore de données AMDEC disponibles.")

    # ── Retouches globales ────────────────────────────────────────────────────────
    articles_retouches = lister_articles_avec_retouches()
    refs_avec_retouches = [r for r in toutes_refs if r["reference"] in articles_retouches]

    if refs_avec_retouches:
        st.divider()
        st.subheader("🔧 Conformité après retouche")
        retouche_rows = []
        for r in refs_avec_retouches:
            s = stats_retouches(r["reference"])
            if s["total"] > 0:
                retouche_rows.append({
                    "Référence": r["reference"],
                    "Total": s["total"],
                    "Conformes": s["conformes"],
                    "Non conformes": s["non_conformes"],
                    "Rebuts": s["rebuts"],
                    "Taux": f"{s['taux_conformite']:.0%}",
                })
        if retouche_rows:
            st.dataframe(pd.DataFrame(retouche_rows), use_container_width=True, hide_index=True)

    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE : NON-CONFORMITÉS
# ═════════════════════════════════════════════════════════════════════════════

if page == "⚠️ Non-Conformités":
    import os
    import pandas as pd
    from datetime import date

    st.title("⚠️ Non-Conformités — Alertes qualité")

    # ── Sous-navigation ────────────────────────────────────────────────────────
    onglet_nc = st.radio(
        "Onglet NC",
        ["📊 KPI & Liste", "➕ Nouvelle NC", "🔍 Détail NC"],
        horizontal=True,
        label_visibility="collapsed",
        key="onglet_nc",
    )

    # ── KPI & Liste ────────────────────────────────────────────────────────────
    if onglet_nc == "📊 KPI & Liste":
        kpi_global = kpi_nc()

        # KPI métriques globaux
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total NC", kpi_global["total"])
        k2.metric("🟠 Ouvertes", kpi_global["ouvertes"])
        k3.metric("🔵 En cours", kpi_global["en_cours"])
        k4.metric("🟢 Fermées", kpi_global["fermees"])

        if kpi_global["total"] > 0:
            st.divider()
            st.subheader("📈 Analyse des alertes qualité")

            # ── Filtres ──────────────────────────────────────────────────────
            f1, f2, f3 = st.columns([2, 2, 4])
            with f1:
                periode = st.selectbox(
                    "Regrouper par",
                    ["Mois", "Année"],
                    key="kpi_periode",
                )
            annees = annees_disponibles()
            with f2:
                if periode == "Mois":
                    annee_sel = st.selectbox("Année", annees, key="kpi_annee")
                else:
                    annee_sel = None
                    st.empty()

            # Calcul KPI filtré
            kpi = kpi_nc_filtre(
                periode="mois" if periode == "Mois" else "annee",
                annee=annee_sel if periode == "Mois" else None,
            )

            col_graph, col_type = st.columns([3, 2])

            with col_graph:
                titre = f"Alertes par {'mois' if periode == 'Mois' else 'année'}" + (f" ({annee_sel})" if annee_sel else "")
                st.markdown(f"**{titre}** — {kpi['total_filtre']} NC")
                if kpi["labels"]:
                    df_periode = pd.DataFrame({
                        "Période": kpi["labels"],
                        "NC":      kpi["data"],
                    }).set_index("Période")
                    st.bar_chart(df_periode, color="#fd7e14")
                else:
                    st.info("Aucune NC sur cette période.")

            with col_type:
                st.markdown("**Par type de défaut**")
                if kpi["par_type"]:
                    df_type = pd.DataFrame(
                        list(kpi["par_type"].items()), columns=["Type", "Nb"]
                    ).set_index("Type")
                    st.bar_chart(df_type, color="#0d6efd")
                else:
                    st.info("Aucune donnée.")

            # Graphique par catégorie
            if kpi.get("par_categorie"):
                st.markdown("**Par catégorie de NC**")
                df_cat = pd.DataFrame(
                    list(kpi["par_categorie"].items()), columns=["Catégorie", "Nb"]
                ).set_index("Catégorie")
                st.bar_chart(df_cat, color="#198754")

            # Gravité + Statut
            st.divider()
            gc1, gc2, gc3, gs1, gs2, gs3, gs4 = st.columns(7)
            gc1.metric("🔴 Critique", kpi["par_gravite"].get("Critique", 0))
            gc2.metric("🟠 Majeure",  kpi["par_gravite"].get("Majeure", 0))
            gc3.metric("🟡 Mineure",  kpi["par_gravite"].get("Mineure", 0))
            gs1.metric("🟠 Ouvertes",    kpi["par_statut"].get("ouverte", 0))
            gs2.metric("🔵 En cours",    kpi["par_statut"].get("en_cours", 0))
            gs3.metric("🟢 Fermées",     kpi["par_statut"].get("fermee", 0))
            gs4.metric("⚫ Abandonnées", kpi["par_statut"].get("abandonnee", 0))

        st.divider()
        st.subheader("Liste des NC")

        # Filtre statut
        filtre_statut = st.selectbox(
            "Filtrer par statut",
            ["Tous"] + list(STATUTS_NC.keys()),
            format_func=lambda x: "Tous" if x == "Tous" else STATUTS_NC[x],
        )
        nc_list = lister_nc(statut=None if filtre_statut == "Tous" else filtre_statut)

        if not nc_list:
            st.success("Aucune NC" + (f" avec le statut sélectionné" if filtre_statut != "Tous" else "") + ".")
        else:
            cols_dispo = ["id", "categorie", "type_defaut", "phase_detection", "gravite", "statut", "numero_of", "created_at"]
            cols_dispo = [c for c in cols_dispo if c in pd.DataFrame(nc_list).columns]
            df_nc = pd.DataFrame(nc_list)[cols_dispo]
            df_nc.columns = [{"id":"ID","categorie":"Catégorie","type_defaut":"Type défaut","phase_detection":"Phase","gravite":"Gravité","statut":"Statut","numero_of":"OF","created_at":"Date"}.get(c,c) for c in cols_dispo]
            df_nc["Date"] = df_nc["Date"].str[:10]
            df_nc["Statut"] = df_nc["Statut"].map(lambda s: STATUTS_NC.get(s, s))

            selection = st.dataframe(
                df_nc, use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
            )
            if selection and selection.selection.rows:
                idx = selection.selection.rows[0]
                nc_id_sel = nc_list[idx]["id"]
                st.session_state["nc_detail_id"] = nc_id_sel
                st.session_state["onglet_nc"] = "🔍 Détail NC"
                st.rerun()

    # ── Nouvelle NC ────────────────────────────────────────────────────────────
    elif onglet_nc == "➕ Nouvelle NC":
        st.subheader("Créer une nouvelle Non-Conformité")

        # ── Recherche OF (hors form pour interactivité) ──────────────────────
        st.markdown("#### 🏭 Ordre de Fabrication (OF)")
        of_col1, of_col2 = st.columns([3, 1])
        numero_of = of_col1.text_input(
            "Numéro d'OF",
            placeholder="ex. OF-2026-001",
            key="input_of",
            help="Entrez le numéro d'OF pour récupérer automatiquement les informations depuis l'ERP" if erp_configure() else "ERP non configuré — saisie manuelle",
        )
        info_of = st.session_state.get("info_of_data", {})

        if of_col2.button("🔍 Rechercher", key="btn_chercher_of"):
            if numero_of.strip():
                with st.spinner("Recherche dans l'ERP…"):
                    result = chercher_of(numero_of.strip())
                if result:
                    st.session_state["info_of_data"] = result
                    info_of = result
                    if result.get("source") == "mock":
                        st.info("⚠️ ERP non configuré — données de démonstration affichées. Configurez ERP_TYPE et ERP_URL dans .env pour brancher sur Infor/SAP.")
                    else:
                        st.success(f"OF trouvé dans l'ERP ({result['source'].upper()})")
                else:
                    st.error(f"OF '{numero_of}' introuvable dans l'ERP.")
            else:
                st.warning("Saisissez un numéro d'OF.")

        # Affichage infos OF récupérées
        if info_of:
            st.markdown("**Informations OF récupérées :**")
            oi1, oi2, oi3, oi4 = st.columns(4)
            oi1.markdown(f"**Désignation**\n{info_of.get('designation', '—')}")
            oi2.markdown(f"**Référence pièce**\n{info_of.get('reference_piece', '—')}")
            oi3.markdown(f"**Client**\n{info_of.get('client', '—')}")
            oi4.markdown(f"**Qté**\n{info_of.get('quantite', '—')}")
            oi_b1, oi_b2 = st.columns(2)
            oi_b1.markdown(f"**Matière**\n{info_of.get('matiere', '—')}")
            oi_b2.markdown(f"**Date lancement**\n{info_of.get('date_lancement', '—')}")

        st.divider()

        with st.form("form_nouvelle_nc"):
            c1, c2 = st.columns(2)
            piece_ref  = c1.text_input(
                "Référence pièce / produit",
                value=info_of.get("reference_piece", ""),
                placeholder="ex. REF-2026-001",
            )
            dossier_rf = c2.text_input("Dossier qualité lié (optionnel)", placeholder="ex. PIECE-001")

            c3, c4, c5 = st.columns(3)
            date_det   = c3.date_input("Date de détection", value=date.today())
            phase_det  = c4.selectbox("Phase de détection", NC_PHASES)
            gravite    = c5.selectbox("Gravité", NC_GRAVITES, index=1)

            ca1, ca2 = st.columns(2)
            categorie  = ca1.selectbox("Catégorie NC", CATEGORIES_NC)
            type_def   = ca2.selectbox("Type de défaut", NC_TYPES_DEFAUT)
            quantite   = st.number_input(
                "Quantité affectée",
                min_value=1,
                value=int(info_of.get("quantite", 1) or 1),
                step=1,
            )
            description = st.text_area(
                "Description de la non-conformité *",
                height=150,
                placeholder="Décrivez précisément la NC : symptômes, localisation, conditions de détection…\n\n(Cette description sera analysée par l'IA pour suggérer des axes 8D.)",
            )

            submitted = st.form_submit_button("✅ Créer la NC", use_container_width=True)
            if submitted:
                if not description.strip():
                    st.error("La description est obligatoire.")
                else:
                    nc_cree = creer_nc({
                        "categorie":        categorie,
                        "numero_of":        numero_of.strip(),
                        "info_of":          info_of,
                        "piece_reference":  piece_ref or info_of.get("reference_piece", ""),
                        "dossier_ref":      dossier_rf,
                        "date_detection":   str(date_det),
                        "phase_detection":  phase_det,
                        "gravite":          gravite,
                        "type_defaut":      type_def,
                        "quantite_affectee": quantite,
                        "description":      description,
                    }, user["username"])
                    st.session_state.pop("info_of_data", None)
                    st.success(f"NC **{nc_cree['id']}** créée avec succès !")
                    st.session_state["nc_detail_id"] = nc_cree["id"]
                    st.session_state["onglet_nc"] = "🔍 Détail NC"
                    st.rerun()

    # ── Détail NC ──────────────────────────────────────────────────────────────
    elif onglet_nc == "🔍 Détail NC":
        # Sélection de la NC
        nc_ids = [e["id"] for e in lister_nc()]
        if not nc_ids:
            st.info("Aucune NC. Créez-en une d'abord.")
            st.stop()

        default_id = st.session_state.get("nc_detail_id", nc_ids[0])
        if default_id not in nc_ids:
            default_id = nc_ids[0]

        nc_id = st.selectbox("Sélectionner une NC", nc_ids, index=nc_ids.index(default_id))
        st.session_state["nc_detail_id"] = nc_id
        nc = charger_nc(nc_id)
        if not nc:
            st.error("NC introuvable.")
            st.stop()

        # En-tête
        st.markdown(f"### {nc['id']} — {nc.get('type_defaut', '?')}")
        hd1, hd2, hd3, hd4 = st.columns(4)
        hd1.metric("Phase", nc.get("phase_detection", "?"))
        hd2.metric("Gravité", nc.get("gravite", "?"))
        hd3.metric("Qté affectée", nc.get("quantite_affectee", "?"))
        hd4.metric("Statut", STATUTS_NC.get(nc.get("statut", "ouverte"), "?"))

        # Fiche NC
        with st.expander("📋 Fiche Non-Conformité", expanded=True):
            if nc.get("numero_of"):
                st.markdown(f"**🏭 OF :** `{nc['numero_of']}`")
                info = nc.get("info_of", {})
                if info:
                    fi1, fi2, fi3 = st.columns(3)
                    fi1.caption(f"**Désignation :** {info.get('designation', '—')}")
                    fi2.caption(f"**Client :** {info.get('client', '—')}")
                    fi3.caption(f"**Matière :** {info.get('matiere', '—')}")
                st.divider()
            if nc.get("categorie"):
                st.markdown(f"**Catégorie :** `{nc['categorie']}`")
            st.markdown(f"**Pièce :** {nc.get('piece_reference') or '—'}")
            st.markdown(f"**Dossier lié :** {nc.get('dossier_ref') or '—'}")
            st.markdown(f"**Détecté par :** {nc.get('detecte_par')} le {nc.get('date_detection')}")
            st.markdown("**Description :**")
            st.info(nc.get("description", ""))

            # Changement statut
            nouveau_statut = st.selectbox(
                "Changer le statut",
                list(STATUTS_NC.keys()),
                index=list(STATUTS_NC.keys()).index(nc.get("statut", "ouverte")),
                format_func=lambda s: STATUTS_NC[s],
            )
            if st.button("Appliquer le statut", key="btn_statut_nc"):
                nc["statut"] = nouveau_statut
                sauvegarder_nc(nc_id, nc)
                st.success("Statut mis à jour.")
                st.rerun()

        # Photos
        with st.expander("📷 Photos", expanded=False):
            # Affichage des photos existantes
            if nc.get("photos"):
                cols_ph = st.columns(min(4, len(nc["photos"])))
                for i, nom_ph in enumerate(nc["photos"]):
                    chemin_ph = NC_PHOTOS_DIR / nom_ph
                    if chemin_ph.exists():
                        with cols_ph[i % 4]:
                            st.image(str(chemin_ph), use_container_width=True, caption=nom_ph)
                            if st.button("🗑️ Supprimer", key=f"del_ph_{i}"):
                                supprimer_photo(nc_id, nom_ph)
                                st.rerun()
            else:
                st.caption("Aucune photo pour cette NC.")

            # Upload
            uploaded = st.file_uploader(
                "Ajouter une photo", type=["jpg", "jpeg", "png", "webp"], key=f"upload_ph_{nc_id}"
            )
            if uploaded:
                sauvegarder_photo(nc_id, uploaded.name, uploaded.read())
                st.success(f"Photo '{uploaded.name}' ajoutée.")
                st.rerun()

        # 8D
        st.subheader("🔧 Résolution 8D")

        # Bouton suggestions IA
        ia_key = os.getenv("ANTHROPIC_API_KEY", "")
        if ia_key:
            if st.button("✨ Générer suggestions IA", key="btn_ia_nc"):
                with st.spinner("L'IA analyse la NC et l'historique…"):
                    sugg = suggerer_8d_ia(nc)
                if sugg:
                    st.session_state["nc_suggestions_ia"] = sugg
                    st.success(f"Suggestions générées (confiance : **{sugg.get('confiance', '?')}**)")
                    st.info(sugg.get("rationale", ""))
                else:
                    st.error("Impossible de générer les suggestions.")

            sugg = st.session_state.get("nc_suggestions_ia")
            if sugg:
                with st.expander("💡 Suggestions IA — cliquez pour appliquer", expanded=True):
                    st.markdown(f"**Confiance :** {sugg.get('confiance', '?')} — {sugg.get('rationale', '')}")
                    st.markdown(f"**D1 (équipe suggérée) :** {sugg.get('d1_suggestion', '')}")
                    st.markdown(f"**D3 (confinement suggéré) :** {sugg.get('d3_suggestion', '')}")
                    st.markdown("**D4 (causes racines) :**")
                    for c in sugg.get("d4_suggestions", []):
                        st.markdown(f"  - {c}")
                    st.markdown("**D5 (actions correctives) :**")
                    for a in sugg.get("d5_suggestions", []):
                        st.markdown(f"  - {a}")
                    st.markdown(f"**D7 (prévention) :** {sugg.get('d7_suggestion', '')}")

                    if st.button("⬇️ Appliquer dans le formulaire 8D", key="btn_appliquer_ia"):
                        huit_d = nc.setdefault("huit_d", {})
                        if sugg.get("d1_suggestion"):
                            huit_d["d1_equipe"] = sugg["d1_suggestion"]
                        if sugg.get("d3_suggestion"):
                            huit_d["d3_confinement"] = sugg["d3_suggestion"]
                        if sugg.get("d4_suggestions"):
                            huit_d["d4_causes_racines"] = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sugg["d4_suggestions"]))
                        if sugg.get("d5_suggestions"):
                            huit_d["d5_actions_correctives"] = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sugg["d5_suggestions"]))
                        if sugg.get("d7_suggestion"):
                            huit_d["d7_prevention"] = sugg["d7_suggestion"]
                        huit_d["suggestions_ia"] = sugg
                        sauvegarder_nc(nc_id, nc)
                        st.session_state.pop("nc_suggestions_ia", None)
                        st.success("Suggestions appliquées !")
                        st.rerun()
        else:
            st.caption("💡 Configurez `ANTHROPIC_API_KEY` dans votre `.env` pour activer les suggestions IA.")

        # Formulaire 8D
        with st.form("form_8d"):
            huit_d = nc.get("huit_d", {})
            d1 = st.text_area("D1 — Équipe pluridisciplinaire", value=huit_d.get("d1_equipe", ""), height=80)
            d2 = st.text_area("D2 — Description du problème",  value=huit_d.get("d2_description", ""), height=80)
            d3 = st.text_area("D3 — Actions de confinement",   value=huit_d.get("d3_confinement", ""), height=100)
            d4 = st.text_area("D4 — Causes racines",           value=huit_d.get("d4_causes_racines", ""), height=120, help="5 Pourquoi, Ishikawa…")
            d5 = st.text_area("D5 — Actions correctives",      value=huit_d.get("d5_actions_correctives", ""), height=100)
            d6 = st.text_area("D6 — Mise en œuvre",            value=huit_d.get("d6_mise_en_oeuvre", ""), height=100)
            d7 = st.text_area("D7 — Prévention récurrence",    value=huit_d.get("d7_prevention", ""), height=100)
            d8 = st.text_area("D8 — Clôture & Félicitations",  value=huit_d.get("d8_cloture", ""), height=80)

            if st.form_submit_button("💾 Sauvegarder 8D", use_container_width=True):
                nc["huit_d"].update({
                    "d1_equipe":              d1,
                    "d2_description":         d2,
                    "d3_confinement":         d3,
                    "d4_causes_racines":      d4,
                    "d5_actions_correctives": d5,
                    "d6_mise_en_oeuvre":      d6,
                    "d7_prevention":          d7,
                    "d8_cloture":             d8,
                })
                if sauvegarder_nc(nc_id, nc):
                    st.success("8D sauvegardé.")
                else:
                    st.error("Erreur lors de la sauvegarde.")

    st.stop()


if page == "📥 Importer un Excel":
    import pandas as pd
    from scripts.importer_excel import (
        COLONNES_AMDEC_PRODUIT, COLONNES_AMDEC_PROCESS, COLONNES_GAMME,
        _mapper_colonnes_auto, _appliquer_mapping, _detecter_ligne_header,
    )

    # Labels lisibles pour le mapping (technique → humain)
    LABELS_COLONNES = {
        # Commun AMDEC Produit / Process
        "no":                       "N° de ligne",
        "famille":                  "Famille / Catégorie",
        "fonction_exigence":        "Fonction / Exigence",
        "caracteristique_critique": "Caractéristique critique (KPC)",
        "mode_defaillance":         "Mode de défaillance ★",
        "effets_defaillance":       "Effets de la défaillance",
        "effets_produit":           "Effets sur le produit",
        "G":                        "G — Gravité (1–10) ★",
        "causes_defaillance":       "Causes de la défaillance",
        "causes_process":           "Causes process",
        "O":                        "O — Occurrence (1–10) ★",
        "controles_existants":      "Contrôles existants",
        "controles_process":        "Maîtrises process",
        "D":                        "D — Détection (1–10) ★",
        "classe_criticite":         "Classe criticité / IPR",
        "actions_correctives":      "Actions correctives",
        "responsable":              "Responsable",
        "delai":                    "Délai / Échéance",
        # AMDEC Process
        "operation_process":        "Opération / Étape process ★",
        "etape_poste":              "Étape / Poste machine",
        "parametre_cle":            "Paramètre clé (KPC)",
        "valeur_cible":             "Valeur cible / Spécification",
        # Gamme
        "no_op":                    "N° d'opération ★",
        "designation":              "Désignation de l'opération ★",
        "description_detaillee":    "Description détaillée",
        "poste_machine":            "Poste / Machine",
        "outillage_fixture":        "Outillage / Fixture",
        "parametre_1":              "Paramètre 1",
        "valeur_1":                 "Valeur 1",
        "parametre_2":              "Paramètre 2",
        "valeur_2":                 "Valeur 2",
        "parametre_3":              "Paramètre 3",
        "temps_min":                "Temps (min)",
        "point_controle":           "Point de contrôle",
        "moyen_controle":           "Moyen de contrôle",
        "frequence":                "Fréquence de contrôle",
        "critere_acceptation":      "Critère d'acceptation",
        "ref_dit":                  "Réf. DIT / Document",
        "ref_infor":                "Réf. Infor / ERP",
    }
    from backend.reference_saver import proposer_code_reference, enregistrer_reference, reference_existe

    st.title(f"📥 Importer un fichier Excel — {categorie_active.nom}")
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
            ligne_h_auto = _detecter_ligne_header(ws)
            data = list(ws.values)
            if len(data) <= ligne_h_auto:
                st.warning(f"{doc_type} : onglet vide.")
                lignes_finales[cle] = []
                continue

            with st.expander(f"**{doc_type}** — onglet `{sheet_name}`", expanded=True):
                # Override manuel : si la détection auto est mauvaise, l'utilisateur
                # peut choisir la ligne d'en-tête depuis un aperçu des 10 premières lignes
                apercu_lignes = []
                for idx in range(min(10, len(data))):
                    ligne = data[idx]
                    apercu = " | ".join(
                        (str(c)[:30] + "…" if c and len(str(c)) > 30 else str(c) if c else "·")
                        for c in (ligne[:6] if ligne else [])
                    )
                    apercu_lignes.append(f"Ligne {idx + 1} : {apercu}")

                ligne_h = st.selectbox(
                    "📍 Ligne d'en-tête (auto-détectée — corrige si nécessaire) :",
                    options=list(range(1, min(11, len(data) + 1))),
                    index=ligne_h_auto - 1,
                    format_func=lambda x: apercu_lignes[x - 1] if x <= len(apercu_lignes) else f"Ligne {x}",
                    key=f"header_row_{cle}",
                )

                headers = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(data[ligne_h - 1])]
                rows = data[ligne_h:]
                df = pd.DataFrame(rows, columns=headers).dropna(how="all")

                colonnes_excel = [c for c in df.columns if c and not str(c).startswith("col_")]
                auto = _mapper_colonnes_auto(colonnes_excel, colonnes_cibles)

                # Résumé du mapping auto
                nb_auto = len(auto)
                nb_total = len(colonnes_cibles)
                nb_manquants = nb_total - nb_auto
                if nb_manquants == 0:
                    st.success(f"✅ **{nb_auto}/{nb_total} colonnes détectées automatiquement** — vérifiez et corrigez si besoin.")
                else:
                    st.warning(f"⚠️ **{nb_auto}/{nb_total} colonnes détectées** — {nb_manquants} colonne(s) à mapper manuellement (marquées ★ si obligatoires).")

                st.caption(f"**{len(df)} lignes de données** | Faites correspondre chaque champ Qual.IA à la colonne de votre fichier Excel.")
                cols_display = st.columns(2)
                mapping_corr = {}
                for i, cible in enumerate(colonnes_cibles):
                    col_widget = cols_display[i % 2]
                    options_col = ["— Ignorer —"] + colonnes_excel
                    val_auto = auto.get(cible, "— Ignorer —")
                    idx_auto = options_col.index(val_auto) if val_auto in options_col else 0
                    label_lisible = LABELS_COLONNES.get(cible, cible)
                    # Badge couleur : vert si auto-détecté, orange sinon
                    badge = "✅ " if val_auto != "— Ignorer —" else "🔶 "
                    choix = col_widget.selectbox(
                        f"{badge}{label_lisible}",
                        options_col,
                        index=idx_auto,
                        key=f"map_{cle}_{cible}",
                        help=f"Champ interne : `{cible}`",
                    )
                    if choix != "— Ignorer —":
                        mapping_corr[cible] = choix

                mapping_final[cle] = mapping_corr
                lignes = _appliquer_mapping(df, mapping_corr, colonnes_cibles)
                lignes_finales[cle] = lignes
                nb_mappes = len(mapping_corr)
                st.caption(f"→ **{nb_mappes}/{nb_total} champs mappés** | **{len(lignes)} lignes** prêtes à importer")

                if lignes:
                    # Aperçu avec noms lisibles
                    df_preview = pd.DataFrame(lignes[:5])
                    df_preview.columns = [LABELS_COLONNES.get(c, c) for c in df_preview.columns]
                    st.dataframe(df_preview, use_container_width=True, hide_index=True)

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
                format_func=lambda x: {"valide": "✅ Validé", "brouillon": "📝 Brouillon"}.get(x, x))
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
                # Badge procédé extrapolé (niveau 2 garde qualité)
                if r.get("premiere_fabrication", False):
                    score_src = r.get("score_reference") or r.get("score_similarite_origine")
                    score_txt = f" — similarité {score_src:.0%}" if score_src else ""
                    st.warning(f"⚠️ Procédé extrapolé{score_txt} — revue renforcée requise")
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
                # Badge procédé extrapolé (niveau 2 garde qualité)
                if r.get("premiere_fabrication", False):
                    score_src = r.get("score_reference") or r.get("score_similarite_origine")
                    score_txt = f" — similarité {score_src:.0%}" if score_src else ""
                    st.warning(f"⚠️ Procédé extrapolé{score_txt} — revue renforcée requise")
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
                # Badge procédé extrapolé (niveau 2 garde qualité)
                if r.get("premiere_fabrication", False):
                    score_src = r.get("score_reference") or r.get("score_similarite_origine")
                    score_txt = f" — similarité {score_src:.0%}" if score_src else ""
                    st.warning(f"⚠️ Procédé extrapolé{score_txt} — revue renforcée requise")
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
                    "mode": m.get("mode_defaillance", ""),
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
                _gate_notif = prochaine_gate(meta_wf) or ""
                _role_notif = role_pour_gate(_gate_notif) if _gate_notif else ""
                ajouter_notification(
                    ref=code_wf,
                    categorie=cat_code_selectionne,
                    statut=meta_wf["statut"],
                    acteur=nom_user,
                    message=f"{nom_user} a effectué l'action '{label_action(action_choisie)}' sur `{code_wf}` — statut : {label_statut(meta_wf['statut'])}",
                    designation=meta_wf.get("designation", ""),
                    commentaire=commentaire_wf.strip(),
                    gate=_gate_notif,
                    role_requis=_role_notif,
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
                    plan_controle=data_wf.get("plan_controle", {}),
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
    st.title(f"🎨 Typologies de traitement — {categorie_active.nom}")
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

    from backend.email_notifier import email_configure
    from backend.notification_manager import ROLES_PAR_STATUT

    st.title("👥 Gestion des utilisateurs")

    tab_comptes, tab_emails, tab_acces = st.tabs([
        "👤 Comptes", "📧 Emails & Notifications", "🔐 Accès & Modules"
    ])

    utilisateurs = lister_utilisateurs()

    # ════════════════════════════════════════════════════════════════
    with tab_comptes:
        st.subheader("Comptes actifs")

        # ── Tableau groupé par groupe de rôle ────────────────────────
        groupes_affiches = {}
        for u in utilisateurs:
            groupe = ROLES.get(u["role"], {}).get("groupe", "autre")
            groupes_affiches.setdefault(groupe, []).append(u)

        for groupe_code, groupe_label in GROUPES_ROLES.items():
            membres = groupes_affiches.get(groupe_code, [])
            if not membres:
                continue
            st.markdown(f"**{groupe_label}**")
            for u in membres:
                role_info = ROLES.get(u["role"], {})
                with st.container(border=True):
                    uc1, uc2, uc3, uc4, uc5 = st.columns([2, 2, 2, 2, 1])
                    uc1.markdown(f"**`{u['username']}`**")
                    uc2.write(u["nom"])
                    uc3.write(role_info.get("label", u["role"]))
                    email_affiche = u.get("email", "")
                    uc4.write(f"✉️ `{email_affiche}`" if email_affiche else "⚠️ *pas d'email*")
                    with uc5:
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

        # ── Réinitialisation mot de passe ────────────────────────────
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

        # ── Créer un nouvel utilisateur ──────────────────────────────
        st.divider()
        st.subheader("➕ Créer un utilisateur")

        # Description des rôles disponibles
        with st.expander("Voir les rôles disponibles"):
            for groupe_code, groupe_label in GROUPES_ROLES.items():
                roles_du_groupe = [(k, v) for k, v in ROLES.items() if v.get("groupe") == groupe_code]
                if not roles_du_groupe:
                    continue
                st.markdown(f"**{groupe_label}**")
                for r_code, r_info in roles_du_groupe:
                    gates_str = ", ".join(r_info.get("gates", [])) or "—"
                    st.markdown(
                        f"- `{r_code}` — **{r_info['label']}** : {r_info.get('description', '')}  "
                        f"_(Gates : {gates_str})_"
                    )

        with st.form("form_creer_user"):
            fc1, fc2 = st.columns(2)
            with fc1:
                new_username = st.text_input("Identifiant *", placeholder="prenom.nom")
                new_nom = st.text_input("Nom affiché *", placeholder="Jean Dupont")
                new_email_form = st.text_input(
                    "Email notifications",
                    placeholder="prenom@entreprise.com",
                    help="L'email utilisé pour envoyer les notifications liées au rôle.",
                )
                new_entreprise_form = st.text_input(
                    "Entreprise",
                    placeholder="Ex: Acme SAS",
                    help="Nom de l'entreprise cliente (utilisé pour le contrôle d'accès multi-client).",
                )
            with fc2:
                new_role = st.selectbox(
                    "Rôle *",
                    options=list(ROLES.keys()),
                    format_func=lambda r: f"{ROLES[r]['label']} — {ROLES[r].get('description', '')}",
                )
                new_mdp = st.text_input("Mot de passe *", type="password", placeholder="Min. 8 caractères")
                new_mdp2 = st.text_input("Confirmer le mot de passe *", type="password")
                st.markdown("**Modules autorisés *** :")
                new_modules_form = []
                for _mod_code, _mod_label in MODULES_DISPONIBLES.items():
                    if st.checkbox(_mod_label, value=True, key=f"new_mod_{_mod_code}"):
                        new_modules_form.append(_mod_code)

            if st.form_submit_button("Créer le compte", type="primary"):
                if not new_username.strip() or not new_nom.strip() or not new_mdp:
                    st.error("Tous les champs obligatoires (identifiant, nom, mot de passe) doivent être remplis.")
                elif new_mdp != new_mdp2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_mdp) < 8:
                    st.error("Le mot de passe doit faire au moins 8 caractères.")
                elif not new_modules_form:
                    st.error("Sélectionnez au moins un module.")
                else:
                    try:
                        creer_utilisateur(
                            new_username.strip(), new_nom.strip(), new_role, new_mdp,
                            email=new_email_form.strip(),
                            entreprise=new_entreprise_form.strip(),
                            modules=new_modules_form,
                        )
                        st.success(f"✅ Compte `{new_username}` créé avec le rôle **{ROLES[new_role]['label']}**.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    # ════════════════════════════════════════════════════════════════
    with tab_emails:
        st.subheader("📧 Adresses email par utilisateur")
        st.caption(
            "Renseignez l'email de chaque personne. "
            "Les notifications seront envoyées automatiquement selon leur rôle."
        )

        # ── Statut Resend ─────────────────────────────────────────────
        if email_configure():
            st.success("✅ Resend actif — les notifications email sont activées.")
        else:
            st.warning(
                "⚠️ Resend non configuré — ajoutez `RESEND_API_KEY` dans vos secrets "
                "Streamlit Cloud (Settings → Secrets) pour activer les emails."
            )

        # ── Tableau "qui reçoit quoi" ────────────────────────────────
        st.markdown("---")
        st.markdown("#### Récapitulatif : qui reçoit quoi")

        EVENT_LABELS = {
            "creation":    "📥 Nouveau dossier créé",
            "en_revue":    "👁️ Dossier soumis en revue",
            "corrections": "🔄 Corrections demandées",
            "approuve":    "✅ Dossier approuvé",
            "libere":      "🚀 Dossier libéré en production",
            "obsolete":    "🗄️ Dossier rendu obsolète",
        }
        import pandas as pd
        routing_rows = []
        for evt_code, evt_label in EVENT_LABELS.items():
            roles_evt = ROLES_PAR_STATUT.get(evt_code, [])
            # Trouver les personnes ayant ces rôles
            personnes = [
                f"{u['nom']} ({ROLES.get(u['role'],{}).get('label', u['role'])})"
                + (" ✉️" if u.get("email") else " ⚠️")
                for u in utilisateurs if u["role"] in roles_evt
            ]
            routing_rows.append({
                "Événement": evt_label,
                "Destinataires": ", ".join(personnes) if personnes else "— (aucun utilisateur avec ce rôle)",
            })
        st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)
        st.caption("✉️ = email configuré | ⚠️ = pas d'email → cet utilisateur ne recevra pas de notification")

        # ── Formulaire email par utilisateur ────────────────────────
        st.markdown("---")
        st.markdown("#### Modifier les emails")

        for groupe_code, groupe_label in GROUPES_ROLES.items():
            membres_g = [u for u in utilisateurs if ROLES.get(u["role"], {}).get("groupe") == groupe_code]
            if not membres_g:
                continue
            st.markdown(f"**{groupe_label}**")
            for u in membres_g:
                role_info = ROLES.get(u["role"], {})
                col_n, col_r, col_e, col_btn = st.columns([2, 2, 3, 1])
                col_n.write(u["nom"])
                col_r.caption(role_info.get("label", u["role"]))
                new_em_val = col_e.text_input(
                    "Email",
                    value=u.get("email", ""),
                    placeholder="prenom@entreprise.com",
                    label_visibility="collapsed",
                    key=f"em_{u['username']}",
                )
                with col_btn:
                    if st.button("💾", key=f"save_em_{u['username']}", help="Sauvegarder"):
                        try:
                            mettre_a_jour_email(u["username"], new_em_val)
                            st.success("✅")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    # ════════════════════════════════════════════════════════════════
    with tab_acces:
        st.subheader("🔐 Accès par entreprise et modules")
        st.caption(
            "Définissez l'entreprise cliente et les modules autorisés pour chaque compte. "
            "Un utilisateur sans accès à un module ne verra pas cette section dans l'application."
        )

        for u in utilisateurs:
            with st.container(border=True):
                hdr_col, badge_col = st.columns([4, 2])
                with hdr_col:
                    role_info = ROLES.get(u["role"], {})
                    st.markdown(f"**`{u['username']}`** — {u['nom']}")
                    st.caption(role_info.get("label", u["role"]))
                with badge_col:
                    ent_badge = u.get("entreprise", "")
                    if ent_badge:
                        st.info(f"🏢 {ent_badge}", icon=None)
                    mods_actuels = u.get("modules", list(MODULES_DISPONIBLES.keys()))
                    badges = " · ".join(MODULES_DISPONIBLES[m] for m in mods_actuels if m in MODULES_DISPONIBLES)
                    st.caption(f"Accès : {badges or '—'}")

                if u["username"] == user["username"]:
                    st.caption("_(votre propre compte — modifiable via l'IT)_")
                    continue

                ent_col, mod_col, btn_col = st.columns([3, 3, 1])
                with ent_col:
                    new_ent = st.text_input(
                        "Entreprise",
                        value=u.get("entreprise", ""),
                        placeholder="Ex: Acme SAS",
                        key=f"ent_{u['username']}",
                    )
                with mod_col:
                    st.markdown("**Modules autorisés :**")
                    new_mods = []
                    for mod_code, mod_label in MODULES_DISPONIBLES.items():
                        if st.checkbox(
                            mod_label,
                            value=mod_code in mods_actuels,
                            key=f"mod_{u['username']}_{mod_code}",
                        ):
                            new_mods.append(mod_code)
                with btn_col:
                    st.write("")
                    st.write("")
                    st.write("")
                    st.write("")
                    if st.button("💾", key=f"save_acces_{u['username']}", help="Sauvegarder les accès"):
                        if not new_mods:
                            st.error("Au moins 1 module obligatoire.")
                        else:
                            try:
                                modifier_acces_utilisateur(
                                    u["username"],
                                    entreprise=new_ent,
                                    modules=new_mods,
                                )
                                st.success(f"✅ Accès de `{u['username']}` mis à jour.")
                                st.rerun()
                            except Exception as e:
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

    st.title(f"📚 Gestion de la base — {categorie_active.nom}")
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

    # ── Recherche textuelle ──
    recherche = st.text_input(
        "Rechercher",
        placeholder="Code, désignation, matière, traitement…",
        key="recherche_refs",
        label_visibility="collapsed",
    )

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

    # Recherche textuelle libre
    if recherche:
        q = recherche.strip().lower()
        def _match_ref(r: dict) -> bool:
            if q in r.get("reference", "").lower():
                return True
            if q in r.get("designation", "").lower():
                return True
            if q in r.get("matiere", "").lower():
                return True
            if q in r.get("type_produit", "").lower():
                return True
            for t in r.get("traitements", []):
                code_t = t.get("code", "") if isinstance(t, dict) else str(t)
                if q in code_t.lower():
                    return True
            return False
        filtered = [r for r in filtered if _match_ref(r)]

    # Filtres par catégorie
    if f_type:
        filtered = [r for r in filtered if r.get("type_produit") in f_type]
    if f_matiere:
        filtered = [r for r in filtered if r.get("matiere") in f_matiere]
    if f_traitement:
        def _codes_traitement(traitements_list):
            return {t.get("code", "") if isinstance(t, dict) else str(t) for t in traitements_list}
        filtered = [r for r in filtered if _codes_traitement(r.get("traitements", [])) & set(f_traitement)]
    if f_statut:
        filtered = [r for r in filtered if r.get("statut") in f_statut]

    nb_total = len(references)
    nb_filtres = len(filtered)
    if recherche or f_type or f_matiere or f_traitement or f_statut:
        st.caption(f"**{nb_filtres}** référence(s) trouvée(s) sur {nb_total}")
    else:
        st.caption(f"**{nb_total}** référence(s) au total")

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

    tab_meta, tab_p, tab_pr, tab_g, tab_pc_ref, tab_dit, tab_zone = st.tabs([
        "📋 Métadonnées", "AMDEC Produit", "AMDEC Process", "Gamme", "📋 Plan de Contrôle", "📄 DIT", "⚙️ Actions"
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

    # ─── Onglet Plan de Contrôle ─────────────────────────────────────────────
    with tab_pc_ref:
        import pandas as pd
        st.markdown("### 📋 Plan de Contrôle")
        plan_ref = data.get("plan_controle", {})
        pts_ref = plan_ref.get("points_controle", [])

        if not pts_ref:
            st.info(
                "Aucun Plan de Contrôle pour cette référence. "
                "Les références créées avant cette mise à jour n'en ont pas encore. "
                "Régénère le dossier pour obtenir le Plan de Contrôle automatiquement."
            )
        else:
            st.caption(
                f"Version {plan_ref.get('version', 'A')} — {len(pts_ref)} point(s) de contrôle"
            )
            for a in plan_ref.get("avertissements_generateur", []):
                st.warning(a)

            df_pc_ref = pd.DataFrame(pts_ref)
            colonnes_pc_ref = [
                "id", "phase", "operation_gamme", "caracteristique",
                "critere_acceptation", "moyen_controle", "frequence",
                "responsable", "enregistrement", "action_non_conformite",
            ]
            for c in colonnes_pc_ref:
                if c not in df_pc_ref.columns:
                    df_pc_ref[c] = ""
            df_pc_ref = df_pc_ref[colonnes_pc_ref]

            edited_pc_ref = st.data_editor(
                df_pc_ref,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_pc_ref",
                disabled=_est_verrouille,
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "phase": st.column_config.SelectboxColumn(
                        "Phase", options=["reception", "en_cours", "final"], width="small"
                    ),
                    "operation_gamme": st.column_config.TextColumn("Opération", width="small"),
                    "caracteristique": st.column_config.TextColumn("Caractéristique"),
                    "critere_acceptation": st.column_config.TextColumn("Critère d'acceptation"),
                    "moyen_controle": st.column_config.TextColumn("Moyen de contrôle"),
                    "frequence": st.column_config.TextColumn("Fréquence", width="small"),
                    "responsable": st.column_config.SelectboxColumn(
                        "Responsable",
                        options=["operateur", "controleur", "qualite"],
                        width="small",
                    ),
                    "enregistrement": st.column_config.TextColumn("Enregistrement"),
                    "action_non_conformite": st.column_config.TextColumn("Action NC"),
                },
            )

            if not _est_verrouille:
                if st.button("💾 Enregistrer le Plan de Contrôle", key="save_pc_ref"):
                    data.setdefault("plan_controle", {})["points_controle"] = edited_pc_ref.fillna("").to_dict("records")
                    sauvegarder_modifications(categorie_active, code_selectionne, meta, data)
                    st.success(f"✅ Plan de Contrôle de `{code_selectionne}` enregistré ({len(edited_pc_ref)} points).")

            col_pc_r1, col_pc_r2, col_pc_r3 = st.columns(3)
            col_pc_r1.metric("📦 Réception", sum(1 for p in pts_ref if p.get("phase") == "reception"))
            col_pc_r2.metric("⚙️ En-cours", sum(1 for p in pts_ref if p.get("phase") == "en_cours"))
            col_pc_r3.metric("✅ Final", sum(1 for p in pts_ref if p.get("phase") == "final"))

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
            "plan_controle": "Plan de Contrôle",
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
                    plan_controle=data.get("plan_controle", {}),
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
        # ── Duplication ───────────────────────────────────────────────────────
        st.markdown("### 📋 Dupliquer la référence")
        st.caption("Crée une copie complète avec un nouveau code. Le doublon démarre en brouillon.")
        col_dup1, col_dup2 = st.columns([3, 1])
        with col_dup1:
            code_copie = st.text_input(
                "Nouveau code pour la copie",
                value=f"{code_selectionne}-COPIE",
                key=f"dup_code_{code_selectionne}",
            )
        with col_dup2:
            acteur_dup = st.text_input("Rédacteur", value="", placeholder="Votre nom", key=f"dup_acteur_{code_selectionne}")
        if st.button("📋 Dupliquer", key=f"btn_dup_{code_selectionne}"):
            from backend.reference_saver import enregistrer_reference, reference_existe
            code_copie_clean = code_copie.strip().upper().replace(" ", "-")
            if not code_copie_clean:
                st.error("Le code de la copie ne peut pas être vide.")
            elif not acteur_dup.strip():
                st.error("Le nom du rédacteur est obligatoire.")
            elif reference_existe(categorie_active, code_copie_clean):
                st.error(f"La référence `{code_copie_clean}` existe déjà. Choisir un autre code.")
            else:
                try:
                    brief_copie = {
                        "type_produit":       meta.get("type_produit"),
                        "matiere":            meta.get("matiere"),
                        "traitements":        meta.get("traitements", []),
                        "dimensions":         meta.get("dimensions", {}),
                        "exigences_speciales": meta.get("exigences_speciales", ""),
                        "designation_client": f"[Copie] {meta.get('designation', '')}",
                    }
                    dossier_copie = {**data, "metadonnees_generation": {
                        "reference_source": code_selectionne,
                        "score_similarite": 1.0,
                        "mode_generation":  "duplication",
                    }}
                    enregistrer_reference(
                        categorie=categorie_active,
                        code=code_copie_clean,
                        brief=brief_copie,
                        dossier=dossier_copie,
                        acteur=acteur_dup.strip(),
                        commentaire_creation=f"Copie de {code_selectionne}",
                        overwrite=False,
                    )
                    st.success(f"Référence `{code_copie_clean}` créée avec succès. Rechargez la page pour la voir.")
                except Exception as e:
                    st.error(f"Erreur lors de la duplication : {e}")

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

st.title(f"Qual.IA — {categorie_active.nom}")
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
        st.subheader(f"Caractéristiques produit — {categorie_active.nom}")

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
                try:
                    refs_comp = trouver_references_composites(brief, categorie_active)
                except Exception:
                    refs_comp = None

            st.session_state.brief = brief
            st.session_state.resultat_similarite = resultat
            st.session_state.refs_composites = refs_comp
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

# ─── Seuils de garde qualité (définis ici pour être accessibles dès l'étape 2)
# Ne pas modifier sans validation Responsable Méthodes.
_SEUIL_GENERATION_NORMALE = 0.60   # >= 60% : génération directe depuis référence connue
_SEUIL_GENERATION_GARDE   = 0.30   # 30–60% : avertissement + squelette, confirmation requise
                                    # < 30%  : blocage complet, aucun bouton de génération

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

    # ─── Tableau de comparaison visuel ───────────────────────────────────────
    criteres_config = categorie_active.criteres_similarite()
    valeurs_comp = extraire_valeurs_comparaison(brief or {}, res.metadata, criteres_config)

    def _indicateur_sim(score: float) -> str:
        if score >= 0.95:
            return "✅"
        if score >= 0.5:
            return "⚠️"
        return "❌"

    def _barre_sim(score: float) -> str:
        filled = int(round(score * 8))
        return "█" * filled + "░" * (8 - filled)

    def _label_court(desc: str) -> str:
        for sep in [" —", " ("]:
            if sep in desc:
                return desc.split(sep)[0].strip()
        return desc

    st.markdown("**🔍 Comparaison — Votre demande ↔ Référence trouvée**")
    with st.container(border=True):
        hcols = st.columns([0.7, 2.5, 2, 2, 1.5])
        hcols[0].markdown("**·**")
        hcols[1].markdown("**Critère**")
        hcols[2].markdown("**Votre demande**")
        hcols[3].markdown("**Référence**")
        hcols[4].markdown("**Score**")
        st.divider()
        for critere, params_c in criteres_config.items():
            score_critere = res.detail_scores.get(critere, 0.0)
            vals = valeurs_comp.get(critere, {})
            label = _label_court(params_c.get("description", critere))
            poids = params_c.get("poids", 0)
            row = st.columns([0.7, 2.5, 2, 2, 1.5])
            row[0].markdown(_indicateur_sim(score_critere))
            row[1].markdown(f"{label}  \n<small style='color:grey'>poids {poids:.0%}</small>", unsafe_allow_html=True)
            row[2].markdown(f"`{vals.get('brief', '—')}`")
            row[3].markdown(f"`{vals.get('ref', '—')}`")
            row[4].markdown(f"{_barre_sim(score_critere)} **{score_critere:.0%}**")

    # ─── Phrase de résumé automatique ────────────────────────────────────────
    _phrases_ok, _phrases_proche, _phrases_diff = [], [], []
    for critere, params_c in criteres_config.items():
        score_critere = res.detail_scores.get(critere, 0.0)
        label = _label_court(params_c.get("description", critere))
        vals = valeurs_comp.get(critere, {})
        bv = vals.get("brief", "—")
        rv = vals.get("ref", "—")
        if score_critere >= 0.95:
            _phrases_ok.append(f"**{label}**")
        elif score_critere >= 0.7:
            _phrases_proche.append(f"**{label}** (demandé : {bv}, référence : {rv})")
        elif score_critere >= 0.5:
            _phrases_diff.append(f"**{label}** diffère notablement : vous demandez {bv}, la référence a {rv}")
        elif score_critere > 0.0:
            _phrases_diff.append(f"**{label}** diffère significativement : vous demandez {bv}, la référence a {rv}")
        else:
            _phrases_diff.append(f"**{label}** ne correspond pas du tout : vous demandez {bv}, la référence a {rv}")

    _resume_parts = []
    if _phrases_ok:
        _resume_parts.append(f"{', '.join(_phrases_ok)} {'correspondent' if len(_phrases_ok) > 1 else 'correspond'} parfaitement")
    if _phrases_proche:
        _resume_parts.append(". ".join(_phrases_proche))
    if _phrases_diff:
        _resume_parts.append(". ".join(_phrases_diff))

    if _resume_parts:
        _resume_txt = ". ".join(_resume_parts) + "."
        _resume_txt = _resume_txt[0].upper() + _resume_txt[1:]
        with st.expander("📝 Résumé de l'analyse en clair", expanded=True):
            st.markdown(_resume_txt)

    if res.avertissements:
        for a in res.avertissements:
            st.warning(a)

    # ── Bouton variantes si configurées ──
    variantes_pretes = [v for v in st.session_state.variantes_config if v.get("article", "").strip() and v.get("traitements")]
    if variantes_pretes and len({v["article"] for v in variantes_pretes}) == len(variantes_pretes):
        st.divider()
        st.info(f"**{len(variantes_pretes)} variante(s) configurées dans le brief** → {', '.join(v['article'] for v in variantes_pretes)}")

        # ── Garde qualité : score < 30% → blocage variantes aussi
        if res.score < _SEUIL_GENERATION_GARDE:
            st.error(
                f"🚫 **Score {score_pct} insuffisant** — la génération de variantes est également bloquée. "
                "Ajoutez d'abord une référence manuelle proche de ce procédé."
            )
        else:
            _squelette_v = res.mode == "manuelle"
            _label_v = (
                f"⚡ Générer le squelette des {len(variantes_pretes)} variantes (extrapolé) →"
                if _squelette_v
                else f"⚡ Générer les {len(variantes_pretes)} variantes →"
            )
            if st.button(_label_v, type="primary", use_container_width=True, key="btn_variantes"):
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
                            mode_squelette=_squelette_v,
                        )
                        # Niveau 2 : marquer les variantes extrapolées
                        if _squelette_v:
                            for art, dos in dossiers.items():
                                dos.setdefault("metadonnees_generation", {})["premiere_fabrication"] = True
                                dos["metadonnees_generation"]["score_reference"] = round(res.score, 4)
                        st.session_state.dossiers_variantes = dossiers
                        ph_v.success(f"✅ {len(dossiers)} variantes générées !")
                        st.rerun()
                    except Exception as e:
                        ph_v.error(f"Erreur : {e}")

# ─── ÉTAPE 3 : Génération ────────────────────────────────────────────────────
# (Seuils de garde qualité définis plus haut, avant l'étape 2)

if (
    st.session_state.resultat_similarite is not None
    and st.session_state.dossier_genere is None
    and st.session_state.dossiers_variantes is None
):
    st.divider()
    st.header("③ Génération des documents")
    res = st.session_state.resultat_similarite
    brief = st.session_state.brief

    # ── Niveau 0 : garde stricte sur les traitements inconnus de la base ─────
    from backend.similarity_engine import traitements_inconnus, charger_references
    _refs_validees = charger_references(categorie_active)
    _inconnus = traitements_inconnus(brief, _refs_validees)

    if _inconnus:
        # Blocage absolu — un ou plusieurs traitements du brief n'existent dans aucune ref validée
        st.error(
            f"🚫 **Traitement(s) inconnu(s) de la base qualité** : `{', '.join(_inconnus)}`\n\n"
            "Aucune référence libérée/approuvée de votre base ne contient ce(s) traitement(s). "
            "Générer un dossier qualité dans ces conditions produirait des données "
            "**entièrement inventées par l'IA** — inacceptable en contexte industriel.\n\n"
            "**Actions requises avant de pouvoir générer :**\n"
            "- Importer (Excel) ou créer manuellement une référence validée utilisant ce(s) traitement(s)\n"
            "- Ou retirer ce(s) traitement(s) du brief si non applicables"
        )
        # Aucun bouton de génération — blocage total

    # ── Niveau 1 : garde selon score de similarité ────────────────────────────
    elif res.score < _SEUIL_GENERATION_GARDE:
        # Blocage complet — procédé inconnu
        st.error(
            f"🚫 **Procédé non maîtrisé dans le système** (score : **{score_pct}**)\n\n"
            "Aucune référence suffisamment proche n'existe dans votre base. "
            "Générer un document qualité depuis cette combinaison produirait des données "
            "entièrement inventées — inacceptable en contexte industriel.\n\n"
            "**Actions requises avant de pouvoir générer :**\n"
            "- Ajoutez d'abord une référence manuelle via l'import Excel\n"
            "- Ou validez ce procédé en atelier et saisissez-le manuellement dans la base"
        )
        # Aucun bouton de génération — blocage total

    elif res.mode == "manuelle":
        # Score 30–60% : avertissement + génération squelette sur confirmation
        st.warning(
            f"⚠️ **Procédé extrapolé — vérification obligatoire** (score : **{score_pct}**)\n\n"
            f"La référence la plus proche `{res.reference}` n'est que partiellement similaire. "
            "En confirmant, Claude générera un **squelette structurel** : les valeurs numériques "
            "(indices G, O, D, tolérances, paramètres process) seront remplacées par "
            "`[À DÉFINIR EN ATELIER]` — aucune valeur ne sera inventée.\n\n"
            "**Ce dossier devra être intégralement vérifié avant tout usage en production.**"
        )
        if st.button(
            "⚡ Générer le squelette (procédé extrapolé) →",
            type="primary",
            key="btn_gen_squelette",
        ):
            try:
                api_key = get_secret("ANTHROPIC_API_KEY")
            except ValueError as e:
                st.error(str(e))
                api_key = ""
            if api_key:
                placeholder = st.empty()
                placeholder.info("Génération du squelette en cours… (30–90 secondes).")
                try:
                    dossier = generer_dossier_complet(
                        brief=st.session_state.brief,
                        resultat_similarite=res,
                        categorie=categorie_active,
                        mode_squelette=True,
                    )
                    # Niveau 2 : injection du flag premiere_fabrication dans les métadonnées
                    dossier["metadonnees_generation"]["premiere_fabrication"] = True
                    dossier["metadonnees_generation"]["score_reference"] = round(res.score, 4)
                    st.session_state.dossier_genere = dossier
                    placeholder.success(
                        "Squelette généré. ⚠️ Toutes les valeurs numériques sont à compléter en atelier."
                    )
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

    else:
        # Score >= 60% : génération normale
        _pn = categorie_active.parametres_numeriques()
        _dim_info = f"{_pn[0]['label']}={brief['dimensions'].get(_pn[0]['cle'], '?')}" if _pn else ""
        st.info(
            f"Prêt à générer **AMDEC Produit + AMDEC Process + Gamme** "
            f"en adaptant `{res.reference}` ({_dim_info})."
        )
        if st.button("Générer les documents IA →", type="primary", key="btn_gen_normal"):
            try:
                api_key = get_secret("ANTHROPIC_API_KEY")
            except ValueError as e:
                st.error(str(e))
                api_key = ""
            if api_key:
                # Afficher le bandeau composite avant de lancer
                refs_comp = st.session_state.get("refs_composites")
                if refs_comp and refs_comp.get("est_composite"):
                    st.info(f"📚 **Génération composite** : {refs_comp['resume']}")
                placeholder = st.empty()
                placeholder.info("Génération en cours… (30–90 secondes). En cas de surcharge API, jusqu'à 3 tentatives automatiques.")
                try:
                    dossier = generer_dossier_complet(
                        brief=st.session_state.brief,
                        resultat_similarite=res,
                        categorie=categorie_active,
                        refs_composites=refs_comp,
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

    tab1, tab2, tab3, tab4 = st.tabs(["AMDEC Produit", "AMDEC Process", "Gamme de Production", "📋 Plan de Contrôle"])

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

    # ─── Plan de Contrôle ────────────────────────────────────────────────────
    with tab4:
        plan = dossier.get("plan_controle", {})
        points = plan.get("points_controle", [])

        if not points:
            st.info("Aucun point de contrôle généré. Relance la génération du dossier pour obtenir le Plan de Contrôle.")
        else:
            st.caption(
                f"Référence : {plan.get('reference', '')} | {plan.get('designation', '')} | "
                f"Version {plan.get('version', 'A')} — {len(points)} point(s) de contrôle"
            )

            # Avertissements
            for a in plan.get("avertissements_generateur", []):
                st.warning(a)

            df_pc = pd.DataFrame(points)
            colonnes_pc = [
                "id", "phase", "operation_gamme", "caracteristique",
                "critere_acceptation", "moyen_controle", "frequence",
                "responsable", "enregistrement", "action_non_conformite",
            ]
            for c in colonnes_pc:
                if c not in df_pc.columns:
                    df_pc[c] = ""
            df_pc = df_pc[colonnes_pc]

            edited_pc = st.data_editor(
                df_pc,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_plan_controle",
                column_config={
                    "id": st.column_config.TextColumn("ID", width="small"),
                    "phase": st.column_config.SelectboxColumn(
                        "Phase",
                        options=["reception", "en_cours", "final"],
                        width="small",
                    ),
                    "operation_gamme": st.column_config.TextColumn("Opération", width="small"),
                    "caracteristique": st.column_config.TextColumn("Caractéristique"),
                    "critere_acceptation": st.column_config.TextColumn("Critère d'acceptation"),
                    "moyen_controle": st.column_config.TextColumn("Moyen de contrôle"),
                    "frequence": st.column_config.TextColumn("Fréquence", width="small"),
                    "responsable": st.column_config.SelectboxColumn(
                        "Responsable",
                        options=["operateur", "controleur", "qualite"],
                        width="small",
                    ),
                    "enregistrement": st.column_config.TextColumn("Enregistrement"),
                    "action_non_conformite": st.column_config.TextColumn("Action NC"),
                },
            )
            st.session_state.dossier_genere["plan_controle"]["points_controle"] = edited_pc.fillna("").to_dict("records")

            # Récapitulatif par phase
            col_pc1, col_pc2, col_pc3 = st.columns(3)
            nb_rec = sum(1 for p in points if p.get("phase") == "reception")
            nb_enc = sum(1 for p in points if p.get("phase") == "en_cours")
            nb_fin = sum(1 for p in points if p.get("phase") == "final")
            col_pc1.metric("📦 Réception", nb_rec)
            col_pc2.metric("⚙️ En-cours", nb_enc)
            col_pc3.metric("✅ Final", nb_fin)

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

    col_e1, col_e2, col_e3, col_e4 = st.columns(4)

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

    with col_e4:
        if dossier.get("plan_controle"):
            if st.button("Générer Plan de Contrôle", use_container_width=True):
                from backend.excel_exporter import exporter_plan_controle
                chemin = exporter_plan_controle(dossier["plan_controle"], f"{prefixe}_Plan_Controle.xlsx", exports_dir)
                with open(chemin, "rb") as f:
                    st.download_button("Télécharger Plan de Contrôle", f.read(), file_name=chemin.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_plan_ctrl")
        else:
            st.info("Plan de Contrôle non généré (IPR insuffisant ou désactivé)", icon="ℹ️")

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
            ev1, ev2, ev3, ev4 = st.columns(4)
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
            with ev4:
                if dossier_v.get("plan_controle"):
                    if st.button("Plan Contrôle", key=f"exp_pc_{article}", use_container_width=True):
                        from backend.excel_exporter import exporter_plan_controle
                        ch = exporter_plan_controle(dossier_v["plan_controle"], f"{article}_Plan_Controle.xlsx", exports_dir_v)
                        with open(ch, "rb") as f:
                            st.download_button("⬇️ Télécharger", f.read(), file_name=ch.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_vpc_{article}")

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
