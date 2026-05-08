"""
Export PDF des documents qualité (AMDEC Produit, AMDEC Process, Gamme).
Génère un PDF multi-sections prêt à imprimer / archiver.
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Palette couleurs ──────────────────────────────────────────────────────────
BLEU_TITRE   = colors.HexColor("#1a3a5c")
BLEU_HEADER  = colors.HexColor("#2563eb")
GRIS_HEADER  = colors.HexColor("#f1f5f9")
ROUGE        = colors.HexColor("#dc2626")
ORANGE       = colors.HexColor("#ea580c")
VERT         = colors.HexColor("#16a34a")
GRIS_LIGNE   = colors.HexColor("#f8fafc")
BLANC        = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


def _styles():
    base = getSampleStyleSheet()
    return {
        "titre_doc": ParagraphStyle("titre_doc", parent=base["Title"],
            fontSize=18, textColor=BLEU_TITRE, spaceAfter=4),
        "sous_titre": ParagraphStyle("sous_titre", parent=base["Normal"],
            fontSize=10, textColor=colors.grey, spaceAfter=12),
        "section": ParagraphStyle("section", parent=base["Heading2"],
            fontSize=13, textColor=BLEU_TITRE, spaceBefore=14, spaceAfter=6),
        "label": ParagraphStyle("label", parent=base["Normal"],
            fontSize=8, textColor=colors.grey),
        "valeur": ParagraphStyle("valeur", parent=base["Normal"],
            fontSize=9, textColor=colors.black),
        "cell": ParagraphStyle("cell", parent=base["Normal"],
            fontSize=7.5, leading=10),
        "cell_bold": ParagraphStyle("cell_bold", parent=base["Normal"],
            fontSize=7.5, leading=10, fontName="Helvetica-Bold"),
        "footer": ParagraphStyle("footer", parent=base["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
    }


def _ipr_color(ipr):
    if ipr >= 100:
        return ROUGE
    if ipr >= 50:
        return ORANGE
    return VERT


def _on_page(canvas, doc, metadata: dict, doc_title: str):
    """En-tête et pied de page sur chaque page."""
    canvas.saveState()
    w, h = A4
    # Bande de titre
    canvas.setFillColor(BLEU_TITRE)
    canvas.rect(0, h - 20 * mm, w, 20 * mm, fill=1, stroke=0)
    canvas.setFillColor(BLANC)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(MARGIN, h - 11 * mm, doc_title)
    canvas.setFont("Helvetica", 8)
    ref = metadata.get("reference", "")
    desig = metadata.get("designation", "")[:60]
    canvas.drawRightString(w - MARGIN, h - 11 * mm, f"{ref} — {desig}")

    # Pied de page
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 8 * mm,
        f"Généré le {date.today().isoformat()} | Qual.IA — Confidentiel")
    canvas.drawRightString(w - MARGIN, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _table_style_amdec(n_rows: int) -> TableStyle:
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLEU_HEADER),
        ("TEXTCOLOR",  (0, 0), (-1, 0), BLANC),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 7),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRIS_LIGNE, BLANC]),
        ("FONTSIZE",   (0, 1), (-1, -1), 7),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    return TableStyle(style)


# ── Fiche de garde ────────────────────────────────────────────────────────────

def _page_garde(metadata: dict, s: dict) -> list:
    ref   = metadata.get("reference", "—")
    desig = metadata.get("designation", "—")
    cat   = metadata.get("categorie", "—")
    wf    = metadata.get("workflow", {})
    statut = wf.get("statut", metadata.get("statut", "—"))
    redige = metadata.get("redige_par", "—")
    approuve = metadata.get("approuve_par", "—")
    indice = metadata.get("indice_revision", "A")
    date_c = metadata.get("date_creation", "—")

    elements = [
        Spacer(1, 20 * mm),
        Paragraph("DOSSIER QUALITÉ", ParagraphStyle("g1",
            fontSize=22, textColor=BLEU_TITRE, alignment=TA_CENTER, fontName="Helvetica-Bold")),
        Spacer(1, 4 * mm),
        Paragraph(desig, ParagraphStyle("g2",
            fontSize=14, textColor=colors.grey, alignment=TA_CENTER)),
        Spacer(1, 10 * mm),
        HRFlowable(width="80%", thickness=1, color=BLEU_HEADER, hAlign="CENTER"),
        Spacer(1, 10 * mm),
    ]

    info_data = [
        ["Référence", ref,          "Catégorie",     cat],
        ["Statut",    statut.upper(),"Indice révision", indice],
        ["Rédigé par", redige,      "Approuvé par",  approuve or "—"],
        ["Date création", date_c,   "", ""],
    ]
    t = Table(info_data, colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BLEU_TITRE),
        ("TEXTCOLOR", (2, 0), (2, -1), BLEU_TITRE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRIS_LIGNE, BLANC]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)

    # Traitements
    traitements = metadata.get("traitements", [])
    if traitements:
        from backend.typologie_manager import format_traitements_str
        trt_str = format_traitements_str(traitements)
        elements += [
            Spacer(1, 6 * mm),
            Paragraph(f"<b>Traitements :</b> {trt_str}", s["valeur"]),
        ]

    dims = metadata.get("dimensions", {})
    if dims:
        dim_str = " | ".join(f"{k} : {v}" for k, v in dims.items() if v is not None)
        elements += [
            Paragraph(f"<b>Dimensions :</b> {dim_str}", s["valeur"]),
        ]

    elements.append(PageBreak())
    return elements


# ── AMDEC Produit ─────────────────────────────────────────────────────────────

def _section_amdec_produit(amdec: dict, s: dict) -> list:
    modes = amdec.get("modes_defaillance", [])
    elements = [
        Paragraph("AMDEC Produit", s["section"]),
        Paragraph(
            f"{len(modes)} mode(s) analysé(s) | "
            f"Confiance IA : {amdec.get('confiance_globale', '—')}%",
            s["sous_titre"],
        ),
    ]
    if not modes:
        elements.append(Paragraph("Aucun mode de défaillance.", s["valeur"]))
        return elements

    headers = ["N°", "Famille", "Mode de défaillance", "Effet", "G", "O", "D", "IPR", "Classe", "Action corrective"]
    col_w_raw = [8, 18, 38, 35, 7, 7, 7, 10, 20, 45]
    usable = PAGE_W - 2 * MARGIN
    total = sum(col_w_raw)
    col_w = [c * mm * usable / (total * mm) for c in col_w_raw]

    rows = [headers]
    style_cmds = []
    for i, m in enumerate(modes, start=1):
        ipr = (m.get("G") or 0) * (m.get("O") or 0) * (m.get("D") or 0)
        row = [
            Paragraph(str(m.get("no", i)), s["cell"]),
            Paragraph(str(m.get("famille", "")), s["cell"]),
            Paragraph(str(m.get("mode_defaillance", "")), s["cell"]),
            Paragraph(str(m.get("effets_defaillance", "")), s["cell"]),
            Paragraph(str(m.get("G", "")), s["cell"]),
            Paragraph(str(m.get("O", "")), s["cell"]),
            Paragraph(str(m.get("D", "")), s["cell"]),
            Paragraph(f"<b>{ipr}</b>", s["cell_bold"]),
            Paragraph(str(m.get("classe_criticite", "")), s["cell"]),
            Paragraph(str(m.get("actions_correctives", "")), s["cell"]),
        ]
        rows.append(row)
        # Colorer la cellule IPR
        c = _ipr_color(ipr)
        style_cmds.append(("TEXTCOLOR", (7, i), (7, i), c))
        style_cmds.append(("FONTNAME", (7, i), (7, i), "Helvetica-Bold"))

    t = Table(rows, colWidths=col_w, repeatRows=1)
    base_style = _table_style_amdec(len(rows))
    for cmd in style_cmds:
        base_style.add(*cmd)
    t.setStyle(base_style)
    elements.append(t)
    return elements


# ── AMDEC Process ─────────────────────────────────────────────────────────────

def _section_amdec_process(amdec: dict, s: dict) -> list:
    modes = amdec.get("modes_defaillance", [])
    elements = [
        PageBreak(),
        Paragraph("AMDEC Process", s["section"]),
        Paragraph(
            f"{len(modes)} mode(s) analysé(s) | "
            f"Confiance IA : {amdec.get('confiance_globale', '—')}%",
            s["sous_titre"],
        ),
    ]
    if not modes:
        elements.append(Paragraph("Aucun mode de défaillance.", s["valeur"]))
        return elements

    headers = ["N°", "Opération", "Mode défaillance", "Effet produit", "G", "O", "D", "IPR", "Classe", "Action corrective"]
    col_w_raw = [8, 30, 35, 32, 7, 7, 7, 10, 20, 45]
    usable = PAGE_W - 2 * MARGIN
    total = sum(col_w_raw)
    col_w = [c * mm * usable / (total * mm) for c in col_w_raw]

    rows = [headers]
    style_cmds = []
    for i, m in enumerate(modes, start=1):
        ipr = (m.get("G") or 0) * (m.get("O") or 0) * (m.get("D") or 0)
        row = [
            Paragraph(str(m.get("no", i)), s["cell"]),
            Paragraph(str(m.get("operation_process", "")), s["cell"]),
            Paragraph(str(m.get("mode_defaillance", "")), s["cell"]),
            Paragraph(str(m.get("effets_produit", "")), s["cell"]),
            Paragraph(str(m.get("G", "")), s["cell"]),
            Paragraph(str(m.get("O", "")), s["cell"]),
            Paragraph(str(m.get("D", "")), s["cell"]),
            Paragraph(f"<b>{ipr}</b>", s["cell_bold"]),
            Paragraph(str(m.get("classe_criticite", "")), s["cell"]),
            Paragraph(str(m.get("actions_correctives", "")), s["cell"]),
        ]
        rows.append(row)
        c = _ipr_color(ipr)
        style_cmds.append(("TEXTCOLOR", (7, i), (7, i), c))
        style_cmds.append(("FONTNAME",  (7, i), (7, i), "Helvetica-Bold"))

    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = _table_style_amdec(len(rows))
    for cmd in style_cmds:
        ts.add(*cmd)
    t.setStyle(ts)
    elements.append(t)
    return elements


# ── Gamme de production ───────────────────────────────────────────────────────

def _section_gamme(gamme: dict, s: dict) -> list:
    ops = gamme.get("operations", [])
    elements = [
        PageBreak(),
        Paragraph("Gamme de Production", s["section"]),
        Paragraph(f"{len(ops)} opération(s)", s["sous_titre"]),
    ]
    if not ops:
        elements.append(Paragraph("Aucune opération.", s["valeur"]))
        return elements

    headers = ["N° Op", "Désignation", "Poste / Machine", "Paramètres clés", "Point contrôle", "Critère", "Tps (min)"]
    col_w_raw = [14, 42, 28, 35, 30, 28, 14]
    usable = PAGE_W - 2 * MARGIN
    total = sum(col_w_raw)
    col_w = [c * mm * usable / (total * mm) for c in col_w_raw]

    rows = [headers]
    for op in ops:
        params = []
        for k in ("parametre_1", "parametre_2", "parametre_3"):
            p = op.get(k, "")
            v_key = k.replace("parametre", "valeur")
            v = op.get(v_key, "")
            if p:
                params.append(f"{p}: {v}" if v else p)
        row = [
            Paragraph(str(op.get("no_op", "")), s["cell"]),
            Paragraph(str(op.get("designation", "")), s["cell_bold"]),
            Paragraph(str(op.get("poste_machine", "")), s["cell"]),
            Paragraph("\n".join(params), s["cell"]),
            Paragraph(str(op.get("point_controle", "")), s["cell"]),
            Paragraph(str(op.get("critere_acceptation", "")), s["cell"]),
            Paragraph(str(op.get("temps_min", "")), s["cell"]),
        ]
        rows.append(row)

    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = _table_style_amdec(len(rows))
    t.setStyle(ts)
    elements.append(t)

    # Temps total
    try:
        temps_total = sum(
            float(op.get("temps_min") or 0) for op in ops
        )
        elements.append(Paragraph(
            f"<b>Temps total gamme : {int(temps_total)} min</b>",
            ParagraphStyle("tp", parent=s["valeur"], spaceBefore=4)
        ))
    except Exception:
        pass
    return elements


# ── Point d'entrée principal ──────────────────────────────────────────────────

def exporter_dossier_pdf(
    metadata: dict,
    amdec_produit: dict,
    amdec_process: dict,
    gamme: dict,
    sections: list[str] | None = None,
) -> bytes:
    """
    Génère un PDF complet du dossier qualité.

    sections : liste de clés à inclure parmi
        ["garde", "amdec_produit", "amdec_process", "gamme"]
        None = toutes
    Retourne les bytes du PDF.
    """
    if sections is None:
        sections = ["garde", "amdec_produit", "amdec_process", "gamme"]

    buf = io.BytesIO()
    ref = metadata.get("reference", "dossier")
    doc_title = f"Dossier Qualité — {ref}"

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=25 * mm, bottomMargin=18 * mm,
        title=doc_title,
        author="Qual.IA",
    )

    s = _styles()
    story = []

    if "garde" in sections:
        story += _page_garde(metadata, s)
    if "amdec_produit" in sections:
        story += _section_amdec_produit(amdec_produit, s)
    if "amdec_process" in sections:
        story += _section_amdec_process(amdec_process, s)
    if "gamme" in sections:
        story += _section_gamme(gamme, s)

    doc.build(
        story,
        onFirstPage=lambda c, d: _on_page(c, d, metadata, doc_title),
        onLaterPages=lambda c, d: _on_page(c, d, metadata, doc_title),
    )

    buf.seek(0)
    return buf.read()
