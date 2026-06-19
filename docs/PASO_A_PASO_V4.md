# Paso a paso para implementar BOT-ARQ V4

## 1. Descargar y descomprimir ZIP

Descomprime:

`BOT-ARQv4_PAPER_TRADING_ENGINE.zip`

## 2. Copiar al repositorio

Copia TODO el contenido dentro de la carpeta local de tu repositorio.

Debe quedar en la raíz:

- `analizador_acciones.py`
- `index.html`
- `script.js`
- `style.css`
- `.github/workflows/analizar.yml`
- `paper/`
- `engine/`
- `config/`
- `docs/`

No debe quedar dentro de una carpeta adicional.

## 3. Subir con GitHub Desktop

1. Abre GitHub Desktop.
2. Revisa los cambios.
3. Commit:
   `Subir BOT-ARQ V4 Paper Trading Engine`
4. Push origin.

## 4. Revisar GitHub Actions

En GitHub:

Actions → BOT-ARQ v4 - Paper Trading Engine

Ejecuta manualmente con:

Run workflow → force = true

## 5. Revisar archivos generados

Después de correr, deben existir o actualizarse:

- `paper/paper_portfolio.json`
- `paper/paper_orders.json`
- `paper/paper_trades.json`
- `paper/paper_risk.json`
- `paper/paper_status.json`
- `paper/paper_state.json`

## 6. Revisar la página

La página debe mostrar un nuevo bloque:

`BOT-ARQ V4 · Paper Trading Engine`

Si no lo ves:
- espera 1 a 3 minutos
- recarga con Ctrl + F5
- revisa que GitHub Pages esté en branch main / root

## 7. Seguridad

Esta versión sigue siendo simulada.
No ejecuta órdenes reales.
