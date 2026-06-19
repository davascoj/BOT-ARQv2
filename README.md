# BOT-ARQ v4.2 - Configuración Real del Motor

Sistema automatizado de análisis técnico, señales simuladas, paper trading y dashboard web.

## Estado actual

✅ GitHub Pages  
✅ GitHub Actions cada 5 minutos  
✅ Señales BUY / HOLD / SELL  
✅ Compra y venta simulada  
✅ Cierre por stop / objetivo / señal  
✅ Paper Trading Engine  
✅ Dashboard V4.1 limpio  
✅ Configuración real desde `config/system_config.json`  

## Cambio principal de V4.2

Antes, las reglas del bot estaban principalmente dentro de `analizador_acciones.py`.

Ahora la configuración operativa está en:

`config/system_config.json`

El código mantiene valores por defecto seguros si el archivo falta o tiene error.

## Archivos importantes

- `analizador_acciones.py`: motor principal.
- `engine/config_loader.py`: carga configuración real.
- `engine/paper_trading_engine.py`: exporta paper trading.
- `config/system_config.json`: configuración operativa.
- `paper/*.json`: datos paper derivados.
- `index.html`, `script.js`, `style.css`: dashboard.
- `.github/workflows/analizar.yml`: automatización.

## Documentación

- `docs/V4_2_CONFIGURACION_REAL_MOTOR.md`
- `docs/PASO_A_PASO_V4_2.md`
- `docs/CURRENT_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`

## Seguridad

No ejecuta dinero real.  
Broker real sigue OFF.  
Este sistema continúa en paper trading / simulación.
