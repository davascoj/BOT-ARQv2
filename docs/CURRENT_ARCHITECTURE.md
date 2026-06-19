# BOT-ARQ V4.1 - Arquitectura actual

## Estado

BOT-ARQ V4.1 conserva el motor real original en `analizador_acciones.py` y agrega una capa V4 de paper trading formalizada en `engine/paper_trading_engine.py`.

## Flujo

GitHub Actions → `analizador_acciones.py` → señales/historial → `engine/paper_trading_engine.py` → archivos `paper/*.json` → dashboard GitHub Pages.

## Componentes

- `analizador_acciones.py`: motor principal actual.
- `engine/paper_trading_engine.py`: exporta cartera, órdenes, trades, riesgo y estado V4.
- `paper/*.json`: datos derivados para dashboard y auditoría.
- `index.html`, `script.js`, `style.css`: dashboard V4.1 limpio.
- `.github/workflows/analizar.yml`: automatización cada 5 minutos en horario de mercado.
