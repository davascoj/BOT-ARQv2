# BOT-ARQ V4 - Paper Trading Engine

## Qué cambia en V4

Esta versión no reemplaza tu simulación actual: la formaliza como un motor profesional de paper trading.

El bot ya abría y cerraba operaciones simuladas en `historial_senales.json`.
V4 agrega una capa ordenada tipo broker:

- `paper/paper_portfolio.json`
- `paper/paper_orders.json`
- `paper/paper_trades.json`
- `paper/paper_risk.json`
- `paper/paper_status.json`
- `paper/paper_state.json`

## Qué significa

El flujo ahora queda así:

1. `analizador_acciones.py` analiza el mercado.
2. Calcula señales BUY / SELL / HOLD.
3. Actualiza el historial simulado.
4. Exporta una cartera paper formal.
5. Exporta órdenes simuladas BUY / SELL.
6. Exporta trades cerrados.
7. Exporta estado de riesgo.
8. El dashboard muestra el panel V4.

## Qué NO hace todavía

No ejecuta dinero real.
No se conecta todavía con broker real.
No envía órdenes reales a Alpaca ni Interactive Brokers.

## Para qué sirve

Esta V4 deja el sistema preparado para una futura V5:

- Alpaca Paper Trading API
- órdenes paper contra broker real
- stop loss automático externo
- trailing stop externo
- broker adapter real

## Archivos nuevos

### `engine/paper_trading_engine.py`

Convierte el historial simulado en estructuras profesionales:
- órdenes
- portfolio
- trades
- riesgo
- estado

### `paper/*.json`

Funcionan como base de datos gratuita dentro del repositorio.

### `config/bot_config_v4.json`

Configura el estado y objetivo de V4.

### Dashboard

El `index.html`, `script.js` y `style.css` ahora muestran un panel:

**BOT-ARQ V4 · Paper Trading Engine**

## Recomendación

Antes de conectar broker real, deja correr esta V4 varias semanas o meses y revisa:

- drawdown
- profit factor
- exposición
- racha de pérdidas
- calidad de stops
- exceso de operaciones abiertas
