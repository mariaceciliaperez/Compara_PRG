# src/compara_prg/io/query_base.py
import os, sys, clr
from pathlib import Path

sys.path.append('C:/Program Files/Energy Exemplar/PLEXOS 10.0 API/')
clr.AddReference('PLEXOS_NET.Core')
clr.AddReference('EEUTILITY')
clr.AddReference('EnergyExemplar.PLEXOS.Utility')

from PLEXOS_NET.Core import *
from EEUTILITY.Enums import *
from EnergyExemplar.PLEXOS.Utility.Enums import *


def query_read_base(base_path):
    """
    Acepta Path o str; si es carpeta, intenta encontrar un archivo de base.
    Devuelve (db, collections, attributes, classes).
    """
    p = Path(base_path)

    # Si es carpeta, intenta localizar un archivo de base adentro
    if p.is_dir():
        candidatos = [
            p / f"{p.name}.xml",   # <carpeta>/<carpeta>.xml
            *p.glob("*.xml"),
            *p.glob("*.zip"),
            *p.glob("*.pmdx"),
        ]
        base_file = next((c for c in candidatos if c.exists()), None)
        if base_file is None:
            raise FileNotFoundError(f"No se encontró archivo de base en: {p}")
    else:
        if not p.exists():
            raise FileNotFoundError(f"No existe: {p}")
        base_file = p

    # ⚠️ .NET requiere str (no Path)
    base_file_str = os.fspath(base_file)

    db = DatabaseCore()
    db.DisplayAlerts = False
    db.Connection(base_file_str)

    collections = db.FetchAllCollectionIds()
    attributes  = db.FetchAllAttributeEnums()
    classes     = db.FetchAllClassIds()
    return db, collections, attributes, classes
