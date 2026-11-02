"""
Preparación analítica de la base de siniestros.

Lee dataset_geo.parquet (generado por enriquecer_coordenadas.py), renombra columnas, crea las
variables derivadas (severidad, franjas, agrupamientos de clima e iluminación, familia de causa y
palanca de intervención), valida la coherencia del calendario, elimina duplicados exactos y, en
`cargar_base`, filtra el período de años completos definido en config.py.

Este módulo es la única implementación de la preparación: lo usan los dos notebooks y el tablero
de la Fase 5. Los notebooks no repiten el renombrado ni los diccionarios de clasificación.

El renombrado es siempre **por nombre**, a través de MAPA_COLUMNAS: si la base de entrada no trae
exactamente las columnas esperadas, la carga falla en vez de asignar nombres por posición.

Uso:  from preparacion import cargar_base, preparar_base
      df = cargar_base()            # el período completo definido en config.py
      completa = preparar_base()    # todos los años, sin filtrar (diagnóstico de cobertura)
"""
import warnings
from pathlib import Path

import pandas as pd

from config import ANIO_DESDE, ANIO_HASTA

RUTA_GEO = Path("dataset_geo.parquet")

# Contrato de columnas: nombre en la base de entrada -> nombre analítico.
# El orden de este diccionario define el orden final de columnas; el renombrado es por nombre,
# nunca por posición (un cambio de orden en el parquet no puede corromper los datos).
MAPA_COLUMNAS = {
    "Fecha del accidente": "fecha",
    "Hora del accidente": "hora",
    "Dispositivo control de transito": "dispositivo_control",
    "Condicion climatica": "clima",
    "condicion luminica": "iluminacion",
    "Primer tipo de choque": "primer_tipo_choque",
    "Tipo de via": "tipo_via",
    "Alineacion": "alineacion",
    "Condicion superficie via": "superficie",
    "Defecto de la via": "defecto_via",
    "Tipo de choque": "tipo_choque",
    "En interseccion": "en_interseccion",
    "Daños": "danos",
    "Causa contribuyente principal": "causa_principal",
    "Vehiculos involucrados": "vehiculos",
    "Lesion mas grave": "lesion_mas_grave",
    "Lesiones totales": "lesiones_totales",
    "Lesiones fatales": "lesiones_fatales",
    "Lesiones incapacitantes": "lesiones_incapacitantes",
    "Lesiones no incapacitantes": "lesiones_no_incapacitantes",
    "Lesiones reportadas no evidentes": "lesiones_no_evidentes",
    "Sin indicacion de lesiones": "sin_lesiones",
    "Dia de la semana del choque": "dia_semana",
    "Mes del choque": "mes",
    "Latitud": "latitud",
    "Longitud": "longitud",
    "Altura": "altura",
    "Direccion calle": "direccion_calle",
    "Calle": "calle",
    "ID siniestro (portal)": "id_portal",
    "Calidad vinculo geo": "calidad_geo",
}
# Columnas de ubicación: no forman parte de la clave de duplicados.
COLS_GEO = ("id_portal", "calidad_geo", "latitud", "longitud", "altura", "direccion_calle", "calle")
# Columnas base (las que definen un siniestro único). Se usa para drop_duplicates.
NOMBRES = [destino for destino in MAPA_COLUMNAS.values() if destino not in COLS_GEO]


def _validar_mapa_columnas():
    """El mapa debe ser inyectivo: dos columnas de origen no pueden compartir destino."""
    destinos = list(MAPA_COLUMNAS.values())
    duplicados = sorted({d for d in destinos if destinos.count(d) > 1})
    if duplicados:
        raise ValueError(f"MAPA_COLUMNAS tiene destinos duplicados: {duplicados}")


_validar_mapa_columnas()


def normalizar_columnas(raw):
    """Renombra las columnas de la base de entrada al vocabulario analítico.

    Valida el contrato antes de tocar nada: si faltan o sobran columnas, falla con un mensaje
    que dice cuáles son, en vez de asignar nombres por posición y corromper los datos en silencio.
    """
    presentes = set(raw.columns)
    esperadas = set(MAPA_COLUMNAS)
    faltantes = sorted(esperadas - presentes)
    sobrantes = sorted(presentes - esperadas)
    if faltantes or sobrantes:
        detalle = []
        if faltantes:
            detalle.append(f"faltan {len(faltantes)}: {faltantes}")
        if sobrantes:
            detalle.append(f"sobran {len(sobrantes)}: {sobrantes}")
        raise ValueError(
            "La base de entrada no cumple el contrato de MAPA_COLUMNAS ("
            + "; ".join(detalle)
            + "). Si el cambio es intencional, actualizá MAPA_COLUMNAS en preparacion.py."
        )
    return raw.rename(columns=MAPA_COLUMNAS)[list(MAPA_COLUMNAS.values())]


DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
FRANJAS = ["Madrugada (0-5)", "Mañana (6-11)", "Tarde (12-17)", "Noche (18-23)"]
NIVELES = ["Fatal", "Incapacitante", "No incapacitante", "Declarada no evidente", "Sin lesión"]
SEVERIDAD = {
    "LESIÓN MORTAL": "Fatal", "LESIÓN INCAPACITANTE": "Incapacitante",
    "LESIÓN NO INCAPACITANTE": "No incapacitante", "LESIÓN DECLARADA, NO EVIDENTE": "Declarada no evidente",
    "SIN INDICIOS DE LESIÓN": "Sin lesión",
}

CLIMA_GRUPO = {
    "DESPEJADO": "Despejado", "NUBLADO/CUBIERTO": "Nublado",
    "LLUVIA": "Lluvia", "LLUVIA HELADA/LLOVIZNA": "Lluvia",
    "NIEVE": "Nieve / hielo", "AGUANIEVE/GRANIZO": "Nieve / hielo", "VENTISCA": "Nieve / hielo",
    "NIEBLA/HUMO/BRUMA": "Niebla / viento / otro", "FUERTE VIENTO CRUZADO": "Niebla / viento / otro",
    "ARENA, TIERRA O POLVO EN SUSPENSIÓN": "Niebla / viento / otro", "OTRO": "Niebla / viento / otro",
    "DESCONOCIDO": "Desconocido",
}
LUZ_GRUPO = {
    "LUZ DEL DÍA": "Día", "AMANECER": "Amanecer / anochecer", "ANOCHECER": "Amanecer / anochecer",
    "OSCURIDAD, CAMINO ILUMINADO": "Noche con alumbrado", "OSCURIDAD": "Noche sin alumbrado",
    "DESCONOCIDO": "Desconocido",
}
ORDEN_CLIMA = ["Despejado", "Nublado", "Lluvia", "Nieve / hielo", "Niebla / viento / otro", "Desconocido"]
ORDEN_LUZ = ["Día", "Amanecer / anochecer", "Noche con alumbrado", "Noche sin alumbrado", "Desconocido"]

FAMILIA = {
    # Velocidad
    "EXCEDER EL LÍMITE DE VELOCIDAD AUTORIZADO": "Velocidad", "EXCEDER LA VELOCIDAD SEGURA PARA LAS CONDICIONES": "Velocidad",
    "NO REDUCIR LA VELOCIDAD PARA EVITAR EL ACCIDENTE": "Velocidad",
    # Alcohol / drogas
    "BAJO LA INFLUENCIA DE ALCOHOL O DROGAS (USAR CUANDO SE REALIZA UNA DETENCIÓN)": "Alcohol / drogas",
    "HABÍA CONSUMIDO ALCOHOL (USAR CUANDO NO SE REALIZA UNA DETENCIÓN)": "Alcohol / drogas",
    # Desobediencia de señales
    "NO RESPETAR LOS SEMÁFOROS": "Desobediencia de señales", "NO RESPETAR LA SEÑAL DE PARE": "Desobediencia de señales",
    "NO RESPETAR LA SEÑAL DE CEDA EL PASO": "Desobediencia de señales", "NO RESPETAR OTRAS SEÑALES DE TRÁNSITO": "Desobediencia de señales",
    "NO RESPETAR LAS MARCAS VIALES": "Desobediencia de señales", "GIRO A LA DERECHA CON LUZ ROJA": "Desobediencia de señales",
    "ADELANTAR A UN AUTOBÚS ESCOLAR DETENIDO": "Desobediencia de señales",
    # Maniobras imprudentes
    "NO CEDER EL DERECHO DE PASO": "Maniobras imprudentes", "SEGUIR DEMASIADO DE CERCA": "Maniobras imprudentes",
    "GIRO INADECUADO O SIN SEÑALIZAR": "Maniobras imprudentes", "ADELANTAMIENTO INADECUADO": "Maniobras imprudentes",
    "USO INADECUADO DEL CARRIL": "Maniobras imprudentes", "MARCHA ATRÁS INADECUADA": "Maniobras imprudentes",
    "CONDUCIR POR EL LADO EQUIVOCADO O EN SENTIDO CONTRARIO": "Maniobras imprudentes",
    "CONDUCCIÓN ERRÁTICA, TEMERARIA, DESCUIDADA, NEGLIGENTE O AGRESIVA": "Maniobras imprudentes",
    # Distracción
    "DISTRACCIÓN DENTRO DEL VEHÍCULO": "Distracción", "DISTRACCIÓN FUERA DEL VEHÍCULO": "Distracción",
    "USO DEL TELÉFONO CELULAR DISTINTO DE MENSAJES DE TEXTO": "Distracción", "ENVÍO DE MENSAJES DE TEXTO": "Distracción",
    "DISTRACCIÓN POR OTRO DISPOSITIVO ELECTRÓNICO (NAVEGADOR, REPRODUCTOR DE DVD, ETC.)": "Distracción",
    # Habilidad / condición del conductor
    "HABILIDAD, CONOCIMIENTO O EXPERIENCIA DE CONDUCCIÓN": "Habilidad / condición del conductor",
    "CONDICIÓN FÍSICA DEL CONDUCTOR": "Habilidad / condición del conductor",
    # Entorno y vía
    "CONDICIONES CLIMÁTICAS": "Entorno y vía", "VISIÓN OBSTRUIDA (SEÑALES, RAMAS DE ÁRBOLES, EDIFICIOS, ETC.)": "Entorno y vía",
    "CONSTRUCCIÓN O MANTENIMIENTO DE LA VÍA": "Entorno y vía", "DEFECTOS DE DISEÑO, SUPERFICIE O SEÑALIZACIÓN DE LA VÍA": "Entorno y vía",
    "RELACIONADO CON UNA PARADA DE AUTOBÚS": "Entorno y vía", "PASOS PEATONALES OBSTRUIDOS": "Entorno y vía",
    "ANIMAL": "Entorno y vía", "MANIOBRA EVASIVA DEBIDO A UN ANIMAL, OBJETO O USUARIO NO MOTORIZADO": "Entorno y vía",
    # Otros
    "EQUIPAMIENTO O ESTADO DEL VEHÍCULO": "Vehículo / otros",
    "BICICLETA AVANZANDO LEGALMENTE CON LUZ ROJA": "Vehículo / otros", "MOTOCICLETA AVANZANDO LEGALMENTE CON LUZ ROJA": "Vehículo / otros",
    # Sin determinar
    "NO SE PUDO DETERMINAR": "Sin determinar", "NO APLICA": "Sin determinar",
}
PALANCA = {
    "Velocidad": "Fiscalización", "Alcohol / drogas": "Fiscalización", "Desobediencia de señales": "Fiscalización",
    "Maniobras imprudentes": "Concientización", "Distracción": "Concientización",
    "Habilidad / condición del conductor": "Concientización",
    "Entorno y vía": "Infraestructura", "Vehículo / otros": "Otros", "Sin determinar": "Sin determinar",
}

# Columna de origen -> (columna derivada, diccionario que la define).
MAPEOS = {
    "clima": ("clima_g", CLIMA_GRUPO),
    "iluminacion": ("luz_g", LUZ_GRUPO),
    "causa_principal": ("familia_causa", FAMILIA),
    "lesion_mas_grave": ("severidad", SEVERIDAD),
}

COLS_REPORTE = ["columna", "columna_destino", "valor", "filas", "porcentaje"]


class CategoriasNoMapeadas(ValueError):
    """La base trae valores que no están en los diccionarios de clasificación."""


class CategoriasNoMapeadasAdvertencia(UserWarning):
    """Aviso de valores sin mapear en modo tolerante (estricto=False)."""


def _validar_palancas():
    """Toda familia de causa tiene que tener una palanca asignada."""
    huerfanas = sorted(set(FAMILIA.values()) - set(PALANCA))
    if huerfanas:
        raise ValueError(f"PALANCA no cubre estas familias de FAMILIA: {huerfanas}")


def _filas(n):
    return f"{n} fila" if n == 1 else f"{n} filas"


class BaseInconsistente(ValueError):
    """La base de entrada no cumple una regla de coherencia interna."""


def _validar_calendario(df):
    """El mes y el día de la semana tienen que coincidir con la fecha del siniestro.

    En el origen el día de la semana está codificado 1 = domingo ... 7 = sábado. Si la base no
    cumple esto, cualquier análisis por día o por mes queda midiendo otra cosa.
    """
    mes_no_coincide = df["fecha"].dt.month != df["mes"]
    dia_no_coincide = ((df["fecha"].dt.day_of_week + 1) % 7 + 1) != df["dia_semana"]
    problemas = []
    if mes_no_coincide.any():
        problemas.append(f"el mes no coincide con la fecha en {_filas(int(mes_no_coincide.sum()))}")
    if dia_no_coincide.any():
        problemas.append(f"el día de la semana no coincide en {_filas(int(dia_no_coincide.sum()))}")
    if problemas:
        raise BaseInconsistente(
            "La base de entrada tiene fechas incoherentes: " + "; ".join(problemas) + "."
        )


_validar_palancas()


def valores_sin_mapear(df):
    """Valores de la base que ningún diccionario de clasificación reconoce.

    Devuelve un DataFrame con una fila por valor problemático: columna de origen, columna
    derivada afectada, el valor, cuántas filas lo tienen y qué porcentaje representan.
    """
    filas = []
    for origen, (destino, mapa) in MAPEOS.items():
        sobrantes = df.loc[~df[origen].isin(list(mapa)), origen]
        if sobrantes.empty:
            continue
        for valor, n in sobrantes.value_counts(dropna=False).items():
            filas.append({
                "columna": origen,
                "columna_destino": destino,
                "valor": "<nulo>" if pd.isna(valor) else str(valor),
                "filas": int(n),
                "porcentaje": round(100 * n / len(df), 4),
            })
    return pd.DataFrame(filas, columns=COLS_REPORTE)


def validar_categorias(df, estricto=True):
    """Verifica que todas las categorías de la base estén clasificadas.

    estricto=True (por defecto) lanza CategoriasNoMapeadas con el detalle completo.
    estricto=False emite una advertencia y deja seguir: los valores desconocidos quedan como
    nulos en su columna derivada y, por lo tanto, no aparecen en los agrupamientos.
    """
    reporte = valores_sin_mapear(df)
    if reporte.empty:
        return reporte

    detalle = "\n".join(
        f"  - {fila.columna}: {fila.valor!r} ({_filas(fila.filas)}, {fila.porcentaje:.4f} %)"
        for fila in reporte.itertuples()
    )
    mensaje = (
        f"Hay {len(reporte)} valor(es) sin mapear en {reporte['columna'].nunique()} columna(s) "
        f"({int(reporte['filas'].sum())} filas afectadas):\n{detalle}\n"
        "Agregalos a los diccionarios de preparacion.py (CLIMA_GRUPO, LUZ_GRUPO, FAMILIA, "
        "SEVERIDAD) o llamá a cargar_base(estricto=False) para continuar dejándolos sin "
        "clasificar."
    )
    if estricto:
        raise CategoriasNoMapeadas(mensaje)
    warnings.warn(mensaje, CategoriasNoMapeadasAdvertencia, stacklevel=2)
    return reporte



def preparar_base(ruta=RUTA_GEO, estricto=True):
    """Base analítica completa: todos los años, sin duplicados y con las variables derivadas.

    estricto=True falla si la base trae categorías desconocidas; estricto=False las deja pasar
    con una advertencia (ver validar_categorias).

    Deja en `df.attrs` el diagnóstico de la carga: `filas_origen` (registros del parquet) y
    `duplicados_eliminados`, para que quien reporta calidad del dato no tenga que releer la base.
    """
    crudo = pd.read_parquet(ruta)
    filas_origen = len(crudo)
    df = normalizar_columnas(crudo)
    validar_categorias(df, estricto=estricto)

    df["fecha"] = pd.to_datetime(df["fecha"], format="%m/%d/%Y")
    hora = pd.to_datetime(df["hora"], format="%H:%M:%S")
    df["hora_num"], df["minuto"] = hora.dt.hour, hora.dt.minute
    df["anio"] = df["fecha"].dt.year
    _validar_calendario(df)
    # En el origen el día de la semana está codificado 1 = domingo ... 7 = sábado
    df["dia"] = pd.Categorical(df["dia_semana"].map(dict(zip([2, 3, 4, 5, 6, 7, 1], DIAS))), categories=DIAS, ordered=True)
    df["mes_nombre"] = pd.Categorical(df["mes"].map(dict(enumerate(MESES, 1))), categories=MESES, ordered=True)
    df["fin_de_semana"] = df["dia"].isin(["Sáb", "Dom"])
    df["franja"] = pd.Categorical(pd.cut(df["hora_num"], [-1, 5, 11, 17, 23], labels=FRANJAS), categories=FRANJAS, ordered=True)

    df["con_heridos"] = df["lesiones_totales"] > 0
    df["grave"] = (df["lesiones_fatales"] + df["lesiones_incapacitantes"]) > 0
    df["fatal"] = df["lesiones_fatales"] > 0
    df["severidad"] = pd.Categorical(df["lesion_mas_grave"].map(SEVERIDAD), categories=NIVELES, ordered=True)

    df["clima_g"] = pd.Categorical(df["clima"].map(CLIMA_GRUPO), categories=ORDEN_CLIMA, ordered=True)
    df["luz_g"] = pd.Categorical(df["iluminacion"].map(LUZ_GRUPO), categories=ORDEN_LUZ, ordered=True)
    df["familia_causa"] = df["causa_principal"].map(FAMILIA)
    df["palanca"] = df["familia_causa"].map(PALANCA)

    df = df.drop_duplicates(subset=NOMBRES).reset_index(drop=True)
    df.attrs["filas_origen"] = filas_origen
    df.attrs["duplicados_eliminados"] = filas_origen - len(df)
    return df


def cargar_base(desde=ANIO_DESDE, hasta=ANIO_HASTA, ruta=RUTA_GEO, estricto=True):
    """Base analítica del período de análisis, lista para los notebooks y el tablero.

    Filtra `preparar_base()` a los años [desde, hasta] y conserva el diagnóstico en `df.attrs`.
    """
    completa = preparar_base(ruta, estricto=estricto)
    df = completa[completa["anio"].between(desde, hasta)].reset_index(drop=True)
    df.attrs.update(completa.attrs)
    return df
