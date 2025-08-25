import polars as pl
from Query_general import *

def get_generation_tables(sol_file: str, tipo_solucion: str, directorio_salida: str, directorio_fecha: str, st_schedule: bool=True, hini: int=1, hfin: int=48) -> None:
    """
    Función query que se encarga de obtener los diversos archivos de generación por tipo de generación y
    les suma el valor de su auto consumo (Gen_AuxUse)
    
    Args:

        sol_file (str): String que entrega el nombre del archivo de solución .zip de Plexos
        directorio_salida (str): String que recibe la ruta donde se generan los archivos de salida
        directorio_fecha (str): ruta hacia la carpeta de la fecha para buscar el archivo gen_aux_use
        st_schedule (boolean): Booleano que indica si es tipo st_schedule o no
        hini (int): Número entero que indica el periodo inicial del cuál se desean extraer los datos
        hfin (int): Número entero que indica el periodo final del cual se desean extraer los datos

    Returns:

        None: El código no posee ningun return
    """
        
    columns = ['category_name','child_name','value','period_id']
    rename = ['Categoría','Nombre_PLEXOS','Gen_Neta','Hora']

   
    query = query_solution(
        name='tables.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Generators',
        property='Generation',
        columns=columns,
        rename=rename,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )
    # 1. Leer archivo
    auxuse = pl.read_csv(r'E:\Aplicaciones\Nuevo_PRG\Compara_PRG\Diccionarios\Gen_AuxUse.csv')

    # 2. Renombrar columnas archivo Gen_AuxUse
    auxuse = auxuse.rename({
        'Name': 'Nombre_PLEXOS',
        'Value': 'Gen_Aux_Use'
    })

    # 3. Hacer join
    df = query.join(auxuse, on='Nombre_PLEXOS', how='left')

    # 4. Rellenar nulos en 'Gen_Aux_Use' con 0
    df = df.with_columns(
        pl.col('Gen_Aux_Use').fill_null(0)
    )

    # 5. Crear columna 'Gen_Bruta' como suma condicional
    df = df.with_columns(
        (pl.col('Gen_Neta') + pl.col('Gen_Aux_Use') * (pl.col('Gen_Neta') != 0)).alias('Gen_Bruta')
    )

    # 6. Filtrar columnas
    df = df.select(['Categoría', 'Nombre_PLEXOS', 'Gen_Bruta', 'Hora'])

    # 7. Redondear
    df = df.with_columns(
        pl.col('Gen_Bruta').round(1)
    )

    # 8. Pivot table (reshape)
    df_pivot = df.pivot(
        values='Gen_Bruta',
        index=['Categoría', 'Nombre_PLEXOS'],
        on='Hora',
        aggregate_function='first'  # ya que no hay agregación real
    ).fill_null(0)

    # 9. Se filtran las centrales por su categoría

    #Centrales Hydro
    df_hydro = df_pivot.filter(
    pl.col('Categoría').str.contains(r'Hydro Gen Group A')
    ).drop('Categoría')

    #Baterías
    df_bess = df_pivot.filter(
    pl.col('Categoría').str.contains(r'Hydro Ficticias')
    ).drop('Categoría')

    #Térmicas
    df_thermal = df_pivot.filter(
    pl.col('Categoría').str.contains(r'Thermal')
    ).drop('Categoría')

    #Solares
    df_solar = df_pivot.filter(
    pl.col('Categoría').str.contains(r'Solar')
    ).drop('Categoría')

    #Eólicas
    df_wind = df_pivot.filter(
    pl.col('Categoría').str.contains(r'Wind')
    ).drop('Categoría')

    return df_hydro, df_bess, df_thermal, df_solar, df_wind

