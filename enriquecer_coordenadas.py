"""
Enriquecimiento de la base de siniestros con coordenadas y dirección.

La base del Observatorio (dataset.xlsx) es un extracto traducido del dataset abierto
"Traffic Crashes - Crashes" de la Ciudad de Chicago, que no incluye ubicación ni ID.
Este script descarga del portal de datos abiertos las columnas necesarias y vincula
cada registro con el siniestro original usando fecha y hora exactas, cantidad de
vehículos, desglose de lesiones y causa principal. Si hay varios candidatos, desempata
por tipo de choque, clima, iluminación, tipo de vía, dispositivo de control y superficie.

Salida: dataset_geo.parquet (la base original + latitud, longitud, dirección y calidad del vínculo).

Uso:  python enriquecer_coordenadas.py
"""
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from config import FECHA_CORTE_PORTAL

URL = "https://data.cityofchicago.org/resource/85ca-t3if.csv"
RUTA_EXCEL = Path("dataset.xlsx")
RUTA_CHICAGO = Path("chicago_crashes_cache.parquet")
RUTA_SALIDA = Path("dataset_geo.parquet")

COLS_CHICAGO = [
    "crash_record_id", "crash_date", "num_units", "injuries_total", "injuries_fatal", "injuries_incapacitating",
    "injuries_non_incapacitating", "injuries_reported_not_evident", "injuries_no_indication",
    "prim_contributory_cause", "first_crash_type", "weather_condition", "lighting_condition", "trafficway_type",
    "traffic_control_device", "roadway_surface_cond", "street_no", "street_direction", "street_name",
    "latitude", "longitude",
]
# Columnas numéricas de la base local y su equivalente en Chicago
CLAVE_NUM = {
    "Vehiculos involucrados": "num_units", "Lesiones totales": "injuries_total", "Lesiones fatales": "injuries_fatal",
    "Lesiones incapacitantes": "injuries_incapacitating", "Lesiones no incapacitantes": "injuries_non_incapacitating",
    "Lesiones reportadas no evidentes": "injuries_reported_not_evident",
    "Sin indicacion de lesiones": "injuries_no_indication",
}
# Columnas categóricas usadas para desempatar
DESEMPATE = {
    "Primer tipo de choque": "first_crash_type", "Condicion climatica": "weather_condition",
    "condicion luminica": "lighting_condition", "Tipo de via": "trafficway_type",
    "Dispositivo control de transito": "traffic_control_device", "Condicion superficie via": "roadway_surface_cond",
}
# Límites aproximados de la ciudad (descarta coordenadas en 0 o fuera de Chicago)
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 41.60, 42.05, -87.95, -87.50


def descargar_chicago(hasta=FECHA_CORTE_PORTAL, pagina=250_000):
    """Descarga (o reusa la caché de) la base de siniestros del portal.

    hasta=None significa traer todo lo disponible; por defecto se corta en la fecha de
    FECHA_CORTE_PORTAL (config.py).
    """
    if RUTA_CHICAGO.exists():
        return pd.read_parquet(RUTA_CHICAGO)
    partes, offset = [], 0
    while True:
        params = {"$select": ",".join(COLS_CHICAGO),
                  "$order": "crash_record_id", "$limit": pagina, "$offset": offset}
        if hasta is not None:
            params["$where"] = f"crash_date < '{hasta}'"
        r = requests.get(URL, params=params, timeout=600)
        r.raise_for_status()
        parte = pd.read_csv(StringIO(r.text), dtype=str)
        print(f"  descargados {offset + len(parte):,} registros")
        partes.append(parte)
        if len(parte) < pagina:
            break
        offset += pagina
    ch = pd.concat(partes, ignore_index=True)
    ch.to_parquet(RUTA_CHICAGO, index=False)
    return ch


def main():
    print("Leyendo base local...")
    loc = pd.read_excel(RUTA_EXCEL, sheet_name="traffic_accidents")
    loc["Hora del accidente"] = loc["Hora del accidente"].astype(str)
    causas = pd.read_excel(RUTA_EXCEL, sheet_name=1)
    es_a_en = dict(zip(causas.iloc[:, 1], causas.iloc[:, 0]))
    loc["fila"] = range(len(loc))
    loc["k_fecha"] = pd.to_datetime(loc["Fecha del accidente"] + " " + loc["Hora del accidente"], format="%m/%d/%Y %H:%M:%S")
    loc["k_causa"] = loc["Causa contribuyente principal"].map(es_a_en)
    sin_traduccion = loc.loc[loc["k_causa"].isna(), "Causa contribuyente principal"]
    if not sin_traduccion.empty:
        raise ValueError(
            "Hay causas del acta que no figuran en la hoja de traducción de dataset.xlsx:\n"
            f"{sin_traduccion.value_counts().to_string()}\n"
            "Agregalas a la segunda hoja del Excel antes de volver a correr el script."
        )
    for c_es, c_en in CLAVE_NUM.items():
        loc[c_en] = loc[c_es].astype(int)

    print("Descargando / leyendo base de Chicago...")
    ch = descargar_chicago()
    ch["k_fecha"] = pd.to_datetime(ch["crash_date"])
    ch["k_causa"] = ch["prim_contributory_cause"]
    for c_en in CLAVE_NUM.values():
        ch[c_en] = pd.to_numeric(ch[c_en], errors="coerce").fillna(-1).astype(int)
    print(f"  {len(ch):,} siniestros en el portal")

    claves = ["k_fecha", "k_causa", *CLAVE_NUM.values()]
    m = loc[["fila", *claves, *DESEMPATE]].merge(
        ch[[*claves, "crash_record_id", *DESEMPATE.values()]], on=claves, how="inner")
    m["n_cand"] = m.groupby("fila")["fila"].transform("size")

    # Diccionario ES -> EN aprendido de los vínculos únicos, para desempatar
    unicos = m[m["n_cand"] == 1]
    puntaje = 0
    for c_es, c_en in DESEMPATE.items():
        mapa = unicos.groupby(c_es)[c_en].agg(lambda s: s.mode().iat[0])
        puntaje = puntaje + (m[c_es].map(mapa) == m[c_en]).astype(int)
    m["puntaje"] = puntaje
    m["max_p"] = m.groupby("fila")["puntaje"].transform("max")
    mejores = m[m["puntaje"] == m["max_p"]]
    mejores = mejores[mejores.groupby("fila")["fila"].transform("size") == 1]
    mejores = mejores.assign(vinculo=lambda d: d["n_cand"].map(lambda n: "único" if n == 1 else "desempate"))

    geo = ch.set_index("crash_record_id")[["latitude", "longitude", "street_no", "street_direction", "street_name"]]
    out = loc.merge(mejores[["fila", "crash_record_id", "vinculo"]], on="fila", how="left")
    out = out.join(geo, on="crash_record_id")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    fuera = ~(out["latitude"].between(LAT_MIN, LAT_MAX) & out["longitude"].between(LON_MIN, LON_MAX))
    out.loc[fuera, ["latitude", "longitude"]] = None
    out["vinculo"] = out["vinculo"].fillna("sin vínculo")
    out.loc[(out["vinculo"] != "sin vínculo") & out["latitude"].isna(), "vinculo"] = "vinculado sin coordenadas"

    out = out.rename(columns={"latitude": "Latitud", "longitude": "Longitud", "street_no": "Altura",
                              "street_direction": "Direccion calle", "street_name": "Calle",
                              "crash_record_id": "ID siniestro (portal)", "vinculo": "Calidad vinculo geo"})
    out = out.drop(columns=["fila", "k_fecha", "k_causa", *CLAVE_NUM.values()])
    out.to_parquet(RUTA_SALIDA, index=False)

    print("\nResultado del vínculo:")
    print(out["Calidad vinculo geo"].value_counts().to_string())
    print(f"\nCon coordenadas válidas: {out['Latitud'].notna().mean():.1%}  ->  {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
