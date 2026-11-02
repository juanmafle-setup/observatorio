# Solicitud de análisis de siniestralidad vial

**De:** Ing. Marina Solá — Subsecretaria de Seguridad Vial
**Área:** Oficina de Seguridad Vial — Departamento de Transporte de la Ciudad de Chicago (CDOT)
**Para:** Grupo 1 de Ciencia de Datos
**Asunto:** Diagnóstico de accidentología vial y priorización de intervenciones

---

## 1. Quiénes somos

Somos la Oficina de Seguridad Vial del Departamento de Transporte de la Ciudad de Chicago (Illinois, Estados Unidos), una ciudad de aproximadamente 2,7 millones de habitantes. Trabajamos junto con el Departamento de Policía de Chicago (CPD), que labra el acta de cada siniestro con daño material relevante o personas heridas, y con el área de Obras Viales. Dentro de la oficina funciona el Observatorio Vial, que centraliza el registro de siniestros.

## 2. Los datos que manejamos hoy

Cada siniestro que atiende la policía queda cargado en nuestra base interna, una fila por hecho, con esta información:

- **Cuándo:** fecha del siniestro, hora, día de la semana, mes, y fecha en que se notificó formalmente a la policía.
- **Condiciones del entorno:** clima, condición de iluminación, estado de la superficie de la calzada (seca, mojada, helada), defectos de la vía, alineación de la calle (recta, curva).
- **Dónde:** latitud y longitud, tipo de vía (avenida, calle local, ruta), cantidad de carriles, si ocurrió en una intersección.
- **Qué pasó:** tipo de choque (frontal, lateral, por alcance, vuelco, atropello a peatón, etc.), si hubo fuga del responsable, cantidad de vehículos involucrados, magnitud del daño material.
- **Por qué (según el acta policial):** causa principal y causa secundaria atribuida (exceso de velocidad, distracción, no respetar prioridad de paso, condiciones climáticas, etc.).
- **Consecuencias:** lesión más grave registrada en el hecho, y desglose de heridos por gravedad — fatales, incapacitantes, no incapacitantes, reportados sin evidencia visible, sin indicios de lesión.

Esto vive en un sistema heredado de planillas Excel, con varios años de historial acumulado. No hay datos identificatorios de las personas involucradas — solo el hecho vial en sí. Sabemos que la carga tiene baches: campos vacíos, causas clasificadas de forma subjetiva por el oficial de turno, y que la enorme mayoría de los registros son choques solo con daño material (los fatales son una fracción chica).

## 3. El problema que tenemos

En los últimos dos años los siniestros con heridos vienen en aumento, y varios hechos fatales tuvieron fuerte repercusión en los medios locales. Eso puso el tema en la agenda del Concejo Municipal (City Council), que nos está pidiendo explicaciones y acciones concretas.

El punto es que hoy no tenemos capacidad analítica real:

- El Observatorio Vial arma un informe mensual manual con conteos simples (total de siniestros, total de heridos), pero no cruza variables — no sabemos con rigor si los siniestros graves se concentran en ciertos horarios, ciertas condiciones climáticas, o ciertos tramos de la ciudad.
- Cuando pedimos presupuesto para semáforos, reductores de velocidad o mejor iluminación, no podemos justificar "por qué esa esquina y no otra" con datos objetivos. Terminamos priorizando por reclamos vecinales o exposición mediática, no por riesgo real medido.
- Intuimos patrones (por ejemplo, más siniestros graves de noche con lluvia en ciertas avenidas) pero no los tenemos confirmados.
- La aseguradora que cubre la flota municipal y la póliza de responsabilidad civil de la ciudad nos está pidiendo cada vez más información para renegociar primas, y no tenemos reportes que sirvan de respaldo.
- Necesitamos poder mostrarle al alcalde y al Concejo Municipal un tablero con evidencia, no una tabla de Excel con totales.

## 4. Qué le estamos pidiendo al grupo 1 de Ciencia de Datos

- Análisis exploratorio del historial completo de siniestros (últimos 3 a 5 años) para entender su composición real: severidad, causas, tipos de choque, condiciones asociadas.
- Identificación de patrones horarios, por día de semana y por mes, cruzados con clima e iluminación, para saber en qué franjas se concentra el riesgo real (no percibido).
- Un mapa de puntos calientes (hotspots geográficos) que cruce latitud/longitud con severidad, para poder priorizar intervenciones de infraestructura con criterio.
- Segmentación por causa principal, para saber si conviene invertir más en fiscalización (velocidad, alcohol), en infraestructura (semaforización, iluminación, señalización) o en campañas de concientización.
- Un tablero interactivo que el equipo del Observatorio Vial pueda consultar y actualizar mes a mes sin depender de un analista externo para cada corte.
- Un listado priorizado de recomendaciones accionables (por ejemplo: top 10 intersecciones o tramos de mayor riesgo, franjas horarias para reforzar patrullaje).
- Si los datos lo permiten, un modelo simple que estime el riesgo relativo por zona y horario — no necesitamos predicción en tiempo real, sino un criterio objetivo para priorizar dónde intervenir primero.

## 5. Restricciones y contexto del proyecto

- No tenemos científico de datos ni analista de BI en planta. El proyecto se ejecutaría enteramente con el proveedor externo, con el Observatorio Vial como contraparte funcional para validar hallazgos y facilitar el acceso a los datos.
- La aprobación de presupuesto pasa por compra directa municipal; tenemos margen para arrancar con un proyecto piloto acotado (diagnóstico + tablero) antes de comprometer fondos para un contrato de mantenimiento anual.
- Nos gustaría tener el diagnóstico y el tablero listos antes de la sesión presupuestaria del Concejo Municipal, para poder pedir fondos de obra vial con datos concretos en mano.
- Somos conscientes de que la calidad del dato de origen (carga policial en el momento del hecho) no es perfecta, y esperamos que el análisis lo contemple en vez de asumir que los datos son perfectos.

## 6. Cómo mediríamos el éxito

- Entrega de un informe de diagnóstico y un tablero interactivo funcionando.
- Al menos tres intervenciones concretas, priorizadas con datos, presentadas y defendibles ante el Concejo Municipal.
- Una línea base clara de siniestros con heridos por zona, para poder medir en 12 meses si las intervenciones aplicadas realmente redujeron la siniestralidad donde se actuó.
- Que el equipo del Observatorio Vial quede en condiciones de usar el tablero de forma autónoma para sus reportes mensuales, sin depender de un tercero para cada actualización.

## 7. Plazos y presupuesto de referencia

- Plazo deseado para el diagnóstico inicial y el primer tablero: 4 a 6 semanas desde el inicio.
- Preferimos un esquema de piloto acotado, con alcance y presupuesto cerrados de antemano, y una segunda etapa opcional de mantenimiento/actualización del tablero si el resultado del piloto es satisfactorio.
- Quedamos abiertos a que nos propongan el esquema de trabajo y el presupuesto que mejor se ajuste a este alcance.

## 8. Contacto

Ing. Marina Solá
Oficina de Seguridad Vial — Departamento de Transporte de la Ciudad de Chicago
marina.sola@ejemplo.com (contacto ficticio, a los fines del trabajo práctico)
