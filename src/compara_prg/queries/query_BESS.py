from compara_prg.io.query_general import *
from compara_prg.config import BESS_DIC_PATH, NEW_BESS_DIC_PATH


dict_bess = pd.read_excel(NEW_BESS_DIC_PATH, sheet_name="Hoja1")
dict_bess = dict_bess.astype(str)
dict_bess = pl.from_pandas(dict_bess)

def get_bess(sol_file: str, tipo_solucion: str, directorio_salida: str, st_schedule: bool=True, hini: int=1, hfin: int=4) -> None:
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

    #Obtengo los datos de los nuevos BESS
    inyeccion_datos, df_charge_gen, df_charge_grid, perfil_completo = Query_new_BESS(sol_file, tipo_solucion, st_schedule, hini, hfin)

    # 1. Cargar diccionario
    bess_dict = pd.read_excel(BESS_DIC_PATH, dtype=str).fillna("")
    
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
    
    # query = query_solution(sol_file, 'Generators', 'Generation', columns, rename, st_schedule, hini, hfin)
    df_pivot = inyeccion_datos.pivot(
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

    #Se intenta encontrar los datos de pumpload en caso de que existan, caso contrario es un archivo vacío

    # Inicializar df_bat_pumpload vacío con las mismas columnas que df_bat
    df_bat_pumpload = pl.DataFrame(schema={"Nombre_PLEXOS": pl.Utf8, **{h: pl.Float64 for h in horas}})

    try:
        # query_pumpload = query_solution(sol_file,'Generators','PumpLoad',columns,rename,st_schedule,hini,hfin)
        query_pumpload = query_solution(
            name='GeneratorPumpLoad.csv',
            label=tipo_solucion,
            sol_file=sol_file,
            collection='Generators',
            property='PumpLoad',
            columns=columns,
            rename=rename,
            st_schedule=st_schedule,
            hini=hini,
            hfin=hfin
        )

        df_pivot_pumpload = query_pumpload.pivot(
            values='Valor',
            index=['Categoría', 'Nombre_PLEXOS'],
            on='Hora',
            aggregate_function='first'
        ).fill_null(0)

        df_bat_pumpload = df_pivot_pumpload.filter(
            pl.col('Categoría').str.contains(r'Hydro Ficticias'),
        ).drop('Categoría')

    except Exception:
        print('No se encontraron datos de PumpLoad para baterías stand alone en ST')


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
        central_gen = df_bat.filter(pl.col("Nombre_PLEXOS") == nombre)
        if central_gen.is_empty():
            valores_gen = {h: 0.0 for h in horas}
            valores_gen["Nombre_PLEXOS"] = nombre
            central_gen = pl.DataFrame([valores_gen])
        else:
            central_gen = central_gen.select(["Nombre_PLEXOS"] + horas)
            
        # Reordenar columnas para que Nombre_PLEXOS esté primero
        central_gen = central_gen.select(["Nombre_PLEXOS"] + horas)

        # Solo restar si df_bat_pumpload tiene datos y la central está incluida
        if not df_bat_pumpload.is_empty():
            central_load = df_bat_pumpload.filter(pl.col("Nombre_PLEXOS") == nombre)
            if not central_load.is_empty():
                central_load = central_load.select(["Nombre_PLEXOS"] + horas)
                central_gen = central_gen.with_columns([
                    (pl.col(h) - central_load[0, h]).alias(h) for h in horas
                ])

        df_pump_list.append(central_gen)

    df_pumps = pl.concat(df_pump_list)

        #Se pasa a nombre de política
    df_pumps = df_pumps.with_columns(
        pl.col("Nombre_PLEXOS").map_elements(lambda x: map_standalone.get(x, x), return_dtype=pl.Utf8).alias("Nombre_PLEXOS")
    )



    # 7. Concatenar resultados
    df_final = df_pumps.vstack(df_csfrs).vstack(df_resultado)
    df_final = df_final.vstack(perfil_completo)

    return df_final





def obtener_datos(sol_file, tipo_solucion: str, st_schedule, hini, hfin):

    # Query carga
    columns_carga = ['category_name', 'child_name', 'property_name','value', 'period_id']
    rename_carga = ['Categoría', 'Nombre_PLEXOS', 'Propiedad' ,'Valor', 'Hora']
    # carga_bateria = query_solution(sol_file, 'Batteries', 'Charging', columns_carga, rename_carga, st_schedule, hini, hfin)
    carga_bateria = query_solution(
        name='carga_bateria.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Batteries',
        property='Charging',
        columns=columns_carga,
        rename=rename_carga,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )


    # Query Inyección generador
    columns_inyeccion = ['category_name', 'child_name', 'property_name','value', 'period_id']
    rename_inyeccion = ['Categoría', 'Nombre_PLEXOS', 'Propiedad' ,'Valor', 'Hora']
    # inyeccion_generador = query_solution(sol_file, 'Generators', 'Generation', columns_inyeccion, rename_inyeccion, st_schedule, hini, hfin)

    inyeccion_generador = query_solution(
        name='inyeccion_generador.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Generators',
        property='Generation',
        columns=columns_inyeccion,
        rename=rename_inyeccion,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )


    # Query flujos
    columns_flujos = ['category_name', 'child_name', 'property_name','value', 'period_id']
    rename_flujos = ['Categoría', 'Nombre_PLEXOS', 'Propiedad' ,'Valor', 'Hora']
    # flujo = query_solution(sol_file, 'Lines', 'Flow', columns_flujos, rename_flujos, st_schedule, hini, hfin)

    flujo = query_solution(
        name='flujo.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Lines',
        property='Flow',
        columns=columns_flujos,
        rename=rename_flujos,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )


    #### 1. CARGA BATERÍA
    nombres_baterias = dict_bess["Nombre"]
    df_carga_bateria = (
        carga_bateria
        .filter(pl.col("Propiedad") == "Charging")
        .filter(pl.col("Nombre_PLEXOS").is_in(nombres_baterias))
        .pivot(index="Nombre_PLEXOS", on="Hora", values="Valor", aggregate_function="first")
        .rename({"Nombre_PLEXOS": "Nombre bateria"})
    )
    # Asegurar que todas las baterías del diccionario estén presentes
    df_carga_bateria = dict_bess.select(pl.col("Nombre").alias("Nombre bateria")).join(
        df_carga_bateria, on="Nombre bateria", how="left"
    ).fill_null(0)

    #### 2. INYECCIÓN PARQUE
    # Filtrar solo nombres válidos desde el diccionario
    inyeccion_dict = dict_bess.select(["Nombre", "Central renovable"]).filter(pl.col("Central renovable") != "-")

    # Unir con datos de inyección
    df_inyeccion_parque = (
        inyeccion_generador
        .filter(pl.col("Propiedad") == "Generation")
        .join(inyeccion_dict, left_on="Nombre_PLEXOS", right_on="Central renovable", how="inner")
        .pivot(index="Nombre", on="Hora", values="Valor", aggregate_function="first")
        .rename({"Nombre": "Nombre bateria"})
    )

    # Detectar columnas de hora automáticamente
    horas = [c for c in df_carga_bateria.columns if c != "Nombre bateria"]
    df_inyeccion_parque = dict_bess.select(pl.col("Nombre").alias("Nombre bateria")).join(
        df_inyeccion_parque, on="Nombre bateria", how="left"
    )
    for h in horas:
        if h not in df_inyeccion_parque.columns:
            df_inyeccion_parque = df_inyeccion_parque.with_columns(pl.lit(0).alias(h))
    df_inyeccion_parque = df_inyeccion_parque.fill_null(0)


    #### 3. FLUJO LÍNEAS
    lineas_dict = dict_bess.select(["Nombre", "Linea"]).filter(pl.col("Linea") != "-")

    # Unir con datos de flujo
    df_flujo_linea = (
        flujo
        .filter(pl.col("Propiedad") == "Flow")
        .join(lineas_dict, left_on="Nombre_PLEXOS", right_on="Linea", how="inner")
        .pivot(index="Nombre", on="Hora", values="Valor", aggregate_function="first")
        .rename({"Nombre": "Nombre bateria"})
    )

    # Rellenar con ceros para las baterías faltantes y asegurar todas las horas
    df_flujo_linea = dict_bess.select(pl.col("Nombre").alias("Nombre bateria")).join(
        df_flujo_linea, on="Nombre bateria", how="left"
    )
    for h in horas:
        if h not in df_flujo_linea.columns:
            df_flujo_linea = df_flujo_linea.with_columns(pl.lit(0).alias(h))
    df_flujo_linea = df_flujo_linea.fill_null(0)

    return inyeccion_generador,df_carga_bateria, df_inyeccion_parque, df_flujo_linea



#Función que genera los archivos de charge grid y charge gen
def charge_gen_grid(df_carga, df_inyeccion, df_flujo):

    columnas_horas = [col for col in df_carga.columns if col != "Nombre bateria"]

    ### --- Parte 1: charge_gen ---
    columnas_charge_gen = [pl.col("Nombre bateria")]
    
    for col in columnas_horas:
        expr = (
            pl.when(
                (df_carga[col] > 0) &
                (df_inyeccion[col] > 0) &
                (df_flujo[col] >= 0)
            )
            .then(df_carga[col])
            .when(
                (df_carga[col] > 0) &
                (df_inyeccion[col] > 0) &
                (df_inyeccion[col] < df_carga[col]) &
                (df_flujo[col] < 0)
            )
            .then(df_inyeccion[col].abs())
            .otherwise(0.0)
            .alias(col)
        )
        columnas_charge_gen.append(expr)

    df_charge_gen = df_carga.select(columnas_charge_gen)

    ### --- Parte 2: charge_grid ---
    # Preparar el dict con columnas necesarias
    df_dict_bess = dict_bess.select([
        pl.col("Nombre").alias("Nombre bateria"),
        pl.col("Carga_red")
    ])

    # Hacemos join para tener la columna "Carga_red"
    df_carga_flag = df_carga.join(df_dict_bess, on="Nombre bateria", how="left")
    
    columnas_charge_grid = [pl.col("Nombre bateria")]

    for col in columnas_horas:
        carga = df_carga[col]
        inyeccion = df_inyeccion[col]
        flujo = df_flujo[col]

        expr = (
            pl.when(df_carga_flag["Carga_red"] == "Si")
            .then(carga)
            .when((carga > 0) & (inyeccion == 0) & (flujo < 0))
            .then(carga)
            .when((carga > 0) & (inyeccion > 0) & (inyeccion < carga) & (flujo < 0))
            .then((carga - inyeccion).abs())
            .otherwise(0.0)
            .alias(col)
        )
        columnas_charge_grid.append(expr)

    df_charge_grid = df_carga_flag.select(columnas_charge_grid)

    return df_charge_gen, df_charge_grid


def obtener_carga_gen_grid(sol_file, tipo_solucion: str, st_schedule, hini, hfin):
    #Primero se llama a la función que hace las consultas
    inyeccion_datos,df_carga_bateria, df_inyeccion_parque, df_flujo_linea = obtener_datos(sol_file, tipo_solucion, st_schedule, hini, hfin)

    #Luego se generan los archivo charge_gen y charge_grid según las reglas
    df_charge_gen, df_charge_grid = charge_gen_grid(df_carga_bateria, df_inyeccion_parque, df_flujo_linea)

    return inyeccion_datos, df_charge_gen, df_charge_grid


def Query_new_BESS(sol_file, tipo_solucion: str,st_schedule, hini, hfin):

    #Primero se obtienen los dos dataframes: carga de red y carga de generador
    inyeccion_datos, df_charge_gen, df_charge_grid = obtener_carga_gen_grid(sol_file, tipo_solucion, st_schedule, hini, hfin)

    #Ahora se debe de obtener el perfil de generación de las bess
    columns = ['child_name', 'value', 'period_id']
    rename = ['Nombre bateria','Valor', 'Hora']
    #generacion = query_solution(sol_file, 'Batteries', 'Generation', columns, rename, True, hini, hfin)
    generacion = query_solution(
        name='generacion.csv',
        label=tipo_solucion,
        sol_file=sol_file,
        collection='Batteries',
        property='Generation',
        columns=columns,
        rename=rename,
        st_schedule=st_schedule,
        hini=hini,
        hfin=hfin
    )

    #Se pivotea la tabla
    generacion = generacion.pivot(
        values="Valor",
        index="Nombre bateria",
        on="Hora"
    ).fill_null(0)

    #Ahora se deben de entregar 3 tablas, una con el perfil completo de la BESS, una solo con carga de la red 
    #y una tercera solo con carga del parque generador asociado a la batería

    # Asegurar mismo tipo de datos
    dfs = [df_charge_gen, df_charge_grid, generacion]
    dfs = [df.cast({col: pl.Float64 for col in df.columns if col != "Nombre bateria"}) for df in dfs]

    # Unir los tres dataframes por outer join para no perder nombres
    df_all = dfs[0].join(dfs[1], on="Nombre bateria", how="full", suffix="_grid") \
                .join(dfs[2], on="Nombre bateria", how="full", suffix="_desc") \
                .fill_null(0)

    # Identificar columnas
    cols_desc = [c for c in generacion.columns if c != "Nombre bateria"]

    # Calcular generacion - (carga_gen + carga_grid)
    perfil_completo = df_all.select(
        ["Nombre bateria"] +
        [
            (
                pl.col(col + "_desc") -
                (pl.col(col) + pl.col(col + "_grid"))
            ).alias(col)
            for col in cols_desc
        ]
    )

    def renombrar_baterias(df: pl.DataFrame, dict_bess: pl.DataFrame) -> pl.DataFrame:
        return ((
            df.join(
                dict_bess.select(["Nombre", "Nombre Politica"]),
                left_on="Nombre bateria",
                right_on="Nombre",
                how="inner"
            )
            .with_columns(
                pl.col("Nombre Politica").alias("Nombre bateria")
            )
            .drop("Nombre Politica")
        ).rename({"Nombre bateria": "Nombre_PLEXOS"}))
    
    df_charge_gen = renombrar_baterias(df_charge_gen, dict_bess)
    df_charge_grid = renombrar_baterias(df_charge_grid, dict_bess)
    perfil_completo = renombrar_baterias(perfil_completo, dict_bess)

    return inyeccion_datos, df_charge_gen, df_charge_grid, perfil_completo