"""
Ventanas temporales del proyecto en un solo lugar.

Todo lo que dependa de años o de fechas de corte se define acá: el período de análisis, el corte
de la validación fuera de muestra y la fecha de descarga del portal de Chicago. Cambiar el período
es editar estas constantes; el resto del pipeline (preparación, notebooks, enriquecimiento) las
consume y no repite años literales.

Uso:  from config import ANIO_DESDE, ANIO_HASTA
"""

# Período de análisis principal (años completos).
ANIO_DESDE = 2018
ANIO_HASTA = 2024

# Último año usado para ajustar los modelos. El año siguiente abre el período de prueba:
# 2018-2022 para entrenar, 2023-2024 para validar fuera de muestra.
ANIO_CORTE_VALIDACION = 2022

# El portal de datos abiertos se descarga hasta esta fecha (exclusiva). Se deja un margen sobre el
# último año analizado para captar siniestros cargados con demora. None descarga todo lo disponible.
FECHA_CORTE_PORTAL = "2025-02-01"

# Aforo vehicular (AADT) del portal: los conteos diarios arrancan a mediados de 2022, así que se
# toma desde el primer mes completo y hasta el cierre del período de análisis.
ANIO_DESDE_AFOROS = 2022
FECHA_DESDE_AFOROS = f"{ANIO_DESDE_AFOROS}-08-01T00:00:00"
FECHA_HASTA_AFOROS = f"{ANIO_HASTA}-12-31T00:00:00"

# Derivadas: no editar a mano.
ANIO_PRUEBA_DESDE = ANIO_CORTE_VALIDACION + 1
N_ANIOS = ANIO_HASTA - ANIO_DESDE + 1


def validar_ventana(desde, hasta, corte):
    """Verifica que la ventana de análisis y el corte de validación tengan sentido."""
    if desde >= hasta:
        raise ValueError(
            f"ANIO_DESDE ({desde}) tiene que ser anterior a ANIO_HASTA ({hasta}): "
            "la validación fuera de muestra necesita al menos un año de prueba"
        )
    if not (desde <= corte < hasta):
        raise ValueError(
            f"ANIO_CORTE_VALIDACION ({corte}) tiene que estar entre ANIO_DESDE ({desde}) y "
            f"ANIO_HASTA - 1 ({hasta - 1}): el período de prueba necesita al menos un año"
        )


validar_ventana(ANIO_DESDE, ANIO_HASTA, ANIO_CORTE_VALIDACION)
