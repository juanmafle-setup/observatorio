"""
Aforo vehicular por segmento de calle (AADT), desde el portal de datos abiertos de Chicago.

La base de siniestros no trae cuántos vehículos pasan por cada cuadra, así que la Fase 4 usaba el
total de siniestros como *proxy* de exposición. El portal publica «Average Daily Traffic Counts»
(`gc7y-n4xa`): el conteo diario promedio de 30 días por segmento de calle, derivado de las cámaras
de tránsito del CDOT, con la latitud y la longitud del punto medio del segmento.

Este script descarga el promedio del período en una sola consulta agregada (en vez de las 2,4
millones de filas diarias) y guarda `aforos_segmentos.parquet`, que la Fase 4 usa para medir el
sesgo del proxy de exposición y comparar rankings.

Uso:  python aforos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

from config import FECHA_DESDE_AFOROS, FECHA_HASTA_AFOROS

RUTA_AFOROS = Path("aforos_segmentos.parquet")
URL = "https://data.cityofchicago.org/resource/gc7y-n4xa.json"
# El conteo diario del portal arranca antes del período de análisis: se toma desde el primer mes
# completo disponible hasta el cierre del período (ver config.py).
DESDE, HASTA = FECHA_DESDE_AFOROS, FECHA_HASTA_AFOROS
COLS = ["segmentid", "roadname", "direction", "aforo", "lat", "lon"]
METROS_POR_GRADO = 111_320.0
LAT_CHICAGO = 41.85

# Los dos lados nombran la misma calle de forma distinta: el portal guarda `WESTERN` y el parte de
# siniestros `WESTERN AVE`, el portal `79TH` y el parte `79TH ST`. Sin normalizar coinciden apenas
# el 1,4 % de los siniestros, porque el nombre exacto casi nunca es igual.
PREFIJO = r"^(N|S|E|W|NORTH|SOUTH|EAST|WEST)\s+"
SUFIJO = (
    r"\s+(AVE|AV|AVENUE|ST|STREET|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE|LN|LANE|PKWY|PARKWAY"
    r"|PL|PLACE|CT|COURT|TER|TERRACE|WAY|SQ|SQUARE|HWY|EXPY|EXPRESSWAY)$"
)


def normalizar_via(nombres):
    """Nombre de calle comparable entre el portal de aforos y el parte de siniestros.

    Quita el prefijo de cuadrante (`N`, `S`, `E`, `W`) y el sufijo de tipo de vía (`AVE`, `ST`,
    `RD`, ...). El resto se deja tal cual: dos calles distintas con el mismo nombre base en
    cuadrantes distintos son la misma vía a los efectos del aforo.
    """
    limpio = (nombres.astype(object).fillna("").astype(str).str.strip().str.upper()
              .str.replace(PREFIJO, "", regex=True).str.replace(SUFIJO, "", regex=True))
    return limpio.str.replace(r"\s+", " ", regex=True).str.strip()


def descargar_aforos(url=URL, desde=DESDE, hasta=HASTA):
    """Promedio diario de vehículos por segmento, con su punto medio."""
    consulta = {
        "$select": (
            "segmentid, max(roadname) as roadname, max(direction) as direction, "
            "avg(vehiclecount) as aforo, max(midpointlat) as lat, max(midpointlon) as lon"
        ),
        "$where": f"timestamp between '{desde}' and '{hasta}'",
        "$group": "segmentid",
        "$limit": 100000,
    }
    respuesta = requests.get(url, params=consulta, timeout=180)
    respuesta.raise_for_status()
    aforos = pd.DataFrame(respuesta.json())
    aforos["aforo"] = aforos["aforo"].astype(float).round().astype(int)
    for columna in ("lat", "lon"):
        aforos[columna] = aforos[columna].astype(float)
    return aforos[COLS]


def cargar_aforos(ruta=RUTA_AFOROS):
    """Aforos ya descargados, con el contrato de columnas verificado."""
    aforos = pd.read_parquet(ruta)
    faltantes = sorted(set(COLS) - set(aforos.columns))
    if faltantes:
        raise ValueError(f"{ruta} no tiene las columnas esperadas; faltan {faltantes}")
    return aforos[COLS]


def _proyectar(latitudes, longitudes):
    """Coordenadas a metros en un plano local. A la latitud de Chicago el error es despreciable."""
    coseno = np.cos(np.radians(LAT_CHICAGO))
    return np.column_stack([np.asarray(longitudes, float) * METROS_POR_GRADO * coseno,
                            np.asarray(latitudes, float) * METROS_POR_GRADO])


def _mas_cercano(puntos, candidatos):
    arbol = cKDTree(candidatos)
    return arbol.query(puntos, k=1)


def asignar_aforo(latitudes, longitudes, aforos, radio_m=75.0):
    """Aforo del segmento más cercano a cada punto, sin mirar el nombre de la calle.

    Es la versión ingenua: sirve para medir cuánto se pierde por no usar el nombre de la vía. A
    75 m solo encuentra segmento para el 13 % de los siniestros, porque el portal publica el punto
    medio del segmento y no el de cada cuadra. Para el análisis se usa `asignar_aforo_por_via`.
    """
    lat = np.asarray(latitudes, float)
    lon = np.asarray(longitudes, float)
    validos = np.isfinite(lat) & np.isfinite(lon)
    distancia = np.full(len(lat), np.nan)
    indice = np.zeros(len(lat), dtype=int)
    distancia[validos], indice[validos] = _mas_cercano(
        _proyectar(lat[validos], lon[validos]),
        _proyectar(aforos["lat"], aforos["lon"]),
    )
    dentro = distancia <= radio_m  # los puntos sin coordenadas quedan fuera (NaN)
    indice_entrada = latitudes.index if isinstance(latitudes, pd.Series) else range(len(lat))
    return pd.DataFrame({
        "aforo": np.where(dentro, aforos["aforo"].to_numpy()[indice], np.nan),
        "distancia_m": distancia,
    }, index=indice_entrada)


def asignar_aforo_por_via(latitudes, longitudes, vias, aforos, radio_m=1500.0):
    """Aforo del segmento más cercano **de la misma calle**.

    Empareja por nombre normalizado y después busca el segmento más próximo de esa vía, así que un
    siniestro en `WESTERN AVE` toma el aforo de un segmento de `WESTERN` y nunca el de la calle de
    al lado. El radio máximo evita asignar el aforo de otra punta del mismo corredor: más allá de
    1,5 km el volumen de la vía ya no describe la cuadra del siniestro.

    Los puntos sin coordenadas, sin calle o sin aforo en su vía quedan con `aforo` nulo y con la
    distancia medida: preferimos un hueco declarado a inventar el dato.
    """
    lat = np.asarray(latitudes, float)
    lon = np.asarray(longitudes, float)
    serie = vias if isinstance(vias, pd.Series) else pd.Series(np.asarray(vias, dtype=object))
    via = normalizar_via(serie)
    via_segmento = normalizar_via(aforos["roadname"])
    aforo_segmento = aforos["aforo"].to_numpy(float)

    distancia = np.full(len(lat), np.nan)
    aforo = np.full(len(lat), np.nan)
    validos = np.isfinite(lat) & np.isfinite(lon)
    puntos = _proyectar(lat, lon)
    for nombre, segmentos in via_segmento.groupby(via_segmento).groups.items():
        if not nombre:
            continue
        indices = np.flatnonzero(validos & (via.to_numpy() == nombre))
        if indices.size == 0:
            continue
        elegidos = np.asarray(segmentos)
        dist, indice = _mas_cercano(puntos[indices],
                                    _proyectar(aforos["lat"].iloc[elegidos], aforos["lon"].iloc[elegidos]))
        distancia[indices] = dist
        aforo[indices] = np.where(dist <= radio_m, aforo_segmento[elegidos][indice], np.nan)
    # Se conserva el índice de entrada para poder asignar el resultado sin riesgo de desalinear.
    return pd.DataFrame({"aforo": aforo, "distancia_m": distancia}, index=serie.index)


if __name__ == "__main__":
    tabla = descargar_aforos()
    tabla.to_parquet(RUTA_AFOROS, index=False)
    print(f"Segmentos con aforo: {len(tabla):,} · {RUTA_AFOROS} ({RUTA_AFOROS.stat().st_size / 1024:.0f} KB)")
    print(f"Aforo mediano: {tabla['aforo'].median():,.0f} vehículos/día · máximo: {tabla['aforo'].max():,.0f}")
