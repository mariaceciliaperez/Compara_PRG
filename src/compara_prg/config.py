# src/compara_prg/config.py
from pathlib import Path

# Raíz del repo (…/Compara_PRG)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── Ruta COMPARTIDA (tu carpeta de red). Cambia aquí si algún día se mueve.
SHARED_BASE = Path(r"\\nas-cen1\DPID\Aplicaciones\Nuevo_PRG\Compara_PRG")




RESOURCES_DIR = PROJECT_ROOT / "src" / "compara_prg" / "resources"
GEN_AUXUSE_CSV = RESOURCES_DIR / "Gen_AuxUse.csv"
BESS_DIC_PATH = RESOURCES_DIR  / 'BESS_dict.xlsx' 
NEW_BESS_DIC_PATH = RESOURCES_DIR  / 'Dict_new_BESS.xlsx' 

# results/ compartidos: si existe la red, úsala; si no, cae a local del repo
_shared_results = SHARED_BASE / "data" / "results"
_local_results  = PROJECT_ROOT / "data" / "results"
_data_intermedia = PROJECT_ROOT / "data" / "interim"

RESULTS_DIR = _shared_results if _shared_results.exists() else _local_results
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Salida = mismo lugar
OUTPUT_DIR = RESULTS_DIR
COMMENTS_DIR = RESULTS_DIR.parent / "comments"
COMMENTS_DIR.mkdir(parents=True, exist_ok=True)


# Nombres por defecto de carpetas (PCP/PID)
DEFAULT_PCP_FOLDER = "Model PRGdia_Full_Definitivo Solution"
DEFAULT_PID_FOLDER = "Model Test15d Solution"
DEFAULT_NAME_BASE   = 'DBSEN_PRGDIARIO_PID.xml'


# (opcional) constantes que ya usas en la app
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
THRESHOLD = 0.5
