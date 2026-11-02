# Siniestralidad vial — Ciudad de Chicago

Trabajo práctico de Ciencia de Datos (Grupo 1). Diagnóstico de los siniestros viales de Chicago
(2018–2024) y modelo de riesgo relativo por zona y horario, pedido por la Oficina de Seguridad Vial
(CDOT) para priorizar intervenciones con datos en vez de reclamos o exposición mediática.

- El pedido del cliente está en [brief-cliente-siniestralidad-vial.md](brief-cliente-siniestralidad-vial.md).
- El plan de trabajo en 6 fases está en [propuesta.md](propuesta.md).

**Estado:** fases 3 (análisis exploratorio) y 4 (modelo de riesgo) terminadas. Faltan la 5 (tablero
interactivo) y la 6 (informe, intervenciones y cierre).

> **Si ya tenías el repositorio clonado:** la historia de `main` se reescribió el 2026-10-26 para
> pasar los datos a Git LFS. Un clon anterior no se actualiza con `git pull`: hay que reubicarlo y
> bajar los datos aparte. Los pasos están en [Clones anteriores a la migración](#clones-anteriores-a-la-migración).

## Archivos

### Documentación

| Archivo | Qué es |
|---|---|
| `brief-cliente-siniestralidad-vial.md` | Pedido del cliente: problema, datos disponibles, entregables y criterios de éxito. |
| `propuesta.md` | Propuesta de trabajo dividida en 6 fases. |

### Datos de entrada

| Archivo | Qué es |
|---|---|
| `dataset.xlsx` | Base original del Observatorio Vial: una fila por siniestro, sin ubicación. Es un extracto traducido del dataset abierto *Traffic Crashes – Crashes* de Chicago. |
| `dataset_geo.parquet` | La base original más latitud, longitud, dirección y calidad del vínculo. La genera `enriquecer_coordenadas.py`. |
| `areas_comunitarias.geojson` | Límites de las 77 áreas comunitarias de Chicago (las "zonas" del modelo). La descarga la Fase 4 si no existe. |
| `aforos_segmentos.parquet` | AADT (tránsito diario promedio) de 2.008 segmentos de calle, 2022-2024, con el punto medio de cada segmento. Lo genera `aforos.py` y lo usa la Fase 4 para contrastar el proxy de exposición. |

### Código

| Archivo | Qué hace |
|---|---|
| `enriquecer_coordenadas.py` | Descarga del portal de datos abiertos de Chicago las columnas de ubicación y las vincula con cada registro de `dataset.xlsx` (por fecha, hora, vehículos, lesiones y causa). Genera `dataset_geo.parquet`. |
| `config.py` | Ventanas temporales del proyecto: período de análisis, corte de la validación fuera de muestra y fecha de corte de la descarga del portal. Es el único archivo con años. |
| `preparacion.py` | Única implementación de la preparación analítica: renombra columnas por nombre, valida el calendario y las categorías, crea las variables derivadas (severidad, franjas, grupos de clima e iluminación, familia de causa, palanca), quita duplicados y recorta el período de `config.py`. La usan las dos fases y el tablero de la Fase 5. |
| `aforos.py` | Descarga el AADT por segmento del portal de Chicago, normaliza el nombre de la calle y asigna a cada siniestro el aforo del segmento más cercano de **su misma vía**. Genera `aforos_segmentos.parquet`. |
| `Fase 3.ipynb` | Análisis exploratorio y diagnóstico: calidad del dato, composición de los siniestros, patrones por hora, día, mes, clima e iluminación, y puntos críticos geográficos. |
| `Fase 4.ipynb` | Modelado de riesgo relativo: viabilidad, Modelo A (frecuencia de graves por zona y horario, Poisson), Modelo B (qué vuelve grave a un siniestro, logística), índice de priorización por zona, puntos críticos corregidos con Empírico Bayesiano, contraste del proxy de exposición con el aforo real del portal y protocolo de validación con el Observatorio. Tiene un anexo que explica los conceptos estadísticos. |

### Configuración y tests

| Archivo | Qué es |
|---|---|
| `requirements.txt` | Dependencias de ejecución con versiones exactas (Python 3.11). |
| `requirements-dev.txt` | Suma `pytest` y `ruff` a las anteriores; se instala solo para desarrollar. |
| `pyproject.toml` | Configuración de `ruff` (reglas y excepciones) y de `pytest` (`testpaths`). |
| `.gitattributes` | Marca los `*.ipynb` para que git los guarde sin salidas (filtro `nbstripout`) y los muestre como diff de notebook, y manda los `*.xlsx` y `*.parquet` a Git LFS. |
| `tests/` | Tests del contrato de columnas, de las categorías, de las ventanas temporales, de los notebooks, de la base completa, del emparejamiento del aforo y del versionado con LFS. Tardan unos 20 segundos. |
| `.github/workflows/ci.yml` | Integración continua: descarga los datos por LFS y corre `ruff check .` y `pytest -q` en cada push a `main` y en cada pull request. |
| `LICENSE` | Licencia MIT. |

### Salidas (generadas por los notebooks)

| Archivo | Lo genera | Contenido |
|---|---|---|
| `mapa_hotspots.html` | Fase 3 | Mapa interactivo de puntos críticos (grilla de ~150 m con índice de severidad). |
| `mapa_riesgo_zonas.html` | Fase 4 | Mapa interactivo del riesgo relativo por área comunitaria. |
| `riesgo_zonas.csv` | Fase 4 | Ficha por zona: prioridad, graves por año, riesgo relativo con intervalo de confianza, horario crítico y palanca dominante. |
| `riesgo_zona_horario.csv` | Fase 4 | Riesgo relativo por cada combinación zona × horario. |
| `puntos_criticos_eb.csv` | Fase 4 | Ranking de puntos críticos corregido por regresión a la media, con la posición que cada punto ocupa según los otros proxies de exposición (`rank_conteo`, `rank_epdo`, `rank_aadt`) y la marca `estable_top20`. |
| `efectos_modelo_B.csv` | Fase 4 | Odds ratios del modelo de severidad (Modelo B). |
| `linea_base_zonas.csv` | Fase 4 | Siniestros, con heridos, graves y fatales por zona y año: la línea base para medir el impacto a 12 meses. |
| `validacion_observatorio.csv` | Fase 4 | Planilla para que el Observatorio confirme en terreno las zonas y puntos priorizados, con `verificacion_prioritaria` y su motivo en los puntos. |

En `puntos_criticos_eb.csv`, `rank_aadt` es la posición del punto si la exposición se midiera con el
aforo del portal en lugar del volumen de siniestros. Donde la celda no tiene aforo suficiente se usa
el AADT mediano de la ciudad como imputación neutra (sección 6.3 de la Fase 4). `estable_top20` dice
`sí` solo cuando el punto está en el top 20 con **los cuatro** proxies: es el núcleo que no depende
de cómo se mida la exposición.

Los mapas `.html` se abren con doble clic en cualquier navegador. Los `.csv` están en UTF-8 con BOM,
así que Excel los abre con los acentos bien.

## Cómo usarlo

Requisitos: Python 3.11 o superior, Git y Git LFS (los datos de entrada van en LFS).

```bash
# 1. Clonar e instalar dependencias
git lfs install                  # una vez por máquina: sin esto los datos llegan como punteros
git clone https://github.com/FranciscoCalahorra/Ciencia_Datos.git
cd Ciencia_Datos
python -m venv .venv
.venv\Scripts\activate          # Windows  (en macOS/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt

# 2. Abrir los notebooks
jupyter notebook
```

Si vas a editar y commitear los notebooks hace falta además activar el filtro que los guarda sin
salidas: está explicado en [Notebooks sin salidas](#notebooks-sin-salidas).

La base ya viene en el repo (`dataset_geo.parquet`), así que una vez clonado no hace falta descargar
nada del portal para ejecutar las dos fases.

### Datos con Git LFS

`dataset.xlsx` (22,9 MB) y `dataset_geo.parquet` (29,5 MB) se versionan con
[Git LFS](https://git-lfs.com): en el historial de git queda un puntero de 133 bytes y el archivo
viaja aparte. Por eso el clon del código pesa 8,6 MB y no 57 MB, y un cambio futuro de los datos no
duplica ese peso en el historial. El primer clon descarga además los 52,5 MB de datos; después no se
vuelven a bajar salvo que cambien.

Git LFS se instala una vez por máquina y después el clon lo usa solo:

```bash
git lfs install
git clone https://github.com/FranciscoCalahorra/Ciencia_Datos.git
```

Si el clon se hizo sin LFS, los archivos quedan con 133 bytes y `pandas` no los puede abrir. Se
arregla instalando LFS y bajando los objetos, sin volver a clonar:

```bash
git lfs install
git lfs pull
```

`aforos_segmentos.parquet` también va en LFS aunque pesa 49 KB: la regla es por extensión y así
ningún `.parquet` vuelve al historial normal. `tests/test_repositorio.py` verifica que los binarios
sigan entrando como punteros.

#### Clones anteriores a la migración

Un clon hecho antes del 2026-10-26 tiene la historia vieja, con los binarios dentro de git. No se
puede actualizar con `git pull` ni mergear contra `main`: la historia es otra. Si no hay trabajo
local pendiente, se reubica con cuatro comandos:

```bash
git fetch origin
git reset --hard origin/main
git lfs install
git lfs pull
```

`git reset --hard` descarta los cambios sin commitear y los commits locales que no estén en
`origin/main`. Si hay trabajo en curso, guardarlo antes en otra rama (`git switch -c respaldo`) o en
un parche (`git diff > respaldo.patch`) y reaplicarlo después sobre el nuevo `main`.

### Orden de ejecución

1. **`enriquecer_coordenadas.py`** — solo hace falta si no está `dataset_geo.parquet` o si cambia
   `dataset.xlsx`. Descarga la base completa de Chicago (puede tardar varios minutos) y la guarda en
   `chicago_crashes_cache.parquet` para no volver a bajarla.
   ```bash
   python enriquecer_coordenadas.py
   ```
2. **`aforos.py`** — solo hace falta si no está `aforos_segmentos.parquet` o si se quiere actualizar
   el aforo. Descarga una consulta agregada del portal (unos segundos) y guarda el parquet.
   ```bash
   python aforos.py
   ```
3. **`Fase 3.ipynb`** — ejecutar todas las celdas. Genera `mapa_hotspots.html`.
4. **`Fase 4.ipynb`** — ejecutar todas las celdas. Genera el mapa de zonas y todos los `.csv`.

Todos los archivos tienen que estar en la misma carpeta: los notebooks y scripts usan rutas relativas.

Para usar la base limpia desde otro notebook o script:

```python
from preparacion import cargar_base, preparar_base

df = cargar_base()          # el período de config.py, ya preparado
completa = preparar_base()  # todos los años, sin recortar: para diagnósticos de cobertura
```

`cargar_base()` deja en `df.attrs` el diagnóstico de la carga: `filas_origen` (registros del parquet)
y `duplicados_eliminados`. Los notebooks lo usan para reportar calidad del dato sin releer la base.

### Notebooks sin salidas

Los `.ipynb` se versionan sin salidas: en el repositorio queda el código y nada más. Las imágenes,
tablas y mapas que genera cada ejecución no se commitean. Así los diffs muestran qué cambió de
código y no megabytes de base64, y los conflictos de merge se pueden resolver.

El filtro se activa una vez por clon:

```bash
python -m pip install -r requirements-dev.txt
python -m nbstripout --install
```

`nbstripout --install` escribe la configuración en `.git/config`, que no se versiona, así que cada
clon nuevo repite el paso. Sin él git igual acepta el notebook, pero lo guarda con todas las
salidas adentro.

Para revisar qué produce una fase se ejecuta el notebook y se mira el HTML resultante en `build/`
(ignorado por git):

```bash
jupyter nbconvert --to html --execute "Fase 4.ipynb" --output-dir build
```

Eso también regenera los entregables de la raíz. Si el análisis no cambió, los `.csv` salen
idénticos y los mapas `.html` cambian solo por identificadores internos de folium, así que se
descartan con `git restore mapa_hotspots.html mapa_riesgo_zonas.html`.

### Tests y estilo

```bash
python -m pip install -r requirements-dev.txt   # pytest y ruff, además de las dependencias de ejecución
python -m pytest -q                             # contrato de columnas, ventanas, base, aforo y LFS
python -m ruff check .                          # estilo e imports, notebooks incluidos
```

Los tests leen `dataset_geo.parquet`, así que hay que correrlos desde la raíz del repo y con los datos
de LFS descargados (`git lfs pull`). Lo mismo corre en GitHub Actions en cada push a `main` y en cada
pull request; si el workflow se pone en rojo, el detalle está en la pestaña *Actions*.

### Actualizar el período de análisis

Todo lo que depende de fechas está en `config.py` y ningún otro archivo repite años:

```python
ANIO_DESDE = 2018              # primer año del análisis
ANIO_HASTA = 2024              # último año completo
ANIO_CORTE_VALIDACION = 2022   # se entrena hasta acá; el año siguiente abre la prueba
FECHA_CORTE_PORTAL = "2025-02-01"   # None descarga todo lo disponible en el portal
```

Para incorporar un año nuevo:

1. Cambiar `ANIO_HASTA` en `config.py` y, si el corte de validación también se corre, `ANIO_CORTE_VALIDACION`.
2. Si hay que traer siniestros nuevos del portal, borrar `chicago_crashes_cache.parquet` y volver a
   correr `python enriquecer_coordenadas.py`.
3. Volver a ejecutar las dos fases. Los rangos de fechas, los títulos de los gráficos y el período de
   entrenamiento y prueba de los modelos salen de esas constantes.

`config.py` valida la coherencia al importarse y falla con un mensaje claro si el corte no deja al menos
un año de prueba. Un test recorre los módulos y las celdas de código de los notebooks para que no vuelva
a aparecer un año escrito a mano.

## Datos y limitaciones

- La fuente es la carga policial en el momento del hecho: hay campos vacíos, causas atribuidas de
  forma subjetiva y horas redondeadas. La sección 2 de la Fase 3 documenta estos problemas y cómo se
  tratan.
- La ubicación no viene en la base del Observatorio: se recuperó vinculando cada registro con el
  dataset abierto de Chicago. La columna de calidad del vínculo indica qué tan confiable es cada caso.
- Fuente pública: [Traffic Crashes – Crashes, City of Chicago Data Portal](https://data.cityofchicago.org/Transportation/Traffic-Crashes-Crashes/85ca-t3if).

## Licencia

MIT. Ver [LICENSE](LICENSE).

