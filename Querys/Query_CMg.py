import polars as pl
from Query_general import *

def get_cmg(sol_file: str, tipo_solucion: str, directorio_salida: str, st_schedule: bool=True, hini: int=1, hfin: int=48) -> None:
    """
    Función query que se encarga de obtener los valores de los costos marginales las líneas de trasnmisión
    del modelo Plexos y entregarlos en el archivo Nod_CMg.xlsx que se genera en la carpeta de resultados
    
    Args:

        sol_file (str): String que entrega el nombre del archivo de solución .zip de Plexos
        directorio_salida (str): String que recibe la ruta donde se genera el archivo Nod_CMg.xlsx
        st_schedule (boolean): Booleano que indica si es tipo st_schedule o no
        hini (int): Número entero que indica el periodo inicial del cuál se desean extraer los datos
        hfin (int): Número entero que indica el periodo final del cual se desean extraer los datos

    Returns:
    
        None: El código no posee ningun return
    """

    columns = ['child_name','value','period_id']
    rename = ['Nombre_PLEXOS','CMg','Hora']

    query = query_solution(
        name='cmg.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Nodes',
        property='Price',
        columns=columns,
        rename=rename,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )

    #Se pivotea la tabla
    pivoted = query.pivot(
        values="CMg",
        index="Nombre_PLEXOS",
        on="Hora"
    ).fill_null(0)

    quillota = pivoted.filter(pl.col('Nombre_PLEXOS') == 'Quillota220')

    quillota = quillota.with_columns(
        pl.when(pl.col("Nombre_PLEXOS") == "Quillota220")
        .then(pl.lit("Costo Marginal Quillota 220 kV"))
        .otherwise(pl.col("Nombre_PLEXOS"))
        .alias("Nombre_PLEXOS")
    )
    return pivoted