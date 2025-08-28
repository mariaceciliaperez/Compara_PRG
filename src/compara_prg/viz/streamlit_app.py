# streamlit_app.py
"""
Streamlit dashboard — Comparación PID1, PID2 VS PCP
==========================================

Modos disponibles (barra lateral)
---------------------------------
1. **Totales por categoría** – Cinco gráficos, uno por tipo de central, cada uno con su filtro de centrales.
2. **CMG nodo** – Comparación del costo marginal por nodo.
3. **Análisis térmicas** – Apartado específico para *Centrales Térmicas* con focos dinámicos
   (por defecto “Central Atacama”). Incluye gráficos comparativos y tabla resumen.

Ejecución
---------
```bash
streamlit run streamlit_app.py
```
(ten a mano `results.pkl`, o súbelo desde la interfaz).
"""

from __future__ import annotations

from pathlib import Path
import sys

# /mount/src/compara_prg/src/compara_prg/viz/streamlit_app.py
# Necesitamos añadir .../compara_prg/src al sys.path
src_dir = Path(__file__).resolve().parents[2]   # → .../compara_prg/src
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from typing import Dict
import warnings

import streamlit as st


st.set_page_config(
    page_title="Compara PRG",   # opcional, título en la pestaña
    page_icon="📊",             # opcional, icono en la pestaña
    layout="wide"               # 👈 fuerza ancho completo
)


# from compara_prg.services.obtener_resultados import generar_resultados_interactivos_v2, Entrada
from compara_prg.utils.funciones             import infer_hours
from compara_prg.viz.plots                   import fecha_caption
from compara_prg.io.readers                  import ruta_por_defecto, load_results,fecha_from_filename
from compara_prg.viz.plots                   import mostrar_totales_por_categoria, mostrar_cmg_nodo, mostrar_analisis_termicas, mostrar_totales_sistema, mostrar_comparador_cotas
from compara_prg.config                      import RESULTS_DIR, OUTPUT_DIR,DEFAULT_PCP_FOLDER, DEFAULT_PID_FOLDER, COLOR, CATEGORY_LABELS, THERMAL_IDX, THRESHOLD
# from compara_prg.viz.grafico_chile     import grafico_chile
from compara_prg.viz.bat_perfil        import bat_perfil



# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
def cargar_o_subir_resultados(RESULTS_DIR: Path) -> Dict:
    data_path = ruta_por_defecto(RESULTS_DIR)
    results = load_results(data_path)

    if not results:
        up = st.sidebar.file_uploader("Sube results.pkl / .parquet")
        if up is not None:
            data_path = Path(up.name)
            data_path.write_bytes(up.getbuffer())
            results = load_results(data_path)
            st.session_state["DATA_PATH"] = str(data_path)
            st.session_state["FECHA_RESULTADO"] = fecha_from_filename(data_path)
            st.rerun()

    st.session_state.setdefault("DATA_PATH", str(data_path))
    st.session_state["FECHA_RESULTADO"] = fecha_from_filename(data_path)
    return results



# -----------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -----------------------------------------------------------------------------
st.sidebar.title("Análisis de resultados")
modo_config = st.sidebar.radio("Selecciona:", ("Configuración", "Visualización"), index=0)

if modo_config == "Visualización":
    st.sidebar.title("Modo de gráfico")
    mode = st.sidebar.radio(
        "Selecciona el modo de análisis:",
        ("Totales por categoría", "Resumen de simulación", "CMG nodo", "Análisis térmicas", "Cotas embalses","Perfil BESS",'Nodos y lineas'),
    )
else:
    mode = "Configuración"

# Carga resultados SOLO si estás en Visualización
results = {}
if modo_config == "Visualización":
    results = cargar_o_subir_resultados(RESULTS_DIR)
    if not results:
        st.warning("Carga un archivo de resultados para continuar o ve a 'Configuración' para generarlo.")
        st.stop()

    SOLUTIONS = tuple(sorted(results.keys()))
    HOURS_FULL = infer_hours(results)
    HOURS_INT = [int(h) for h in HOURS_FULL]
    MIN_H, MAX_H = HOURS_INT[0], HOURS_INT[-1]

fecha_lbl = st.session_state.get("FECHA_RESULTADO")
# -----------------------------------------------------------------------------
# MODO 0 — CONFIGURACIÓN INICIAL
# -----------------------------------------------------------------------------
if mode == "Configuración":
    st.title("Configuración inicial del entorno")

    # 1) Cargar .pkl existente
    archivos_pkl = sorted(RESULTS_DIR.glob("results_*.pkl"))
    etiquetas = [f.name for f in archivos_pkl]
    st.subheader("Seleccionar archivo existente")
    if etiquetas:
        seleccionado = st.selectbox("Elige un archivo de resultados", etiquetas, key="sel_exist")
        if st.button("Cargar archivo seleccionado", key="btn_load_exist"):
            selected_path = RESULTS_DIR / seleccionado
            res = load_results(selected_path)
            if res:
                st.success(f"Archivo {seleccionado} cargado exitosamente.")
                st.session_state["DATA_PATH"] = str(selected_path)
                st.session_state["FECHA_RESULTADO"] = fecha_from_filename(selected_path)
                st.rerun()
    else:
        st.info("No se encontraron archivos .pkl en la carpeta Resultados/.")

#     st.markdown("---")
#     st.subheader("Generar nuevo archivo de resultados (1 a 3 entradas, PID/PCP)")

#     n = st.number_input("¿Cuántas entradas quieres agregar?", min_value=1, max_value=3, value=2, step=1, key="n_entradas")

#     with st.form("form_config_v2"):
#         entradas: list[Entrada] = []
#         for i in range(int(n)):
#             st.markdown(f"#### Entrada {i+1}")
#             c1, c2, c3 = st.columns([1, 2, 2])

#             with c1:
#                 tipo = st.selectbox("Tipo", options=["PID", "PCP"], key=f"tipo_{i}")

#             with c2:
#                 base = st.text_input(
#                     "Ruta base",
#                     key=f"base_{i}",
#                     placeholder=r"E:\...\PID_YYYYMMDD\Publicacion\YYYYMMDD_PP  (o raíz PCP)",
#                 )

#             with c3:
#                 carpeta_default = DEFAULT_PCP_FOLDER if tipo == "PCP" else DEFAULT_PID_FOLDER
#                 carpeta = st.text_input("Carpeta (dentro de la base)", value=carpeta_default, key=f"carpeta_{i}")

#             if tipo == "PID":
#                 periodo = st.number_input("Periodo (1–24)", min_value=1, max_value=24, value=1, step=1, key=f"periodo_{i}")
#             else:
#                 periodo = None

#             if base.strip():
#                 entradas.append(Entrada(tipo=tipo, base=base.strip(), carpeta=carpeta.strip(), periodo=periodo))

#         st.components.v1.html(
#             """
#             <script>
#             const form = window.parent.document.querySelectorAll('div[data-testid="stForm"]')[0];
#             if (form) {
#                 form.querySelectorAll('input').forEach(inp => {
#                     inp.addEventListener('keydown', e => {
#                         if (e.key === 'Enter') e.preventDefault();
#                     });
#                 });
#             }
#             </script>
#             """,
#             height=0,
#         )
#         submitted = st.form_submit_button("Ejecutar configuración y generar archivo", type="primary")

#     if submitted:
#         try:
#             if not entradas:
#                 st.error("No hay entradas válidas.")
#                 st.stop()

#             output_path, res = generar_resultados_interactivos_v2(
#                 entradas=entradas,
#                 directorio_salida=OUTPUT_DIR,
#                 default_pcp_carpeta=DEFAULT_PCP_FOLDER,
#                 default_pid_carpeta=DEFAULT_PID_FOLDER,
#             )
#             st.success(f"✅ Archivo generado: {output_path.name}")
#             st.session_state["DATA_PATH"] = str(output_path)
#             st.session_state["FECHA_RESULTADO"] = fecha_from_filename(output_path)
#             st.rerun()
#         except Exception as e:
#             st.error(f"Error al generar resultados: {e}")


# -----------------------------------------------------------------------------
# MODO 1 — TOTALES POR CATEGORÍA
# -----------------------------------------------------------------------------
elif mode == "Totales por categoría":
    if fecha_lbl:
        fecha_caption(fecha_lbl)

    mostrar_totales_por_categoria(
        results, SOLUTIONS, HOURS_FULL, HOURS_INT,
        MIN_H, MAX_H, CATEGORY_LABELS, COLOR
    )

# -----------------------------------------------------------------------------
# MODO 2 — CMG POR NODO
# -----------------------------------------------------------------------------
elif mode == "CMG nodo":
    if fecha_lbl:
        fecha_caption(fecha_lbl)
    mostrar_cmg_nodo(
        results, SOLUTIONS, HOURS_FULL,
        HOURS_INT, MIN_H, MAX_H, COLOR
    )

# -----------------------------------------------------------------------------
# MODO 3 — ANÁLISIS TÉRMICAS
# -----------------------------------------------------------------------------
elif mode == "Análisis térmicas":
    if fecha_lbl:
        fecha_caption(fecha_lbl)
    mostrar_analisis_termicas(
        results, SOLUTIONS, HOURS_FULL,
        THRESHOLD, THERMAL_IDX
    )

elif mode == "Totales sistema (GENT)":
    if fecha_lbl:
        fecha_caption(fecha_lbl)
    mostrar_totales_sistema(
        results=results,
        solutions=SOLUTIONS,
        hours_full=HOURS_FULL,
        hours_int=HOURS_INT,
        color_palette=COLOR
    )
elif mode == "Cotas embalses":
    if fecha_lbl:
        fecha_caption(fecha_lbl)
    mostrar_comparador_cotas(
        results=results,
        solutions=SOLUTIONS
    )



# elif mode == "Nodos y lineas":
#     if fecha_lbl:
#         fecha_caption(fecha_lbl)
#     fig = grafico_chile()   # 👈 ya cacheado
#     st.plotly_chart(fig, use_container_width=True)



elif mode == "Perfil BESS":
    if fecha_lbl:
        fecha_caption(fecha_lbl)
    bat_perfil(results,SOLUTIONS )
