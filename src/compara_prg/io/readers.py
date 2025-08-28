from __future__ import annotations
from pathlib import Path
import warnings
import re
import polars as pl
import streamlit as st
import pickle
warnings.filterwarnings("ignore", category=RuntimeWarning)

# -----------------------------------------------------------------------------
# RUTA POR DEFECTO INCIAL
# -----------------------------------------------------------------------------

# El último .pkl usado queda en la sesión; si no existe tomamos el más reciente
def ruta_por_defecto(RESULTADOS_DIR) -> Path:
    if "DATA_PATH" in st.session_state:
        try:
            p = Path(st.session_state["DATA_PATH"])
            if p.exists():
                return p
        except TypeError:
            del st.session_state["DATA_PATH"]  # valor corrupto
    base = RESULTADOS_DIR / "results.pkl"
    if base.exists() and load_results(base):     # ← valida que sea dict
        return base
    for pkl in sorted(
        RESULTADOS_DIR.glob("results_*.pkl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        if load_results(pkl):                    # ← retorna dict ≠ {}
            return pkl
    return base



# -----------------------------------------------------------------------------
# CARGA DE DATOS
# -----------------------------------------------------------------------------

@st.cache_resource(show_spinner=True)
def load_results(path: Path | str) -> dict:
    """Carga un archivo de resultados (.pkl o .parquet).
       - Devuelve {} si algo sale mal.
       - Valida que el pickle deserializado sea dict.
    """
    # Aceptar string o Path
    path = Path(path)
    # 1) Verifica existencia
    if not path.exists():
        st.warning(f"⚠️  No se encontró {path}. Se devuelve {{}}.")
        return {}
    try:
        # 2) Pickle binario
        if path.suffix.lower() == ".pkl":
            with path.open("rb") as fh:
                data = pickle.load(fh)
            if not isinstance(data, dict):
                st.error(f"❌ {path.name} no contiene un dict válido.")
                return {}
            return data
        # 3) Parquet
        elif path.suffix.lower() == ".parquet":
            return pl.read_parquet(path).to_dict(False)
        else:
            st.error(f"❌ Formato no soportado: {path.suffix}")
            return {}
    except Exception as e:
        st.error(f"❌ Error al leer {path.name}: {e}")
        return {}


def fecha_from_filename(path: Path | str) -> str | None:
    """
    Extrae 'YYYYMMDD' de un nombre tipo results_YYYYMMDD_HH.pkl.
    Devuelve None si no hace match.
    """
    m = re.search(r"results_(\d{8})_", Path(path).name)
    return m.group(1) if m else None