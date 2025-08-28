import pandas as pd
import polars as pl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st




def bat_perfil(results,SOLUTIONS ):

    # --- helpers ---
    def _get_bess_df(sol):
        df = results.get(sol, {}).get("BESS")
        if df is None:
            return None
        return df.to_pandas() if isinstance(df, pl.DataFrame) else df

    def _hour_cols(df):
        # columnas que son horas (números) en BESS
        return [c for c in df.columns if c != "Nombre_PLEXOS" and str(c).isdigit()]

    # Soluciones que traen BESS
    sols_with_bess = [s for s in SOLUTIONS if _get_bess_df(s) is not None]
    if not sols_with_bess:
        st.info("No hay datos de BESS en los resultados cargados.")
        st.stop()

    st.subheader("Perfil de BESS")

    # ====== FILTROS (en página) ======
    with st.container(border=True):
        st.markdown("**Filtros**")
        c1, c2 = st.columns([1, 1])

        with c1:
            # ─────────────────────────────────────────────────────────────
            # 1) Selección de soluciones (solo BESS)
            # ─────────────────────────────────────────────────────────────
            sols = [s for s in SOLUTIONS if "BESS" in results.get(s, {})]
            if len(sols) < 2:
                st.info("Se necesitan al menos 2 soluciones con BESS para comparar.")
                st.stop()

            # Generar pares de soluciones
            pair_options = [(a, b) for a in sols for b in sols if a != b]
            pair_labels  = [f"{a} – {b}" for a, b in pair_options]

            sel_pair   = st.selectbox("Comparación de soluciones (BESS)", pair_labels, index=0, key="bess_pair")
            solA, solB = pair_options[pair_labels.index(sel_pair)]

            # Etiquetas dinámicas
            labelA = solA
            labelB = solB


        # Baterías disponibles según soluciones elegidas
        all_bess = set()
        for sol in [solA, solB]:
            dfp = _get_bess_df(sol) 
            if dfp is not None and "Nombre_PLEXOS" in dfp.columns:
                all_bess |= set(dfp["Nombre_PLEXOS"].astype(str).unique().tolist())
        all_bess = sorted(all_bess)

        with c2:
            sel_bess = st.multiselect(
                "Baterías",
                options=all_bess,
                default=[],
                placeholder="(opcional) filtra baterías",
            )

        # rango de horas (default: primeras 48)
        hours_union = set()
        for sol in [solA, solB]:
            dfp = _get_bess_df(sol) 
            if dfp is not None:
                hours_union |= set(int(str(c)) for c in _hour_cols(dfp))
        if not hours_union:
            st.info("No se detectaron columnas de horas en BESS.")
            st.stop()

        hmin, hmax = min(hours_union), max(hours_union)
        default_end = min(hmin + 47, hmax)
        hr_ini, hr_fin = st.slider(
            "Rango de horas",
            min_value=hmin, max_value=hmax,
            value=(hmin, default_end),
            step=1,
        )

    if not [solA, solB]:
        st.info("Selecciona al menos una solución.")
        st.stop()

    # ---- Construir DF largo (BESS) ----
    long_list = []
    for s in [solA, solB]:
        dfp = _get_bess_df(s)
        if dfp is None:
            continue
        dfp = dfp.copy()
        dfp["Nombre_PLEXOS"] = dfp["Nombre_PLEXOS"].astype(str)
        hcols = _hour_cols(dfp)
        if not hcols:
            continue
        hkeep = [c for c in hcols if hr_ini <= int(str(c)) <= hr_fin]
        if not hkeep:
            continue
        sub = dfp[["Nombre_PLEXOS"] + hkeep]
        if sel_bess:
            sub = sub[sub["Nombre_PLEXOS"].isin(sel_bess)]
        if sub.empty:
            continue
        long = sub.melt(id_vars="Nombre_PLEXOS", var_name="Hora", value_name="Valor")
        long["Hora"] = long["Hora"].astype(int)
        long["Solución"] = s
        long_list.append(long)

    if not long_list:
        st.info("No hay datos de BESS que coincidan con los filtros actuales.")
        st.stop()

    long_df = pd.concat(long_list, ignore_index=True)

    # ============== GRÁFICO ==================
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bess_traces = 0
    cmg_traces = 0

    # --- PERFIL BESS (eje primario) ---
    for (bess_name, sol), g in long_df.groupby(["Nombre_PLEXOS", "Solución"]):
        g = g.sort_values("Hora")
        fig.add_trace(
            go.Scatter(
                x=g["Hora"], y=g["Valor"],
                mode="lines",
                name=f"{bess_name} ({sol})"
            ),
            secondary_y=False,
        )
        bess_traces += 1

    # --- CMG nodos BAT_* (eje secundario) ---
    for sol in [solA, solB]:
        cmg = results.get(sol, {}).get("CMG")
        if cmg is None:
            continue
        cmg = cmg.to_pandas() if isinstance(cmg, pl.DataFrame) else cmg
        if cmg is None or "Nombre_PLEXOS" not in cmg.columns:
            continue

        # Detectar forma: largo (Hora, Valor) o ancho (5..49)
        cols_set = set(map(str, cmg.columns))
        is_long = {"Hora", "Valor"}.issubset(cols_set)

        if is_long:
            # ---- LARGO: filtrar BAT_, rango de horas y trazar por nodo ----
            cmg_bat = cmg[cmg["Nombre_PLEXOS"].astype(str).str.upper().str.startswith("BAT_")]
            if cmg_bat.empty:
                continue
            cmg_bat = cmg_bat[(cmg_bat["Hora"] >= hr_ini) & (cmg_bat["Hora"] <= hr_fin)]
            for nodo, serie in cmg_bat.groupby("Nombre_PLEXOS"):
                y = pd.to_numeric(serie["Valor"], errors="coerce")
                if y.notna().any():
                    fig.add_trace(
                        go.Scatter(
                            x=serie["Hora"], y=y,
                            mode="lines",
                            name=f"CMG {nodo} ({sol})",
                            line=dict(dash="dot", width=1.5),
                        ),
                        secondary_y=True,
                    )
                    cmg_traces += 1
        else:
            # ---- ANCHO: filas por nodo, columnas por horas (5..49) ----
            cmg_bat = cmg[cmg["Nombre_PLEXOS"].astype(str).str.upper().str.startswith("BAT_")]
            if cmg_bat.empty:
                continue

            hour_cols = [c for c in cmg_bat.columns if str(c).isdigit()]
            if not hour_cols:
                continue
            hour_map = {c: int(str(c)) for c in hour_cols}
            in_range = [c for c in hour_cols if hr_ini <= hour_map[c] <= hr_fin]
            if not in_range:
                continue
            in_range = sorted(in_range, key=lambda c: hour_map[c])

            for _, row in cmg_bat.iterrows():
                nodo = row["Nombre_PLEXOS"]
                x = [hour_map[c] for c in in_range]
                y = pd.to_numeric(row[in_range], errors="coerce").values
                if pd.notna(y).any():
                    fig.add_trace(
                        go.Scatter(
                            x=x, y=y,
                            mode="lines",
                            name=f"CMG {nodo} ({sol})",
                            line=dict(dash="dot", width=1.5),
                        ),
                        secondary_y=True,
                    )
                    cmg_traces += 1

    # Layout
    fig.update_layout(
        height=600,
        legend_title_text="Series",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_xaxes(title_text="Hora")
    fig.update_yaxes(title_text="Perfil BESS (MW)", secondary_y=False, showgrid=True)
    fig.update_yaxes(title_text="CMG (BAT_)", secondary_y=True, showgrid=False)

    if bess_traces == 0 and cmg_traces == 0:
        st.warning("No se agregaron series. Revisa filtros de horas/baterías o las soluciones.")
    elif cmg_traces == 0:
        st.info("No se encontraron nodos CMG que empiecen por 'BAT_' en las soluciones seleccionadas.")

    st.plotly_chart(fig, use_container_width=True)