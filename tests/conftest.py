"""Configuración de pytest para el proyecto.

Agrega la raíz del repositorio a sys.path para poder importar preparacion.py sin instalar el
paquete (el proyecto es un conjunto de scripts con rutas relativas a la raíz).
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture(scope="session")
def base():
    """Base analítica completa, cargada una sola vez por sesión de tests."""
    from preparacion import cargar_base

    return cargar_base()


@pytest.fixture(scope="session")
def base_completa():
    """Todos los años, deduplicados: lo que necesita el diagnóstico de cobertura."""
    from preparacion import preparar_base

    return preparar_base()
