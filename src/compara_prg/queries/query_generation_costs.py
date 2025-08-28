import polars as pl
from compara_prg.io.query_general import *

def get_gen_costs(sol_file: str,  tipo_solucion: str,directorio_salida: str, st_schedule: bool=True, hini: int=1, hfin: int=48, output_filename: str='Gen_costs.xlsx') -> None:
    """
    Función query que se encarga de obtener los valores de los costos de operación, costos de encendido/detención
     y los costos totales de la operación del modelo Plexos y entregarlos en el archivo Gen_costs.xlsx que se 
     genera en la carpeta de resultados
    
    Args:

        sol_file (str): String que entrega el nombre del archivo de solución .zip de Plexos
        directorio_salida (str): String que recibe la ruta donde se genera el archivo Gen_costs.xlsx
        st_schedule (boolean): Booleano que indica si es tipo st_schedule o no
        hini (int): Número entero que indica el periodo inicial del cuál se desean extraer los datos
        hfin (int): Número entero que indica el periodo final del cual se desean extraer los datos
        output_filename (str): String que indica el nombre del archivo de salida de la función

    Returns:
    
        None: El código no posee ningun return
    """
    columns = ['property_name','child_name','value','period_id']
    rename = ['Propiedad','Nombre_PLEXOS','Costo','Hora']
    query = query_solution(
        name='gencost.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Generators',
        property=['GenerationCost', 'Start&ShutdownCost', 'TotalGenerationCost'],
        columns=columns,
        rename=rename,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin,
        multiple=True
    )

    query = query.with_columns(
    (pl.col('Costo') / 1000).alias('Costo')
    )

    df_pivot = query.pivot(
    values="Costo",
    index="Propiedad",
    on="Hora",
    aggregate_function="sum"
    )

        # Diccionario de reemplazo
    reemplazos = {
        "Generation Cost": "Costos Operación",
        "Start & Shutdown Cost": "Costos Encendido/Detención",
        "Total Generation Cost": "Costos Totales [kUSD]"
    }

    # Aplicar reemplazo
    df_pivot = df_pivot.with_columns(
        pl.col("Propiedad").replace(reemplazos).alias("Propiedad")
    )

    return df_pivot