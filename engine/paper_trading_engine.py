"""
BOT-ARQ V4 - Paper Trading Engine

Este módulo NO ejecuta órdenes reales.
Toma el historial simulado existente de BOT-ARQ y lo convierte en una estructura
más profesional tipo broker/paper trading:

- paper_portfolio.json
- paper_orders.json
- paper_trades.json
- paper_risk.json
- paper_status.json
- paper_state.json
- paper_audit.json

Objetivo:
preparar el sistema para un futuro broker adapter real sin romper la simulación actual.
"""

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math

ZONA_HORARIA = ZoneInfo("America/Bogota")
PAPER_DIR = Path("paper")


def _now_visible():
    return datetime.now(ZONA_HORARIA).strftime("%d-%m-%Y %I:%M %p Colombia")


def _num(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        n = float(value)
        if math.isnan(n) or math.isinf(n):
            return default
        return n
    except Exception:
        return default


def _round(value, digits=2):
    return round(_num(value), digits)


def _safe_text(value):
    return str(value or "").strip()


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _operaciones(historial):
    return list((historial or {}).get("operaciones", []) or [])


def _resumen(historial):
    return dict((historial or {}).get("resumen", {}) or {})


def _operation_id(op, fallback_idx=0):
    return _safe_text(op.get("id")) or f"{_safe_text(op.get('fecha_entrada'))}-{_safe_text(op.get('accion'))}-{fallback_idx}"


def _position_from_operation(op, idx):
    ticker = _safe_text(op.get("accion"))
    qty = _num(op.get("acciones_estimadas"), 0)
    entry = _num(op.get("precio_entrada"), 0)
    current = _num(op.get("precio_actual"), entry)
    invested = _num(op.get("posicion_usd_estimada"), qty * entry)
    market_value = _num(op.get("valor_cartera_usd"), qty * current if qty else invested * (1 + _num(op.get("ganancia_pct"), 0) / 100))
    pnl_usd = _num(op.get("ganancia_abierta_usd_estimada"), market_value - invested)
    pnl_pct = _num(op.get("ganancia_pct"), 0)

    return {
        "position_id": _operation_id(op, idx),
        "ticker": ticker,
        "sector": _safe_text(op.get("sector")),
        "status": "OPEN",
        "entry_date": _safe_text(op.get("fecha_entrada")),
        "days_open": int(_num(op.get("dias_abierta"), 0)),
        "entry_signal": _safe_text(op.get("senal_bot_entrada")),
        "current_signal": _safe_text(op.get("senal_bot_actual")),
        "entry_price": _round(entry),
        "current_price": _round(current),
        "quantity_estimated": _round(qty, 6),
        "invested_usd": _round(invested),
        "market_value_usd": _round(market_value),
        "open_pnl_usd": _round(pnl_usd),
        "open_pnl_pct": _round(pnl_pct),
        "stop": _round(op.get("stop")),
        "target": _round(op.get("objetivo")),
        "risk_usd": _round(op.get("riesgo_usd_estimado")),
        "max_loss_stop_usd": _round(op.get("perdida_maxima_stop_usd")),
        "risk_pct_account": _round(op.get("riesgo_pct_cuenta_estimado")),
        "distance_stop_pct": _round(op.get("distancia_stop_actual_pct", op.get("distancia_stop_pct"))),
        "distance_target_pct": _round(op.get("distancia_objetivo_pct")),
        "score_entry": _round(op.get("score_calidad_entrada")),
        "score_current": _round(op.get("score_calidad_actual")),
        "market_entry": _safe_text(op.get("mercado_entrada")),
        "market_current": _safe_text(op.get("mercado_actual")),
        "result": _safe_text(op.get("resultado")) or "EN SEGUIMIENTO"
    }


def _orders_from_operation(op, idx):
    op_id = _operation_id(op, idx)
    ticker = _safe_text(op.get("accion"))
    qty = _num(op.get("acciones_estimadas"), 0)
    entry_price = _num(op.get("precio_entrada"), 0)
    close_price = _num(op.get("precio_cierre"), _num(op.get("precio_actual"), entry_price))

    orders = [{
        "order_id": f"{op_id}-BUY",
        "operation_id": op_id,
        "created_at": _safe_text(op.get("fecha_entrada")),
        "filled_at": _safe_text(op.get("fecha_entrada")),
        "ticker": ticker,
        "side": "BUY",
        "status": "FILLED_SIMULATED",
        "order_type": "MARKET_SIMULATED",
        "quantity_estimated": _round(qty, 6),
        "price": _round(entry_price),
        "notional_usd": _round(_num(op.get("posicion_usd_estimada"), qty * entry_price)),
        "reason": _safe_text(op.get("senal_bot_entrada")),
        "score": _round(op.get("score_calidad_entrada")),
        "risk_usd": _round(op.get("riesgo_usd_estimado")),
        "stop": _round(op.get("stop")),
        "target": _round(op.get("objetivo")),
        "mode": "PAPER_ONLY"
    }]

    if _safe_text(op.get("estado")).upper() == "CERRADA":
        orders.append({
            "order_id": f"{op_id}-SELL",
            "operation_id": op_id,
            "created_at": _safe_text(op.get("fecha_cierre")),
            "filled_at": _safe_text(op.get("fecha_cierre")),
            "ticker": ticker,
            "side": "SELL",
            "status": "FILLED_SIMULATED",
            "order_type": "MARKET_SIMULATED",
            "quantity_estimated": _round(qty, 6),
            "price": _round(close_price),
            "notional_usd": _round(qty * close_price if qty else 0),
            "reason": _safe_text(op.get("tipo_cierre")) or _safe_text(op.get("resultado")),
            "result": _safe_text(op.get("resultado")),
            "pnl_usd_estimated": _round(op.get("pnl_usd_estimado")),
            "pnl_pct": _round(op.get("ganancia_pct_final")),
            "mode": "PAPER_ONLY"
        })

    return orders


def _trade_from_closed_operation(op, idx):
    op_id = _operation_id(op, idx)
    return {
        "trade_id": op_id,
        "ticker": _safe_text(op.get("accion")),
        "sector": _safe_text(op.get("sector")),
        "entry_date": _safe_text(op.get("fecha_entrada")),
        "exit_date": _safe_text(op.get("fecha_cierre")),
        "entry_price": _round(op.get("precio_entrada")),
        "exit_price": _round(op.get("precio_cierre")),
        "quantity_estimated": _round(op.get("acciones_estimadas"), 6),
        "invested_usd": _round(op.get("posicion_usd_estimada")),
        "pnl_usd_estimated": _round(op.get("pnl_usd_estimado")),
        "pnl_pct": _round(op.get("ganancia_pct_final")),
        "cost_usd_estimated": _round(op.get("costo_usd_estimado")),
        "result": _safe_text(op.get("resultado")),
        "exit_type": _safe_text(op.get("tipo_cierre")),
        "entry_signal": _safe_text(op.get("senal_bot_entrada")),
        "exit_signal": _safe_text(op.get("senal_bot_actual")),
        "score_entry": _round(op.get("score_calidad_entrada")),
        "score_exit": _round(op.get("score_calidad_actual")),
        "mode": "PAPER_ONLY"
    }



def _audit_from_historial(historial, resultados, positions, warnings, config):
    resumen = _resumen(historial)
    bloqueadas = list(resumen.get("nuevas_bloqueadas", []) or [])
    abiertas = [p.get("ticker") for p in positions if p.get("ticker")]

    blocked = []
    for idx, b in enumerate(bloqueadas[-80:]):
        blocked.append({
            "id": f"BLOCK-{idx+1}",
            "date": _safe_text(b.get("fecha")),
            "ticker": _safe_text(b.get("accion")),
            "signal": _safe_text(b.get("senal_bot")),
            "reason": _safe_text(b.get("motivo")),
            "risk": _safe_text(b.get("riesgo")),
            "rr": _round(b.get("rr")),
            "decision": "BLOCKED_BY_EXISTING_RULE"
        })

    buy_candidates = []
    for r in resultados or []:
        bot = _safe_text(r.get("Senal Bot"))
        if bot in ("BUY STRONG", "BUY"):
            t = _safe_text(r.get("Accion"))
            buy_candidates.append({
                "ticker": t,
                "signal": bot,
                "score": _round(r.get("Score calidad")),
                "risk": _safe_text(r.get("Riesgo")),
                "already_open": t in abiertas,
                "entry": f"{_safe_text(r.get('Entrada min'))} - {_safe_text(r.get('Entrada max'))}",
                "stop": _round(r.get("Stop loss")),
                "target": _round(r.get("Objetivo")),
            })

    motivos = {}
    for b in blocked:
        m = b.get("reason") or "SIN MOTIVO"
        motivos[m] = motivos.get(m, 0) + 1

    return {
        "updated": _now_visible(),
        "version": "V4.3",
        "mode": "AUDITORIA_BLOQUEOS_EXISTENTES",
        "summary": {
            "blocked_count": len(blocked),
            "buy_candidates_count": len(buy_candidates),
            "open_positions_count": len(positions),
            "warnings_count": len(warnings),
            "main_block_reason": max(motivos, key=motivos.get) if motivos else "SIN BLOQUEOS REGISTRADOS",
        },
        "warnings": warnings,
        "block_reasons": [{"reason": k, "count": v} for k, v in sorted(motivos.items(), key=lambda x: x[1], reverse=True)],
        "blocked_signals": blocked,
        "buy_candidates": buy_candidates[:80],
        "notes": [
            "Este archivo no crea lógica nueva; resume bloqueos ya existentes en historial_senales.json.",
            "Sirve para explicar por qué el bot no abrió compras aunque hubiera señales BUY.",
        ]
    }

def build_paper_state(historial, resultados, mercado, config):
    ops = _operaciones(historial)
    resumen = _resumen(historial)

    open_ops = [op for op in ops if _safe_text(op.get("estado")).upper() == "ABIERTA"]
    closed_ops = [op for op in ops if _safe_text(op.get("estado")).upper() == "CERRADA"]

    positions = [_position_from_operation(op, idx) for idx, op in enumerate(open_ops)]
    orders = []
    for idx, op in enumerate(ops):
        orders.extend(_orders_from_operation(op, idx))

    trades = [_trade_from_closed_operation(op, idx) for idx, op in enumerate(closed_ops)]

    sim = dict(resumen.get("simulacion", {}) or {})
    risk = dict(resumen.get("riesgo", {}) or {})
    metrics = dict(resumen.get("metricas", {}) or {})
    diagnostico = dict(resumen.get("diagnostico_bot", {}) or {})

    capital_inicial = _num(config.get("capital_inicial"), _num(sim.get("capital_inicial"), 5000))
    exposure_usd = sum(_num(p.get("market_value_usd")) for p in positions)
    open_risk_usd = sum(_num(p.get("risk_usd")) for p in positions)
    open_pnl_usd = sum(_num(p.get("open_pnl_usd")) for p in positions)
    closed_pnl_usd = sum(_num(t.get("pnl_usd_estimated")) for t in trades)

    max_positions = int(_num(config.get("max_operaciones_abiertas"), 20))
    exposure_pct = (exposure_usd / capital_inicial * 100) if capital_inicial else 0
    risk_pct = (open_risk_usd / capital_inicial * 100) if capital_inicial else 0

    warnings = []
    if len(positions) >= max_positions:
        warnings.append("Máximo de posiciones abiertas alcanzado.")
    if exposure_pct > _num(config.get("max_exposicion_total_pct"), 80):
        warnings.append("Exposición estimada supera el límite configurado.")
    if risk_pct > 10:
        warnings.append("Riesgo abierto total elevado.")
    if diagnostico.get("riesgo") == "ALTO":
        warnings.append("Diagnóstico general marca riesgo ALTO.")

    portfolio = {
        "updated": _now_visible(),
        "version": "V4",
        "mode": "PAPER_TRADING_SIMULATED",
        "capital_initial_usd": _round(capital_inicial),
        "cash_model_note": "Cash derivado de simulación histórica; no representa cuenta broker real.",
        "closed_pnl_usd_estimated": _round(closed_pnl_usd),
        "open_pnl_usd_estimated": _round(open_pnl_usd),
        "total_pnl_usd_estimated": _round(closed_pnl_usd + open_pnl_usd),
        "exposure_usd": _round(exposure_usd),
        "exposure_pct": _round(exposure_pct),
        "open_risk_usd": _round(open_risk_usd),
        "open_risk_pct": _round(risk_pct),
        "open_positions": len(positions),
        "closed_trades": len(trades),
        "positions": positions
    }

    risk_state = {
        "updated": _now_visible(),
        "version": "V4",
        "mode": "PAPER_TRADING_SIMULATED",
        "market_state": mercado,
        "risk_config": config,
        "summary_from_bot": risk,
        "metrics_from_bot": metrics,
        "diagnostic_from_bot": diagnostico,
        "warnings": warnings,
        "can_open_more_positions": len(positions) < max_positions,
        "remaining_position_slots": max(max_positions - len(positions), 0),
        "exposure_pct": _round(exposure_pct),
        "open_risk_pct": _round(risk_pct)
    }

    status = {
        "updated": _now_visible(),
        "version": "V4",
        "engine": "PAPER_TRADING_ENGINE",
        "mode": "PAPER_ONLY_NO_REAL_ORDERS",
        "health": "OK" if not warnings else "WARNING",
        "warnings_count": len(warnings),
        "warnings": warnings,
        "market": mercado,
        "positions_open": len(positions),
        "orders_total": len(orders),
        "trades_closed": len(trades),
        "signals_available": len(resultados or []),
        "broker_real_enabled": False,
        "files": {
            "portfolio": "paper/paper_portfolio.json",
            "orders": "paper/paper_orders.json",
            "trades": "paper/paper_trades.json",
            "risk": "paper/paper_risk.json",
            "status": "paper/paper_status.json",
            "state": "paper/paper_state.json",
            "audit": "paper/paper_audit.json"
        }
    }

    audit = _audit_from_historial(historial, resultados, positions, warnings, config)

    state = {
        "updated": _now_visible(),
        "version": "V4.3",
        "status": status,
        "portfolio": portfolio,
        "orders": {
            "updated": _now_visible(),
            "mode": "PAPER_ONLY",
            "orders": orders[-600:]
        },
        "trades": {
            "updated": _now_visible(),
            "mode": "PAPER_ONLY",
            "trades": trades[-600:]
        },
        "risk": risk_state,
        "audit": audit
    }

    return state


def export_paper_state(historial, resultados, mercado, config):
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    state = build_paper_state(historial, resultados, mercado, config)

    _write_json(PAPER_DIR / "paper_portfolio.json", state["portfolio"])
    _write_json(PAPER_DIR / "paper_orders.json", state["orders"])
    _write_json(PAPER_DIR / "paper_trades.json", state["trades"])
    _write_json(PAPER_DIR / "paper_risk.json", state["risk"])
    _write_json(PAPER_DIR / "paper_status.json", state["status"])
    _write_json(PAPER_DIR / "paper_audit.json", state["audit"])
    _write_json(PAPER_DIR / "paper_state.json", state)

    return state
