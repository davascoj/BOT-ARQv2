# BOT-ARQ V4.2 - Arquitectura actual

## Flujo

GitHub Actions → `analizador_acciones.py` → carga `config/system_config.json` → analiza mercado → actualiza historial → exporta paper trading → actualiza dashboard.

## Componentes

- `analizador_acciones.py`: motor principal actual.
- `engine/config_loader.py`: carga configuración real del motor.
- `engine/paper_trading_engine.py`: exporta cartera, órdenes, trades, riesgo y estado paper.
- `config/system_config.json`: configuración operativa real.
- `paper/*.json`: estado derivado de paper trading.
- `index.html`, `script.js`, `style.css`: dashboard web.
