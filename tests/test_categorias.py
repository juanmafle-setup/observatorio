"""Validación de categorías: la base nunca se carga con valores sin clasificar en silencio.

Cubre el issue #4.
"""
import inspect
import re
from pathlib import Path

import pytest

import preparacion
from preparacion import (
    FAMILIA,
    NIVELES,
    PALANCA,
    SEVERIDAD,
    CategoriasNoMapeadas,
    CategoriasNoMapeadasAdvertencia,
    cargar_base,
    validar_categorias,
    valores_sin_mapear,
)

RUTA_MODULO = Path(preparacion.__file__)


# --- Contrato de la base ----------------------------------------------------

def test_base_actual_no_tiene_valores_sin_mapear(base):
    assert valores_sin_mapear(base).empty


def test_cargar_base_no_deja_nulos_en_las_derivadas(base):
    """Reemplaza el assert que había en cargar_base: el invariante ahora es un test."""
    columnas = ["clima_g", "luz_g", "severidad", "familia_causa", "palanca"]
    assert base[columnas].notna().all().all()


def test_estricto_es_el_comportamiento_por_defecto():
    assert inspect.signature(cargar_base).parameters["estricto"].default is True


# --- Detección y mensaje ----------------------------------------------------

def test_causa_inventada_falla_con_columna_valor_y_filas(base):
    df = base.head(1000).copy()
    df.loc[df.index[:3], "causa_principal"] = "CAUSA INVENTADA"

    with pytest.raises(CategoriasNoMapeadas) as exc:
        validar_categorias(df)

    mensaje = str(exc.value)
    assert "causa_principal" in mensaje
    assert "CAUSA INVENTADA" in mensaje
    assert "3 filas" in mensaje


def test_varias_columnas_se_reportan_juntas(base):
    df = base.head(500).copy()
    df.loc[df.index[0], "clima"] = "GRANIZO MARCIANO"
    df.loc[df.index[1], "iluminacion"] = "LUZ DE LUNA"

    reporte = valores_sin_mapear(df)

    assert set(reporte["columna"]) == {"clima", "iluminacion"}
    assert set(reporte["columna_destino"]) == {"clima_g", "luz_g"}
    with pytest.raises(CategoriasNoMapeadas) as exc:
        validar_categorias(df)
    assert "columna(s)" in str(exc.value)


def test_un_nulo_se_reporta_como_nulo(base):
    df = base.head(200).copy()
    df.loc[df.index[0], "lesion_mas_grave"] = None

    reporte = valores_sin_mapear(df)

    assert len(reporte) == 1
    assert reporte.iloc[0]["valor"] == "<nulo>"
    assert reporte.iloc[0]["columna"] == "lesion_mas_grave"
    assert reporte.iloc[0]["filas"] == 1


def test_el_reporte_trae_el_porcentaje_afectado(base):
    df = base.head(1000).copy()
    df.loc[df.index[:10], "clima"] = "CLIMA NUEVO"

    reporte = valores_sin_mapear(df)

    assert reporte.iloc[0]["filas"] == 10
    assert reporte.iloc[0]["porcentaje"] == pytest.approx(1.0)


# --- Modo tolerante ---------------------------------------------------------

def test_modo_tolerante_advierte_en_vez_de_fallar(base):
    df = base.head(100).copy()
    df.loc[df.index[0], "causa_principal"] = "CAUSA INVENTADA"

    with pytest.warns(CategoriasNoMapeadasAdvertencia) as aviso:
        reporte = validar_categorias(df, estricto=False)

    assert len(reporte) == 1
    assert "CAUSA INVENTADA" in str(aviso[0].message)


def test_modo_tolerante_no_modifica_los_datos(base):
    df = base.head(100).copy()
    df.loc[df.index[0], "causa_principal"] = "CAUSA INVENTADA"

    with pytest.warns(CategoriasNoMapeadasAdvertencia):
        validar_categorias(df, estricto=False)

    assert df.loc[df.index[0], "causa_principal"] == "CAUSA INVENTADA"


# --- Consistencia de los diccionarios --------------------------------------

def test_palanca_cubre_todas_las_familias():
    assert set(FAMILIA.values()) - set(PALANCA) == set()


def test_severidad_cubre_todos_los_niveles():
    assert set(SEVERIDAD.values()) == set(NIVELES)


def test_no_quedan_asserts_como_control_de_calidad():
    """Los assert desaparecen con python -O: la validación tiene que ser código real.

    Los notebooks quedan fuera de este test: su preparación duplicada se elimina en el issue #2.
    """
    archivos = sorted(RUTA_MODULO.parent.glob("*.py"))
    assert archivos, "no se encontraron módulos Python en la raíz del repo"
    con_asserts = {}
    for archivo in archivos:
        encontrados = re.findall(r"^\s*assert\b.*$", archivo.read_text(encoding="utf-8"), flags=re.MULTILINE)
        if encontrados:
            con_asserts[archivo.name] = encontrados
    assert con_asserts == {}
