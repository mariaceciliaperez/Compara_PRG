from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import warnings
import re
import polars as pl
import streamlit as st
import pandas as pd
import numpy as np
import pickle
from typing import Any, Set  
warnings.filterwarnings("ignore", category=RuntimeWarning)
import os
from typing import Tuple, Optional

# ─────────────────────────────────────────────────────────────
# 1. Utilidad: extraer fecha y hora (periodo)
#    • Si no hay HH, usa 1 por defecto.
# ─────────────────────────────────────────────────────────────
def extraer_fecha_y_hora_desde_ruta(ruta: str) -> Tuple[str, int]:
    """
    Extrae la fecha (AAAAMMDD) y la hora/periodo (HH).
    Si la ruta solo contiene la fecha, devuelve periodo = 1.

    Ejemplos aceptados:
        .../PID_20250730_02/...
        .../PID_20250730/...
    """
    patron = r'PID_(\d{8})(?:_(\d{2}))?'   # 2º grupo (HH) es opcional
    match = re.search(patron, ruta)
    if not match:
        raise ValueError(f"No se pudo extraer fecha y hora desde la ruta: {ruta}")

    fecha = match.group(1)
    hora  = int(match.group(2)) if match.group(2) is not None else 1
    return fecha, hora

# 2) Valida inputs antes de lanzar hilos --------------------------
def validar_ruta_carpeta(base: str, carpeta: str) -> Path:
    p = Path(base, carpeta)
    if not p.is_dir():
        raise FileNotFoundError(f"❌ Carpeta no encontrada: {p}")
    zips = list(p.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"❌ No hay .zip en {p}")
    return zips[0]          # primer zip




def normalize_hours(df: pl.DataFrame, hours_full: list[str]) -> pl.DataFrame:
    # Renombra CUALQUIER columna int a string (antes cortabas en <=100)
    ren = {c: str(c) for c in df.columns if isinstance(c, int)}
    df  = df.rename(ren) if ren else df

    # Completa sólo las horas esperadas
    miss = [h for h in hours_full if h not in df.columns]
    if miss:
        df = df.with_columns([pl.lit(0).alias(h) for h in miss])

    # Orden final
    if "Nombre_PLEXOS" in df.columns:
        df = df.select(["Nombre_PLEXOS", *hours_full])
    return df




# ---------------------------------------------------------------------------
def _agrega_horas_from_df(df: Any, horas: Set[int]) -> None:
    """
    Añade al set las columnas numéricas (1–168…).
    Acepta tanto polars como pandas DataFrames.
    """
    try:                                # polars y pandas tienen .columns
        for c in df.columns:
            if isinstance(c, int) and 1 <= c <= 1000:
                horas.add(c)
            elif isinstance(c, str) and re.fullmatch(r"\d+", c):
                horas.add(int(c))
    except Exception:
        pass                            # por si el objeto no es DF realmente

def _explora(obj: Any, horas: Set[int]) -> None:
    """
    Recorre cualquier estructura anidada (dict, list, tuple) buscando DataFrames.
    """
    if isinstance(obj, (pl.DataFrame, pd.DataFrame)):
        _agrega_horas_from_df(obj, horas)
    elif isinstance(obj, dict):
        for v in obj.values():
            _explora(v, horas)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            _explora(v, horas)
    # otros tipos se ignoran

def infer_hours(results: Dict[str, dict]) -> List[str]:
    """
    Devuelve todas las horas encontradas en todas las soluciones, ordenadas.
    Si no se encuentra ninguna, hace *fallback* a 1-48.
    """
    horas: Set[int] = set()
    _explora(results, horas)

    if not horas:                       # fallo seguro → 1-48
        return [str(h) for h in range(1, 49)]

    return [str(h) for h in sorted(horas)]

@st.cache_data(show_spinner=False, max_entries=1)
def prepara_datos(
    _results: dict,
    sol_a: str,
    sol_b: str,
    thermal_idx: int,
    hours_full: list[str],
    hours: list[str],          # ventana visible (24 h): "1".."24" o "25".."48"
    th: float):
    """
    Compara SOLO la ventana 'hours' (día visible), sin NaN/-0, y devuelve:
    - pivot_pd: tabla hora-a-hora (centrales x horas)
    - resumen_df: totales del día visible por central, ORDENADO por |Δ| desc
    - styles: estilos para la tabla coloreada
    """

    # --- Normaliza horas a str (importante para selects y renames) ---
    hours_full = [str(h) for h in hours_full]
    hrs = [str(h) for h in hours]

    # --- Carga tablas y fuerza esquema ---
    try:
        df1 = normalize_hours(_results[sol_a]["GENTABLES"][thermal_idx], hours_full)
        df2 = normalize_hours(_results[sol_b]["GENTABLES"][thermal_idx], hours_full)
    except Exception:
        return None, None, None

    df1 = coerce_schema(df1, hours_full)
    df2 = coerce_schema(df2, hours_full)

    if (
        df1 is None or df2 is None or df1.is_empty() or df2.is_empty()
        or "Nombre_PLEXOS" not in df1.columns or "Nombre_PLEXOS" not in df2.columns
    ):
        return None, None, None

    # Asegura numérico y sin nulos en TODO el horizonte
    df1 = df1.with_columns([pl.col(h).cast(pl.Float64).fill_null(0).alias(h) for h in hours_full])
    df2 = df2.with_columns([pl.col(h).cast(pl.Float64).fill_null(0).alias(h) for h in hours_full])

    # =======================
    # (A) RESUMEN EN VENTANA
    # =======================
    resumen_pl = (
        df1.select("Nombre_PLEXOS", pl.sum_horizontal([pl.col(h) for h in hrs]).alias("Tot_1_win"))
          .join(
              df2.select("Nombre_PLEXOS", pl.sum_horizontal([pl.col(h) for h in hrs]).alias("Tot_2_win")),
              on="Nombre_PLEXOS", how="inner"
          )
          .with_columns([
              pl.col("Tot_1_win").round(0).cast(pl.Int64),
              pl.col("Tot_2_win").round(0).cast(pl.Int64),
              (pl.col("Tot_2_win") - pl.col("Tot_1_win")).round(0).cast(pl.Int64).alias("Δ Total"),
          ])
          .filter(
              ((pl.col("Tot_1_win") != 0) & (pl.col("Tot_2_win") != 0) & (pl.col("Δ Total").abs() > 50))
              | (pl.col("Tot_1_win") == 0) ^ (pl.col("Tot_2_win") == 0)
          )
          .select(["Nombre_PLEXOS", "Tot_1_win", "Tot_2_win", "Δ Total"])
          .sort(pl.col("Δ Total").abs(), descending=True)   # 👈 orden mayor→menor por |Δ|
    )
    if resumen_pl.is_empty():
        return None, None, None

    # ======================================
    # (B) DIFERENCIAS HORA-A-HORA (ventana)
    # ======================================
    ren1 = {h: f"{h}_1" for h in hrs}
    ren2 = {h: f"{h}_2" for h in hrs}

    joined = (
        df1.select(["Nombre_PLEXOS", *hrs]).rename(ren1)
          .join(df2.select(["Nombre_PLEXOS", *hrs]).rename(ren2),
                on="Nombre_PLEXOS", how="outer")  # outer para permitir on/off entre soluciones
          .with_columns([
              (pl.coalesce([pl.col(f"{h}_2"), pl.lit(0.0)]) -
               pl.coalesce([pl.col(f"{h}_1"), pl.lit(0.0)])).alias(h)
              for h in hrs
          ])
          .with_columns([
              pl.when(pl.col(h).abs() < 1e-9).then(0.0).otherwise(pl.col(h)).alias(h)
              for h in hrs
          ])
          .fill_null(0)
    )

    

    # filtra centrales con alguna |Δ| > th
    diff_cols = hrs
    centrales_ok = (
        joined
        .with_columns(pl.max_horizontal([pl.col(c).abs() for c in diff_cols]).alias("mx"))
        .filter(pl.col("mx") > th)
        .select("Nombre_PLEXOS")
    )
    if centrales_ok.is_empty():
        return None, None, None

    # largo → ancho
    long = (
        joined
        .filter(pl.col("Nombre_PLEXOS").is_in(centrales_ok.get_column("Nombre_PLEXOS").to_list()))
        .unpivot(index="Nombre_PLEXOS", on=diff_cols, variable_name="Hora", value_name="Δ MWh")
        .with_columns(pl.col("Hora").cast(pl.UInt16))
        .filter(pl.col("Δ MWh") != 0)
    )
    pivot_pl = long.pivot(values="Δ MWh", index="Nombre_PLEXOS", on="Hora").fill_null(0)

    # --- pandas pivot (desde polars) ---
    pivot_pd = pivot_pl.to_pandas().set_index("Nombre_PLEXOS")

    # 1) Ordenar por el resumen, pero solo las que existen en el pivot
    orden_resumen = resumen_pl.get_column("Nombre_PLEXOS").to_list()
    orden = [n for n in orden_resumen if n in pivot_pd.index]
    pivot_pd = pivot_pd.reindex(orden)

    # 2) Quedarse solo con las horas visibles
    pivot_pd.columns = pivot_pd.columns.astype(int)
    pivot_pd = pivot_pd.reindex([int(h) for h in hrs], axis=1)

        # 3) Filtrar filas sin diferencias significativas (NaN → 0 para evaluar)
    mask_sig = (pivot_pd.fillna(0.0).abs() > th).any(axis=1)
    pivot_pd = pivot_pd.loc[mask_sig].fillna(0.0).astype(float)

    # Guarda las columnas de horas ANTES de agregar el total
    hours_cols = list(pivot_pd.columns)  # típicamente [1..24] (ints)

    # ==========================
    # (D) COLUMNA TOTAL POR FILA
    # ==========================
    total_col = "Δ Total fila"
    pivot_pd[total_col] = pivot_pd[hours_cols].sum(axis=1)  # suma solo horas
    # (si prefieres suma absoluta: pivot_pd[total_col] = pivot_pd[hours_cols].abs().sum(axis=1))

    # ==========================
    # (C) ESTILOS DE LA TABLA
    # ==========================
    # g1 = sol_a ; g2 = sol_b ; diff = g2 - g1 (usado solo para tolerancia)
    g1 = joined.select([pl.col(f"{h}_1").fill_null(0) for h in hrs]).to_numpy()
    g2 = joined.select([pl.col(f"{h}_2").fill_null(0) for h in hrs]).to_numpy()

    # Alineamos con el orden/filtrado de pivot_pd
    idx_map = {name: i for i, name in enumerate(joined.get_column("Nombre_PLEXOS").to_list())}
    rows = [idx_map[n] for n in pivot_pd.index]

    g1v = g1[rows]
    g2v = g2[rows]

    # Tolerancia para “cero” e “igualdad”
    EPS = 0.5  # ajusta si lo necesitas más/menos estricto

    # Máscaras lógicas (misma forma que las HORAS, no incluyen la col. total)
    ambos_cero      = (np.abs(g1v) <= EPS) & (np.abs(g2v) <= EPS)
    iguales_no_cero = (np.abs(g2v - g1v) <= EPS) & (np.abs(g1v) > EPS) & (np.abs(g2v) > EPS)
    # Verde (sol_a > sol_b)
    verde_oscuro = (g1v - g2v > EPS) & (np.abs(g2v) <= EPS)   # segundo == 0
    verde_opaco  = (g1v - g2v > EPS) & (np.abs(g2v) > EPS)    # segundo != 0
    # Rojo (sol_a < sol_b)
    rojo_oscuro = (g2v - g1v > EPS) & (np.abs(g1v) <= EPS)    # primero == 0
    rojo_opaco  = (g2v - g1v > EPS) & (np.abs(g1v) > EPS)     # primero != 0

    # DataFrame de estilos para TODAS las columnas (horas + total), vacío por defecto
    styles = pd.DataFrame("", index=pivot_pd.index, columns=pivot_pd.columns)

    def _mask_to_df(mask_bool):
        # Mapea las máscaras SOLO a las columnas de horas (coinciden en forma)
        return pd.DataFrame(mask_bool, index=pivot_pd.index, columns=hours_cols)

    # Colores — MISMOS que ya usabas
    COL_GRIS      = "background-color:#D9D9D9;color:#333"     # ambos 0
    COL_CELESTE   = "background-color:#CFE2F3;color:#1E4F7B"  # iguales ≠ 0
    COL_VERDE_OP  = "background-color:#C8E6C9;color:#0B3D0B"  # a>b, b≠0
    COL_VERDE_OSC = "background-color:#81C784;color:#0B3D0B"  # a>b, b==0
    COL_ROJO_OP   = "background-color:#FFCDD2;color:#6E0000"  # a<b, a≠0
    COL_ROJO_OSC  = "background-color:#E57373;color:#6E0000"  # a<b, a==0

    # Aplica estilos a las HORAS sin tocar la columna total
    styles.loc[:, hours_cols] = ""  # explícito
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(ambos_cero),      COL_GRIS)
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(iguales_no_cero), COL_CELESTE)
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(rojo_opaco),     COL_VERDE_OP)
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(rojo_oscuro),    COL_VERDE_OSC)
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(verde_opaco),      COL_ROJO_OP)
    styles.loc[:, hours_cols] = styles.loc[:, hours_cols].mask(_mask_to_df(verde_oscuro),     COL_ROJO_OSC)

    # (opcional) Si quieres colorear el total, descomenta uno de estos:
    # 1) Sin color (default): styles[total_col] = ""
    # 2) Verde/rojo por signo:
    styles[total_col] = np.where(
        pivot_pd[total_col] >= 0,
        "background-color:#C8E6C9;color:#0B3D0B",
        "background-color:#FFCDD2;color:#6E0000",
    )

    # pandas final: columnas con nombres claros
    resumen_df = resumen_pl.to_pandas().rename(columns={
        "Tot_1_win": f"Total {sol_a} (día)",
        "Tot_2_win": f"Total {sol_b} (día)",
        "Δ Total":   f"Δ Total ({sol_b} – {sol_a}) (día)"
    })

    return pivot_pd, resumen_df, styles









def coerce_schema(df: pl.DataFrame, hours_full: list[str], name_col: str = "Nombre_PLEXOS") -> pl.DataFrame:
    """
    Asegura que la primera columna sea 'Nombre_PLEXOS' y que las horas sean strings
    según 'hours_full'. Repara casos como ['column_0','1','2',...].
    """
    if df is None or df.is_empty():
        return df

    cols = df.columns

    # Si ya tiene la columna clave, sólo convierte horas int->str
    if name_col in cols:
        ren = {c: str(c) for c in cols if isinstance(c, int)}
        return df.rename(ren) if ren else df

    # Caso típico roto: primera col sin nombre útil + horas numeradas
    # Intentamos mapear: primera -> 'Nombre_PLEXOS', resto -> hours_full
    if len(cols) >= 1:
        ren = {cols[0]: name_col}
        for i, c in enumerate(cols[1:]):
            if i < len(hours_full):
                ren[c] = str(hours_full[i])
        try:
            return df.rename(ren)
        except Exception:
            pass  # fallback abajo

    # Fallback: si cantidad calza exactamente (1 + horas)
    if len(cols) == 1 + len(hours_full):
        newcols = [name_col] + [str(h) for h in hours_full]
        return df.rename(dict(zip(cols, newcols)))

    # Último intento: convertir headers int->str
    ren = {c: str(c) for c in cols if isinstance(c, int)}
    return df.rename(ren) if ren else df