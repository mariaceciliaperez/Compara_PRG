#Se importan librerías para la consulta
import polars as pl
import pandas as pd
import os, sys, clr
import time

sys.path.append('C:/Program Files/Energy Exemplar/PLEXOS 10.0 API')
clr.AddReference('PLEXOS_NET.Core')
clr.AddReference('EEUTILITY')
clr.AddReference('EnergyExemplar.PLEXOS.Utility')

from PLEXOS_NET.Core import *
from EEUTILITY.Enums import *
from EnergyExemplar.PLEXOS.Utility.Enums import *

def generar_propiedades(sol_file: str, campos: list, collection:str, prefix: int='System') -> str:
    """
    Función auxiliar que permite concatenar strings de manera que se puedan ingresar
    dentro de una misma consulta de Plexos

    Args:
    
        sol_file (str): ruta al archivo de solución de Plexos
        campos (list): corresponde a la lista de propertys a concatenar
        collection (str): corresponde a la lista
        prefix (str): define el prefijo al cual se realizara la consulta de PLEXOS (lo que va antes de collection)

    Returns:
        
        String: Entrega la concatenación del string para la consulta de Plexos

    """

    # Create a PLEXOS solution file object and load the solution
    sol = Solution()

    if not os.path.exists(sol_file):
        print('No such file')
        exit()
        
    sol.Connection(sol_file)
    properties = sol.FetchAllPropertyEnums()
    expresiones = [
        str(properties[f"{prefix}{collection}.{campo}"]) for campo in campos
    ]
    return ','.join(expresiones)



def query_solution(name, 
                   label: str,
                   sol_file: str,
                   collection: str,
                   property: str,
                   columns: list[str],
                   rename: list[str],
                   st_schedule: bool=True,
                   hini: int=1,
                   hfin: int=48,
                   multiple: bool=False,
                   prefix: str='System') -> pl.DataFrame:
    """
    Query o consulta general que permite obtener información para la collection 
    y property especificada

    Args:

        sol_file (str): corresponde a la ruta al archivo de solución a consultar
        collection (str): es la collection de la solución a consultar (ej:generators, Nodes, etc)
        property (str): es la property de la solución a consultar (ej:Generation, price, etc)
        columns (list): nombres de las columnas a extraer desde Plexos
        rename (list): nuevos nombres que tendran las columnas extraídas
        st_schedule (boolean): booleano que especifica si se está trabajando con ST o MT (True=ST, False=MT)
        hini (int): hora de inicio de la consulta
        hfin (int): hora de fin de la consulta
        multiple (bool): indica si se requieren consultar varias propiedades para la misma collection
        prefix (str): define el prefijo al cual se realizara la consulta de PLEXOS (lo que va antes de collection)

    Returns:

        dataframe: dataframe con los datos solicitados sin filtrar
    """
    
    # Create a PLEXOS solution file object and load the solution
    sol = Solution()

    if not os.path.exists(sol_file):
        print(sol_file)
        print('No such file')
        #exit()
        
    sol.Connection(sol_file)

    collections = sol.FetchAllCollectionIds()
    properties = sol.FetchAllPropertyEnums()
    
    if multiple:
        propiedad = generar_propiedades(sol_file,property,collection)
    else:
        propiedad = str(properties[f"{prefix}{collection}.{property}"])

    rename_map = {"gentotal.csv": f"gentotal{label}.csv",
                  "gencost.csv":  f"gencost{label}.csv",
                  "bess.csv":     f"bess{label}.csv",
                  "pumpload.csv": f"pumpload{label}.csv",
                  "cmg.csv":      f"cmg{label}.csv",
                  "tables.csv":   f"tables{label}.csv",
                  "loss.csv":     f"loss{label}.csv", 
                  "GeneratorGeneration.csv":      f"GeneratorGeneration{label}.csv",
                  "GeneratorPumpLoad.csv":        f"GeneratorPumpLoad{label}.csv",
                  "carga_bateria.csv":            f"carga_bateria{label}.csv",
                  "inyeccion_generador.csv":      f"inyeccion_generador{label}.csv",
                  "flujo.csv":                    f"flujo{label}.csv", }
    name = rename_map.get(name, name)
        
    if st_schedule:
        results = sol.QueryToCSV(name,
                            False
                            ,SimulationPhaseEnum.STSchedule, \
                        collections[f"{prefix}{collection}"], \
                        'SEN', \
                        '', \
                        PeriodEnum.Interval, \
                        SeriesTypeEnum.Values, \
                        propiedad)

    else:
        results = sol.QueryToCSV(name,
                                 False,
                                 SimulationPhaseEnum.MTSchedule, \
                        collections[f"{prefix}{collection}"], \
                        'SEN', \
                        '', \
                        PeriodEnum.Interval, \
                        SeriesTypeEnum.Values, \
                        propiedad)
    time.sleep(1)
    # Cargar, filtrar y renombrar columnas del CSV
    df = pl.read_csv(name, schema_overrides={"value": pl.Float64}).select(columns)

    # Se intenta eliminar el temporal
    for _ in range(2):
        try:
            os.remove(name)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        print("Advertencia: No se pudo eliminar temporal.csv")

    new_names = dict(zip(columns, rename))
    df = df.rename(new_names)

    # Filtrar por rango de horas
    df = df.filter((df["Hora"] >= hini) & (df["Hora"] <= hfin))

    return df