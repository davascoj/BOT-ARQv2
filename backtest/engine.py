"""Daily OHLC replay using the SAME ledger, entry/risk gates and sale lock as live.
Signals at close T; fills at open T+1. Intraday path is unknown: stop first
if both levels touch. Last-day purchases remain open, never force sold illegally.
"""
from copy import deepcopy
from datetime import timedelta
import pandas as pd

from engine.ledger import update, close_position, balances, drawdown
from engine.policy import schedule, can_sell, number


def _fila(df, day):
    if df is None or day not in df.index:
        return None
    row = df.loc[day]
    try:
        vals = {k.lower(): number(row[k]) for k in ("Open", "High", "Low", "Close")}
        if min(vals.values()) <= 0 or vals["low"] > min(vals["open"], vals["close"]) or vals["high"] < max(vals["open"], vals["close"]):
            return None
        return vals
    except (ValueError, TypeError):
        return None


def run_backtest(precios, signal_fn, mercado_fn, config, sectores=None, log=None):
    sectores = sectores or {}
    prices = {}
    for tk, data in precios.items():
        df = data.copy()
        df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
        if df.index.has_duplicates:
            raise ValueError(f"Duplicate bars: {tk}")
        prices[tk] = df.sort_index()
    dates = sorted(set().union(*(set(df.index) for df in prices.values()))) if prices else []
    if not dates:
        return {"trades": [], "equity_curve": [], "posiciones_abiertas": [], "resumen": {}, "config_usada": config}
    calendar = schedule(str(dates[0].date()), str(dates[-1].date()))
    book = {"operaciones": [], "resumen": {}}
    pending = []
    curve = []
    diagnostics = {"missing_marks": [], "ambiguous_bars": 0, "signal_errors": 0}
    prior_market = {"estado": "SIN DATOS"}
    for T in dates:
        if T not in calendar.index:
            continue
        if not any(len(df.loc[:T]) >= 220 for df in prices.values()):
            continue
        bounds = calendar.loc[T]
        opening = bounds.market_open.to_pydatetime()
        closing = bounds.market_close.to_pydatetime() - timedelta(microseconds=1)
        # Quotes at OPEN only. Future close cannot affect sizing any pending buy.
        open_quotes = {tk: {"price": row["open"], "timestamp": opening.isoformat()}
                       for tk, df in prices.items() if (row := _fila(df, T))}
        execution_signals = deepcopy(pending)
        for sig in execution_signals:
            sig["bar_session"] = str(T.date())  # order scheduled for this session, signal timestamp remains T-1
        book = update(book, execution_signals, prior_market, config, opening, open_quotes)
        pending = []
        # OHLC bounds for positions already eligible. No same-session liquidation.
        for op in book["operaciones"]:
            if op["estado"] != "ABIERTA" or not can_sell(op["fecha_entrada"], opening):
                continue
            row = _fila(prices.get(op["accion"]), T)
            if not row:
                diagnostics["missing_marks"].append({"ticker": op["accion"], "date": str(T.date())})
                continue
            stop, target = row["low"] <= op["stop"], row["high"] >= op["objetivo"]
            if stop and target:
                diagnostics["ambiguous_bars"] += 1
            if stop or target:
                price = op["stop"] if stop else op["objetivo"]
                reason = "STOP_OHLC_CONSERVADOR" if stop else "OBJETIVO_OHLC"
                # Timestamp denotes modeled session event, not a recovered intraday tick.
                modeled = opening + (closing - opening) / 2
                close_position(op, price, reason, modeled, modeled.isoformat(), prior_market.get("estado"))
                op["execution_model"] = "OHLC_TIME_UNKNOWN_STOP_FIRST"
        close_quotes = {tk: {"price": row["close"], "timestamp": closing.isoformat()}
                        for tk, df in prices.items() if (row := _fila(df, T))}
        market = mercado_fn(T) if mercado_fn else {"estado": "NEUTRO"}
        book = update(book, [], market, config, closing, close_quotes)
        b = balances(book)
        # Omit indicator warm-up from performance statistics.
        ready = any(len(df.loc[:T]) >= 220 for df in prices.values())
        if ready:
            book["daily_equity"][-1]["session_final"] = True
            curve.append({"fecha": str(T.date()), "equity": b["equity"], "caja": b["cash"],
                          "posiciones_abiertas": len(b["opened"]), "drawdown_pct": drawdown(book, b["equity"])})
        for tk, df in prices.items():
            if T not in df.index or len(df.loc[:T]) < 220:
                continue
            try:
                sig = signal_fn(df.loc[:T].copy(), tk, market)
            except Exception as error:
                diagnostics["signal_errors"] += 1
                raise RuntimeError(f"Signal failure {tk} {T}") from error
            if sig:
                sig = dict(sig)
                sig["Accion"] = tk
                sig["Sector"] = sectores.get(tk, sig.get("Sector", "Otro"))
                sig["signal_timestamp"] = closing.isoformat()
                pending.append(sig)
        # Match live ordering; ties deterministic. No future data in this ranking.
        pending.sort(key=lambda s: (
            {"BUY STRONG": 4, "BUY": 3, "HOLD": 2}.get(s.get("Senal Bot"), 1),
            {"BAJO": 3, "MEDIO": 2}.get(s.get("Riesgo"), 1),
            {"ACOMPAÑA": 3, "NEUTRO +": 2, "NEUTRO": 1, "GENERAL": 1}.get(s.get("Contexto sector"), 0),
            s.get("Score calidad", 0), s.get("Probabilidad tecnica", 0), s.get("Fuerza relativa", 0),
            -s.get("ATR %", 99), s["Accion"]), reverse=True)
        prior_market = market
    b = balances(book)
    trades = [{**op, "ticker": op["accion"], "fecha_cierre": op["fecha_cierre"],
               "entrada_precio": op["precio_entrada"], "salida_precio": op["precio_cierre"],
               "cantidad": op["acciones_estimadas"]} for op in b["closed"]]
    wins = sum(o["pnl_usd_estimado"] > 0 for o in trades)
    return {"trades": trades, "equity_curve": curve, "posiciones_abiertas": b["opened"],
            "config_usada": deepcopy(config), "diagnostics": diagnostics,
            "resumen": {"capital_inicial": b["initial"], "capital_final": b["equity"],
                        "caja_final": b["cash"], "valor_liquidacion_estimado": b["net_value"],
                        "retorno_total_pct": (b["equity"] / b["initial"] - 1) * 100,
                        "trades_total": len(trades), "trades_ganados": wins,
                        "trades_perdidos": len(trades) - wins, "posiciones_abiertas": len(b["opened"]),
                        "win_rate_pct": wins / len(trades) * 100 if trades else 0,
                        "dias_simulados": len(curve),
                        "nota": "Sin cierre artificial final. Equity incluye valoración neta de posiciones aún bloqueadas."}}
