import polars as pl
from compara_prg.io.query_general import *
from compara_prg.config import GEN_AUXUSE_CSV

def get_total_generation(sol_file: str, 
                         tipo_solucion: str,
                         directorio_salida: str, 
                         directorio_fecha: str, 
                         periodo_pid: int, 
                         st_schedule: bool=True, 
                         hini: int=1, 
                         hfin: int=48, 
                         output_filename: str='Total_gen.xlsx', 
                         tx_loss: bool = False) -> None:
    """
    Función query que se encarga de obtener los valores de los la generación total en sus componentes,
    del modelo Plexos y entregarlos en el archivo Total_gen.xlsx que se genera en la carpeta de resultados
    
    Args:

        sol_file (str): String que entrega el nombre del archivo de solución .zip de Plexos
        directorio_salida (str): String que recibe la ruta donde se genera el archivo Total_gen.xlsx
        directorio_fecha (str): string que apunta a la carpeta del día
        periodo_pid (int): entero que entrega el valor del periodo pid a trabajar
        st_schedule (boolean): Booleano que indica si es tipo st_schedule o no
        hini (int): Número entero que indica el periodo inicial del cuál se desean extraer los datos
        hfin (int): Número entero que indica el periodo final del cual se desean extraer los datos
        output_filename (str): String que indica el nombre del archivo de salida de la función
        tx_loss (bool): Booleano que define si se estan considerandoa las pérdidas de la pcp o pid (False = pcp, True = PID)

    Returns:
    
        None: El código no posee ningun return
    """
    auxuse = pl.read_csv(GEN_AUXUSE_CSV)
    columns = ['child_name','value','period_id']
    rename_generation = ['Nombre_PLEXOS','Gen_Neta','Hora']
    rename_loss = ['Nombre_PLEXOS', 'Loss', 'Hora']

    query_generation = query_solution(
            name='gentotal.csv',
            label=tipo_solucion,
            sol_file=sol_file,
            collection='Generators',
            property='Generation',
            columns=columns,
            rename=rename_generation,
            st_schedule=st_schedule,
            hini=hini,
            hfin=hfin)


    query_loss = query_solution(
                name='loss.csv',
                label=tipo_solucion,
                sol_file=sol_file,  #Esto debería cambiar a futuro si es que las PID calculan las pérdidas
                collection='Lines',
                property='Loss',
                columns=columns,
                rename=rename_loss,
                st_schedule=tx_loss,
                hini=hini,
                hfin=hfin
            )


    # 2) Construir LOSSES en formato ancho (1 fila "Pérdidas [MWh]" + columnas por hora)
    #    Nota: losses_long viene con columnas ['Nombre_PLEXOS','Loss','Hora']
    # query_loss0 = (
    #     query_loss
    #     .group_by("Hora")
    #     .agg(pl.col("Loss").sum().alias("Pérdidas [MWh]"))
    #     .sort("Hora")
    # )
    # horas = [str(h) for h in query_loss0["Hora"].to_list()]

    # query_loss0 = (
    #     query_loss0
    #     .select("Pérdidas [MWh]")
    #     .transpose(column_names=horas)
    #     .with_columns(pl.lit("Pérdidas [MWh]").alias("Hora"))
    #     .select(["Hora", *horas])
    # )
  

    auxuse = auxuse.rename({
    'Name': 'Nombre_PLEXOS',
    'Value': 'Gen_Aux_Use'
    })

    # Join con consumos propios
    df = query_generation.join(auxuse, on='Nombre_PLEXOS', how='left')

    # Rellenar Gen_Aux_Use con 0 si hay nulos
    df = df.with_columns([
        pl.col('Gen_Aux_Use').fill_null(0)
    ])


    # Calcular Gen_Bruta (solo suma si Gen_Neta != 0)
    df = df.with_columns([
        (pl.col('Gen_Neta') + pl.col('Gen_Aux_Use') * (pl.col('Gen_Neta') != 0)).alias('Gen_Bruta')
    ])

    # Recalcular Gen_Aux_Use como diferencia entre Gen_Bruta y Gen_Neta
    df = df.with_columns([
        (pl.col('Gen_Bruta') - pl.col('Gen_Neta')).alias('Gen_Aux_Use')
    ])

    #Se suman los valores por hora
    df = df.group_by('Hora').agg([
        pl.all().sum()
    ]).drop('Nombre_PLEXOS').sort('Hora')

    query_loss2 = query_loss.group_by('Hora').agg([
        pl.all().sum()
    ]).drop('Nombre_PLEXOS').sort('Hora')

    df_final = df.join(query_loss2, on='Hora', how='left')

    # Calcular Gen_Neta
    df_final = df_final.with_columns([
        (pl.col('Gen_Neta') - pl.col('Loss').fill_null(0)).alias('Gen_Neta')
    ])

    df_final = df_final.rename({
    'Gen_Neta': 'Demanda Total [MWh]',
    'Gen_Aux_Use': 'Consumos Propios [MWh]',
    'Gen_Bruta': 'Generación Total [MWh]',
    'Loss': 'Pérdidas [MWh]'
    })

    # Suponiendo que df_final es tu DataFrame original
    horas = df_final["Hora"].to_list()
    nombres_filas = df_final.drop("Hora").columns  # guardamos los nombres de las variables

    # Transponer y agregar columna con nombres de variables
    df_transpuesto = (
        df_final.drop("Hora")
        .transpose(column_names=[str(h) for h in horas])
        .with_columns([
            pl.Series("Hora", nombres_filas)  # agregamos los nombres como una columna adicional
        ])
        .select(["Hora", *[str(h) for h in horas]])  # reorganizamos columnas si quieres que 'variable' quede al inicio
    )

    return df_transpuesto, query_loss