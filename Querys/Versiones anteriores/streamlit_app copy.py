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
import streamlit as st
st.set_page_config(layout="wide")
from pathlib import Path
from typing import Dict
from datetime import datetime
import warnings
import polars as pl

from Obtener_resultados import generar_resultados_interactivos
from funciones import ruta_por_defecto, load_results, infer_hours, fecha_from_filename,fecha_caption
from Graficos import  mostrar_totales_por_categoria, mostrar_cmg_nodo,mostrar_analisis_termicas

warnings.filterwarnings("ignore", category=RuntimeWarning)

# -----------------------------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
RESULTADOS_DIR = BASE_DIR / "Resultados"
RESULTADOS_DIR.mkdir(exist_ok=True)

COLOR = [
    "#0072B2", "#E69F00", "#009E73", "#CC79A7",
    "#D55E00", "#F0E442", "#56B4E9", "#000000",
]
CATEGORY_LABELS = [
    "Centrales de Embalse",
    "Sistemas de Almacenamiento",
    "Centrales Térmicas",
    "Centrales Solares",
    "Centrales Eólicas",
]
THERMAL_IDX = 2
THRESHOLD = 0.1

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
def cargar_o_subir_resultados(resultados_dir: Path) -> Dict:
    data_path = ruta_por_defecto(resultados_dir)
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
results = cargar_o_subir_resultados(RESULTADOS_DIR)
if not results:
    st.warning("Carga un archivo de resultados para continuar.")
    st.stop()

SOLUTIONS = tuple(sorted(results.keys()))
HOURS_FULL = infer_hours(results)
HOURS_INT = [int(h) for h in HOURS_FULL]
MIN_H, MAX_H = HOURS_INT[0], HOURS_INT[-1]

st.sidebar.title("Análisis de resultados")
modo_config = st.sidebar.radio(
    "Selecciona:",
    ("Configuración", "Visualización"),
)

if modo_config == "Visualización":
    st.sidebar.title("Modo de gráfico")
    mode = st.sidebar.radio(
        "Selecciona el modo de análisis:",
        ("Totales por categoría", "CMG nodo", "Análisis térmicas"),
    )
else:
    mode = "Configuración"


if "DATA_PATH" in st.session_state:
    st.sidebar.caption(f"Archivo actual: `{Path(st.session_state['DATA_PATH']).name}`")


fecha_lbl = st.session_state.get("FECHA_RESULTADO")   # ← sin KeyError

# -----------------------------------------------------------------------------
# MODO 0 — CONFIGURACIÓN INICIAL
# -----------------------------------------------------------------------------
if mode == "Configuración":
    st.title("Configuración inicial del entorno")

    # ── 1) Cargar .pkl existente ──────────────────────────────────────
    archivos_pkl = sorted(RESULTADOS_DIR.glob("results_*.pkl"))
    etiquetas     = [f.name for f in archivos_pkl]
    st.subheader("Seleccionar archivo existente")
    if etiquetas:
        seleccionado = st.selectbox("Elige un archivo de resultados", etiquetas)
        if st.button("Cargar archivo seleccionado"):
            selected_path = RESULTADOS_DIR / seleccionado
            results = load_results(selected_path)
            if results:
                st.success(f"Archivo {seleccionado} cargado exitosamente.")
                st.session_state["DATA_PATH"] = str(selected_path)
                st.rerun()
    else:
        st.info("No se encontraron archivos .pkl en la carpeta Resultados/.")

    st.markdown("---")
    st.subheader("Generar nuevo archivo de resultados")

    # ── 2) Casilla PID2 fuera del form (render inmediato) ─────────────
    incluir_pid2 = st.checkbox("¿Deseas incluir carpeta PID2?", value=False, key="chk_pid2")

    # ── 3) Formulario con TODOS los campos y el botón submit ──────────
    with st.form("form_config"):
        st.markdown("### PID1")
        base_pid1    = st.text_input("Ruta base PID1", key="base_pid1")
        carpeta_pid1 = st.text_input("Nombre carpeta PID1",
                                     value="Model Test15d Solution",
                                     key="carpeta_pid1")

        st.markdown("### PCP")
        base_pcp     = st.text_input("Ruta base PCP", key="base_pcp")

        st.markdown("### PID2 (opcional)")
        base_pid2    = st.text_input("Ruta base PID2",
                                     disabled=not incluir_pid2,
                                     key="base_pid2")
        carpeta_pid2 = st.text_input("Nombre carpeta PID2",
                                     disabled=not incluir_pid2,
                                     key="carpeta_pid2")

        # ── JS: bloquear Enter para que no dispare el envío ───────────
        st.components.v1.html(
            """
            <script>
            // Evita que la tecla Enter envíe el formulario automáticamente
            const form = window.parent.document.querySelectorAll('div[data-testid="stForm"]')[0];
            if (form) {
                form.querySelectorAll('input').forEach(inp => {
                    inp.addEventListener('keydown', e => {
                        if (e.key === 'Enter') e.preventDefault();
                    });
                });
            }
            </script>
            """,
            height=0,
        )

        # ── Botón submit (obligatorio dentro del form) ────────────────
        submitted = st.form_submit_button(
            "Ejecutar configuración y generar archivo",
            type="primary"
        )

    # ── 4) Acción tras pulsar el botón ────────────────────────────────
    if submitted:
        try:
            output_path, results = generar_resultados_interactivos(
                base_pid1=base_pid1,
                carpeta_pid1=carpeta_pid1,
                base_pcp=base_pcp,
                base_pid2=base_pid2 if incluir_pid2 else None,
                carpeta_pid2=carpeta_pid2 if incluir_pid2 else None
            )
            st.success(f"✅ Archivo generado: {output_path.name}")
            st.session_state["DATA_PATH"] = str(output_path)
            st.session_state["FECHA_RESULTADO"] = fecha_from_filename(output_path)
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error al generar resultados: {e}")


# -----------------------------------------------------------------------------
# MODO 1 — TOTALES POR CATEGORÍA
# -----------------------------------------------------------------------------
elif mode == "Totales por categoría":
    fecha_caption(fecha_lbl)
    mostrar_totales_por_categoria(
        results, SOLUTIONS, HOURS_FULL, HOURS_INT,
        MIN_H, MAX_H, CATEGORY_LABELS, COLOR
    )

# -----------------------------------------------------------------------------
# MODO 2 — CMG POR NODO
# -----------------------------------------------------------------------------
elif mode == "CMG nodo":
    fecha_caption(fecha_lbl)
    mostrar_cmg_nodo(
        results, SOLUTIONS, HOURS_FULL,
        HOURS_INT, MIN_H, MAX_H, COLOR
    )

# -----------------------------------------------------------------------------
# MODO 3 — ANÁLISIS TÉRMICAS
# -----------------------------------------------------------------------------
elif mode == "Análisis térmicas":
    fecha_caption(fecha_lbl)
    mostrar_analisis_termicas(
        results, SOLUTIONS, HOURS_FULL,
        BASE_DIR, THRESHOLD, THERMAL_IDX
    )

st.caption("Generado con Streamlit · © 2025")