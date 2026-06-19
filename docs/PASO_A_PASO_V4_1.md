# Paso a paso para implementar V4.1

## 1. Descomprimir ZIP

Descomprime `BOT-ARQv4_1_DASHBOARD_CLEANUP_PRO.zip`.

## 2. Copiar contenido

Entra a la carpeta descomprimida y copia TODO el contenido.

Pégalo dentro de la carpeta local de tu repositorio, donde ya está `.git`.

Debe quedar en la raíz:

- `.github/`
- `config/`
- `docs/`
- `engine/`
- `execution/`
- `paper/`
- `scripts/`
- `analizador_acciones.py`
- `index.html`
- `script.js`
- `style.css`
- `README.md`

## 3. Reemplazar

Cuando Windows pregunte si deseas reemplazar archivos, acepta reemplazar.

## 4. No borrar `.git`

Nunca borres la carpeta `.git`.

## 5. Revisar cambios en GitHub Desktop

Commit sugerido:

`Subir BOT-ARQ V4.1 Dashboard Cleanup Pro`

Luego `Push origin`.

## 6. Si salen conflictos

Si son archivos generados:
- `datos_acciones.json`
- `historial_senales.json`
- `analisis_acciones.xlsx`
- `historial_senales.xlsx`
- `paper/*.json`

normalmente conserva la versión remota o la más reciente.

## 7. Ejecutar Actions

GitHub → Actions → `BOT-ARQ v4.1 - Dashboard Cleanup Pro` → Run workflow → force=true.

## 8. Ver página

Refresca la página con Ctrl + F5.
Debe verse el nuevo dashboard con:
- Panel ejecutivo
- Alertas operativas
- Paper Trading Engine
- Top oportunidades
- Vistas avanzadas colapsables
