import os
import re
from typing import Tuple, Optional

def extraer_fecha_y_hora_desde_ruta(ruta: str) -> Tuple[str, int]:
    match = re.search(r'PID_(\d{8})_(\d{2})', ruta)
    if match:
        fecha = match.group(1)
        hora = int(match.group(2))
        return fecha, hora
    else:
        raise ValueError(f"No se pudo extraer fecha y hora desde la ruta: {ruta}")

def rutas_entrada() -> Tuple[str, Optional[str], str, str, str, int, str]:
    print("== Comparación de PRGs ==")

    # --- PID1 ---
    base_pid1 = input("Ruta base de carpeta PID1: ").strip('"').strip()
    carpeta_pid1 = input("Nombre carpeta del modelo PID1 (ej: Model Test15d Solution_auto): ").strip()
    path_pid1 = os.path.join(base_pid1, carpeta_pid1)
    zip_pid1 = [f for f in os.listdir(path_pid1) if f.endswith(".zip")]
    if not zip_pid1:
        raise FileNotFoundError(f"No se encontró ningún archivo .zip en: {path_pid1}")
    sol_file_pid1 = os.path.join(path_pid1, zip_pid1[0])

    # Extraer fecha/hora desde PID1 (sigue siendo nuestra referencia principal)
    fecha, periodo_pid = extraer_fecha_y_hora_desde_ruta(base_pid1)

    # --- PCP ---
    base_pcp = input("Ruta base de carpeta PCP: ").strip('"').strip()
    carpeta_pcp = "Model PRGdia_Full_Definitivo Solution"
    path_pcp = os.path.join(base_pcp, carpeta_pcp)
    zip_pcp = [f for f in os.listdir(path_pcp) if f.endswith(".zip")]
    if not zip_pcp:
        raise FileNotFoundError(f"No se encontró ningún archivo .zip en: {path_pcp}")
    sol_file_pcp = os.path.join(path_pcp, zip_pcp[0])

    # --- PID2 (opcional) ---
    incluir_pid2 = input("¿Desea incluir una segunda carpeta PID2 para comparar? (s/n): ").strip().lower()
    sol_file_pid2 = None
    if incluir_pid2 == 's':
        base_pid2 = input("Ruta base de carpeta PID2: ").strip('"').strip()
        carpeta_pid2 = input("Nombre carpeta del modelo PID2: ").strip()
        path_pid2 = os.path.join(base_pid2, carpeta_pid2)
        zip_pid2 = [f for f in os.listdir(path_pid2) if f.endswith(".zip")]
        if not zip_pid2:
            raise FileNotFoundError(f"No se encontró ningún archivo .zip en: {path_pid2}")
        sol_file_pid2 = os.path.join(path_pid2, zip_pid2[0])

    # --- Salida ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directorio_salida = os.path.join(base_dir, 'Resultados')
    os.makedirs(directorio_salida, exist_ok=True)

    ruta_prg = os.path.join(directorio_salida, f'Comparacion_{fecha}_{periodo_pid:02}.xlsx')

    return sol_file_pid1, sol_file_pid2, sol_file_pcp, directorio_salida, base_pid1, periodo_pid, ruta_prg
