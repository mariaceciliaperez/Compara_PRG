
# -*- coding: utf-8 -*-
"""graficos.py"""
from __future__ import annotations

import polars as pl
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from compara_prg.utils.funciones import normalize_hours, prepara_datos, coerce_schema
import re, json
# al inicio del archivo:
from compara_prg.config import COMMENTS_DIR

def persistent_multiselect(label, options, key):
    import streamlit as st
    from streamlit import components

    # Multiselect nativo (sin etiqueta)
    seleccion = st.multiselect(
        label, options,
        key=key,
        label_visibility="collapsed"
    )

    # Guardar/restaurar el término buscado + COLAPSAR el iframe
    query_key = f"_query_{key}"
    script = f"""
    <script>
    (function(){{
        // restaurar/guardar lo tecleado en el buscador del último multiselect
        const root  = window.parent.document;
        const inputs = root.querySelectorAll("div[data-testid='stMultiSelect'] input[type='text']");
        const box = inputs[inputs.length - 1];
        if (box) {{
            const K = "{query_key}";
            const prev = window.parent.sessionStorage.getItem(K) || "";
            if (prev && !box.value) box.value = prev;
            box.addEventListener("keyup", e => {{
                window.parent.sessionStorage.setItem(K, e.target.value || "");
            }});
        }}
        // colapsar ESTE iframe para que no deje espacio
        const f = window.frameElement;
        if (f) {{
            f.style.height    = "0px";
            f.style.minHeight = "0";
            f.style.border    = "0";
            f.style.margin    = "0";
            f.style.padding   = "0";
            f.style.display   = "block";
            // quitar márgenes del contenedor padre del iframe
            const p = f.parentElement;
            if (p) {{
                p.style.margin  = "0";
                p.style.padding = "0";
            }}
        }}
    }})();
    </script>
    """

    # Usa components.html (este sí acepta height)
    components.v1.html(script, height=0)

    # CSS compacto adicional
    st.markdown("""
    <style>
      div[data-testid="stMultiSelect"]{ margin-bottom:0.25rem; }
      div[data-testid="stCaptionContainer"]{ margin-top:0.25rem; margin-bottom:0; }
      div.stPlotlyChart{ margin-top:0 !important; margin-bottom:0.25rem !important; }
    </style>
    """, unsafe_allow_html=True)

    return seleccion


# ───────────────────────────────────────────────────────────────
#  Ejemplo de uso dentro de tu gráfico por categoría
# ───────────────────────────────────────────────────────────────
def mostrar_totales_por_categoria(results, SOLUTIONS, HOURS_FULL,
                                  HOURS_INT, MIN_H, MAX_H,
                                  CATEGORY_LABELS, COLOR):

    for cat_idx, category in enumerate(CATEGORY_LABELS):
        # 1) Soluciones con la GENTABLE de la categoría
        sols = [
            s for s in SOLUTIONS
            if "GENTABLES" in results.get(s, {})
            and cat_idx < len(results[s]["GENTABLES"])
        ]
        if not sols:
            st.info("Sin datos disponibles.")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            continue

        # Universo de centrales (normaliza/valida)
        centrales_sets = []
        for s in sols:
            df_cat = normalize_hours(results[s]["GENTABLES"][cat_idx], HOURS_FULL)
            df_cat = coerce_schema(df_cat, HOURS_FULL)
            if df_cat is None or df_cat.is_empty() or "Nombre_PLEXOS" not in df_cat.columns:
                continue
            centrales_sets.append(set(df_cat["Nombre_PLEXOS"].to_list()))

        if not centrales_sets:
            st.info("No hay columnas esperadas en las tablas (falta 'Nombre_PLEXOS').")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            continue

        centrales = sorted(set().union(*centrales_sets))

        # -------------- Filtro sin que se cierre (checkboxes) --------------
        opciones = centrales  # tu lista completa
        seleccion = persistent_multiselect(
            f"Filtrar centrales ({category})",
            opciones,
            key=f"ms_{cat_idx}"
        )

        # caption compacto (sin “undefined”)
        if 0 < len(seleccion) <= 20:
            st.caption(f"🔍 {len(seleccion)}/{len(opciones)} seleccionadas — " + ", ".join(seleccion))
        else:
            st.caption(f"🔍 {len(seleccion)}/{len(opciones)} seleccionadas")





        # -------------- Gráfico --------------
        fig = go.Figure()
        for i, sol in enumerate(sols):
            df = normalize_hours(results[sol]["GENTABLES"][cat_idx], HOURS_FULL)
            df = coerce_schema(df, HOURS_FULL)
            if df is None or df.is_empty() or "Nombre_PLEXOS" not in df.columns:
                continue
            if seleccion:
                df = df.filter(pl.col("Nombre_PLEXOS").is_in(seleccion))
            if df.is_empty():
                continue

            y = df.select(HOURS_FULL).sum().to_numpy().ravel()
            fig.add_trace(
                go.Scatter(
                    x=HOURS_INT, y=y,
                    mode="lines+markers",
                    name=sol,
                    line=dict(color=COLOR[i % len(COLOR)], width=2),
                    marker=dict(size=4)
                )
            )



        fig.update_layout(
            # título centrado FUERA del área del trazo
            title=dict(text=f"<b>{category}</b>", x=0.5, xanchor="center"),
            title_font=dict(size=16),
            xaxis=dict(
                title="Hora", range=[MIN_H, MIN_H + 47], dtick=1,
                rangeslider=dict(visible=True)
            ),
            yaxis_title="MWh",
            legend_title="Solución",
            template="simple_white",
            margin=dict(l=40, r=10, t=60, b=20),  # ↑ deja espacio arriba para el título
            height=360
        )



        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)






def mostrar_cmg_nodo(
    results: dict,
    solutions: list,
    hours_full: list[str],
    hours_int: list[int],
    min_h: int,
    max_h: int,
    color_palette: list[str]
) -> None:

    st.subheader("Comparación CMG por nodo")

    available_solutions = [s for s in solutions if "CMG" in results.get(s, {})]
    if not available_solutions:
        st.warning("El archivo no contiene CMG para ninguna solución.")
        st.stop()

    # --- NUEVO: normalizar el CMG base para listar nodos
    cmg0 = coerce_schema(results[available_solutions[0]]["CMG"], hours_full)
    if cmg0 is None or cmg0.is_empty():
        st.warning("CMG vacío.")
        st.stop()

    name_col = "Nombre_PLEXOS"
    if name_col not in cmg0.columns:
        # Último recurso: usa la primera columna como nombre
        name_col = cmg0.columns[0]

    node_list = cmg0.get_column(name_col).to_list()
    nodes_sorted = sorted(node_list)

    default_node = "Quillota220"
    default_index = nodes_sorted.index(default_node) if default_node in nodes_sorted else 0

    node = st.selectbox("Nodo", nodes_sorted, index=default_index, key="node")

    # Gráfico
    fig = go.Figure()
    for i, sol in enumerate(available_solutions):
        df = normalize_hours(results[sol]["CMG"], hours_full)
        df = coerce_schema(df, hours_full)
        if df is None or df.is_empty():
            continue
        col_nom = "Nombre_PLEXOS" if "Nombre_PLEXOS" in df.columns else df.columns[0]
        df_row = df.filter(pl.col(col_nom) == node)
        if df_row.is_empty():
            continue
        y = df_row.select(hours_full).to_numpy().ravel()
        fig.add_trace(
            go.Scatter(
                x=hours_int,
                y=y,
                mode="lines+markers",
                name=sol,
                line=dict(color=color_palette[i % len(color_palette)], width=2),
            )
        )

    if not fig.data:
        st.info(f"No se encontró el nodo '{node}' en las soluciones elegidas.")
        return

    fig.update_layout(
        title=f"CMG — {node}",
        xaxis=dict(title="Hora", range=[min_h, min_h+47],
                   dtick=1, rangeslider=dict(visible=True)),
        yaxis_title="USD/MWh",
        legend_title="Solución",
        template="simple_white",
    )
    st.plotly_chart(fig, use_container_width=True)




def mostrar_analisis_termicas(
    results,
    SOLUTIONS,
    HOURS_FULL,
    THRESHOLD,
    THERMAL_IDX
):
    """
    Compara 2 soluciones, permite elegir rango horario libre (1..168),
    muestra tabla de diferencias coloreada (con scroll horizontal, header y
    1a columna pegados) y un resumen ordenable.
    También gestiona el comentario persistente en ./Comentarios/.
    """

    # -----------------------------
    # 1) Controles de UI (pares + rango)
    # -----------------------------
    sols = [s for s in SOLUTIONS if "GENTABLES" in results.get(s, {})]
    if len(sols) < 2:
        st.info("Se necesitan al menos 2 soluciones con GENTABLES para comparar.")
        return

    pair_options = [(a, b) for a in sols for b in sols if a != b]
    pair_labels  = [f"{b} – {a}" for a, b in pair_options]
    sel_label    = st.selectbox("Comparación de soluciones", pair_labels, index=0)
    sol1, sol2   = pair_options[pair_labels.index(sel_label)]

    st.subheader("")
    col_a, col_b = st.columns([2, 1])

    with col_a:
        h1, h2 = st.slider(
            "Rango horario a mostrar",
            min_value=1, max_value=168, value=(1, 24), step=1,
            key="termicas_rango"
        )

    with col_b:
        preset = st.selectbox(
            "Atajos",
            ["—", "1–24", "25–48", "49–72", "73–96", "97–120", "121–144", "145–168"],
            index=0
        )
        if preset != "—":
            a, b = preset.split("–")
            h1, h2 = int(a), int(b)

    if h1 > h2:
        h1, h2 = h2, h1

    # Mapeo seguro int->str según HOURS_FULL
    int2str = {int(h): h for h in HOURS_FULL if str(h).isdigit()}
    hours_range = [int2str[h] for h in range(h1, h2 + 1) if h in int2str]
    if not hours_range:
        st.warning("El rango seleccionado no existe en los datos cargados.")
        st.stop()

    # -----------------------------
    # 2) Datos + comentario
    # -----------------------------
    pivot_pd, resumen_pd, styles_pd = prepara_datos(
        _results=results,
        sol_a=sol1,
        sol_b=sol2,
        thermal_idx=THERMAL_IDX,
        hours_full=HOURS_FULL,
        hours=hours_range,
        th=THRESHOLD,
    )

    nombre_resultado = Path(st.session_state.get("DATA_PATH", "default")).stem
    comentario_path  = COMMENTS_DIR / f"comentario_termicas__{nombre_resultado}.txt"

    st.subheader("¿Deseas incluir un comentario?")
    if "edit_comentario" not in st.session_state:
        st.session_state["edit_comentario"] = False

    comentario_inicial = comentario_path.read_text(encoding="utf-8").strip() if comentario_path.exists() else ""

    if comentario_inicial and not st.session_state["edit_comentario"]:
        st.markdown("### Comentario actual:")
        st.markdown(
            f"""
            <div style='background-color:#eaf4fc; padding: 12px 16px; border-radius: 8px; font-size: 0.92rem; white-space: pre-line;'>
            {comentario_inicial}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("✏️ Editar comentario"):
            st.session_state["edit_comentario"] = True
    else:
        with st.form("form_comentario_termicas"):
            comentario = st.text_area(
                "Comentario (análisis de térmicas)",
                value=comentario_inicial,
                height=150,
            )
            if st.form_submit_button("Guardar comentario"):
                comentario_path.write_text(comentario.strip(), encoding="utf-8")
                st.session_state["edit_comentario"] = False
                st.success("Comentario guardado correctamente ✅")
                st.rerun()

    if pivot_pd is None:
        st.info("No se detectaron cambios significativos.")
        st.stop()

    # -----------------------------
    # 3) Tabla coloreada + scroll (una sola barra)
    # -----------------------------
    st.subheader("Diferencias hora-a-hora – tabla coloreada")

    styled = (
        pivot_pd.style
        .set_properties(**{"text-align": "center"})
        .apply(lambda _: styles_pd, axis=None)
        .format(precision=0, na_rep="")
    )

    # Altura y ancho mínimo para forzar overflow-x
    height_px            = 80 + 28 * len(pivot_pd)      # ≈28 px por fila
    tabla_min_width_px   = 220 + 28 * len(hours_range)  # 220 1ª col + 28 por hora
    extra_scrollbar_space = 24



    css_iframe = f"""
    <style>
    html, body {{ margin:0; overflow:hidden; }}   /* sin barra del iframe */
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
      min-width: {tabla_min_width_px}px;  /* asegura desborde horizontal */
      table-layout: fixed;
      border-collapse: collapse;
      font-family: 'Segoe UI', sans-serif;
      font-size: 10px;
    }}
    .styled-table, .styled-table * {{ box-sizing: border-box; }}
    .styled-table th, .styled-table td {{
      padding: 2px 3px; text-align: center; white-space: nowrap;
    }}
    /* Header pegado arriba */
    .styled-table th {{ position: sticky; top: 0; z-index: 5; background: #f4f4f4; }}
    /* Primera columna pegada + esquina superior izquierda */
    .styled-table th:first-child, .styled-table td:first-child {{ width: 220px; text-align: left; }}
    .styled-table td:first-child {{
      position: sticky; left: 0; z-index: 4;
      background: #fff0f0;   /* color destacado */
    }}
    .styled-table th:first-child {{
      position: sticky; top: 0; left: 0; z-index: 6;
      background: #ffe0e0;   /* color header fijo */
      box-shadow: 1px 0 0 #ddd;
    }}
    /* Columnas de horas */
    .styled-table th:not(:first-child), .styled-table td:not(:first-child) {{ width: 28px; }}
    .styled-table thead th:not(:first-child) {{
      writing-mode: vertical-rl; transform: rotate(180deg);
      white-space: nowrap; height: 90px; padding: 6px 0;
    }}
    /* Zebra/hover opcionales */
    .styled-table tbody tr:nth-child(even) td {{ background: #fafafa; }}
    .styled-table tbody tr:nth-child(even) td:first-child {{ background: #f0e0e0; }}
    .styled-table tbody tr:hover td {{ background: #f9fbff; }}
    .styled-table tbody tr:hover td:first-child {{ background: #ffdede; }}
    .styled-table td {{ letter-spacing: 0.2px; }}
    </style>
    """


    iframe_html = f"""
    {css_iframe}
    <div class="resp-wrap">
      {styled.to_html(classes="styled-table")}
    </div>
    """

    components.html(
        iframe_html,
        height=height_px + extra_scrollbar_space,
        scrolling=False,  # solo scroll del div; el iframe no agrega otro
    )

    # -----------------------------
    # 4) Resumen ordenable
    # -----------------------------
    st.subheader("Resumen del día – ordenado por diferencia")

    diff_col = next(c for c in resumen_pd.columns if c.startswith("Δ Total"))

    c1, c2 = st.columns([2, 1])
    with c1:
        orden_sel = st.radio(
            "Ordenar por:",
            ("Mayor |Δ|", "Mayor Δ", "Menor Δ"),
            horizontal=True,
            index=0,
            key="orden_resumen_dia",
        )
    with c2:
        top_n = st.number_input(
            "Top N",
            min_value=5,
            max_value=max(5, len(resumen_pd)),
            value=min(50, len(resumen_pd)),
            step=5,
        )

    df_show = resumen_pd.copy()
    if orden_sel == "Mayor |Δ|":
        df_show = df_show.reindex(df_show[diff_col].abs().sort_values(ascending=False).index)
    elif orden_sel == "Mayor Δ":
        df_show = df_show.sort_values(diff_col, ascending=False)
    else:
        df_show = df_show.sort_values(diff_col, ascending=True)

    st.dataframe(df_show.head(top_n), use_container_width=True)







def mostrar_totales_sistema(
    results: dict,
    solutions: list[str],
    hours_full: list[str],   # no dependemos de esto estrictamente
    hours_int: list[int],
    color_palette: list[str]
) -> None:
    import plotly.graph_objects as go

    VARS = [
        "Generación Total [MWh]",
        "Consumos Propios [MWh]",
        "Pérdidas [MWh]",
        "Demanda Total [MWh]",
    ]
    DEFAULT_VARS = ["Consumos Propios [MWh]", "Pérdidas [MWh]"]

    # Colores fijos por VARIABLE (mismo color entre soluciones)
    var_color = {
        "Generación Total [MWh]": "#009E73",
        "Consumos Propios [MWh]": "#0072B2",
        "Pérdidas [MWh]": "#D55E00",
        "Demanda Total [MWh]": "#CC79A7",
    }

    # ---- Soluciones con GENT válido
    sols_ok = []
    for s in solutions:
        gent_raw = results.get(s, {}).get("GENT", None)
        gent = _coerce_gent_payload(gent_raw)
        if gent and _looks_like_polars_df(gent.get("tabla")):
            sols_ok.append(s)
    if not sols_ok:
        st.info("No hay resultados GENT en el archivo cargado.")
        return

    # ---- Selectores
    sel = st.multiselect("Soluciones", sols_ok, default=sols_ok, key="gent_solutions")
    if not sel:
        st.warning("Selecciona al menos una solución.")
        return

    vars_sel = st.multiselect("Series a mostrar", VARS, default=DEFAULT_VARS, key="gent_vars")
    # fuerza que solo estén las dos deseadas si estaban elegidas otras
    vars_sel = [v for v in vars_sel if v in DEFAULT_VARS] or DEFAULT_VARS

    dashes = ["solid", "dash", "dot", "dashdot", "longdash"]
    dash_for = lambda idx: dashes[idx % len(dashes)]

    # =========================
    # 1) Evolución horaria (líneas)
    # =========================
    st.subheader("Consumos y Pérdidas – Evolución horaria")
    fig = go.Figure()
    any_trace = False
    xmin, xmax = None, None

    for i, sol in enumerate(sel):
        gent = _coerce_gent_payload(results[sol]["GENT"])
        df_tabla = gent["tabla"]

        for var in vars_sel:
            x, y = _row_xy(df_tabla, var)
            if x is None or y is None or len(x) == 0:
                continue
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=f"{sol} – {var}",
                    line=dict(
                        color=var_color.get(var, color_palette[i % len(color_palette)]),
                        width=2,
                        dash=dash_for(i),
                    ),
                    legendgroup=var,
                )
            )
            any_trace = True
            xmin = min(xmin, min(x)) if xmin is not None else min(x)
            xmax = max(xmax, max(x)) if xmax is not None else max(x)

    if not any_trace:
        st.info("No se pudieron construir series; revisa que existan horas en el DataFrame.")
        return

    fig.update_layout(
        xaxis=dict(
            title="Hora",
            range=[xmin, xmin + min(47, (xmax - xmin))],
            dtick=1,
            rangeslider=dict(visible=True)
        ),
        yaxis_title="MWh",
        legend_title="Serie",
        template="simple_white",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 2) Pérdidas por línea – comparación entre soluciones (NO agregadas)
    # =========================
    st.subheader("Pérdidas por línea – comparación entre soluciones")

    # Reúne el universo de líneas disponibles en las soluciones seleccionadas
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

    # Sugerencia de líneas por defecto: top-5 por pérdida total en la primera solución seleccionada
    default_lines = []
    if sel and all_lines:
        gent0 = _coerce_gent_payload(results[sel[0]]["GENT"])
        df0 = gent0.get("losses", None)
        if df0 is not None and _looks_like_polars_df(df0) and not df0.is_empty():
            try:
                default_lines = (
                    df0.group_by("Nombre_PLEXOS")
                    .agg(pl.col("Loss").sum().alias("Loss_total"))
                    .sort("Loss_total", descending=True)
                    .head(5)
                    .get_column("Nombre_PLEXOS")
                    .to_list()
                )
            except Exception:
                pass
    if not default_lines:
        default_lines = all_lines[:5]

    lineas_sel = st.multiselect("Líneas a mostrar", all_lines, default=default_lines, key="loss_lines")

    fig_lines = go.Figure()
    any_line = False
    xmin2, xmax2 = None, None

    # Paleta para líneas (color por línea; dash por solución)
    line_colors = [
        "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
        "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"
    ]
    dashes = ["solid", "dash", "dot", "dashdot", "longdash"]

    for li_idx, linea in enumerate(lineas_sel):
        color = line_colors[li_idx % len(line_colors)]
        for so_idx, sol in enumerate(sel):
            gent = _coerce_gent_payload(results[sol]["GENT"])
            x, y = _losses_line_xy(gent, linea)
            if x is None or y is None or len(x) == 0:
                continue

            fig_lines.add_trace(
                go.Scatter(
                    x=x, y=y, mode="lines",
                    name=f"{linea} – {sol}",
                    line=dict(color=color, width=1.8, dash=dashes[so_idx % len(dashes)]),
                    legendgroup=linea,
                    hovertemplate=(
                        f"Línea: {linea}<br>Solución: {sol}"
                        "<br>Hora=%{x}<br>Pérdida=%{y:.3f} MWh<extra></extra>"
                    ),
                )
            )
            any_line = True
            xmin2 = min(xmin2, min(x)) if xmin2 is not None else min(x)
            xmax2 = max(xmax2, max(x)) if xmax2 is not None else max(x)

    if any_line:
        fig_lines.update_layout(
            template="simple_white",
            height=420,
            legend_title="Línea – Solución",
        )
        fig_lines.update_xaxes(
            title_text="Hora",
            range=[xmin2, xmin2 + min(47, (xmax2 - xmin2))] if xmin2 is not None else None,
            dtick=1,
            rangeslider=dict(visible=True),
        )
        fig_lines.update_yaxes(title_text="Pérdida [MWh]")
        st.plotly_chart(fig_lines, use_container_width=True)
    else:
        st.info("No se encontraron datos de pérdidas por línea para la selección actual.")

def _losses_line_xy(gent: dict, line_name: str):
    """
    Serie de pérdidas por una línea específica desde gent['losses'].
    Retorna (x, y) con horas (int) y pérdidas (float) sin agregar con otras líneas.
    """
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




def _coerce_gent_payload(gent_obj):
    """
    Normaliza GENT a {'tabla': DF, 'losses': DF} si viene como:
      - dict {'tabla':..., 'losses':...}
      - tuple (tabla, losses)
    Retorna dict o None.
    """
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




# --- Helpers robustos para detectar esquema ---

def _hours_from_df(df: pl.DataFrame) -> list[str]:
    """
    Devuelve las columnas de horas como strings ordenadas (1..n).
    Acepta nombres "1","2",... (texto). Si tus horas vinieran como enteros
    en los nombres, conviértelas previamente al leer/normalizar.
    """
    hs = [c for c in df.columns if isinstance(c, str) and c.isdigit()]
    return sorted(hs, key=lambda x: int(x))


def _label_col(df: pl.DataFrame) -> str:
    """
    Intenta detectar la columna 'etiqueta' (donde viven nombres como
    'Generación Total [MWh]', 'Pérdidas [MWh]', etc.).
    Prefiere columnas de texto con nombres comunes; si no, toma la
    primera columna de tipo texto; como último recurso, la 1ª columna.
    """
    # 1) si hay alguna de estas y es texto, úsala
    preferidas = ["Variable", "Nombre", "Nombre_PLEXOS", "Serie", "Concepto", "Etiqueta", "Categoria", "Fila", "Descripción", "Hora"]
    schema = dict(zip(df.columns, df.dtypes))
    for col in preferidas:
        if col in df.columns and schema[col] == pl.Utf8:
            return col

    # 2) primera columna de tipo texto
    for c, t in schema.items():
        if t == pl.Utf8:
            return c

    # 3) fallback: la primera columna (aunque no sea texto)
    return df.columns[0]


def _row_xy(df_tabla: pl.DataFrame, var_name: str):
    """
    Devuelve (x, y) para la fila cuya etiqueta == var_name.
    Usa la columna detectada por _label_col y asegura comparación en texto.
    """
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

def _strip_expr(expr: pl.Expr) -> pl.Expr:
    # quita espacios al inicio y al final (compatible con versiones antiguas)
    return expr.cast(pl.Utf8).str.replace_all(r"^\s+|\s+$", "")


def mostrar_comparador_cotas(
    results: dict,
    solutions: list[str],
) -> None:
    """
    Comparador de tablas 'COTAS' por pares de soluciones.

    Muestra:
      1) Tabla de diferencias (SolB − SolA) con colores (verde=positivo, rojo=negativo), hora 24 destacada
      2) Δ internos por solución (h2 − h1): tabla coloreada + barras de Δ(SolB−SolA) | h1/h2 seleccionables (defecto 1 y 24)
      3) Trayectoria diaria comparada (todas las cotas) con hora 24 marcada
      4) Panel compacto por cota (pequeños múltiplos) – modo "trayectorias" o "diferencia", top-k (defecto 8)
    """
    import streamlit as st
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import math

    # ─────────────────────────────────────────────────────────────
    # Paleta pastel
    # ─────────────────────────────────────────────────────────────
    PASTEL_GREEN_CELL = "#c8e6c9"  # verde 100
    PASTEL_RED_CELL   = "#ffcdd2"  # rojo 100
    PASTEL_GREEN_BAR  = "#a5d6a7"  # verde 200
    PASTEL_RED_BAR    = "#ef9a9a"  # rojo 200
    NEUTRAL_WHITE     = "#ffffff"
    BORDER_COLOR      = "#777"

    # ─────────────────────────────────────────────────────────────
    # Utilidades
    # ─────────────────────────────────────────────────────────────
    def to_pd(df_like):
        if hasattr(df_like, "to_pandas"):
            return df_like.to_pandas()
        return pd.DataFrame(df_like)

    def infer_name_and_hours(df) -> tuple[str, list[str]]:
        cols = list(df.columns)
        hours = sorted([c for c in cols if isinstance(c, str) and c.isdigit()],
                       key=lambda x: int(x))
        if "Nombre" in cols:
            name = "Nombre"
        elif "Nombre_PLEXOS" in cols:
            name = "Nombre_PLEXOS"
        else:
            non_hours = [c for c in cols if c not in hours]
            name = non_hours[0] if non_hours else cols[0]
        return name, hours

    # ─────────────────────────────────────────────────────────────
    # 1) Selección de soluciones (solo COTAS)
    # ─────────────────────────────────────────────────────────────
    sols = [s for s in solutions if "COTAS" in results.get(s, {})]
    if len(sols) < 2:
        st.info("Se necesitan al menos 2 soluciones con COTAS para comparar.")
        return

    pair_options = [(a, b) for a in sols for b in sols if a != b]
    pair_labels  = [f"{b} – {a}" for a, b in pair_options]
    sel_pair     = st.selectbox("Comparación de soluciones (COTAS)", pair_labels, index=0, key="cotas_pair")
    solA, solB   = pair_options[pair_labels.index(sel_pair)]

    # Etiquetas dinámicas
    labelA = solA
    labelB = solB
    deltaA_col  = f"Δ {labelA}"
    deltaB_col  = f"Δ {labelB}"
    deltaBA_col = f"Δ({labelB} − {labelA})"

    dfA = to_pd(results[solA]["COTAS"])
    dfB = to_pd(results[solB]["COTAS"])

    # ─────────────────────────────────────────────────────────────
    # 2) Alinear esquema y filtrar
    # ─────────────────────────────────────────────────────────────
    nameA, hoursA = infer_name_and_hours(dfA)
    nameB, hoursB = infer_name_and_hours(dfB)
    hours = [h for h in hoursA if h in set(hoursB)]
    if not hours:
        st.warning("Las tablas COTAS no comparten columnas de horas en común.")
        return

    names_union = pd.Series(
        pd.concat([dfA[nameA].astype(str), dfB[nameB].astype(str)], ignore_index=True)
    ).dropna().unique()
    seleccion = st.multiselect("Filtrar por nombre (opcional)", sorted(map(str, names_union)))
    if seleccion:
        keep = [s.strip() for s in seleccion]
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
        st.info("No hay filas en común entre las soluciones elegidas.")
        return

    # Rango horario (para tablas/gráficos)
    hours_int = [int(h) for h in hours]
    hmin, hmax = min(hours_int), max(hours_int)
    r1, r2 = st.slider("Rango horario", min_value=hmin, max_value=hmax,
                       value=(hmin, min(hmin+23, hmax)), step=1, key="cotas_range")
    hrs_sel = [str(h) for h in hours_int if r1 <= h <= r2]
    highlight_col = "24" if "24" in hrs_sel else hrs_sel[-1]  # marcar 24 si existe

    # ─────────────────────────────────────────────────────────────
    # 3) Diferencias (SolB − SolA) con COLORES (pastel) + scroll
    # ─────────────────────────────────────────────────────────────
    diff_cols = {h: joined[h] - joined[f"{h}_A"] for h in hrs_sel}
    diff_pd   = pd.concat([joined[["Nombre"]], pd.DataFrame(diff_cols)], axis=1)

    st.subheader(f"Diferencia de COTAS — {labelB} − {labelA}")
    st.caption("Verde = diferencia positiva; Rojo = diferencia negativa. Hora 24 destacada. (Desliza horizontalmente ↔)")

    def row_style(row):
        styles = []
        for c in diff_pd.columns:
            if c == "Nombre":
                styles.append("")  # sin fondo
                continue
            v = row[c]
            try:
                v = float(v)
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

    # CSS con scroll + 1ª columna sticky + fuente más grande
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
        try:
            return styler.hide(axis="index")
        except Exception:
            try:
                return styler.hide_index()
            except Exception:
                return styler

    styled = _hide_index_safe(styled)
    html_table = css + f'<div class="scroll-wrap">{styled.to_html()}</div>'
    height = 120 + 22 * max(1, len(diff_pd))
    st.components.v1.html(html_table, height=min(800, height), scrolling=False)

    # ─────────────────────────────────────────────────────────────
    # 4) Δ internos (h2 − h1) — INICIAL/FINAL + barras (pastel)
    #     Orden por Δ({solB} − {solA})
    # ─────────────────────────────────────────────────────────────
    st.subheader("Δ internos del día (h₂ − h₁)")

    horas_disp = hrs_sel
    h1_default = "1"  if "1"  in horas_disp else horas_disp[0]
    h2_default = "24" if "24" in horas_disp else horas_disp[-1]

    csel1, csel2 = st.columns(2, gap="small")
    with csel1:
        h1_sel = st.selectbox("Hora inicial (h₁)", horas_disp, index=horas_disp.index(h1_default), key="h1_delta")
    with csel2:
        h2_sel = st.selectbox("Hora final (h₂)",   horas_disp, index=horas_disp.index(h2_default), key="h2_delta")

    # Valores inicial/final etiquetados con nombres de soluciones
    A_two = (A[["Nombre", h1_sel, h2_sel]]
            .rename(columns={h1_sel: f"{labelA}[h{h1_sel}]", h2_sel: f"{labelA}[h{h2_sel}]"}))
    B_two = (B[["Nombre", h1_sel, h2_sel]]
            .rename(columns={h1_sel: f"{labelB}[h{h1_sel}]", h2_sel: f"{labelB}[h{h2_sel}]"}))

    AB = pd.merge(A_two, B_two, on="Nombre", how="inner")
    AB[deltaA_col]   = AB[f"{labelA}[h{h2_sel}]"] - AB[f"{labelA}[h{h1_sel}]"]
    AB[deltaB_col]   = AB[f"{labelB}[h{h2_sel}]"] - AB[f"{labelB}[h{h1_sel}]"]
    AB[deltaBA_col]  = AB[deltaB_col] - AB[deltaA_col]

    # Ordenar por Δ({solB} − {solA})
    col_ord1, _ = st.columns([1, 3])
    with col_ord1:
        desc = st.toggle("Orden descendente (mayor Δ primero)", value=False, key="cotas_desc")
    AB = AB.sort_values(deltaBA_col, ascending=not desc).reset_index(drop=True)

    left, right = st.columns([2, 2], gap="medium")

    with left:
        # Colorear SOLO las columnas Δ
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
            # , deltaBA_col  # <- si quieres verla también en la tabla
        ]
        AB_view = AB[cols_view].round(2)

        styled_ab = (AB_view.style
                     .map(color_delta, subset=pd.IndexSlice[:, [deltaA_col, deltaB_col]])
                     .format(precision=2, na_rep="")
                     .set_table_attributes('class="styled-table"'))
        styled_ab = _hide_index_safe(styled_ab)

        html_ab = css + f'<div class="scroll-wrap">{styled_ab.to_html()}</div>'
        height_ab = 100 + 22 * max(1, len(AB_view))
        st.components.v1.html(html_ab, height=min(600, height_ab), scrolling=False)

    with right:
        # Mismo orden que la tabla
        plot_df = AB.copy()
        bar_colors = [PASTEL_GREEN_BAR if v >= 0 else PASTEL_RED_BAR
                      for v in plot_df[deltaBA_col].tolist()]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=plot_df[deltaBA_col],
            y=plot_df["Nombre"],
            orientation="h",
            marker=dict(color=bar_colors),
            hovertemplate=f"Nombre=%{{y}}<br>{deltaBA_col}=%{{x:.2f}}<extra></extra>",
            showlegend=False,
        ))
        fig.update_yaxes(
            categoryorder="array",
            categoryarray=plot_df["Nombre"].tolist(),
            autorange="reversed",
            title_text="Nombre"
        )
        fig.update_layout(
            title=f"{deltaBA_col} en variación diaria (h{h2_sel} − h{h1_sel})",
            xaxis_title=deltaBA_col,
            template="simple_white",
            height=max(320, 18*len(plot_df)+80),
            margin=dict(l=10, r=20, t=60, b=10),
        )
        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=len(plot_df)-0.5,
                      line=dict(width=1, color="#888"))
        st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────────────────────────────────
    # 5) Panel compacto por cota (pequeños múltiplos)
    # ─────────────────────────────────────────────────────────────
    st.subheader("Panel compacto por embalse")

    col_modo, col_k, col_cols = st.columns([1, 1, 1])
    with col_modo:
        modo = st.radio("Modo", options=["diferencia", "trayectorias"], index=0, horizontal=True, key="cotas_modo")
    with col_k:
        top_k = st.number_input("Top-k", min_value=2, max_value=24, value=10, step=1, key="cotas_topk")
    with col_cols:
        ncols = st.number_input("Columnas", min_value=1, max_value=4, value=2, step=1, key="cotas_ncols")

    if len(diff_pd) == 0:
        return
    diff_abs_max = diff_pd.set_index("Nombre")[hrs_sel].abs().max(axis=1)
    top_names = diff_abs_max.sort_values(ascending=False).head(int(top_k)).index.tolist()

    # Datos largos para A/B y diferencia
    A_long = A[A["Nombre"].isin(top_names)].melt(id_vars="Nombre", value_vars=hrs_sel,
                                                 var_name="Hora", value_name="A")
    B_long = B[B["Nombre"].isin(top_names)].melt(id_vars="Nombre", value_vars=hrs_sel,
                                                 var_name="Hora", value_name="B")
    AB_long = pd.merge(A_long, B_long, on=["Nombre", "Hora"], how="inner")
    AB_long["Hora_i"] = AB_long["Hora"].astype(int)
    AB_long["Diff"] = AB_long["B"] - AB_long["A"]

    # Subplots
    nitems = len(top_names)
    ncols = int(ncols)
    nrows = math.ceil(nitems / ncols)
    fig_sm = make_subplots(rows=nrows, cols=ncols, subplot_titles=top_names,
                           shared_xaxes=True, vertical_spacing=0.10, horizontal_spacing=0.06)

    # Para cada activo, graficar según modo
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
        else:  # diferencia
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
        fig_sm.update_yaxes(title_text=(f"{labelB}−{labelA}" if modo == "diferencia" else "Cota"),
                            row=r, col=c, ticks="outside")

    fig_sm.update_layout(
        template="simple_white",
        height=max(360, 260*nrows),
        margin=dict(l=10, r=10, t=40, b=10),
        title=(f"Diferencia {labelB}−{labelA}" if modo=='diferencia' else f"{labelA} vs {labelB}")
    )
    st.plotly_chart(fig_sm, use_container_width=True)


def fecha_caption(fecha_lbl):
    if fecha_lbl:
        return st.markdown(
            f"""
            <div style="font-size:24px; font-weight:600; margin:4px 0 12px;">
                📅 Fecha seleccionada: {fecha_lbl}
            </div>
            """,
            unsafe_allow_html=True
        )
