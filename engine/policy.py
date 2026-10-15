"""Shared execution/risk rules. No broker access. All times are exchange-aware."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import isfinite
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal
import pandas as pd

VERSION = "5.0.0"
NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError("Missing/boolean numeric value")
    result = float(value)
    if not isfinite(result):
        raise ValueError("Non-finite numeric value")
    return result


def timestamp(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires timezone")
    return result.astimezone(UTC)


@lru_cache(maxsize=16)
def _year_schedule(year):
    return mcal.get_calendar("NYSE").schedule(start_date=f"{year}-01-01", end_date=f"{year}-12-31")


def schedule(start, end):
    first, last = int(str(start)[:4]), int(str(end)[:4])
    return pd.concat([_year_schedule(year) for year in range(first, last + 1)]).loc[start:end]


def market_session(now):
    now = timestamp(now)
    day = now.astimezone(NY).date()
    rows = schedule(day.isoformat(), (day + timedelta(days=14)).isoformat())
    today = rows.loc[str(day):str(day)]
    opened = closed = None
    if not today.empty:
        opened = today.iloc[0]["market_open"].to_pydatetime()
        closed = today.iloc[0]["market_close"].to_pydatetime()
    upcoming = rows[rows.market_open > now]
    return {
        "calendar": "NYSE", "session_date": str(day), "checked_at": now.isoformat(),
        "is_open": bool(opened and opened <= now < closed),
        "market_open": opened.isoformat() if opened else None,
        "market_close": closed.isoformat() if closed else None,
        "next_open": upcoming.iloc[0].market_open.isoformat() if not upcoming.empty else None,
    }


def next_sell_at(entry_date):
    day = datetime.strptime(str(entry_date)[:10], "%Y-%m-%d").date()
    rows = schedule((day + timedelta(days=1)).isoformat(), (day + timedelta(days=14)).isoformat())
    if rows.empty:
        raise ValueError("No next exchange session")
    return rows.iloc[0].market_open.to_pydatetime().isoformat()


def can_sell(entry_date, now):
    """Mandatory user rule: applies to EVERY exit, including stops and liquidation."""
    now = timestamp(now)
    return market_session(now)["is_open"] and now >= timestamp(next_sell_at(entry_date))


def holding_sessions(entry_date, now):
    end = timestamp(now).astimezone(NY).date().isoformat()
    start = str(entry_date)[:10]
    if end <= start:
        return 0
    rows = schedule(start, end)
    return sum(str(idx.date()) > start for idx in rows.index)


def fresh_quote(quote, now, max_age=180):
    try:
        qt = timestamp(quote["timestamp"])
        now = timestamp(now)
        return (number(quote["price"]) > 0 and 0 <= (now - qt).total_seconds() <= max_age
                and market_session(qt)["is_open"] and qt.astimezone(NY).date() == now.astimezone(NY).date())
    except (ValueError, TypeError, KeyError):
        return False


def side_cost(config):
    return (number(config["comision_por_operacion_pct"]) + number(config["slippage_pct"]) + number(config["spread_pct"]) / 2) / 100


def entry_filter(signal, config, price=None):
    """Same static eligibility for live and historical execution; never trust rounded R/R."""
    try:
        price = number(signal["Precio actual"] if price is None else price)
        stop, target = number(signal["Stop loss"]), number(signal["Objetivo"])
        if not 0 < stop < price < target:
            return "Niveles inválidos"
        rr = (target - price) / (price - stop)
        cost = side_cost(config)
        net_rr = (target * (1 - cost) - price * (1 + cost)) / (price * (1 + cost) - stop * (1 - cost))
        if rr + 1e-9 < config["rr_minimo"] or net_rr < config.get("rr_neto_minimo", 1.0):
            return "R/R ejecutable insuficiente (incluye costos)"
        if signal.get("Senal Bot") not in ("BUY", "BUY STRONG"):
            return "Sin señal de compra"
        if signal.get("Riesgo") not in ("BAJO", "MEDIO"):
            return "Riesgo alto o desconocido"
        if signal.get("Confirmacion") not in ("ALTA", "MEDIA"):
            return "Confirmación insuficiente"
        if signal.get("Contexto sector") == "NO ACOMPAÑA":
            return "Sector no acompaña"
        if signal.get("Mercado") in ("SIN DATOS", None):
            return "Mercado sin datos"
        if signal.get("Mercado") in ("DÉBIL", "DEBIL"):
            if signal.get("Senal Bot") != "BUY STRONG" or not config["permitir_buy_strong_en_mercado_debil"]:
                return "Mercado débil o sin datos"
        if number(signal["Volumen relativo"]) < config["volumen_relativo_minimo"]:
            return "Volumen relativo bajo"
    except (KeyError, TypeError, ValueError):
        return "Datos de entrada incompletos/no finitos"
    return ""


def position_size(equity, cash, price, stop, config, exposure=0, open_risk=0, sector_exposure=0):
    equity, cash, price, stop = map(number, (equity, cash, price, stop))
    if equity <= 0 or cash <= 0 or not 0 < stop < price:
        return None
    cost = side_cost(config)
    risk_fraction = (price * (1 + cost) - stop * (1 - cost)) / price
    def cap(percent, used=0, weight=1):
        fraction = percent / 100
        return (equity * fraction - used) / (weight + fraction * 2 * cost)
    notional = min(cap(config["riesgo_por_operacion_pct"], weight=risk_fraction),
                   cap(config["max_riesgo_total_abierto_pct"], open_risk, risk_fraction),
                   cash / (1 + cost), cap(config["max_posicion_pct"]),
                   cap(config["max_exposicion_total_pct"], exposure),
                   cap(config.get("max_exposicion_sector_pct", 35), sector_exposure))
    if notional < config.get("min_posicion_usd", 10):
        return None
    qty = int(notional / price * 1e8) / 1e8  # fractional paper shares, floor to avoid cash overshoot
    return {"quantity": qty, "notional": qty * price, "entry_cost": qty * price * cost,
            "risk": qty * price * risk_fraction}


def portfolio_gate(config, equity, drawdown, losing_streak, count, strong=False):
    if equity <= 0:
        return "Capital agotado"
    if count >= config["max_operaciones_abiertas"]:
        return "Máximo de operaciones abiertas"
    if drawdown >= config["bloquear_entradas_drawdown_pct"]:
        return "Bloqueo por drawdown actual"
    if losing_streak >= config["bloquear_si_perdidas_seguidas"]:
        return "Bloqueo por racha de pérdidas netas; requiere revisión"
    if drawdown >= config["modo_defensivo_drawdown_pct"]:
        if not strong or not config["permitir_buy_strong_en_modo_defensivo_drawdown"]:
            return "Modo defensivo por drawdown"
    if losing_streak >= config["pausar_si_perdidas_seguidas"] and not strong:
        return "Modo defensivo por racha neta"
    return ""


def exit_reason(op, price, signal, now, config):
    if not can_sell(op["fecha_entrada"], now):
        return ""
    if price <= op["stop"]:
        return "STOP"
    if price >= op["objetivo"]:
        return "OBJETIVO"
    if signal == "SELL / EVITAR":
        return "SEÑAL SELL"
    if holding_sessions(op["fecha_entrada"], now) >= config["max_dias_holding"]:
        return "TIEMPO MAXIMO"
    return ""
