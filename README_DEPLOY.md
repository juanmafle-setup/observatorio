# Dashboard Observatorio Vial · Chicago

Dashboard estático (HTML + Chart.js) con datos derivados de los CSV del proyecto.

## Publicar en Vercel
1. Descomprimí este paquete.
2. Subí **index.html** y **data.json** a la raíz del repositorio GitHub que conectaste con Vercel.
3. En Vercel, entrá al proyecto → **Deployments** → **Redeploy** (o hacé un commit/push).
4. Vercel publica automáticamente. La página principal es `index.html`.

No requiere build command ni framework. `data.json` debe permanecer junto a `index.html`.
Los gráficos usan Chart.js desde CDN, por lo que el navegador necesita internet.

## Qué incluye
- KPIs y selector de año (2018–2024).
- Torta: siniestros con/sin heridos reportados.
- Barras: evolución anual, zonas con mayor volumen y graves observados vs esperados por franja.
- Torta: palanca dominante por zona.
- Tabla de prioridad territorial.

## Nota metodológica
El dashboard visualiza los CSV analíticos ya generados en el repositorio. Los conteos describen siniestros registrados; no equivalen automáticamente a riesgo. Las comparaciones de riesgo dependen de la exposición y de la metodología del proyecto. La categoría “sin heridos reportados” se calcula como siniestros menos siniestros con heridos.
