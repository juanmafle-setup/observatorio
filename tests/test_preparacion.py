"""La preparación vive en preparacion.py y la Fase 3 no la reimplementa.

Cubre el issue #2: la sección 1 del notebook `Fase 3.ipynb` repetía el renombrado de columnas, el
tipado y los diccionarios de clasificación (36 líneas de `FAMILIA` incluidas), en paralelo a
`preparacion.py`. Con dos copias vivas, el tablero de la Fase 5 podía mostrar cifras distintas de
las del informe sin que nadie se enterara.

Los tests fijan el contrato que comparten el módulo, los notebooks y el tablero: qué filas entran,
cuántos duplicados se eliminan, qué columnas salen y cuáles son los totales del período.
"""
import inspect
import json
import re
from pathlib import Path

import pandas as pd
import pytest

import preparacion
from config import ANIO_DESDE, ANIO_HASTA
from preparacion import (
    MAPA_COLUMNAS,
    NOMBRES,
    BaseInconsistente,
    _validar_calendario,
    preparar_base,
)

RAIZ = Path(preparacion.__file__).parent

# Invariantes del período de análisis, los mismos que publica la Fase 3.
TOTALES = {"siniestros": 181051, "con_heridos": 49053, "graves": 6146, "fatales": 321}
FILAS_PARQUET = 209306
DUPLICADOS = 31
FILAS_COMPLETAS = FILAS_PARQUET - DUPLICADOS


def _codigo_fase_3():
    notebook = json.loads((RAIZ / "Fase 3.ipynb").read_text(encoding="utf-8"))
    return "\n".join(
        "".join(celda["source"]) for celda in notebook["cells"] if celda["cell_type"] == "code"
    )


def test_base_completa_cubre_todos_los_anios(base_completa):
    assert base_completa["anio"].min() == 2013
    assert base_completa["anio"].max() == 2025
    assert len(base_completa) == FILAS_COMPLETAS


def test_ventana_de_analisis_es_un_recorte_de_la_completa(base, base_completa):
    recorte = base_completa[base_completa["anio"].between(ANIO_DESDE, ANIO_HASTA)]
    assert len(base) == len(recorte)
    pd.testing.assert_series_equal(
        base.groupby("anio", observed=True).size(),
        recorte.groupby("anio", observed=True).size(),
    )


def test_totales_del_periodo(base):
    obtenidos = {
        "siniestros": len(base),
        "con_heridos": int(base["con_heridos"].sum()),
        "graves": int(base["grave"].sum()),
        "fatales": int(base["fatal"].sum()),
    }
    assert obtenidos == TOTALES


def test_diagnostico_de_la_carga(base, base_completa):
    assert base_completa.attrs == {"filas_origen": FILAS_PARQUET, "duplicados_eliminados": DUPLICADOS}
    # El recorte conserva el diagnóstico para que el notebook reporte calidad sin releer la base.
    assert base.attrs == base_completa.attrs
    assert base.attrs["filas_origen"] - base.attrs["duplicados_eliminados"] == len(base_completa)


def test_base_completa_no_tiene_duplicados(base_completa):
    assert not base_completa.duplicated(subset=NOMBRES).any()


def test_contrato_de_columnas(base):
    assert list(base.columns)[: len(MAPA_COLUMNAS)] == list(MAPA_COLUMNAS.values())
    assert base.shape[1] == 46


def test_calendario_incoherente():
    marco = pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2020-01-15", "2020-02-15"]),
            "mes": [1, 3],
            "dia_semana": [4, 7],
        }
    )
    with pytest.raises(BaseInconsistente, match="el mes no coincide con la fecha"):
        _validar_calendario(marco)


def test_calendario_coherente():
    marco = pd.DataFrame(
        {
            "fecha": pd.to_datetime(["2020-01-15", "2020-02-15"]),
            "mes": [1, 2],
            "dia_semana": [4, 7],
        }
    )
    _validar_calendario(marco)


def test_preparar_base_valida_el_calendario():
    assert "_validar_calendario(df)" in inspect.getsource(preparar_base)


@pytest.mark.parametrize(
    "definicion",
    ["FAMILIA = {", "PALANCA = {", "FRANJAS = [", "DIAS = [", "MESES = [", "NIVELES = [", "ORDEN_CLIMA = ", "ORDEN_LUZ = "],
)
def test_fase_3_no_redefine_la_preparacion(definicion):
    # `(?<![A-Z_])` deja pasar COLOR_PALANCA, que es una paleta de gráfico y no el diccionario.
    patron = rf"(?<![A-Z_]){re.escape(definicion)}"
    assert re.search(patron, _codigo_fase_3()) is None


def test_fase_3_importa_la_preparacion():
    codigo = _codigo_fase_3()
    assert "from preparacion import" in codigo
    assert "preparar_base()" in codigo
    assert "cargar_base()" in codigo
    assert "read_parquet" not in codigo
