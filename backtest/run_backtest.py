"""
BOT-ARQ V4.7 - CLI del backtest.

Une todas las piezas: datos (data) + contexto de mercado reconstruido (market)
+ compute_signal (motor live) + engine + metrics. Escribe un JSON con métricas,
resumen, curva de equity y trades.

Uso:
    python -m backtest.run_backtest                         # universo del motor, 3 años
    python -m backtest.run_backtest --periodo 5y
    python -m backtest.run_backtest --tickers AAPL,MSFT,NVDA
    python -m backtest.run_backtest --salida backtest/mi_resultado.json

Requiere yfinance + pandas instalados (igual que el motor live).
"""
import argparse
import importlib.util
import json
import hashlib
import platform
from datetime import datetime, timezone
from engine.policy import VERSION
from engine.ledger import config_hash
from engine.storage import atomic_json
from pathlib import Path


def cargar_motor():
    """Importa el motor live para reutilizar compute_signal, compute_driver,
    armar_contexto_mercado, ACCIONES_INFO, DRIVERS_CONTEXTO y CONFIG_SIMULACION."""
    spec = importlib.util.spec_from_file_location("motor", Path(__file__).resolve().parents[1] / "analizador_acciones.py")
    motor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(motor)
    return motor


def main():
    ap = argparse.ArgumentParser(description="Backtest BOT-ARQ V4.7 (reutiliza compute_signal del live)")
    ap.add_argument("--periodo", default="3y", help="periodo yfinance (1y, 3y, 5y, max)")
    ap.add_argument("--tickers", default="", help="lista separada por comas; vacío = universo del motor")
    ap.add_argument("--salida", default="backtest/resultado_backtest.json")
    ap.add_argument("--sin-cache", action="store_true", help="ignora el cache parquet y re-descarga")
    args = ap.parse_args()

    motor = cargar_motor()
    config = dict(motor.CONFIG_SIMULACION)

    from backtest.data import descargar_ohlcv
    from backtest.market import reconstruir_mercado_fn
    from backtest.engine import run_backtest
    from backtest.metrics import calcular_metricas_backtest, winrate_por_sector

    if args.tickers.strip():
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = sorted(motor.ACCIONES_INFO.keys())
    sectores = {t: motor.ACCIONES_INFO.get(t, "Otro") for t in tickers}
    drivers_tickers = sorted({t for lista in motor.DRIVERS_CONTEXTO.values() for t in lista})

    usar_cache = not args.sin_cache
    print(f"[1/3] Descargando {len(tickers)} tickers + {len(drivers_tickers)} drivers ({args.periodo})...")
    precios = descargar_ohlcv(tickers, args.periodo, usar_cache=usar_cache)
    precios_drivers = descargar_ohlcv(drivers_tickers, args.periodo, usar_cache=usar_cache)
    print(f"      Datos OK: {len(precios)} tickers, {len(precios_drivers)} drivers")
    if not precios:
        print("      Sin datos: abortando.")
        return

    print("[2/3] Reconstruyendo contexto de mercado point-in-time y simulando...")
    mercado_fn = reconstruir_mercado_fn(precios_drivers, motor)
    def signal(df, ticker, mercado):
        result = motor.compute_signal(df, ticker, mercado)
        if result:
            result["Score calidad"] = motor.calcular_score_calidad(result)
        return result
    res = run_backtest(precios, signal, mercado_fn, config, sectores=sectores)

    print("[3/3] Calculando métricas...")
    met = calcular_metricas_backtest(res["equity_curve"], res["trades"], config["capital_inicial"])
    met["winrate_por_sector"] = winrate_por_sector(res["trades"])

    salida = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "config_usada": config,
        "config_hash": config_hash(config),
        "data_hashes": {t: hashlib.sha256(df.to_csv().encode()).hexdigest() for t, df in precios.items()},
        "driver_hashes": {t: hashlib.sha256(df.to_csv().encode()).hexdigest() for t, df in precios_drivers.items()},
        "posiciones_abiertas": res["posiciones_abiertas"],
        "diagnostics": res["diagnostics"],
        "periodo": args.periodo,
        "universo_tickers": len(tickers),
        "metricas": met,
        "resumen": res["resumen"],
        "equity_curve": res["equity_curve"],
        "trades": res["trades"],
        "notas": [
            "Backtest sin look-ahead: decisión en cierre de T, ejecución en apertura de T+1.",
            "Costos aditivos por lado (comisión + slippage + medio spread) congelados en entrada, mismo modelo que live.",
            "Toda venta solo desde sesión posterior y en horario NYSE. No se liquida artificialmente al final.",
            "OHLC diario no identifica la hora intradía; si toca ambos niveles se elige stop primero. Live usa muestras 1m.",
            "Caja real (V4.5): cada posición descuenta efectivo; sin sobre-apalancamiento.",
            "Universo = tickers actuales del motor => posible survivorship bias (ver README).",
        ],
    }
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.salida, salida)

    print(f"\nResultado -> {args.salida}")
    print(f"  Retorno total : {met.get('retorno_total_pct')}%")
    print(f"  Sharpe        : {met.get('sharpe_ratio')}   Sortino: {met.get('sortino_ratio')}")
    print(f"  Max drawdown  : {met.get('max_drawdown_pct')}%   Calmar: {met.get('calmar_ratio')}")
    print(f"  Win rate      : {met.get('win_rate_pct')}%   Profit factor: {met.get('profit_factor')}")
    print(f"  Trades        : {met.get('trades_total')}   Holding medio: {met.get('avg_holding_dias')} días")


if __name__ == "__main__":
    main()
