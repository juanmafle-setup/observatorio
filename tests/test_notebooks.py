"""Los notebooks se versionan sin salidas: en git va el código, no los resultados.

Cubre el issue #7: `Fase 3.ipynb` pesaba 3,1 MB y `Fase 4.ipynb` 3,6 MB, casi todo imágenes PNG
en base64 y HTML de mapas embebidos. Cada re-ejecución producía un diff de megabytes donde no se
distinguía el cambio de código del cambio de gráfico.

El test mira el contenido versionado y no el archivo del disco: si alguien ejecuta un notebook, el
archivo local queda lleno de salidas y el filtro `nbstripout` las quita recién al agregarlo a git,
así que el disco no dice nada sobre lo que se commitea.
"""
import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
NOTEBOOKS = ["Fase 3.ipynb", "Fase 4.ipynb"]
TAMANIO_MAXIMO_KB = 200


def _contenido_versionado(nombre):
    """Devuelve el notebook tal como va a quedar en el repositorio.

    Lo lee del índice de git, que es el resultado de aplicar el filtro `nbstripout` al archivo.
    Si no hay git disponible (por ejemplo, un export del código), cae al archivo del disco.
    """
    try:
        resultado = subprocess.run(
            ["git", "-C", str(RAIZ), "cat-file", "blob", f":{nombre}"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return (RAIZ / nombre).read_bytes()
    return resultado.stdout


@pytest.mark.parametrize("nombre", NOTEBOOKS)
def test_notebook_sin_salidas(nombre):
    notebook = json.loads(_contenido_versionado(nombre).decode("utf-8"))
    for indice, celda in enumerate(notebook["cells"]):
        assert not celda.get("outputs"), f"la celda {indice} tiene salidas"
        assert celda.get("execution_count") is None, (
            f"la celda {indice} tiene execution_count"
        )


@pytest.mark.parametrize("nombre", NOTEBOOKS)
def test_notebook_liviano(nombre):
    kb = len(_contenido_versionado(nombre)) / 1024
    assert kb < TAMANIO_MAXIMO_KB, f"{nombre} pesa {kb:.0f} KB"


def test_gitattributes_declara_el_filtro():
    reglas = {
        linea.split("#")[0].strip()
        for linea in (RAIZ / ".gitattributes").read_text(encoding="utf-8").splitlines()
    }
    assert "*.ipynb filter=nbstripout" in reglas
    assert "*.ipynb diff=ipynb" in reglas


@pytest.mark.parametrize("nombre", NOTEBOOKS)
def test_notebook_conserva_el_codigo(nombre):
    """El strip tiene que quitar salidas y nada más: las celdas siguen ahí."""
    notebook = json.loads(_contenido_versionado(nombre).decode("utf-8"))
    tipos = [celda["cell_type"] for celda in notebook["cells"]]
    assert tipos.count("code") > 10, f"{nombre} perdió celdas de código"
    assert "markdown" in tipos
    assert notebook["nbformat"] == 4
