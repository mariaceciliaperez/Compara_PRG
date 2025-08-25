from Query_general import *

def get_bess(sol_file: str, tipo_solucion: str, directorio_salida: str, st_schedule: bool=True, hini: int=1, hfin: int=48, output_filename: str='Query_BESS.xlsx') -> None:
    """
    Función para obtener y procesar los valores de carga/descarga de baterías a partir de una solución Plexos,
    usando un diccionario con nombres de baterías.

    Args:
        sol_file (str): Archivo de solución .zip de Plexos
        directorio_salida (str): Ruta de salida para el archivo Excel generado
        st_schedule (bool): Si es tipo st_schedule
        hini (int): Periodo inicial
        hfin (int): Periodo final
        output_filename (str): Nombre del archivo de salida
        bess_dict_path (str): Ruta al archivo BESS_dict.xlsx

    Returns:
        None
    """

    bess_dict_path = r"E:\Aplicaciones\Nuevo_PRG\Diccionarios\BESS_dict.xlsx"

    # 1. Cargar diccionario
    bess_dict = pd.read_excel(bess_dict_path, dtype=str).fillna("")
    
    csfrs_names = bess_dict['Nombre_Plexos_CSFRS'].tolist()
    load_names = bess_dict['Nombre_Plexos_Load'].tolist()
    normal_names = bess_dict['Nombre_Plexos'].tolist()
    standalone_names = bess_dict['Nombre_Plexos_standalone'].tolist()
    nombre_pol = bess_dict['Nombre_Pol']

    #Se mapean los datos según su nombre de política
    map_normal = dict(zip(bess_dict['Nombre_Plexos'], nombre_pol))
    map_standalone = dict(zip(bess_dict['Nombre_Plexos_standalone'], nombre_pol))


    #Filtrado de vacíos
    csfrs_names = [x for x in csfrs_names if x != '']
    load_names = [x for x in load_names if x != '']
    normal_names = [x for x in normal_names if x != '']
    standalone_names = [x for x in standalone_names if x != '']

    # 2. Cargar query desde solución
    columns = ['category_name', 'child_name', 'value', 'period_id']
    rename = ['Categoría', 'Nombre_PLEXOS', 'Valor', 'Hora']
    query = query_solution(
            name='bess.csv',
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

    df_pivot = query.pivot(
        values='Valor',
        index=['Categoría', 'Nombre_PLEXOS'],
        on='Hora',
        aggregate_function='first'
    ).fill_null(0)

    df_bat = df_pivot.filter(
        pl.col('Categoría').str.contains(r'Hydro Ficticias'),
    ).drop('Categoría')


    # Detectar columnas de hora automáticamente
    horas = [col for col in df_bat.columns if col != "Nombre_PLEXOS"]


    # 3. CSFRS
    normal_names_csfrs = [name for name in normal_names if "VR1" in name]
    df_csfrs = df_bat.filter(pl.col("Nombre_PLEXOS").is_in(csfrs_names)).with_columns(
        pl.col("Nombre_PLEXOS").replace({k: v for k, v in zip(csfrs_names, normal_names_csfrs)}).alias("Nombre_PLEXOS")
    ).select(["Nombre_PLEXOS"] + horas)


        #Se pasa a nombre de política
    df_csfrs = df_csfrs.with_columns(
        pl.col("Nombre_PLEXOS").map_elements(lambda x: map_normal.get(x, x), return_dtype=pl.Utf8).alias("Nombre_PLEXOS")
    )

    # 4. LOAD y Normal
    df_load = df_bat.filter(pl.col("Nombre_PLEXOS").is_in(load_names)).with_columns(
        pl.col("Nombre_PLEXOS").replace({k: v for k, v in zip(load_names, normal_names)}).alias("Nombre_PLEXOS")
    )

    df_normal = df_bat.filter(
        pl.col("Nombre_PLEXOS").is_in(normal_names) &
        ~pl.col("Nombre_PLEXOS").is_in(standalone_names)
    )

    # 5. Join Normal y Load
    df_merged = df_normal.join(df_load, on="Nombre_PLEXOS", suffix="_load", how="left")

    for h in horas:
        col_load = f"{h}_load"
        if col_load in df_merged.columns:
            df_merged = df_merged.with_columns(
                (pl.col(h) - pl.col(col_load) * 1000).alias(h)
            )

    df_resultado = df_merged.select(["Nombre_PLEXOS"] + horas)

        #Se pasa a nombre de política
    df_resultado = df_resultado.with_columns(
        pl.col("Nombre_PLEXOS").map_elements(lambda x: map_normal.get(x, x), return_dtype=pl.Utf8).alias("Nombre_PLEXOS")
    )

    # 6. PUMPs / Standalone
    df_pump_list = []
    for nombre in standalone_names:
        central = df_bat.filter(pl.col("Nombre_PLEXOS") == nombre)
        if central.is_empty():
            valores_cero = {h: 0.0 for h in horas}
            valores_cero["Nombre_PLEXOS"] = nombre
            central = pl.DataFrame([valores_cero])
        else:
            central = central.select(["Nombre_PLEXOS"] + horas)
        # Reordenar columnas para que Nombre_PLEXOS esté primero
        central = central.select(["Nombre_PLEXOS"] + horas)
        df_pump_list.append(central)

    df_pumps = pl.concat(df_pump_list)

        #Se pasa a nombre de política
    df_pumps = df_pumps.with_columns(
        pl.col("Nombre_PLEXOS").map_elements(lambda x: map_standalone.get(x, x), return_dtype=pl.Utf8).alias("Nombre_PLEXOS")
    )

    # 7. Concatenar resultados
    df_final = df_pumps.vstack(df_csfrs).vstack(df_resultado)

    # 8. Exportar a Excel
    return df_final