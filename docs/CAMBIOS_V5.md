# Cambios V5 — auditoría y regla de venta

Implementación: 14–15 octubre 2026. Solo simulación. El historial generado por Actions no forma parte del cambio de código; se migra el estado más reciente al ejecutar V5.

## Correcciones y decisiones

| Área | Cambio | Validación / límite |
|---|---|---|
| Contabilidad | Entradas inmutables; cantidad × precio = importe; costos por lado fijados al entrar | Huella de entrada y pruebas de invariantes; P&L cerrado no se recalcula con otra configuración |
| Retención | Eliminado recorte de 300 y recorte contable de órdenes | Prueba con 501 operaciones; paginación de 50 filas en UI |
| Migración | Copia original con hash, importes congelados, cantidades legacy registradas | No recuperación ficticia de operaciones borradas; balance heredado no certificado |
| Venta | Siguiente sesión NYSE y solo horario regular, sin excepciones | Compra mismo día, stop, objetivo, SELL, pre/post-market, festivos, DST y medio día |
| Holding | Sesiones bursátiles; vencimiento también para posiciones en pérdida | No overrides del bloqueo de compra; cooldown evita reentrada el día de cierre |
| Riesgo | Equity con abiertas, drawdown actual distinto del máximo; caja/exposición/riesgo/sector prospectivos | Costos reservados en sizing; riesgo de gaps explícito, no stop garantizado |
| Datos | Cotizaciones 1m no ajustadas separadas de indicadores diarios; timestamps, antigüedad y cierre final | Sin cotización válida no hay fill. Un split pendiente bloquea esa posición y nuevas entradas |
| Señales | RSI ascendente=100, descendente=0, plano=50; finitos; R/R sin redondear al comparar | Se preserva estrategia base. Objetivo se redondea hacia arriba para no violar R/R mínimo por centavos |
| Backtest | Mismo libro, filtros, costos, límites y bloqueo; compra T+1 al open; sin cierre futuro al dimensionar | No fuerza venta final; OHLC no prueba ejecución por ticks; stop primero en barra ambigua |
| Métricas | P&L neto, rachas netas, retornos ponderados por importe, downside RMS para Sortino | Ratios del tablero N/D hasta tener sesiones V5; datos legacy siguen no certificados |
| Persistencia | JSON estricto, escritura temporal+fsync+replace, run_id común y snapshot único | Publicación solo tras validación; Git commit agrupa archivos. No sustituye transacciones de servidor multiusuario |
| Velocidad | Descarga por lotes, 4 threads, un reintento, benchmark reutiliza descarga, no Excel cuando está desactivado | Primera ejecución local completa observada: 33,554 s, no SLA ni benchmark de infraestructura idéntica |
| CI/seguridad | Actions con SHA, Python 3.13, paquetes fijados, checkout depth 1 sin persistir token, pruebas de PR y publicación | PAT existente solo en push; no se inspecciona ni cambia su alcance, no se relajan protecciones |
| Concurrencia | Rechaza publicar si main cambió; no rebase de estado antiguo sobre código nuevo | Concurrency estable, fallo explícito y siguiente corrida vuelve a leer estado vigente |
| UI | Snapshot coherente, costos/benchmark correctos, N/D distinto de cero, estado bursátil ≠ salud, datos viejos visibles | Pruebas JS, actualización con timeout y exclusión de solicitudes simultáneas |
| UX | Historial paginado, resultado neto, motivo de bloqueo, venta bloqueada visible, score no probabilístico | Encabezado no sticky en móvil, foco visible, etiquetas accesibles, tabla alternativa al gráfico |

## Parámetros modificados / preservados

- Regla obligatoria: no vender en día de compra, tampoco stop. Aplica a live simulado, backtest y cierre manual interno.
- Nuevo tope por categoría sectorial: 35% de equity neta. No equivale a un modelo de correlaciones.
- Nuevo mínimo R/R neto 1,0 además del bruto 1,5. R/R se recalcula sobre precio ejecutable, no el número redondeado del tablero.
- Mínimo de posición 10 USD para evitar restos de caja insignificantes.
- Cotización máxima 180 segundos de antigüedad en sesión. Sin datos de cartera se bloquean nuevas entradas.
- Capital 5.000, riesgo 1%, máximo posición 20%, exposición 80%, riesgo abierto 10%, 20 posiciones y drawdown 30/35 se conservan. No se presentan como óptimos.
- Máximo holding 2 sesiones se respeta también con pérdidas. Esto corrige el sesgo de prolongar perdedoras, pero cambia resultados y requiere evaluar la nueva estrategia fuera de muestra.
- Costos por lado = comisión + slippage + medio spread. Se modelan como cargo sobre notional observado, tanto en backtest como en simulación; no son bid/ask reales.

## Despliegue y aceptación

1. Ejecutar Python y JS tests; revisar que el diff solo contenga código, configuración, pruebas y documentación.
2. Abrir PR, esperar CI verde y verificar que no haya conflictos de código con main.
3. Fusionar PR con SHA esperado. La automatización lee el último historial, guarda copia legacy y publica snapshot V5.
4. Revisar que `schema_version=2`, `version_bot=5.0.0`, todos los run_id coincidan y el validador pase.
5. Comprobar en Pages antigüedad, regla de venta, costes, benchmark, cartera e historial; probar móvil/tablet/escritorio.
6. Comprobar otra corrida para verificar idempotencia y estabilidad de entradas/cierres existentes. No afirmar rentabilidad por haber pasado pruebas de software.

## Reversión y recuperación

No ejecutar V4 sobre un ledger V5 ni restaurar a ciegas JSON antiguo: provocaría pérdida de eventos o nuevo redimensionamiento. Si falla V5: pausar el workflow y cualquier disparador externo, conservar el último commit y `paper/legacy`, reparar o revertir **código compatible con schema 2**, ejecutar tests/validador, comparar operaciones por ID y reanudar. Para una vuelta completa a V4 se requiere conciliación explícita de todas las operaciones posteriores; no es una reversión segura automática.

La copia legacy y Git conservan lo recibido al migrar. Las operaciones eliminadas antes de V5 y la hora real de fills antiguos siguen sin conocerse. Recuperarlas requiere reconstrucción y revisión independiente; no se alteran para aparentar beneficios.

## No incluido por falta de evidencia suficiente

ML, ajuste de stops para maximizar beneficios, optimización de parámetros sin walk-forward, proveedor de ticks/broker, correlación estadística, calendario de resultados corporativos completo, migración SQL, cambios del PAT/rulesets o del disparador externo. Son ampliaciones con validación/infraestructura propias, no arreglos demostrados por esta auditoría. La arquitectura actual queda apta para recoger evidencia V5 antes de optimizar estrategia.

Referencias de implementación: calendario [pandas-market-calendars](https://pandas-market-calendars.readthedocs.io/en/latest/usage.html); la programación de [GitHub Actions puede retrasarse](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
