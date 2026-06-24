# Setup BOT-ARQ

El proyecto vive en git y se publica con GitHub Pages. Ya no se instala por ZIP.

## Para trabajar en el repo

1. Clona el repositorio (o trabaja en una rama desde GitHub Desktop). No borres `.git`.
2. Edita el frontend (`index.html`, `script.js`, `style.css`) o el motor según corresponda.
3. Commit y push.
4. GitHub Pages publica el dashboard automáticamente.

## Para forzar una actualización de datos

- Pestaña **Actions → "BOT-ARQ" → Run workflow** con `force=true`.
- Revisa que se actualicen `datos_acciones.json` y `paper/paper_state.json`.

## Configuración

La configuración operativa real (capital, riesgo, límites, reglas V4.4) está en:

`config/system_config.json`

## Notas

- No edites a mano los archivos generados (`datos_acciones.json`, `historial_senales.json`, `paper/*.json`): los reescribe GitHub Actions.
- Los reportes `*.xlsx` se generan pero no se versionan.
- Tras desplegar cambios de `script.js`/`style.css`, el cache-busting por versión (`?v=...`) evita que el navegador sirva una copia vieja.
