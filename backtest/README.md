# BOT-ARQ — Backtest Core (V4.7)

Módulo **aislado** que simula la estrategia del bot sobre datos históricos.
**No ejecuta dinero real, no modifica el motor live ni el paper trading.**

## Principio clave: misma lógica que el live

El backtest **reutiliza** las funciones puras del motor (`analizador_acciones.py`),
no las reimplementa:

- `compute_signal(df, ticker, mercado)` — la señal BUY/HOLD/SELL.
- `compute_driver(df, ticker)` + `armar_contexto_mercado(drivers)` — el contexto de mercado.

Así, lo que se prueba en el backtest es **exactamente** lo que opera en producción.
Si la lógica del live cambia, el backtest cambia con ella automáticamente.

## Cómo correrlo

```bash
# Universo completo del motor, 3 años
python -m backtest.run_backtest

# Periodo y tickers concretos
python -m backtest.run_backtest --periodo 5y --tickers AAPL,MSFT,NVDA,AMD

# Forzar re-descarga (ignora cache parquet)
python -m backtest.run_backtest --sin-cache
```

Requiere `yfinance` y `pandas` (igual que el motor live). Escribe
`backtest/resultado_backtest.json` con métricas, curva de equity y trades.

## Qué hace bien (rigor)

- **Sin look-ahead**: la decisión usa datos solo hasta el cierre del día T; la
  orden se ejecuta en la **apertura de T+1**.
- **Costos reales**: comisión + slippage + spread (de `config/system_config.json`)
  en entrada y salida.
- **Caja real (V4.5)**: cada compra descuenta efectivo, cada venta lo devuelve.
  No hay sobre-apalancamiento (verificado: la caja nunca queda negativa).
- **Stops/objetivos** evaluados con el rango (high/low) de cada día; los gaps de
  apertura se ejecutan a la apertura (conservador).
- **Datos ajustados** por splits/dividendos (`auto_adjust=True`), cacheados a parquet.
- **Métricas sobre la equity diaria** (estándar de la industria): Sharpe/Sortino
  anualizados (√252), Max Drawdown, CAGR, Calmar, profit factor, expectancy,
  win rate global y por sector.

## Límites honestos (leer antes de confiar en los números)

- **Survivorship bias**: el universo son los tickers *actuales* del motor. Acciones
  que quebraron o salieron del índice no están → los resultados pueden verse mejores
  de lo real. Para eliminarlo haría falta un universo histórico point-in-time.
- **Fills idealizados**: se asume que se puede comprar en la apertura de T+1 al precio
  de apertura ± slippage. No modela falta de liquidez ni huecos extremos.
- **Sin dividendos como flujo**: se usan precios ajustados (incorpora el efecto en el
  precio), pero no se modela el cobro de dividendos como caja.
- **Un backtest bueno no garantiza rendimiento futuro.** Reduce el autoengaño, no el riesgo.

## Validación pendiente (siguientes pasos)

- **Walk-forward / out-of-sample**: optimizar en una ventana y medir en la siguiente.
- **Análisis de sensibilidad**: ¿aguantan los resultados si se mueven los parámetros ±20%?
- **Benchmark**: comparar contra comprar y mantener SPY/QQQ en el mismo periodo.
- **Panel en el dashboard**: sección colapsable "Backtest" leyendo `resultado_backtest.json`.

## Estructura

```
backtest/
  engine.py        # motor event-driven (caja, posiciones, stops, costos)
  metrics.py       # métricas sobre la equity diaria + por trade y sector
  market.py        # reconstrucción del contexto de mercado point-in-time
  data.py          # descarga + cache OHLCV (yfinance -> parquet)
  run_backtest.py  # CLI que orquesta todo
```
