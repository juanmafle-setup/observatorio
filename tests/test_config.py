"""Las ventanas temporales del proyecto viven en config.py y en ningún otro lado.

Cubre el issue #5: antes, el período de análisis y el corte de la validación estaban repetidos
a mano en `preparacion.py`, `enriquecer_coordenadas.py` y once celdas de los notebooks, así que
cambiar un año obligaba a buscar literales por todo el repo y era fácil dejar uno desactualizado.
"""
import inspect
import json
import re
from datetime import date
from pathlib import Path

import pytest

import config
import enriquecer_coordenadas
import preparacion
from config import (
    ANIO_CORTE_VALIDACION,
    ANIO_DESDE,
    ANIO_HASTA,
    ANIO_PRUEBA_DESDE,
    FECHA_CORTE_PORTAL,
    N_ANIOS,
    validar_ventana,
)

RAIZ = Path(preparacion.__file__).parent
NOTEBOOKS = ["Fase 3.ipynb", "Fase 4.ipynb"]

# Un año de cuatro dígitos o una fecha ISO dentro de una celda de código.
LITERAL_TEMPORAL = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)|\d{4}-\d{2}-\d{2}")


# --- Coherencia de la configuración ----------------------------------------

def test_la_ventana_es_coherente():
    assert ANIO_DESDE < ANIO_HASTA
    assert ANIO_DESDE <= ANIO_CORTE_VALIDACION < ANIO_HASTA


def test_las_derivadas_se_calculan_desde_las_constantes():
    assert ANIO_PRUEBA_DESDE == ANIO_CORTE_VALIDACION + 1
    assert N_ANIOS == ANIO_HASTA - ANIO_DESDE + 1


def test_el_anio_de_prueba_queda_dentro_del_periodo():
    assert ANIO_DESDE < ANIO_PRUEBA_DESDE <= ANIO_HASTA


def test_la_fecha_de_corte_del_portal_es_iso_y_posterior_al_periodo():
    corte = date.fromisoformat(FECHA_CORTE_PORTAL)
    assert corte.year > ANIO_HASTA


def test_importar_config_valida_la_ventana():
    """El propio módulo se valida al importarse: no se puede dejar una ventana absurda en disco."""
    fuente = Path(config.__file__).read_text(encoding="utf-8")
    assert "validar_ventana(ANIO_DESDE, ANIO_HASTA, ANIO_CORTE_VALIDACION)" in fuente


# --- Validación de la ventana ----------------------------------------------

def test_validar_ventana_acepta_la_ventana_del_proyecto():
    validar_ventana(ANIO_DESDE, ANIO_HASTA, ANIO_CORTE_VALIDACION)


def test_validar_ventana_acepta_una_ventana_de_dos_anios():
    validar_ventana(2018, 2019, 2018)


def test_validar_ventana_falla_si_el_periodo_esta_invertido():
    with pytest.raises(ValueError, match="tiene que ser anterior"):
        validar_ventana(2024, 2018, 2022)


def test_validar_ventana_falla_si_el_periodo_no_tiene_anios():
    with pytest.raises(ValueError, match="al menos un año de prueba"):
        validar_ventana(2020, 2020, 2019)


def test_validar_ventana_falla_si_el_corte_es_el_ultimo_anio():
    """Sin año posterior al corte no hay período de prueba."""
    with pytest.raises(ValueError, match="al menos un año"):
        validar_ventana(2018, 2024, 2024)


def test_validar_ventana_falla_si_el_corte_es_anterior_al_inicio():
    with pytest.raises(ValueError, match="tiene que estar entre"):
        validar_ventana(2020, 2024, 2019)


def test_el_mensaje_de_error_nombra_las_constantes_y_los_valores():
    with pytest.raises(ValueError) as exc:
        validar_ventana(2018, 2024, 2024)
    mensaje = str(exc.value)
    assert "ANIO_CORTE_VALIDACION (2024)" in mensaje
    assert "ANIO_HASTA - 1 (2023)" in mensaje


# --- El resto del código consume la configuración --------------------------

def test_cargar_base_toma_el_periodo_de_config():
    parametros = inspect.signature(preparacion.cargar_base).parameters
    assert parametros["desde"].default == ANIO_DESDE
    assert parametros["hasta"].default == ANIO_HASTA


def test_descargar_chicago_toma_la_fecha_de_corte_de_config():
    parametros = inspect.signature(enriquecer_coordenadas.descargar_chicago).parameters
    assert parametros["hasta"].default == FECHA_CORTE_PORTAL


def _falso_get(llamadas):
    class Respuesta:
        text = "crash_record_id\n1\n"

        def raise_for_status(self):
            pass

    def get(url, params=None, timeout=None):
        llamadas.append(params)
        return Respuesta()

    return get


def test_descargar_chicago_filtra_por_la_fecha_de_corte(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(enriquecer_coordenadas, "RUTA_CHICAGO", tmp_path / "cache.parquet")
    monkeypatch.setattr(enriquecer_coordenadas.requests, "get", _falso_get(llamadas))

    enriquecer_coordenadas.descargar_chicago()

    assert llamadas[0]["$where"] == f"crash_date < '{FECHA_CORTE_PORTAL}'"


def test_descargar_chicago_con_hasta_none_trae_todo_sin_filtro(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(enriquecer_coordenadas, "RUTA_CHICAGO", tmp_path / "cache.parquet")
    monkeypatch.setattr(enriquecer_coordenadas.requests, "get", _falso_get(llamadas))

    enriquecer_coordenadas.descargar_chicago(hasta=None)

    assert "$where" not in llamadas[0]


def test_el_periodo_del_docstring_de_preparacion_no_esta_hardcodeado():
    """El docstring de ejemplo citaba '2018-2024': cambiaba el período y quedaba mintiendo."""
    docstring = preparacion.__doc__
    assert not LITERAL_TEMPORAL.search(docstring)


# --- Guardas contra literales temporales -----------------------------------

def test_los_modulos_del_repo_no_tienen_anios_literales():
    """config.py es el único archivo que puede nombrar años o fechas."""
    infractores = {}
    for archivo in sorted(RAIZ.glob("*.py")):
        if archivo.name == "config.py":
            continue
        encontrados = LITERAL_TEMPORAL.findall(archivo.read_text(encoding="utf-8"))
        if encontrados:
            infractores[archivo.name] = encontrados
    assert infractores == {}, (
        f"Usá las constantes de config.py en vez de literales: {infractores}"
    )


def test_las_celdas_de_codigo_de_los_notebooks_no_tienen_anios_literales():
    infractores = {}
    for nombre in NOTEBOOKS:
        ruta = RAIZ / nombre
        if not ruta.exists():
            pytest.skip(f"falta {nombre}")
        celdas = json.loads(ruta.read_text(encoding="utf-8"))["cells"]
        for indice, celda in enumerate(celdas):
            if celda["cell_type"] != "code":
                continue
            fuente = "".join(celda["source"])
            encontrados = LITERAL_TEMPORAL.findall(fuente)
            if encontrados:
                infractores[f"{nombre}:{indice}"] = encontrados
    assert infractores == {}, (
        f"Las celdas de código tienen que importar de config.py: {infractores}"
    )
