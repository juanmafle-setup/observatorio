"""Contrato de columnas de la base: el renombrado es por nombre, nunca por posición.

Cubre el issue #3. Los tests de integración leen dataset_geo.parquet y tardan unos segundos.
"""
import pandas as pd
import pytest

from preparacion import MAPA_COLUMNAS, NOMBRES, RUTA_GEO, cargar_base, normalizar_columnas


def base_falsa():
    """DataFrame mínimo con exactamente las columnas de origen del contrato."""
    return pd.DataFrame({origen: [None] for origen in MAPA_COLUMNAS})


# --- Contrato ---------------------------------------------------------------

def test_mapa_tiene_31_columnas_y_destinos_unicos():
    assert len(MAPA_COLUMNAS) == 31
    destinos = list(MAPA_COLUMNAS.values())
    assert len(destinos) == len(set(destinos))


def test_nombres_excluye_las_columnas_de_ubicacion():
    assert len(NOMBRES) == 24
    assert "latitud" not in NOMBRES
    assert "calle" not in NOMBRES


def test_columnas_de_ubicacion_estan_en_el_mapa():
    for columna in ("latitud", "longitud", "altura", "direccion_calle", "calle", "id_portal", "calidad_geo"):
        assert columna in MAPA_COLUMNAS.values()


# --- Validación del contrato ------------------------------------------------

def test_falta_una_columna_y_el_error_la_nombra():
    df = base_falsa().drop(columns=["Calle"])
    with pytest.raises(ValueError) as exc:
        normalizar_columnas(df)
    mensaje = str(exc.value)
    assert "faltan 1" in mensaje
    assert "Calle" in mensaje
    assert "MAPA_COLUMNAS" in mensaje


def test_sobra_una_columna_y_el_error_la_nombra():
    df = base_falsa()
    df["Columna nueva"] = 1
    with pytest.raises(ValueError) as exc:
        normalizar_columnas(df)
    mensaje = str(exc.value)
    assert "sobran 1" in mensaje
    assert "Columna nueva" in mensaje


def test_varias_faltantes_se_reportan_juntas():
    df = base_falsa().drop(columns=["Calle", "Latitud", "Mes del choque"])
    with pytest.raises(ValueError) as exc:
        normalizar_columnas(df)
    mensaje = str(exc.value)
    assert "faltan 3" in mensaje
    for columna in ("Calle", "Latitud", "Mes del choque"):
        assert columna in mensaje


def test_renombrado_es_por_nombre_y_no_por_posicion():
    df = base_falsa()
    columnas = list(df.columns)
    df["Fecha del accidente"] = "01/01/2020"
    df["Calle"] = "STATE ST"

    esperado = normalizar_columnas(df)[["fecha", "calle"]]
    desordenado = normalizar_columnas(df[columnas[::-1]])[["fecha", "calle"]]

    pd.testing.assert_frame_equal(esperado, desordenado)
    assert esperado["fecha"].iat[0] == "01/01/2020"
    assert esperado["calle"].iat[0] == "STATE ST"


def test_orden_final_sigue_el_mapa():
    resultado = normalizar_columnas(base_falsa())
    assert list(resultado.columns) == list(MAPA_COLUMNAS.values())


# --- Integración sobre la base real ----------------------------------------

def test_cargar_base_invariantes():
    df = cargar_base()
    assert df.shape == (181051, 46)
    assert int(df["grave"].sum()) == 6146
    assert int(df["fatal"].sum()) == 321
    assert int(df["con_heridos"].sum()) == 49053
    assert not df.duplicated(subset=NOMBRES).any()
    assert df["anio"].between(2018, 2024).all()


def test_severidad_es_funcion_de_lesion_mas_grave():
    df = cargar_base()
    por_nivel = df.groupby("lesion_mas_grave", observed=True)["severidad"].nunique()
    assert (por_nivel == 1).all(), f"severidad ambigua en: {por_nivel[por_nivel > 1].to_dict()}"


def test_orden_de_columnas_del_parquet_no_altera_el_resultado(tmp_path):
    """Prueba de regresión del bug de ISS-3: con las columnas invertidas, el resultado es igual."""
    crudo = pd.read_parquet(RUTA_GEO)
    ruta = tmp_path / "dataset_geo_invertido.parquet"
    crudo[list(crudo.columns[::-1])].to_parquet(ruta, index=False)

    esperado = cargar_base()
    obtenido = cargar_base(ruta=ruta)

    pd.testing.assert_frame_equal(esperado, obtenido)
