"""Exportación de reportes ejecutivos en PDF (F64)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace

_REPLACE = {"≥": ">=", "≤": "<=", "−": "-", "→": "->", "Δ": "Var.", "·": "-", "✔": "Si", "—": "-", "–": "-",
            "“": '"', "”": '"', "’": "'"}


def _t(text) -> str:
    s = "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text)
    for k, v in _REPLACE.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 6, _t("EDU-ALERTA Panamá · Reporte ejecutivo · Datos sintéticos de demostración"),
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 6, _t(f"Página {self.page_no()} · generado {datetime.now():%Y-%m-%d %H:%M}"), align="R")


def _table(pdf: _PDF, df: pd.DataFrame, widths: list[float] | None = None, max_rows: int = 40):
    """Tabla con ajuste de línea (no recorta fórmulas ni títulos); anchos proporcionales al contenido."""
    if df.empty:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, _t("Sin registros."), new_x="LMARGIN", new_y="NEXT")
        return
    cols = list(df.columns)
    if not widths:
        lens = [max(len(_t(c)), int(df[c].head(max_rows).map(lambda v: len(_t(v))).max() or 0)) for c in cols]
        widths = [min(max(n, 6), 70) for n in lens]
    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(190, 198, 204)
    with pdf.table(col_widths=tuple(widths), width=pdf.epw, line_height=4.6, text_align="LEFT",
                   headings_style=FontFace(emphasis="BOLD", fill_color=(230, 236, 240))) as table:
        table.row([_t(c) for c in cols])
        for rec in df.head(max_rows).itertuples(index=False):
            table.row([_t(v) for v in rec])


def executive_pdf(titulo: str, filtros: dict, kpis: dict, tablas: dict[str, pd.DataFrame]) -> bytes:
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, _t(titulo), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, _t("Filtros: " + "; ".join(f"{k}: {v}" for k, v in filtros.items())))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Indicadores clave", new_x="LMARGIN", new_y="NEXT")
    rows = [{"KPI": k["nombre"], "Valor": "N/D" if k["valor"] is None else f"{k['valor']} {k['unidad']}",
             "Fórmula": k["formula"], "Fuente": k["fuente"]} for k in kpis.values()]
    _table(pdf, pd.DataFrame(rows), [42, 22, 76, 50])
    for name, df in tablas.items():
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _t(name), new_x="LMARGIN", new_y="NEXT")
        _table(pdf, df)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _t("Las alertas son señales de riesgo basadas en reglas explicables y configurables; no son "
                            "probabilidades de deserción ni política oficial de MEDUCA. Toda acción requiere revisión "
                            "humana."))
    return bytes(pdf.output())
