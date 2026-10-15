# BOT-ARQ · V5.0.0

Simulador de acciones/ETF con señales técnicas, libro de operaciones continuo y dashboard en GitHub Pages. **Solo paper trading: no envía órdenes a un broker ni promete rentabilidad.**

## Regla de venta obligatoria

Una compra **nunca se vende en su misma sesión**, ni siquiera por stop loss. Todas las salidas se habilitan desde la siguiente sesión válida de NYSE, solo dentro del horario regular. El calendario contempla fines de semana, festivos, cambios de hora y cierres anticipados. `force=true` permite actualizar el análisis fuera de horario, **no operar**.

Ejemplo: compra el viernes → primera venta posible el lunes al abrir, salvo festivo. Si el precio cae por debajo del stop durante el bloqueo, se espera a una sesión habilitada y una cotización reciente. El precio real simulado puede ser peor que el stop: **el stop no garantiza la pérdida máxima**.

## Cambios principales de V5

- Cantidad, importe, precio y costos se fijan al entrar; actualizar métricas no redimensiona posiciones.
- No se eliminan operaciones al llegar a 300. Historial completo paginado en la interfaz.
- Caja, equity, drawdown y riesgo usan una base consistente; resultados y rachas se clasifican por P&L **neto**.
- Nuevas compras respetan caja con costos, exposición total, riesgo agregado y tope sectorial.
- Datos corruptos o configuración inválida detienen la ejecución. Cotizaciones atrasadas bloquean fills y nuevas entradas cuando afectan cartera abierta.
- El backtest comparte libro y reglas con el simulador; decide al cierre y compra desde la siguiente apertura, sin usar el cierre futuro para dimensionar.
- Un único snapshot coherente alimenta el tablero. Antigüedad de datos, motivos de bloqueo, regla de venta y calidad contable son visibles.
- Descargas por lotes con concurrencia acotada y reintento; dependencias y Actions fijadas; pruebas antes de publicar.

## Arquitectura

```text
GitHub Actions → pruebas → analizador_acciones.py
  ├─ engine/market_data.py: barras diarias + cotizaciones 1m separadas
  ├─ engine/policy.py: calendario, costos, filtros y límites compartidos
  ├─ engine/ledger.py: entradas inmutables, valoraciones, cierres y migración
  ├─ historial_senales.json: libro persistente, sin recorte
  ├─ paper/*.json: derivados trazables y copia legacy inicial
  └─ datos_acciones.json: snapshot completo con run_id común → dashboard
backtest/engine.py → mismo libro/políticas, modelo OHLC diario conservador
```

El cron solicita una ejecución cada cinco minutos, no garantiza esa latencia. Una ventana de 20 minutos después del cierre permite registrar valoraciones finales; no permite ventas fuera de horario. Se conserva el PAT existente únicamente en el paso de push para mantener el despliegue Pages actual. Sus permisos efectivos deben revisarse en GitHub; no se crea otro secreto.

## Migración sin inventar un histórico

La primera ejecución V5 guarda el historial recibido, intacto, en `paper/legacy/<sha256>.json`. Conserva los valores publicados de operaciones cerradas. Para posiciones abiertas congela el último **importe publicado** y deriva la cantidad como importe/precio; conserva la cantidad anterior para auditar la diferencia. Costos legacy se continúan con la tasa registrada, o el fallback explícito 0,23% ida/vuelta si falta.

Esto **no recupera operaciones borradas ni certifica la rentabilidad anterior**. Se informa `LEGACY_NO_RECONCILIADO` y la base de migración. Las nuevas entradas V5 llevan timestamps, versión, configuración y huella de sus campos inmutables. No se reinicia el capital ni se atribuyen ganancias a una reconciliación ficticia.

## Desarrollo y comprobaciones

Python **3.13**, Node **22**:

```sh
python -m pip install -r requirements.txt
python -m pytest
node --check script.js
node tests/frontend.test.cjs
```

La prueba integral usa un directorio temporal y no modifica el estado operativo. Para ejecutar el bot use una **copia** del historial; `python analizador_acciones.py` sí actualiza los JSON en el directorio de trabajo. Luego `python scripts/validate_snapshot.py` verifica IDs, balances y ventas permitidas antes de publicar.

```sh
python -m backtest.run_backtest --tickers AAPL,MSFT --periodo 3y --salida backtest/resultado_backtest.json
```

El backtest conserva posiciones finales sin liquidarlas ilegalmente. Reporta caja, valoración neta, configuración y hashes de datos. Barras OHLC no reconstruyen el camino intradía: si toca stop y objetivo se elige el stop conservadoramente. Tiene sesgo potencial de supervivencia por usar el universo actual. No es idéntico a un replay de ticks.

## Límites deliberados

- yfinance/Actions/Pages no son infraestructura de ejecución garantizada; solo simulación.
- No se añadió ML sin una muestra limpia ni se ensancharon límites de drawdown para forzar compras.
- Los límites 30%/35% de drawdown se preservan; no equivalen a protección óptima validada. El tope sectorial V5 es 35% de equity, configurable.
- Holding máximo: sesiones bursátiles posteriores a entrada, también cierra pérdidas al vencer, siempre sujeto al bloqueo de día de compra.
- Sharpe/Sortino del tablero solo se calculan con al menos 20 sesiones finales observadas V5; CAGR/Calmar necesitan una muestra mayor. N/D no es cero.
- Splits detectados en posiciones abiertas bloquean ejecución hasta conciliación; no se inventan ajustes corporativos.
- No hay SQL que optimizar: almacenamiento JSON/Git. Para múltiples escritores/usuarios operativos será necesario un servicio transaccional; no se incorpora una base de datos sin migración validada.

Detalle, aceptación y reversión segura: [CAMBIOS_V5.md](docs/CAMBIOS_V5.md).
