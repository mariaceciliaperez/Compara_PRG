# -*- coding: utf-8 -*-
"""graficos_v2.py — versión sin Streamlit: devuelve HTML puro por sección."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import math
import numpy as np
import pandas as pd
import polars as pl
import plotly.graph_objects as go
import plotly.io as pio

from funciones import normalize_hours, prepara_datos, coerce_schema

# ───────────────────────────────────────────────────────────────
# Utilidades HTML
# ───────────────────────────────────────────────────────────────

def _card(html: str) -> str:
    return f'<div class="card">{html}</div>'

def _h2(title: str) -> str:
    return f'<h2 style="margin:16px 0 8px;font-family:Segoe UI,Inter,Arial">{title}</h2>'

def _p_info(text: str) -> str:
    return ('<div style="background:#e9f5ff;border:1px solid #cfe8ff;'
            'padding:8px 12px;border-radius:8px;color:#084c7a;'
            'font-family:Segoe UI,Inter,Arial">{}</div>').format(text)

def _p_warn(text: str) -> str:
    return ('<div style="background:#fff3cd;border:1px solid #ffeeba;'
            'padding:8px 12px;border-radius:8px;color:#856404;'
            'font-family:Segoe UI,Inter,Arial">{}</div>').format(text)

def _hr() -> str:
    return '<hr style="border:none;border-top:1px solid #e5e7eb;margin:18px 0">'

def _fig_html(fig: go.Figure, height: Optional[int] = None) -> str:
    if height is not None:
        fig.update_layout(height=height)
    return pio.to_html(fig, include_plotlyjs="cdn", full_html=False, config={"responsive": True})

def _df_html(df: pd.DataFrame) -> str:
    return f'<div style="overflow:auto">{df.to_html(border=0)}</div>'

# ───────────────────────────────────────────────────────────────
# Helpers “GENT”
# ───────────────────────────────────────────────────────────────

def _coerce_gent_payload(gent_obj):
    """Normaliza GENT a {'tabla': DF, 'losses': DF} si viene como dict o tuple."""
    if isinstance(gent_obj, dict) and "tabla" in gent_obj and "losses" in gent_obj:
        return gent_obj
    if isinstance(gent_obj, tuple) and len(gent_obj) == 2:
        return {"tabla": gent_obj[0], "losses": gent_obj[1]}
    return None

def _looks_like_polars_df(x):
    """Evita depender de isinstance(pl.DataFrame)."""
    return (
        x is not None
        and hasattr(x, "columns")
        and hasattr(x, "height")
        and hasattr(x, "select")
        and hasattr(x, "to_numpy")
    )

def _hours_from_df(df: pl.DataFrame) -> List[str]:
    hs = [c for c in df.columns if isinstance(c, str) and c.isdigit()]
    return sorted(hs, key=lambda x: int(x))

def _label_col(df: pl.DataFrame) -> str:
    preferidas = [
        "Variable", "Nombre", "Nombre_PLEXOS", "Serie", "Concepto", "Etiqueta",
        "Categoria", "Fila", "Descripción", "Hora"
    ]
    schema = dict(zip(df.columns, df.dtypes))
    for col in preferidas:
        if col in df.columns and schema[col] == pl.Utf8:
            return col
    for c, t in schema.items():
        if t == pl.Utf8:
            return c
    return df.columns[0]

def _strip_expr(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.replace_all(r"^\s+|\s+$", "")

def _row_xy(df_tabla: pl.DataFrame, var_name: str):
    if df_tabla is None or df_tabla.is_empty():
        return None, None
    lab = _label_col(df_tabla)
    hs = _hours_from_df(df_tabla)
    if not hs:
        return None, None
    row = df_tabla.filter(_strip_expr(pl.col(lab)) == var_name.strip())
    if row.is_empty():
        return None, None
    x = [int(h) for h in hs]
    y = row.select(hs).to_numpy().ravel()
    return x, y

def _losses_line_xy(gent: dict, line_name: str):
    df = gent.get("losses", None)
    if df is None or not _looks_like_polars_df(df) or df.is_empty():
        return None, None
    if not {"Nombre_PLEXOS", "Loss", "Hora"}.issubset(set(df.columns)):
        return None, None
    try:
        df2 = (
            df.filter(pl.col("Nombre_PLEXOS") == line_name)
              .select(
                  pl.col("Hora").cast(pl.Int64, strict=False).alias("Hora"),
                  pl.col("Loss").cast(pl.Float64, strict=False).alias("Loss")
              )
              .drop_nulls(["Hora", "Loss"])
              .sort("Hora")
        )
    except Exception:
        return None, None
    if df2.is_empty():
        return None, None
    x = df2.get_column("Hora").to_list()
    y = df2.get_column("Loss").to_numpy().ravel()
    return x, y

# ───────────────────────────────────────────────────────────────
# 1) Totales por categoría
# ───────────────────────────────────────────────────────────────

def render_totales_por_categoria(
    results: dict,
    SOLUTIONS: Sequence[str],
    HOURS_FULL: Sequence[str],
    HOURS_INT: Sequence[int],
    MIN_H: int,
    MAX_H: int,
    CATEGORY_LABELS: Sequence[str],
    COLOR: Sequence[str],
    filtros_por_categoria: Optional[Dict[str, Sequence[str]]] = None,  # {"Centrales de Embalse": ["X","Y"], ...}
) -> str:
    parts: List[str] = [_h2("Totales por categoría")]
    for cat_idx, category in enumerate(CATEGORY_LABELS):
        sols = [
            s for s in SOLUTIONS
            if "GENTABLES" in results.get(s, {})
            and cat_idx < len(results[s]["GENTABLES"])
        ]
        if not sols:
            parts.append(_card(_p_info("Sin datos disponibles.")))
            continue

        # Filtro opcional de centrales
        seleccion = set((filtros_por_categoria or {}).get(category, []))

        fig = go.Figure()
        any_trace = False
        for i, sol in enumerate(sols):
            df = normalize_hours(results[sol]["GENTABLES"][cat_idx], HOURS_FULL)
            df = coerce_schema(df, HOURS_FULL)
            if df is None or df.is_empty() or "Nombre_PLEXOS" not in df.columns:
                continue
            if seleccion:
                df = df.filter(pl.col("Nombre_PLEXOS").is_in(list(seleccion)))
            if df.is_empty():
                continue
            y = df.select(HOURS_FULL).sum().to_numpy().ravel()
            fig.add_trace(go.Scatter(
                x=list(HOURS_INT), y=y, mode="lines+markers",
                name=sol, line=dict(color=COLOR[i % len(COLOR)], width=2), marker=dict(size=4)
            ))
            any_trace = True

        fig.add_annotation(
            xref="paper", yref="paper", x=0.0, y=1.0, xanchor="left", yanchor="top",
            text=f"<b>{category}</b>", showarrow=False, font=dict(size=15)
        )
        fig.update_layout(
            title=None,
            xaxis=dict(title="Hora", range=[MIN_H, MIN_H + 47], dtick=1,
                       rangeslider=dict(visible=True)),
            yaxis_title="MWh",
            legend_title="Solución",
            template="simple_white",
            margin=dict(l=40, r=10, t=28, b=20),
            height=360
        )
        if any_trace:
            parts.append(_card(_fig_html(fig)))
        else:
            parts.append(_card(_p_info(f"Sin series para {category} con el filtro actual.")))
    return "\n".join(parts)

# ───────────────────────────────────────────────────────────────
# 2) CMG por nodo
# ───────────────────────────────────────────────────────────────

def render_cmg_nodo(
    results: dict,
    solutions: Sequence[str],
    hours_full: Sequence[str],
    hours_int: Sequence[int],
    min_h: int,
    max_h: int,
    color_palette: Sequence[str],
    node: Optional[str] = None,
) -> str:
    parts = [_h2("CMG nodo")]
    available_solutions = [s for s in solutions if "CMG" in results.get(s, {})]
    if not available_solutions:
        return "\n".join([_h2("CMG nodo"), _card(_p_warn("El archivo no contiene CMG para ninguna solución."))])

    cmg0 = coerce_schema(results[available_solutions[0]]["CMG"], hours_full)
    if cmg0 is None or cmg0.is_empty():
        return "\n".join([_h2("CMG nodo"), _card(_p_warn("CMG vacío."))])

    name_col = "Nombre_PLEXOS" if "Nombre_PLEXOS" in cmg0.columns else cmg0.columns[0]
    nodes_sorted = sorted(cmg0.get_column(name_col).to_list())
    node_sel = node if node in nodes_sorted else ( "Quillota220" if "Quillota220" in nodes_sorted else nodes_sorted[0] )

    fig = go.Figure()
    any_trace = False
    for i, sol in enumerate(available_solutions):
        df = normalize_hours(results[sol]["CMG"], hours_full)
        df = coerce_schema(df, hours_full)
        if df is None or df.is_empty():
            continue
        col_nom = "Nombre_PLEXOS" if "Nombre_PLEXOS" in df.columns else df.columns[0]
        df_row = df.filter(pl.col(col_nom) == node_sel)
        if df_row.is_empty():
            continue
        y = df_row.select(list(hours_full)).to_numpy().ravel()
        fig.add_trace(go.Scatter(
            x=list(hours_int), y=y, mode="lines+markers", name=sol,
            line=dict(color=color_palette[i % len(color_palette)], width=2)
        ))
        any_trace = True

    if not any_trace:
        return "\n".join([_h2("CMG nodo"), _card(_p_info(f"No se encontró el nodo '{node_sel}' en las soluciones elegidas."))])

    fig.update_layout(
        title=f"CMG — {node_sel}",
        xaxis=dict(title="Hora", range=[min_h, min_h + 47], dtick=1, rangeslider=dict(visible=True)),
        yaxis_title="USD/MWh",
        legend_title="Solución",
        template="simple_white",
    )
    parts.append(_card(_fig_html(fig)))
    return "\n".join(parts)

# ───────────────────────────────────────────────────────────────
# 3) Análisis térmicas (par de soluciones + rango)
# ───────────────────────────────────────────────────────────────

def render_analisis_termicas(
    results: dict,
    SOLUTIONS: Sequence[str],
    HOURS_FULL: Sequence[str],
    BASE_DIR: Path,
    THRESHOLD: float,
    THERMAL_IDX: int,
    sol_pair: Optional[Tuple[str, str]] = None,
    rango: Optional[Tuple[int, int]] = None,
    nombre_resultado: Optional[str] = None,
) -> str:
    parts = [_h2("Análisis térmicas")]

    sols = [s for s in SOLUTIONS if "GENTABLES" in results.get(s, {})]
    if len(sols) < 2:
        return "\n".join([_h2("Análisis térmicas"), _card(_p_info("Se necesitan al menos 2 soluciones con GENTABLES para comparar."))])

    # Par por defecto: primeras dos distintas
    if sol_pair is None:
        sol_pair = (sols[0], sols[1])
    sol1, sol2 = sol_pair

    # Rango por defecto
    h1, h2 = (1, 24) if not rango else rango
    if h1 > h2: h1, h2 = h2, h1

    # map int->str válidos
    int2str = {int(h): h for h in HOURS_FULL if str(h).isdigit()}
    hours_range = [int2str[h] for h in range(h1, h2 + 1) if h in int2str]
    if not hours_range:
        return "\n".join([_h2("Análisis térmicas"), _card(_p_warn("El rango seleccionado no existe en los datos cargados."))])

    # Datos + comentario (solo mostrar existente si lo hay)
    pivot_pd, resumen_pd, styles_pd = prepara_datos(
        _results=results,
        sol_a=sol1,
        sol_b=sol2,
        thermal_idx=THERMAL_IDX,
        hours_full=HOURS_FULL,
        hours=hours_range,
        th=THRESHOLD,
    )
    if pivot_pd is None:
        return "\n".join([_h2("Análisis térmicas"), _card(_p_info("No se detectaron cambios significativos."))])

    comentarios_dir = BASE_DIR / "Comentarios"
    comentarios_dir.mkdir(exist_ok=True)
    nombre_resultado = nombre_resultado or "default"
    comentario_path  = comentarios_dir / f"comentario_termicas__{Path(nombre_resultado).stem}.txt"
    comentario_html = ""
    if comentario_path.exists():
        txt = comentario_path.read_text(encoding="utf-8").strip()
        if txt:
            comentario_html = _card(
                "<h3 style='margin-top:0'>Comentario</h3>"
                f"<div style='background:#eaf4fc;padding:12px 16px;border-radius:8px;white-space:pre-line'>{txt}</div>"
            )

    # Tabla coloreada (estática)
    styled = (
        pivot_pd.style
        .set_properties(**{"text-align": "center"})
        .apply(lambda _: styles_pd, axis=None)
        .format(precision=0, na_rep="")
    )
    height_px = 80 + 28 * len(pivot_pd)
    tabla_min_width_px = 220 + 28 * len(hours_range)
    extra_scrollbar_space = 24
    css_iframe = f"""
    <style>
    .resp-wrap {{
      width: 100%;
      overflow-x: auto;
      overflow-y: hidden;
      border: 1px solid #ddd;
      padding: 6px 6px 10px 6px;
      -webkit-overflow-scrolling: touch;
      scrollbar-gutter: stable both-edges;
    }}
    .styled-table {{
      width: max-content;
      min-width: {tabla_min_width_px}px;
      table-layout: fixed;
      border-collapse: collapse;
      font-family: 'Segoe UI', sans-serif;
      font-size: 10px;
    }}
    .styled-table, .styled-table * {{ box-sizing: border-box; }}
    .styled-table th, .styled-table td {{
      padding: 2px 3px; text-align: center; white-space: nowrap;
    }}
    .styled-table th {{ position: sticky; top: 0; z-index: 5; background: #f4f4f4; }}
    .styled-table th:first-child, .styled-table td:first-child {{ width: 220px; text-align: left; }}
    .styled-table td:first-child {{
      position: sticky; left: 0; z-index: 4; background: #fff0f0;
    }}
    .styled-table th:first-child {{
      position: sticky; top: 0; left: 0; z-index: 6; background: #ffe0e0; box-shadow: 1px 0 0 #ddd;
    }}
    .styled-table th:not(:first-child), .styled-table td:not(:first-child) {{ width: 28px; }}
    .styled-table thead th:not(:first-child) {{
      writing-mode: vertical-rl; transform: rotate(180deg);
      white-space: nowrap; height: 90px; padding: 6px 0;
    }}
    </style>
    """
    table_html = css_iframe + f'<div class="resp-wrap">{styled.to_html(classes="styled-table")}</div>'

    # Resumen ordenado por |Δ|
    diff_col = next(c for c in resumen_pd.columns if c.startswith("Δ Total"))
    df_show = resumen_pd.reindex(resumen_pd[diff_col].abs().sort_values(ascending=False).index).head(min(50, len(resumen_pd)))

    parts.append(comentario_html if comentario_html else "")
    parts.append(_card("<h3 style='margin-top:0'>Diferencias hora-a-hora – tabla coloreada</h3>" + table_html))
    parts.append(_card("<h3 style='margin-top:0'>Resumen del día – top por |Δ|</h3>" + _df_html(df_show)))

    return "\n".join(parts)

# ───────────────────────────────────────────────────────────────
# 4) Totales de sistema (GENT)
# ───────────────────────────────────────────────────────────────

def render_totales_sistema(
    results: dict,
    solutions: Sequence[str],
    hours_full: Sequence[str],
    hours_int: Sequence[int],
    color_palette: Sequence[str],
    sel_solutions: Optional[Sequence[str]] = None,
    vars_sel: Optional[Sequence[str]] = None,
    lineas_sel: Optional[Sequence[str]] = None,
) -> str:
    parts = [_h2("Totales sistema (GENT)")]

    VARS = [
        "Generación Total [MWh]",
        "Consumos Propios [MWh]",
        "Pérdidas [MWh]",
        "Demanda Total [MWh]",
    ]
    DEFAULT_VARS = ["Consumos Propios [MWh]", "Pérdidas [MWh]"]
    var_color = {
        "Generación Total [MWh]": "#009E73",
        "Consumos Propios [MWh]": "#0072B2",
        "Pérdidas [MWh]": "#D55E00",
        "Demanda Total [MWh]": "#CC79A7",
    }

    sols_ok = []
    for s in solutions:
        gent_raw = results.get(s, {}).get("GENT", None)
        gent = _coerce_gent_payload(gent_raw)
        if gent and _looks_like_polars_df(gent.get("tabla")):
            sols_ok.append(s)
    if not sols_ok:
        return "\n".join([_h2("Totales sistema (GENT)"), _card(_p_info("No hay resultados GENT en el archivo cargado."))])

    sel = list(sel_solutions or sols_ok)
    if not sel:
        return "\n".join([_h2("Totales sistema (GENT)"), _card(_p_warn("Debes seleccionar al menos una solución."))])

    vars_sel = [v for v in (vars_sel or DEFAULT_VARS) if v in DEFAULT_VARS] or DEFAULT_VARS

    # 1) Evolución horaria
    fig = go.Figure()
    any_trace = False
    xmin, xmax = None, None
    dashes = ["solid", "dash", "dot", "dashdot", "longdash"]

    for i, sol in enumerate(sel):
        gent = _coerce_gent_payload(results[sol]["GENT"])
        df_tabla = gent["tabla"]
        for var in vars_sel:
            x, y = _row_xy(df_tabla, var)
            if x is None or y is None or len(x) == 0:
                continue
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=f"{sol} – {var}",
                line=dict(color=var_color.get(var, color_palette[i % len(color_palette)]),
                          width=2, dash=dashes[i % len(dashes)]),
                legendgroup=var,
            ))
            any_trace = True
            xmin = min(xmin, min(x)) if xmin is not None else min(x)
            xmax = max(xmax, max(x)) if xmax is not None else max(x)

    if not any_trace:
        parts.append(_card(_p_info("No se pudieron construir series; revisa que existan horas en el DataFrame.")))
    else:
        fig.update_layout(
            xaxis=dict(title="Hora", range=[xmin, xmin + min(47, (xmax - xmin))], dtick=1,
                       rangeslider=dict(visible=True)),
            yaxis_title="MWh",
            legend_title="Serie",
            template="simple_white",
            height=420,
        )
        parts.append(_card("<h3 style='margin-top:0'>Consumos y Pérdidas – Evolución horaria</h3>" + _fig_html(fig)))

    # 2) Pérdidas por línea (NO agregadas)
    # Reúne universo de líneas
    all_lines = set()
    for sol in sel:
        gent = _coerce_gent_payload(results[sol]["GENT"])
        df = gent.get("losses", None)
        if df is not None and _looks_like_polars_df(df) and not df.is_empty() and "Nombre_PLEXOS" in df.columns:
            try:
                all_lines |= set(df.get_column("Nombre_PLEXOS").unique().to_list())
            except Exception:
                pass
    all_lines = sorted(all_lines)
    defaults = (all_lines[:5] if not all_lines else all_lines[:5])
    lineas_sel = list(lineas_sel or defaults)

    fig_lines = go.Figure()
    any_line = False
    xmin2, xmax2 = None, None
    line_colors = [
        "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
        "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"
    ]
    dashes2 = ["solid", "dash", "dot", "dashdot", "longdash"]

    for li_idx, linea in enumerate(lineas_sel):
        color = line_colors[li_idx % len(line_colors)]
        for so_idx, sol in enumerate(sel):
            gent = _coerce_gent_payload(results[sol]["GENT"])
            x, y = _losses_line_xy(gent, linea)
            if x is None or y is None or len(x) == 0:
                continue
            fig_lines.add_trace(go.Scatter(
                x=x, y=y, mode="lines",
                name=f"{linea} – {sol}",
                line=dict(color=color, width=1.8, dash=dashes2[so_idx % len(dashes2)]),
                legendgroup=linea,
                hovertemplate=f"Línea: {linea}<br>Solución: {sol}<br>Hora=%{{x}}<br>Pérdida=%{{y:.3f}} MWh<extra></extra>",
            ))
            any_line = True
            xmin2 = min(xmin2, min(x)) if xmin2 is not None else min(x)
            xmax2 = max(xmax2, max(x)) if xmax2 is not None else max(x)

    if any_line:
        fig_lines.update_layout(template="simple_white", height=420, legend_title="Línea – Solución")
        fig_lines.update_xaxes(title_text="Hora",
                               range=[xmin2, xmin2 + min(47, (xmax2 - xmin2))] if xmin2 is not None else None,
                               dtick=1, rangeslider=dict(visible=True))
        fig_lines.update_yaxes(title_text="Pérdida [MWh]")
        parts.append(_card("<h3 style='margin-top:0'>Pérdidas por línea – comparación</h3>" + _fig_html(fig_lines)))
    else:
        parts.append(_card(_p_info("No se encontraron datos de pérdidas por línea para la selección actual.")))

    return "\n".join(parts)

# ───────────────────────────────────────────────────────────────
# 5) Comparador de COTAS
# ───────────────────────────────────────────────────────────────

def render_comparador_cotas(
    results: dict,
    solutions: Sequence[str],
    rango: Optional[Tuple[int, int]] = None,
    pair: Optional[Tuple[str, str]] = None,
    modo: str = "diferencia",  # "diferencia" | "trayectorias"
    top_k: int = 10,
    ncols: int = 2,
    h1: Optional[int] = None,
    h2: Optional[int] = None,
    filtro_nombres: Optional[Sequence[str]] = None,
) -> str:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PASTEL_GREEN_CELL = "#c8e6c9"
    PASTEL_RED_CELL   = "#ffcdd2"
    PASTEL_GREEN_BAR  = "#a5d6a7"
    PASTEL_RED_BAR    = "#ef9a9a"
    NEUTRAL_WHITE     = "#ffffff"
    BORDER_COLOR      = "#777"

    def to_pd(df_like):
        if hasattr(df_like, "to_pandas"):
            return df_like.to_pandas()
        return pd.DataFrame(df_like)

    def infer_name_and_hours(df) -> tuple[str, List[str]]:
        cols = list(df.columns)
        hours = sorted([c for c in cols if isinstance(c, str) and c.isdigit()], key=lambda x: int(x))
        if "Nombre" in cols:
            name = "Nombre"
        elif "Nombre_PLEXOS" in cols:
            name = "Nombre_PLEXOS"
        else:
            non_hours = [c for c in cols if c not in hours]
            name = non_hours[0] if non_hours else cols[0]
        return name, hours

    parts = [_h2("Cotas embalses")]

    sols = [s for s in solutions if "COTAS" in results.get(s, {})]
    if len(sols) < 2:
        return "\n".join([_h2("Cotas embalses"), _card(_p_info("Se necesitan al menos 2 soluciones con COTAS para comparar."))])

    if pair is None:
        pair = (sols[0], sols[1])
    solA, solB = pair
    labelA, labelB = solA, solB
    deltaA_col  = f"Δ {labelA}"
    deltaB_col  = f"Δ {labelB}"
    deltaBA_col = f"Δ({labelB} − {labelA})"

    dfA = to_pd(results[solA]["COTAS"])
    dfB = to_pd(results[solB]["COTAS"])
    nameA, hoursA = infer_name_and_hours(dfA)
    nameB, hoursB = infer_name_and_hours(dfB)
    hours = [h for h in hoursA if h in set(hoursB)]
    if not hours:
        return "\n".join([_h2("Cotas embalses"), _card(_p_warn("Las tablas COTAS no comparten columnas de horas en común."))])

    if filtro_nombres:
        keep = [str(s).strip() for s in filtro_nombres]
        dfA = dfA[dfA[nameA].astype(str).isin(keep)]
        dfB = dfB[dfB[nameB].astype(str).isin(keep)]

    def prep(df, name_col, hours_cols):
        out = df[[name_col] + hours_cols].copy()
        out.rename(columns={name_col: "Nombre"}, inplace=True)
        for h in hours_cols:
            out[h] = pd.to_numeric(out[h], errors="coerce")
        return out

    A = prep(dfA, nameA, hours)
    B = prep(dfB, nameB, hours)
    joined = pd.merge(B, A, on="Nombre", suffixes=("", "_A"), how="inner")
    if joined.empty:
        return "\n".join([_h2("Cotas embalses"), _card(_p_info("No hay filas en común entre las soluciones elegidas."))])

    hours_int = [int(h) for h in hours]
    hmin, hmax = min(hours_int), max(hours_int)
    r1, r2 = (hmin, min(hmin+23, hmax)) if rango is None else rango
    hrs_sel = [str(h) for h in hours_int if r1 <= h <= r2]
    highlight_col = "24" if "24" in hrs_sel else hrs_sel[-1]

    # 3) Diferencias (B-A) tabla coloreada
    diff_cols = {h: joined[h] - joined[f"{h}_A"] for h in hrs_sel}
    diff_pd   = pd.concat([joined[["Nombre"]], pd.DataFrame(diff_cols)], axis=1)

    def row_style(row):
        styles = []
        for c in diff_pd.columns:
            if c == "Nombre":
                styles.append("")
                continue
            try:
                v = float(row[c])
            except Exception:
                v = np.nan
            if pd.isna(v):
                s = ""
            elif v > 0:
                s = f"background-color:{PASTEL_GREEN_CELL};"
            elif v < 0:
                s = f"background-color:{PASTEL_RED_CELL};"
            else:
                s = f"background-color:{NEUTRAL_WHITE};"
            if c == highlight_col:
                s += f"border:2px solid {BORDER_COLOR}; font-weight:600;"
            styles.append(s)
        return styles

    styled = (diff_pd.style
              .format(precision=2, na_rep="")
              .apply(row_style, axis=1)
              .set_table_attributes('class="styled-table"'))

    css = """
    <style>
    .scroll-wrap { max-width: 100%; overflow-x: auto; border: 1px solid #ddd; border-radius: 6px; }
    .styled-table { border-collapse: collapse; width: max-content;
                    font-family: 'Segoe UI', sans-serif; font-size: 13px; }
    .styled-table th, .styled-table td {
        padding: 4px 8px; text-align: center; white-space: nowrap; border-bottom: 1px solid #eee;
    }
    .styled-table thead th { position: sticky; top: 0; background: #fafafa; z-index: 2; }
    .styled-table th:first-child, .styled-table td:first-child {
        position: sticky; left: 0; background: #fff; z-index: 3; text-align: left; min-width: 220px;
    }
    </style>
    """
    def _hide_index_safe(styler):
        try: return styler.hide(axis="index")
        except Exception:
            try: return styler.hide_index()
            except Exception: return styler

    styled = _hide_index_safe(styled)
    html_table = css + f'<div class="scroll-wrap">{styled.to_html()}</div>'

    # 4) Δ internos (h2 − h1) + barras
    h1 = h1 if (h1 is not None and str(h1) in hrs_sel) else (1 if "1" in hrs_sel else int(hrs_sel[0]))
    h2 = h2 if (h2 is not None and str(h2) in hrs_sel) else (24 if "24" in hrs_sel else int(hrs_sel[-1]))
    h1_sel, h2_sel = str(h1), str(h2)

    A_two = (A[["Nombre", h1_sel, h2_sel]]
            .rename(columns={h1_sel: f"{labelA}[h{h1_sel}]", h2_sel: f"{labelA}[h{h2_sel}]"}))
    B_two = (B[["Nombre", h1_sel, h2_sel]]
            .rename(columns={h1_sel: f"{labelB}[h{h1_sel}]", h2_sel: f"{labelB}[h{h2_sel}]"}))
    AB = pd.merge(A_two, B_two, on="Nombre", how="inner")
    AB[deltaA_col]   = AB[f"{labelA}[h{h2_sel}]"] - AB[f"{labelA}[h{h1_sel}]"]
    AB[deltaB_col]   = AB[f"{labelB}[h{h2_sel}]"] - AB[f"{labelB}[h{h1_sel}]"]
    AB[deltaBA_col]  = AB[deltaB_col] - AB[deltaA_col]
    AB = AB.sort_values(deltaBA_col, ascending=True).reset_index(drop=True)  # ascendente por defecto

    # tabla Δ internos (solo columnas Δ visibles por defecto)
    def color_delta(v):
        try:
            v = float(v)
            return f"background-color:{PASTEL_GREEN_CELL};" if v > 0 \
                else (f"background-color:{PASTEL_RED_CELL};" if v < 0 else "")
        except Exception:
            return ""

    cols_view = [
        "Nombre",
        f"{labelA}[h{h1_sel}]", f"{labelA}[h{h2_sel}]", deltaA_col,
        f"{labelB}[h{h1_sel}]", f"{labelB}[h{h2_sel}]", deltaB_col
    ]
    AB_view = AB[cols_view].round(2)
    styled_ab = (AB_view.style
                 .map(color_delta, subset=pd.IndexSlice[:, [deltaA_col, deltaB_col]])
                 .format(precision=2, na_rep="")
                 .set_table_attributes('class="styled-table"'))
    styled_ab = _hide_index_safe(styled_ab)
    html_ab = css + f'<div class="scroll-wrap">{styled_ab.to_html()}</div>'

    # barras de Δ(B−A)
    fig = go.Figure()
    plot_df = AB.copy()
    bar_colors = [PASTEL_GREEN_BAR if v >= 0 else PASTEL_RED_BAR for v in plot_df[deltaBA_col].tolist()]
    fig.add_trace(go.Bar(
        x=plot_df[deltaBA_col], y=plot_df["Nombre"], orientation="h",
        marker=dict(color=bar_colors), hovertemplate=f"Nombre=%{{y}}<br>{deltaBA_col}=%{{x:.2f}}<extra></extra>",
        showlegend=False,
    ))
    fig.update_yaxes(categoryorder="array", categoryarray=plot_df["Nombre"].tolist(),
                     autorange="reversed", title_text="Nombre")
    fig.update_layout(
        title=f"{deltaBA_col} en variación diaria (h{h2_sel} − h{h1_sel})",
        xaxis_title=deltaBA_col, template="simple_white",
        height=max(320, 18*len(plot_df)+80), margin=dict(l=10, r=20, t=60, b=10),
    )
    fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=len(plot_df)-0.5, line=dict(width=1, color="#888"))

    # 5) Panel compacto por embalse
    # top por |diff| dentro del rango
    if len(diff_pd) > 0:
        diff_abs_max = diff_pd.set_index("Nombre")[hrs_sel].abs().max(axis=1)
        top_names = diff_abs_max.sort_values(ascending=False).head(int(top_k)).index.tolist()

        A_long = A[A["Nombre"].isin(top_names)].melt(id_vars="Nombre", value_vars=hrs_sel,
                                                     var_name="Hora", value_name="A")
        B_long = B[B["Nombre"].isin(top_names)].melt(id_vars="Nombre", value_vars=hrs_sel,
                                                     var_name="Hora", value_name="B")
        AB_long = pd.merge(A_long, B_long, on=["Nombre", "Hora"], how="inner")
        AB_long["Hora_i"] = AB_long["Hora"].astype(int)
        AB_long["Diff"] = AB_long["B"] - AB_long["A"]

        from plotly.subplots import make_subplots
        nitems = len(top_names)
        ncols = int(max(1, min(4, ncols)))
        nrows = math.ceil(nitems / ncols)
        fig_sm = make_subplots(rows=nrows, cols=ncols, subplot_titles=top_names,
                               shared_xaxes=True, vertical_spacing=0.10, horizontal_spacing=0.06)

        for idx, name in enumerate(top_names, start=1):
            r = (idx-1)//ncols + 1
            c = (idx-1)%ncols + 1
            df_i = AB_long[AB_long["Nombre"] == name].sort_values("Hora_i")
            if modo == "trayectorias":
                fig_sm.add_trace(go.Scatter(
                    x=df_i["Hora_i"], y=df_i["A"], mode="lines", line=dict(width=1),
                    name=labelA, showlegend=False,
                    hovertemplate=f"h=%{{x}}<br>{labelA}=%{{y:.2f}}<extra></extra>"
                ), row=r, col=c)
                fig_sm.add_trace(go.Scatter(
                    x=df_i["Hora_i"], y=df_i["B"], mode="lines", line=dict(width=1),
                    name=labelB, showlegend=False,
                    hovertemplate=f"h=%{{x}}<br>{labelB}=%{{y:.2f}}<extra></extra>"
                ), row=r, col=c)
            else:
                fig_sm.add_trace(go.Bar(
                    x=df_i["Hora_i"], y=df_i["Diff"],
                    marker=dict(color=[PASTEL_GREEN_BAR if v >= 0 else PASTEL_RED_BAR for v in df_i["Diff"]]),
                    name=f"{labelB}−{labelA}", showlegend=False,
                    hovertemplate=f"h=%{{x}}<br>{labelB}−{labelA}=%{{y:.2f}}<extra></extra>"
                ), row=r, col=c)

            if "24" in hrs_sel:
                fig_sm.add_vline(x=24, line_width=1.5, line_dash="dash", line_color="#666", row=r, col=c)

            fig_sm.update_xaxes(title_text="h", row=r, col=c, tickmode="array",
                                tickvals=[r1, (r1+r2)//2, r2], ticks="outside")
            fig_sm.update_yaxes(title_text=("Dif" if modo=="diferencia" else "Cota"),
                                row=r, col=c, ticks="outside")

        fig_sm.update_layout(template="simple_white", height=max(360, 260*nrows),
                             margin=dict(l=10, r=10, t=40, b=10),
                             title=(f"Diferencia {labelB}−{labelA}" if modo=='diferencia' else f"{labelA} vs {labelB}"))
        panel_compacto_html = _fig_html(fig_sm)
    else:
        panel_compacto_html = _p_info("No hay datos para el panel compacto.")

    parts.append(_card("<h3 style='margin-top:0'>Diferencia de COTAS — {b} − {a}</h3>".format(a=labelA, b=labelB) + html_table))
    parts.append(_card("<h3 style='margin-top:0'>Δ internos (h₂ − h₁)</h3>" + html_ab))
    parts.append(_card(_fig_html(fig)))
    parts.append(_card("<h3 style='margin-top:0'>Panel compacto por embalse</h3>" + panel_compacto_html))
    return "\n".join(parts)
