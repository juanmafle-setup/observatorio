# Dashboard Observatorio Vial · listo para Vercel

## Publicar (sin Python / sin build)
1. Descomprimí este ZIP.
2. Subí **todo el contenido** de esta carpeta a la raíz del repositorio GitHub conectado a Vercel (index.html, data.json y los dos mapas HTML).
3. En Vercel → Settings → Build and Deployment:
   - Framework Preset: **Other**
   - Build Command: vacío / Override desactivado
   - Output Directory: vacío (o `.`)
   - Install Command: vacío / Override desactivado
4. Deployments → Redeploy, o hacé commit/push a GitHub.

No requiere Python ni instalación de dependencias. Los gráficos usan Chart.js desde CDN.

## Archivos
- `index.html`: dashboard interactivo responsive.
- `data.json`: datos preparados desde CSVs del proyecto (2018–2024).
- `mapa_hotspots.html` y `mapa_riesgo_zonas.html`: mapas interactivos existentes.

Nota: la torta de heridos representa siniestros con heridos vs sin heridos; no es un conteo de personas lesionadas.
