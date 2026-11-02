"""Los datos binarios van en Git LFS: en el historial queda un puntero, no el archivo.

Cubre el issue #6: `dataset.xlsx` (22,9 MB) y `dataset_geo.parquet` (29,5 MB) estaban en el
historial normal de git, así que cada clon se llevaba 52 MB que no hacen falta para leer el código y
cada cambio futuro de los datos duplicaba ese peso. Con `.gitattributes` y la migración a LFS el
clon del código quedó en 8,6 MB y los datos se descargan aparte.

El test mira el contenido del índice de git y no el archivo del disco: en disco está el binario
completo (el filtro de LFS lo materializa en el checkout), en git queda el puntero de 133 bytes.
"""
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BINARIOS = ["dataset.xlsx", "dataset_geo.parquet", "aforos_segmentos.parquet"]
CABECERA_LFS = "version https://git-lfs.github.com/spec/v1"


def _versionado(nombre):
    """Contenido del archivo tal como está en el índice de git (el puntero de LFS)."""
    return subprocess.run(
        ["git", "-C", str(RAIZ), "cat-file", "blob", f":{nombre}"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout


def _reglas_gitattributes():
    """Patrón de archivo -> atributos declarados, sin comentarios ni líneas vacías."""
    reglas = {}
    for linea in (RAIZ / ".gitattributes").read_text(encoding="utf-8").splitlines():
        limpia = linea.split("#")[0].strip()
        if not limpia:
            continue
        patron, *atributos = limpia.split()
        reglas[patron] = set(atributos)
    return reglas


@pytest.mark.parametrize("patron", ["*.xlsx", "*.parquet"])
def test_gitattributes_declara_lfs(patron):
    atributos = _reglas_gitattributes().get(patron, set())
    assert "filter=lfs" in atributos, f"{patron} no está en LFS"
    assert "-text" in atributos, f"{patron} tiene que viajar tal cual, sin conversión de fin de línea"


@pytest.mark.parametrize("nombre", BINARIOS)
def test_los_binarios_se_versionan_como_puntero(nombre):
    contenido = _versionado(nombre)
    assert contenido.startswith(CABECERA_LFS), f"{nombre} está versionado como binario completo"
    assert "oid sha256:" in contenido
    assert "\nsize " in contenido
    # Un puntero de LFS ronda los 133 bytes; un binario de decenas de MB no pasa por acá.
    assert len(contenido.encode("utf-8")) < 200
