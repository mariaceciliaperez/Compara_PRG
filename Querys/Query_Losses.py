# losses_utils.py
from __future__ import annotations
import polars as pl
from typing import Iterable, Dict, Any, Optional
from Query_general import query_solution

def get_losses(
    sol_file: str,
    tipo_solucion: str,
    sol_file_pcp: str,
    directorio_salida: str,
    directorio_fecha: str,
    periodo_pid: int,
    st_schedule: bool = True,
    hini: int = 1,
    hfin: int = 48,
    output_filename: str = "Total_gen.xlsx",
    tx_loss: bool = False,
) -> pl.DataFrame:
    """
    Obtiene las pérdidas desde solución PCP (por defecto) o PID (si tx_loss=True).
    Devuelve formato *largo*: ['Nombre_PLEXOS','Loss','Hora'].
    """
    columns = ["child_name", "value", "period_id"]
    rename_loss = ["Nombre_PLEXOS", "Loss", "Hora"]

    # Fuente de datos: por defecto PCP; si tx_loss=True, usa sol_file (PID)
    sol_src = sol_file if tx_loss else sol_file_pcp

    df = query_solution(
        name="loss.csv",
        label=tipo_solucion,
        sol_file=sol_src,
        collection="Lines",
        property="Loss",
        columns=columns,
        rename=rename_loss,
        st_schedule=st_schedule,   # deja tu lógica actual
        hini=hini,
        hfin=hfin,
    )
    return df