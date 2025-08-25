# Obtener_resultados.py

import os
import pickle
from pathlib import Path
from funciones import extraer_fecha_y_hora_desde_ruta
from Query_generation_tables import *
from Query_generation_costs import *
from Query_total_generation import *
from Query_CMg import *
from Query_BESS import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path
import streamlit as st

def ruta_zip_valida(base: str, sub: str, descripcion: str) -> Path:
    """Devuelve el primer .zip encontrado o lanza un error claro."""
    p = Path(base).expanduser().resolve() / sub
    if not p.is_dir():
        st.error(f"❌ Carpeta no encontrada: {p}")
        raise FileNotFoundError(p)
    zips = list(p.glob("*.zip"))
    if not zips:
        st.error(f"❌ No hay archivos .zip en {p}")
        raise FileNotFoundError(f"No zip in {p}")
    st.info(f"✓ {descripcion}: {zips[0].name}")
    return zips[0]            # Path al zip



def generar_resultados_interactivos(
    base_pid1: str,
    carpeta_pid1: str,
    base_pcp: str,
    base_pid2: str | None = None,
    carpeta_pid2: str | None = None
) -> tuple[Path, dict]:

    carpeta_pcp = "Model PRGdia_Full_Definitivo Solution"
    fecha, periodo_pid = extraer_fecha_y_hora_desde_ruta(base_pid1)
    hini = periodo_pid
    hfin = hini + 48
    

    # Rutas PID1
    path_pid1 = os.path.join(base_pid1, carpeta_pid1)
    zip_pid1 = [f for f in os.listdir(path_pid1) if f.endswith(".zip")]
    if not zip_pid1:
        raise FileNotFoundError(f"No se encontró ningún .zip en {path_pid1}")
    sol_file_pid1 = os.path.join(path_pid1, zip_pid1[0])

    # Rutas PCP
    path_pcp = os.path.join(base_pcp, carpeta_pcp)
    zip_pcp = [f for f in os.listdir(path_pcp) if f.endswith(".zip")]
    if not zip_pcp:
        raise FileNotFoundError(f"No se encontró ningún .zip en {path_pcp}")
    sol_file_pcp = os.path.join(path_pcp, zip_pcp[0])

    # Rutas PID2 (opcional)
    sol_file_pid2 = None
    if base_pid2 and carpeta_pid2:
        path_pid2 = os.path.join(base_pid2, carpeta_pid2)
        zip_pid2 = [f for f in os.listdir(path_pid2) if f.endswith(".zip")]
        if not zip_pid2:
            raise FileNotFoundError(f"No se encontró ningún .zip en {path_pid2}")
        sol_file_pid2 = os.path.join(path_pid2, zip_pid2[0])

    # Carpeta resultados
    base_dir = Path(__file__).parent
    directorio_salida = base_dir / "Resultados"
    directorio_salida.mkdir(parents=True, exist_ok=True)

    # Diccionario de entrada por solución
    solutions_files = {
        "PID1": sol_file_pid1,
        "PID2": sol_file_pid2,
        "PCP": sol_file_pcp,
    }

    results = defaultdict(dict)
    function_names = ["GENTABLES", "GENC", "GENT", "CMG", "BESS"]

    def run_single_query(label, path, function_name):
        is_pcp =  (label == "PCP")
        st_flag = not is_pcp
        hfin_local = 168 if is_pcp else hfin      # 168 h para PCP, 48 h para PIDs
        try:
            if function_name == "GENTABLES":
                return label, function_name, get_generation_tables(
                    sol_file=path, tipo_solucion=label,
                    directorio_salida=directorio_salida,
                    directorio_fecha=base_pid1,
                    hini=hini, hfin=hfin_local,
                    st_schedule=st_flag
                )
            elif function_name == "GENC":
                return label, function_name, get_gen_costs(
                    sol_file=path, tipo_solucion=label,
                    directorio_salida=directorio_salida,
                    hini=hini, hfin=hfin_local,
                    st_schedule=st_flag
                )
            
            elif function_name == "GENT":
                st.write(label, path, sol_file_pcp, base_pid1, hini, hfin)
                return label, function_name, get_total_generation(
                    sol_file=path, tipo_solucion=label, sol_file_pcp=sol_file_pcp,
                    directorio_salida=directorio_salida,
                    directorio_fecha=base_pid1,
                    periodo_pid=periodo_pid,
                    st_schedule=st_flag,
                    hini=hini, hfin=hfin_local,
                    tx_loss=(not is_pcp)
                )
            elif function_name == "CMG":
                return label, function_name, get_cmg(
                    sol_file=path, tipo_solucion=label,
                    directorio_salida=directorio_salida,
                    st_schedule=st_flag,
                    hini=hini, hfin=hfin_local
                )
            elif function_name == "BESS":
                return label, function_name, get_bess(
                    sol_file=path, tipo_solucion=label,
                    directorio_salida=directorio_salida,
                    st_schedule=st_flag,
                    hini=hini, hfin=hfin_local
                )
        except Exception as e:
            print(f"[ERR] {label} – {function_name}: {e}")
            return label, function_name, None

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [
            executor.submit(run_single_query, label, path, func)
            for label, path in solutions_files.items() if path is not None
            for func in function_names
        ]
        for fut in as_completed(futures):
            label, func_name, result = fut.result()
            if result is not None:
                results[label][func_name] = result

    # 2) Valida inputs antes de lanzar hilos --------------------------
    def validar_ruta_carpeta(base: str, carpeta: str) -> Path:
        p = Path(base, carpeta)
        if not p.is_dir():
            raise FileNotFoundError(f"❌ Carpeta no encontrada: {p}")
        zips = list(p.glob("*.zip"))
        if not zips:
            raise FileNotFoundError(f"❌ No hay .zip en {p}")
        return zips[0]          # primer zip

    sol_file_pid1 = validar_ruta_carpeta(base_pid1, carpeta_pid1)
    sol_file_pcp  = validar_ruta_carpeta(base_pcp,  "Model PRGdia_Full_Definitivo Solution")
    sol_file_pid2 = None
    if base_pid2 and carpeta_pid2:
        sol_file_pid2 = validar_ruta_carpeta(base_pid2, carpeta_pid2)

    # 4) Etiqueta idéntica al esquema antiguo -------------------------
    etiqueta = f"{fecha}_{periodo_pid:02d}"   # p.ej. 20250701_01
    output_path = directorio_salida / f"results_{etiqueta}.pkl"
    with output_path.open("wb") as fh:
        pickle.dump(results, fh, protocol=pickle.HIGHEST_PROTOCOL)


    return output_path, results
