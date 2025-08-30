# Obtener_resultados.py
from __future__ import annotations
import pickle
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Any, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime
import streamlit as st
from compara_prg.utils.funciones import extraer_fecha_y_hora_desde_ruta, detectar_carpeta_por_zip

# Funciones de consultas 
from compara_prg.queries.query_generation_tables import get_generation_tables
from compara_prg.queries.query_generation_costs  import get_gen_costs
from compara_prg.queries.query_total_generation  import get_total_generation
from compara_prg.queries.query_CMg               import get_cmg
from compara_prg.queries.query_BESS              import get_bess
from compara_prg.queries.query_Ini_Volumes       import get_ini_volumes


# ─────────────────────────────────────────────────────────────────────────────
# Modelo de entrada genérica
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Entrada:
    tipo: Literal["PID", "PCP"]
    base: str
    carpeta: Optional[str] = None       # para PID y PCP
    periodo: Optional[int] = None       # requerido si tipo == "PID"


# ─────────────────────────────────────────────────────────────────────────────
# Valida base/carpeta y devuelve el primer .zip encontrado (no crea rutas nuevas)
# ─────────────────────────────────────────────────────────────────────────────
def ruta_zip_valida(base: str, sub: str, descripcion: str) -> Path:
    p = Path(base).expanduser().resolve() / (sub or "")
    if not p.is_dir():
        st.error(f"❌ Carpeta no encontrada: {p}")
        raise FileNotFoundError(p)
    zips = list(p.glob("*.zip"))
    if not zips:
        st.error(f"❌ No hay archivos .zip en {p}")
        raise FileNotFoundError(f"No zip in {p}")
    st.info(f"✓ {descripcion}: {zips[0].name}")
    return zips[0]


# ─────────────────────────────────────────────────────────────────────────────
# Función principal (usada por streamlit_app.py)
# ─────────────────────────────────────────────────────────────────────────────
def generar_resultados_interactivos_v2(
    entradas: List[Entrada],
    directorio_salida: Path,
    default_pcp_carpeta: str,
    default_pid_carpeta: str,
) -> Tuple[Path, Dict[str, Any]]:

    if not entradas:
        raise ValueError("Debes proporcionar al menos una entrada.")
    if len(entradas) > 3:
        raise ValueError("El máximo permitido es de 3 entradas.")

    # 1) Defaults y validaciones (sin usar 'lbl' aún)
    for e in entradas:
        if e.tipo == "PCP" and (e.carpeta is None or e.carpeta.strip() == ""):
            e.carpeta = default_pcp_carpeta
        if e.tipo == "PID" and (e.carpeta is None or e.carpeta.strip() == ""):
            e.carpeta = default_pid_carpeta

        if e.tipo == "PID":
            if e.periodo is None:
                raise ValueError("Si la entrada es PID, debes informar 'periodo' (1–24).")
            if not (1 <= int(e.periodo) <= 24):
                raise ValueError("Periodo PID fuera de rango (1–24).")

    # 2) Construir labels
    labels: List[str] = []
    pid_idx = 0
    pcp_count = 0
    for e in entradas:
        if e.tipo == "PID":
            pid_idx += 1
            labels.append(f"PID{pid_idx}")
        else:
            pcp_count += 1
            labels.append("PCP" if pcp_count == 1 else f"PCP{pcp_count}")

    # 3) Localizar zips y configurar por etiqueta (ahora sí existe 'lbl')
    zip_by_label: Dict[str, Path] = {}
    cfg_by_label: Dict[str, Dict[str, Any]] = {}

    fecha_nombre: Optional[str] = None
    periodo_nombre: Optional[int] = None

    for e, lbl in zip(entradas, labels):
        # Intentar con la carpeta indicada; si falla, detectar automáticamente
        try:
            zip_path = ruta_zip_valida(e.base, e.carpeta or "", lbl)
        except FileNotFoundError:
            auto_sub = detectar_carpeta_por_zip(e.base)
            if auto_sub is None:
                st.error(f"❌ {lbl}: No se encontró ningún .zip dentro de {Path(e.base).resolve()}")
                raise
            ubicacion = (auto_sub or ".")  # "." representa la base
            st.warning(
                f"⚠ {lbl}: carpeta '{e.carpeta}' no disponible/sin .zip. "
                f"Usando detección automática: '{ubicacion}'."
            )
            e.carpeta = auto_sub  # puede ser "" (usar base)
            zip_path = ruta_zip_valida(e.base, e.carpeta, lbl)

        zip_by_label[lbl] = zip_path

        if e.tipo == "PID" and (fecha_nombre is None):
            try:
                f_detect, _ = extraer_fecha_y_hora_desde_ruta(e.base)
                if f_detect:
                    fecha_nombre = f_detect
                    periodo_nombre = int(e.periodo)
            except Exception:
                pass

        if e.tipo == "PID":
            hini = int(e.periodo)
            hfin = hini + 48
            st_flag = True
            periodo_pid = int(e.periodo)
        else:
            hini = 1
            hfin = 168
            st_flag = False
            periodo_pid = 1

        cfg_by_label[lbl] = {
            "tipo": e.tipo,
            "base": e.base,
            "hini": hini,
            "hfin": hfin,
            "st_schedule": st_flag,
            "periodo_pid": periodo_pid,
        }

    # Referencia para get_total_generation: primer PCP; si no hay, primera entrada
    order = list(zip_by_label.keys())
    first_pcp_lbl = next((lbl for lbl in order if cfg_by_label[lbl]["tipo"] == "PCP"), None)
    ref_lbl = first_pcp_lbl or order[0]
    sol_file_ref = str(zip_by_label[ref_lbl])  # ← cadena, no Path

    # Asegura carpeta de salida
    directorio_salida.mkdir(parents=True, exist_ok=True)
    dir_out_str = str(directorio_salida)       # ← por si tus Query_* esperan str

    # Ejecuta consultas por solución x función
    results: Dict[str, Dict[str, Any]] = defaultdict(dict)
    #function_names = ["GENTABLES", "GENC", "GENT", "CMG",'COTAS', "BESS"]
    function_names = ["GENTABLES",  "GENT"]

    # ... líneas previas iguales ...

    def run_single_query(label: str, func_name: str):
        cfg = cfg_by_label[label]
        sol_file = str(zip_by_label[label])    # ← cadena, no Path
        is_pcp = (cfg["tipo"] == "PCP")

        try:
            if func_name == "GENTABLES":
                return label, func_name, get_generation_tables(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    directorio_fecha=cfg["base"],
                    hini=cfg["hini"], hfin=cfg["hfin"],
                    st_schedule=cfg["st_schedule"],
                )

            elif func_name == "GENC":
                return label, func_name, get_gen_costs(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    hini=cfg["hini"], hfin=cfg["hfin"],
                    st_schedule=cfg["st_schedule"],
                )

            elif func_name == "GENT":
                # ⬇️ AHORA desempaquetamos y guardamos con nombres
                df_tabla, df_losses = get_total_generation(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    directorio_fecha=cfg["base"],
                    periodo_pid=cfg["periodo_pid"],
                    st_schedule=cfg["st_schedule"],
                    hini=cfg["hini"], hfin=cfg["hfin"],
                    # Si NO es PCP → usar pérdidas con “modo PID” (tu lógica actual)
                    tx_loss=(not is_pcp),
                )
                return label, func_name, {
                    "tabla": df_tabla,
                    "losses": df_losses
                }

            elif func_name == "CMG":
                return label, func_name, get_cmg(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    st_schedule=cfg["st_schedule"],
                    hini=cfg["hini"], hfin=cfg["hfin"],
                )

            elif func_name == "COTAS":
                    return label, func_name, get_ini_volumes(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    st_schedule=cfg["st_schedule"],
                    hini=cfg["hini"], hfin=cfg["hfin"],
                )

            elif func_name == "BESS":
                return label, func_name, get_bess(
                    sol_file=sol_file,
                    tipo_solucion=label,
                    directorio_salida=dir_out_str,
                    st_schedule=cfg["st_schedule"],
                    hini=cfg["hini"], hfin=cfg["hfin"],
                )

        except Exception as e:
            print(f"[ERR] {label} – {func_name}: {e}")
            return label, func_name, None


    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(run_single_query, lbl, fn)
                   for lbl in zip_by_label.keys()
                   for fn in function_names]
        for fut in as_completed(futures):
            lbl, fn, res = fut.result()
            if res is not None:
                results[lbl][fn] = res

    # Nombre de salida
    if not fecha_nombre:
        try:
            f_detect, _ = extraer_fecha_y_hora_desde_ruta(cfg_by_label[ref_lbl]["base"])
            fecha_nombre = f_detect or datetime.now().strftime("%Y%m%d")
        except Exception:
            fecha_nombre = datetime.now().strftime("%Y%m%d")

    periodo_nombre = periodo_nombre or 1
    etiqueta = f"{fecha_nombre}_{int(periodo_nombre):02d}"
    output_path = directorio_salida / f"results_{etiqueta}.pkl"

    with output_path.open("wb") as fh:
        pickle.dump(results, fh, protocol=pickle.HIGHEST_PROTOCOL)

    return output_path, results
