#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Exporta la visualización a HTML estático usando graficos_v2 (sin Streamlit).

Uso:
  python export_visual_to_html_v2.py ^
    -i "Resultados/results_20250219_01.pkl" ^
    -o "visual_20250219.html" ^
    --cmg-node "Quillota220" --term-range 1 24 --cotas-range 1 24
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pickle

# ───────── Builder HTML ─────────
class HtmlBuilder:
    def __init__(self, title: str = "Visualización"):
        self.parts: List[str] = []
        self.title = title

    def add_html(self, html: str): self.parts.append(html)
    def add_section(self, title: str):
        self.parts.append(f'<h2 style="margin:16px 0 8px;font-family:Segoe UI,Inter,Arial">{title}</h2>')
    def add_text(self, text: str, cls: str = "p"):
        if cls == "warn":
            self.parts.append(f'<div style="background:#fff3cd;border:1px solid #ffeeba;padding:8px 12px;border-radius:8px;color:#856404;font-family:Segoe UI,Inter,Arial">{text}</div>')
        elif cls == "info":
            self.parts.append(f'<div style="background:#e9f5ff;border:1px solid #cfe8ff;padding:8px 12px;border-radius:8px;color:#084c7a;font-family:Segoe UI,Inter,Arial">{text}</div>')
        else:
            self.parts.append(f'<p style="margin:6px 0;font-family:Segoe UI,Inter,Arial">{text}</p>')
    def add_hr(self): self.parts.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:18px 0">')
    def build(self) -> str:
        css = """
        <style>
        body{margin:0;padding:20px;background:#0b0f14;color:#e8eef6;font-family:Segoe UI,Inter,Arial}
        .card{background:#0c121a;border:1px solid #172131;border-radius:16px;padding:16px;margin:12px 0}
        h1{font-size:20px;margin:0 0 6px}
        h2{font-size:18px;color:#cfe1fa}
        a, a:visited{color:#8dc2ff}
        table{border-collapse:collapse}
        </style>
        """
        head = (
            '<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{self.title}</title>{css}</head><body><h1>⚡ {self.title}</h1>\n"
        )
        return head + "\n".join(self.parts) + "\n</body></html>"

# ───────── Helpers ─────────
def load_results(path: Path) -> dict:
    if path.suffix.lower() in (".pkl", ".pickle"):
        with open(path, "rb") as f:
            return pickle.load(f)
    if path.suffix.lower() in (".parquet", ".pq"):
        import polars as pl
        return {"PARQUET": pl.read_parquet(path)}
    raise ValueError(f"Extensión no soportada: {path.suffix}")

# ───────── Main ─────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", required=True)
    ap.add_argument("-o","--output", default="visualizacion.html")
    ap.add_argument("--title", default="Comparación PID/PCP · Visualización")
    ap.add_argument("--cmg-node", default=None)
    ap.add_argument("--term-range", nargs=2, type=int, default=None, metavar=("H1","H2"))
    ap.add_argument("--cotas-range", nargs=2, type=int, default=None, metavar=("H1","H2"))
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"No existe: {in_path}")

    from funciones import infer_hours, fecha_from_filename
    import Graficos_v2 as G  # ← versión sin Streamlit

    builder = HtmlBuilder(title=args.title)

    # datos base
    results = load_results(in_path)
    solutions = tuple(sorted(results.keys()))

    # horas (fallback a 1..24 si no se pueden inferir)
    hours_full = infer_hours(results)
    if not hours_full:
        hours_full = [str(i) for i in range(1, 25)]
    hours_int = [int(h) for h in hours_full]
    min_h, max_h = (hours_int[0], hours_int[-1]) if hours_int else (1, 24)

    # estilo y constantes
    COLOR = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#F0E442", "#56B4E9", "#000000"]
    CATEGORY_LABELS = [
        "Centrales de Embalse",
        "Sistemas de Almacenamiento",
        "Centrales Térmicas",
        "Centrales Solares",
        "Centrales Eólicas",
    ]
    THERMAL_IDX = 2   # índice de "Centrales Térmicas" en CATEGORY_LABELS
    THRESHOLD = 0.5   # umbral para resaltar diferencias (tu lógica en prepara_datos)

    # meta/cabecera
    try:
        cap = f"Fuente: {in_path.name} · Fecha: {fecha_from_filename(in_path)}"
    except Exception:
        cap = f"Fuente: {in_path.name}"
    builder.add_text(cap, cls="info")

    # ----- secciones -----
    # 1) Totales por categoría
    try:
        html_tc = G.render_totales_por_categoria(
            results, solutions, hours_full, hours_int, min_h, max_h,
            CATEGORY_LABELS, COLOR, filtros_por_categoria=None
        )
        builder.add_html(html_tc)
    except Exception as e:
        builder.add_text(f"Totales por categoría: {e}", cls="warn")
    builder.add_hr()

    # 2) CMG por nodo
    try:
        html_cmg = G.render_cmg_nodo(
            results, solutions, hours_full, hours_int, min_h, max_h, COLOR,
            node=args.cmg_node
        )
        builder.add_html(html_cmg)
    except Exception as e:
        builder.add_text(f"CMG nodo: {e}", cls="warn")
    builder.add_hr()

    # 3) Análisis térmicas
    try:
        term_range = tuple(args.term_range) if args.term_range else None  # (h1,h2) o None
        # Par por defecto: primeras 2 soluciones con GENTABLES lo decide v2 si None
        html_term = G.render_analisis_termicas(
            results=results,
            SOLUTIONS=solutions,
            HOURS_FULL=hours_full,
            BASE_DIR=in_path.parent,
            THRESHOLD=THRESHOLD,
            THERMAL_IDX=THERMAL_IDX,
            sol_pair=None,
            rango=term_range,
            nombre_resultado=in_path.stem,
        )
        builder.add_html(html_term)
    except Exception as e:
        builder.add_text(f"Análisis térmicas: {e}", cls="warn")
    builder.add_hr()

    # 4) Totales sistema (GENT)
    try:
        html_gent = G.render_totales_sistema(
            results=results,
            solutions=solutions,
            hours_full=hours_full,
            hours_int=hours_int,
            color_palette=COLOR,
            sel_solutions=None,   # por defecto: todas las que tengan GENT
            vars_sel=None,        # por defecto: ["Consumos Propios","Pérdidas"]
            lineas_sel=None,      # por defecto: top-5 primeras
        )
        builder.add_html(html_gent)
    except Exception as e:
        builder.add_text(f"Totales sistema (GENT): {e}", cls="warn")
    builder.add_hr()

    # 5) Comparador de COTAS
    try:
        cotas_range = tuple(args.cotas_range) if args.cotas_range else None
        html_cotas = G.render_comparador_cotas(
            results=results,
            solutions=solutions,
            rango=cotas_range,
            pair=None,            # por defecto: primeras 2 con COTAS
            modo="diferencia",    # puedes cambiar a "trayectorias"
            top_k=10,
            ncols=2,
            h1=None, h2=None,     # por defecto: 1 y 24 si existen
            filtro_nombres=None,
        )
        builder.add_html(html_cotas)
    except Exception as e:
        builder.add_text(f"COTAS: {e}", cls="warn")

    # ----- escribir HTML -----
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = builder.build()
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Archivo escrito: {out.resolve()}")
    try:
        print(f"[INFO] Tamaño: {out.stat().st_size} bytes")
    except Exception:
        pass

if __name__ == "__main__":
    main()
