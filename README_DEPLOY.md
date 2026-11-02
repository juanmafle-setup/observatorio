# Landing rediseñada · Observatorio Vial

Este paquete contiene:
- `index.html`: nueva landing/dashboard (reemplaza la página principal).
- `data.json`: export de las salidas analíticas CSV del repositorio para que los gráficos se rendericen en el navegador.

## Cómo integrarlo al repositorio ya conectado a Vercel
1. Descomprimí este ZIP.
2. Copiá `index.html` y `data.json` a la raíz del repositorio que alimenta `observatorio-vial-grupo1.vercel.app`.
3. Conservá en esa raíz los archivos existentes `mapa_hotspots.html` y `mapa_riesgo_zonas.html` (la landing los enlaza).
4. Commit y push a la rama que Vercel tiene conectada. No crees un proyecto Vercel nuevo.
5. Si el proyecto es estático, en Vercel usá Framework Preset `Other` y sin Build Command.

La página usa Chart.js desde CDN; para ver los gráficos necesita conexión a internet.
