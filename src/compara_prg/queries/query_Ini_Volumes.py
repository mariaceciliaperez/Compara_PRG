from compara_prg.io.query_general import *
from compara_prg.io.FUNCCDEC_CDEC import *

def get_ini_volumes(sol_file: str, tipo_solucion: str, directorio_salida: str, st_schedule: bool=True, hini: int=1, hfin: int=48, output_filename: str='Emb_Ini_Vol.xlsx') -> None:
    """
    Función query que se encarga de obtener los valores de las iniciales de las cotas de los embalses
    del modelo Plexos y entregarlos en el archivo Emb_Ini_Vol.xlsx que se genera en la carpeta de resultados
    
    Args:

        sol_file (str): String que entrega el nombre del archivo de solución .zip de Plexos
        directorio_salida (str): String que recibe la ruta donde se genera el archivo Emb_Ini_Vol.xlsx
        st_schedule (boolean): Booleano que indica si es tipo st_schedule o no
        hini (int): Número entero que indica el periodo inicial del cuál se desean extraer los datos
        hfin (int): Número entero que indica el periodo final del cual se desean extraer los datos
        output_filename (str): String que indica el nombre del archivo de salida de la función

    Returns:
    
        None: El código no posee ningun return
    """
    columns = ['child_name','value','period_id']
    rename = ['Nombre_PLEXOS','Volumen','Hora']

    query = query_solution(
        name='bess.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Storages',
        property='InitialVolume',
        columns=columns,
        rename=rename,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )


    f_conv = 0.0864

    # Paso 1: Agregar una nueva columna 'Cota' usando apply_row
    df = query.with_columns([
    pl.struct(['Nombre_PLEXOS', 'Volumen']).map_elements(
        lambda row: cot_embalse(row['Nombre_PLEXOS'], row['Volumen'] * f_conv),
        return_dtype=pl.Float64
    ).alias('Cota')
    ])
    
    # Paso 2: Pivoteo horario
    df_pivot = df.pivot(
    values='Cota',
    index='Nombre_PLEXOS',
    on='Hora',
    aggregate_function='first'
    ).fill_null(0)

    # Paso 3: Se filtran las filas que poseen solo valores -1

    columnas_horas = [col for col in df_pivot.columns if col != 'Nombre_PLEXOS']

    df_bool = df_pivot[columnas_horas] == -1

    df_bool_pandas= df_bool.to_pandas()

    indices_menos_1 = df_bool_pandas[df_bool_pandas.all(axis=1)].index.tolist()

    df_pivot = df_pivot.to_pandas()
    df_pivot = df_pivot.drop(indices_menos_1)
    df_pivot = pl.from_pandas(df_pivot)

    return df_pivot