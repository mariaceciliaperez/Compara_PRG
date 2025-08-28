import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st

from compara_prg.io.query_base import query_read_base
from compara_prg.config import _data_intermedia, DEFAULT_NAME_BASE

# 👇 importante: el decorador cachea el resultado
@st.cache_data(show_spinner="Cargando nodos y líneas...")
def grafico_chile():
    PATH_TO_BASE = str(_data_intermedia / DEFAULT_NAME_BASE)  # pasar a str, no Path
    db, collections, attributes, classes = query_read_base(PATH_TO_BASE)

    # Nodos
    rows = []
    for nod in db.GetChildMembers(collections['SystemNodes'], 'SEN'):
        lat = db.GetAttributeValue(classes['Node'], nod, attributes['Node.Latitude'], 0)[1]
        lon = db.GetAttributeValue(classes['Node'], nod, attributes['Node.Longitude'], 0)[1]
        rows.append({"Nodo": nod, "Lat": float(lat) if lat else None, "Lon": float(lon) if lon else None})
    df_nodes = pd.DataFrame(rows).drop_duplicates(subset=["Nodo"]).reset_index(drop=True)

    # Líneas
    def parse_mships_line(mships, col_nodo):
        rows = []
        for mem in mships:
            op1 = mem.find('('); cp1 = mem.find(')')
            op2 = mem.find('(', op1+1); cp2 = mem.find(')', op2+1)
            linea = mem[op1+2:cp1-1]
            nodo  = mem[op2+2:cp2-1]
            rows.append({"Linea": linea, col_nodo: nodo})
        return pd.DataFrame(rows)

    mships_from = db.GetMemberships(collections['LineNodeFrom'])
    mships_to   = db.GetMemberships(collections['LineNodeTo'])

    df_from = parse_mships_line(mships_from, "NodoFrom")
    df_to   = parse_mships_line(mships_to,   "NodoTo")

    df_lines = (
        pd.merge(df_from, df_to, on="Linea", how="outer")
        .dropna(subset=["NodoFrom","NodoTo"], how="any")
        .drop_duplicates(subset=["Linea","NodoFrom","NodoTo"])
        .reset_index(drop=True)
    )

    # Juntar con coordenadas
    LAT_MIN, LAT_MAX = -56, -17
    LON_MIN, LON_MAX = -76, -66

    df_from_xy = df_lines.merge(
        df_nodes.rename(columns={"Nodo": "NodoFrom", "Lat": "LatFrom", "Lon": "LonFrom"}),
        on="NodoFrom", how="left"
    )
    df_lines_xy = df_from_xy.merge(
        df_nodes.rename(columns={"Nodo": "NodoTo", "Lat": "LatTo", "Lon": "LonTo"}),
        on="NodoTo", how="left"
    ).dropna(subset=["LatFrom","LonFrom","LatTo","LonTo"])

    df_lines_xy = df_lines_xy.query(
        "@LAT_MIN <= LatFrom <= @LAT_MAX and @LON_MIN <= LonFrom <= @LON_MAX and \
         @LAT_MIN <= LatTo   <= @LAT_MAX and @LON_MIN <= LonTo   <= @LON_MAX"
    ).reset_index(drop=True)

    df_nodes_cl = df_nodes.dropna().query(
        "@LAT_MIN <= Lat <= @LAT_MAX and @LON_MIN <= Lon <= @LON_MAX"
    ).reset_index(drop=True)

    # Figura
    fig = go.Figure()

    for _, row in df_lines_xy.iterrows():
        fig.add_trace(go.Scattergeo(
            lon=[row["LonFrom"], row["LonTo"]],
            lat=[row["LatFrom"], row["LatTo"]],
            mode="lines",
            line=dict(width=2, color="#B0B6BE"),
            customdata=[[row["Linea"], row["NodoFrom"], row["NodoTo"]]],
            hovertemplate="<b>%{customdata[0]}</b><br>From: %{customdata[1]}<br>To: %{customdata[2]}<extra></extra>",
            showlegend=False,
        ))

    fig.add_trace(go.Scattergeo(
        lon=df_nodes_cl["Lon"], lat=df_nodes_cl["Lat"],
        text=df_nodes_cl["Nodo"],
        mode="markers",
        marker=dict(size=5, color="#1F6FEB", line=dict(width=0.5, color="white"), opacity=0.95),
        hovertemplate="Nodo: %{text}<br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        title="<b>Red Eléctrica — Chile</b>",
        geo=dict(
            projection_type="mercator",
            showland=True, landcolor="#F8F9FA",
            showcountries=True, countrycolor="#A3AAB2",
            coastlinecolor="#A3AAB2",
            lakecolor="#E8F2FF", showlakes=True,
            lonaxis=dict(range=[LON_MIN, LON_MAX]),
            lataxis=dict(range=[LAT_MIN, LAT_MAX]),
            fitbounds="locations"
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        height=1000, width=700,
    )

    return fig
