# BOT-ARQ V4.4.5 - Arquitectura actual

## Flujo

GitHub Actions (cada 5 min, mercado abierto) → `analizador_acciones.py` → carga `config/system_config.json` → analiza mercado y acciones (yfinance) → actualiza el historial persistente → exporta el paper trading → escribe `datos_acciones.json`. GitHub Pages sirve el dashboard, que lee `datos_acciones.json` y `paper/paper_state.json`.

## Componentes

- `analizador_acciones.py`: motor principal. Lee y reescribe `historial_senales.json` (estado persistente).
- `engine/config_loader.py`: carga la configuración real del motor.
- `engine/paper_trading_engine.py`: exporta cartera, órdenes, trades, riesgo, estado, auditoría y reglas operativas a `paper/*.json`.
- `config/system_config.json`: configuración operativa real (capital, riesgo, límites, reglas V4.4).
- `index.html`, `script.js`, `style.css`: dashboard web (layout A–H).

## Datos

| Archivo | Lo usa la web | Estado persistente del motor | Se versiona |
|---------|:---:|:---:|:---:|
| `datos_acciones.json` | ✅ | — | ✅ |
| `paper/paper_state.json` (ligero) | ✅ | — | ✅ |
| `historial_senales.json` | — | ✅ (lo lee al arrancar) | ✅ |
| `paper/paper_orders.json`, `paper_trades.json`, etc. | — | — | ✅ (auditoría) |
| `*.xlsx` | — | — | ❌ no versionado (opt-in `BOT_ARQ_EXPORT_XLSX=1`) |

## Notas de diseño

- `paper_state.json` es la versión **ligera** del estado: no embebe los arrays completos de `orders`/`trades` (viven en sus archivos aparte). El dashboard solo necesita conteos y resúmenes.
- Las reglas operativas V4.4 reutilizan métricas existentes; **no hay un risk engine paralelo**.
- El cache-busting es por versión para assets y por ventana de 5 minutos para los datos.
- Broker real: OFF. Todo es paper trading / simulación.
