"""El aforo del portal se empareja con el siniestro por nombre de calle normalizado.

Cubre el issue #9: la Fase 4 estima la exposición de cada celda con el total de siniestros porque
la base no trae flujo vehicular. El portal de Chicago publica el AADT por segmento, pero los dos
lados nombran la misma calle distinto (`WESTERN` contra `WESTERN AVE`), así que sin normalizar
coincide apenas el 1,4 % de los siniestros y el aforo no sirve para nada.

Los tests fijan el contrato del emparejamiento: qué nombres se consideran la misma vía, que nunca
se asigne el aforo de otra calle, que el radio máximo se respete y que la cobertura sobre la base
real no se derrumbe si alguien toca la normalización.
"""
import numpy as np
import pandas as pd
import pytest

from aforos import (
    COLS,
    asignar_aforo,
    asignar_aforo_por_via,
    cargar_aforos,
    normalizar_via,
)

LAT = 41.85
METROS_POR_GRADO_LON = 111_320.0 * np.cos(np.radians(LAT))


def _lon(metros):
    """Longitud desplazada `metros` hacia el este desde -87,70."""
    return -87.70 + metros / METROS_POR_GRADO_LON


def _aforos(filas):
    return pd.DataFrame(filas, columns=COLS)


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("WESTERN", "WESTERN"),
        ("WESTERN AVE", "WESTERN"),
        ("N WESTERN AVE", "WESTERN"),
        ("S Stony Island Ave", "STONY ISLAND"),
        ("79TH ST", "79TH"),
        ("E 79th St", "79TH"),
        ("N LINCOLN PARK WEST", "LINCOLN PARK WEST"),
        ("  w  madison   st ", "MADISON"),
        ("CICERO AVE", "CICERO"),
        ("S Cicero Ave", "CICERO"),
        ("", ""),
    ],
)
def test_normalizar_via(entrada, esperado):
    assert normalizar_via(pd.Series([entrada])).iat[0] == esperado


def test_normalizar_via_ignora_nulos():
    assert normalizar_via(pd.Series([None, np.nan])).tolist() == ["", ""]


def test_normalizar_via_no_rompe_nombres_sin_sufijo():
    # "WESTERN" no es "W" + "ESTERN": el prefijo exige un espacio después de la letra.
    assert normalizar_via(pd.Series(["WESTERN"])).iat[0] == "WESTERN"
    assert normalizar_via(pd.Series(["ASHBY"])).iat[0] == "ASHBY"


def test_asignar_por_via_elige_la_misma_calle_aunque_haya_otra_mas_cerca():
    aforos = _aforos([
        [-1, "WESTERN", "NB", 20_000, LAT, _lon(400)],   # la calle del siniestro, 400 m al este
        [-2, "ASHLAND", "NB", 9_000, LAT, _lon(10)],     # otra calle, prácticamente encima
    ])
    asignado = asignar_aforo_por_via(
        pd.Series([LAT]), pd.Series([-87.70]), pd.Series(["WESTERN AVE"]), aforos
    )
    assert asignado["aforo"].iat[0] == 20_000
    assert asignado["distancia_m"].iat[0] == pytest.approx(400, abs=1)


def test_asignar_por_via_respeta_el_radio():
    aforos = _aforos([[-1, "WESTERN", "NB", 20_000, LAT, _lon(1_200)]])
    cerca = asignar_aforo_por_via(pd.Series([LAT]), pd.Series([-87.70]), pd.Series(["WESTERN"]), aforos)
    lejos = asignar_aforo_por_via(
        pd.Series([LAT]), pd.Series([-87.70]), pd.Series(["WESTERN"]), aforos, radio_m=500
    )
    assert cerca["aforo"].iat[0] == 20_000
    assert np.isnan(lejos["aforo"].iat[0])
    # La distancia se informa igual: sirve para diagnosticar por qué quedó sin aforo.
    assert lejos["distancia_m"].iat[0] == pytest.approx(1_200, abs=1)


def test_asignar_por_via_sin_calle_o_sin_aforo_queda_nulo():
    aforos = _aforos([[-1, "WESTERN", "NB", 20_000, LAT, _lon(50)]])
    asignado = asignar_aforo_por_via(
        pd.Series([LAT, LAT]), pd.Series([-87.70, -87.70]), pd.Series(["", "CALIFORNIA"]), aforos
    )
    assert asignado["aforo"].isna().all()


def test_asignar_por_via_sin_coordenadas_no_falla():
    aforos = _aforos([[-1, "WESTERN", "NB", 20_000, LAT, _lon(50)]])
    asignado = asignar_aforo_por_via(
        pd.Series([np.nan]), pd.Series([-87.70]), pd.Series(["WESTERN"]), aforos
    )
    assert np.isnan(asignado["aforo"].iat[0])
    assert np.isnan(asignado["distancia_m"].iat[0])


def test_asignar_por_via_conserva_el_indice():
    aforos = _aforos([[-1, "WESTERN", "NB", 20_000, LAT, _lon(50)]])
    asignado = asignar_aforo_por_via(
        pd.Series([LAT, LAT], index=[7, 42]),
        pd.Series([-87.70, -87.70], index=[7, 42]),
        pd.Series(["WESTERN", "WESTERN"], index=[7, 42]),
        aforos,
    )
    assert asignado.index.tolist() == [7, 42]


def test_asignar_por_radio_ignora_el_nombre():
    """La versión ingenua sirve de línea base: a 75 m encuentra muy poco."""
    aforos = _aforos([
        [-1, "WESTERN", "NB", 20_000, LAT, _lon(400)],
        [-2, "ASHLAND", "NB", 9_000, LAT, _lon(10)],
    ])
    asignado = asignar_aforo(pd.Series([LAT]), pd.Series([-87.70]), aforos)
    assert asignado["aforo"].iat[0] == 9_000  # la más cercana, aunque sea otra calle


def test_cargar_aforos_contrato():
    aforos = cargar_aforos()
    assert list(aforos.columns) == COLS
    assert len(aforos) == 2_008
    assert aforos["segmentid"].is_unique
    assert aforos["aforo"].between(1_000, 40_000).all()
    assert aforos["aforo"].median() == pytest.approx(8_862, abs=300)
    assert aforos["roadname"].nunique() > 100


def test_cargar_aforos_avisa_si_falta_una_columna(tmp_path):
    aforos = cargar_aforos().drop(columns=["roadname"])
    ruta = tmp_path / "sin_roadname.parquet"
    aforos.to_parquet(ruta, index=False)
    with pytest.raises(ValueError, match="roadname"):
        cargar_aforos(ruta)


def test_cobertura_del_aforo_sobre_la_base(base):
    """El emparejamiento por vía tiene que cubrir la mayor parte de los siniestros.

    Si alguien cambia la normalización o el radio, este test avisa antes de que el proxy de
    exposición de la Fase 4 se quede sin datos. La cobertura medida con el radio de 1,5 km es del
    59 %; se exige el 55 % para no atar el test al último decimal.
    """
    con_coord = base.dropna(subset=["latitud", "longitud"])
    asignado = asignar_aforo_por_via(
        con_coord["latitud"], con_coord["longitud"], con_coord["calle"], cargar_aforos()
    )
    assert asignado["aforo"].notna().mean() > 0.55
    # La versión ingenua, sin nombre de calle, no llega ni al 15 %: es la razón de normalizar.
    ingenuo = asignar_aforo(con_coord["latitud"], con_coord["longitud"], cargar_aforos())
    assert ingenuo["aforo"].notna().mean() < 0.15
