"""Immutable entry accounting and append-only trade retention for simulated stocks.

Legacy balances are carried forward explicitly, never claimed as reconstructed fills.
Cash is derived from frozen entries and realized PnL, not from repeated position sizing.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json

from engine.policy import (VERSION, NY, number, timestamp, side_cost, fresh_quote,
                           market_session, next_sell_at, can_sell, holding_sessions,
                           entry_filter, position_size, portfolio_gate, exit_reason)


def config_hash(config):
    return sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest()


def validate(book):
    if not isinstance(book, dict) or not isinstance(book.get("operaciones"), list):
        raise ValueError("Historial inválido: se detiene sin reiniciar capital")
    if book.get("schema_version", 1) not in (1, 2):
        raise ValueError("Versión de historial no soportada")
    ids = set()
    opened = set()
    for op in book["operaciones"]:
        if not isinstance(op, dict) or not op.get("id") or op["id"] in ids:
            raise ValueError("Operación sin ID/duplicada")
        ids.add(op["id"])
        if op.get("estado") not in ("ABIERTA", "CERRADA"):
            raise ValueError("Estado de operación inválido")
        if number(op.get("precio_entrada")) <= 0 or number(op.get("posicion_usd_estimada")) <= 0:
            raise ValueError("Base contable inválida")
        if op["estado"] == "CERRADA":
            number(op.get("pnl_usd_estimado"))
        else:
            if op.get("accion") in opened:
                raise ValueError("Posición duplicada")
            opened.add(op.get("accion"))
            if not 0 < number(op.get("stop")) < number(op["precio_entrada"]) < number(op.get("objetivo")):
                raise ValueError("Niveles de posición abierta inválidos")
            next_sell_at(op["fecha_entrada"])
        if book.get("schema_version") == 2 and op.get("accounting_quality") == "V5":
            if abs(number(op["acciones_estimadas"]) * op["precio_entrada"] - op["posicion_usd_estimada"]) > 1e-6:
                raise ValueError("Cantidad × precio no coincide con importe")
            if op["entry_fingerprint"] != entry_fingerprint(op):
                raise ValueError("Entrada inmutable modificada")
    if book.get("schema_version") == 2:
        number(book["accounting"]["initial_capital"])


def entry_fingerprint(op):
    keys = ("id", "entry_timestamp", "precio_entrada", "acciones_estimadas", "posicion_usd_estimada",
            "entry_cost_usd", "cost_rate_per_side", "stop", "objetivo", "config_hash")
    return config_hash({k: op[k] for k in keys})


def migrate(book, config, now):
    """Idempotent: freeze latest published notional, not the inconsistent old quantity."""
    validate(book)
    if book.get("schema_version") == 2:
        if number(config["capital_inicial"]) != book["accounting"]["initial_capital"]:
            raise ValueError("Cambiar capital requiere un depósito/retiro explícito, no editar config")
        return book
    old = deepcopy(book)
    now = timestamp(now)
    book["schema_version"] = 2
    book["accounting"] = {
        "initial_capital": number(config["capital_inicial"]),
        "migrated_at": now.isoformat(), "legacy_snapshot_sha256": config_hash(old),
        "legacy_operations": len(book["operaciones"]),
        "legacy_certified": False,
        "basis": "Último importe publicado congelado; cantidad abierta derivada de importe/precio. No reconstruye fills antiguos.",
        "missing_history_recovered": False,
    }
    book["daily_equity"] = []
    for op in book["operaciones"]:
        op["accounting_quality"] = "LEGACY_NO_RECONCILIADO"
        if op["estado"] == "CERRADA":
            continue  # historical prices, quantities, notional and PnL remain byte-for-value unchanged
        op["legacy_quantity_before_migration"] = op.get("acciones_estimadas")
        op["acciones_estimadas"] = op["posicion_usd_estimada"] / op["precio_entrada"]
        op["cost_rate_per_side"] = number(op.get("costo_total_estimado_pct", 0.23)) / 200
        op["entry_cost_usd"] = op["posicion_usd_estimada"] * op["cost_rate_per_side"]
        op["sell_eligible_at"] = next_sell_at(op["fecha_entrada"])
    # Keep the published high-water mark as a conservative legacy reference.
    previous_dd = number(old.get("resumen", {}).get("riesgo", {}).get("max_drawdown_pct", 0))
    book["accounting"]["legacy_max_drawdown_pct"] = previous_dd
    book["accounting"]["peak_equity"] = config["capital_inicial"]
    return book


def mark(op, price):
    price = number(price)
    if price <= 0:
        raise ValueError("Non-positive mark")
    qty, basis = number(op["acciones_estimadas"]), number(op["posicion_usd_estimada"])
    gross = qty * price
    exit_cost = gross * op["cost_rate_per_side"]
    pnl = gross - exit_cost - basis - op["entry_cost_usd"]
    op.update({"precio_actual": price, "valor_cartera_usd": gross - exit_cost,
               "market_value_gross_usd": gross, "ganancia_abierta_usd_estimada": pnl,
               "pnl_usd_estimado": pnl, "ganancia_pct": (price / op["precio_entrada"] - 1) * 100,
               "ganancia_pct_neta_estimada": pnl / basis * 100,
               "costo_usd_estimado": op["entry_cost_usd"] + exit_cost,
               "riesgo_usd_estimado": max(gross - qty * op["stop"], 0) + exit_cost,
               "distancia_stop_actual_pct": (price - op["stop"]) / price * 100,
               "distancia_objetivo_pct": (op["objetivo"] - price) / price * 100})
    op["max_ganancia_pct"] = max(op.get("max_ganancia_pct", 0), op["ganancia_pct"])
    op["max_perdida_pct"] = min(op.get("max_perdida_pct", 0), op["ganancia_pct"])


def balances(book):
    opened = [o for o in book["operaciones"] if o["estado"] == "ABIERTA"]
    closed = [o for o in book["operaciones"] if o["estado"] == "CERRADA"]
    initial = book["accounting"]["initial_capital"]
    realized = sum(number(o["pnl_usd_estimado"]) for o in closed)
    committed = sum(o["posicion_usd_estimada"] + o["entry_cost_usd"] for o in opened)
    cash = initial + realized - committed
    net_value = sum(o["valor_cartera_usd"] for o in opened)
    equity = cash + net_value
    exposure = sum(o["market_value_gross_usd"] for o in opened)
    risk = sum(o["riesgo_usd_estimado"] for o in opened)
    return {"initial": initial, "realized": realized, "committed": committed, "cash": cash,
            "equity": equity, "exposure": exposure, "risk": risk, "net_value": net_value,
            "open_pnl": sum(o["pnl_usd_estimado"] for o in opened), "opened": opened, "closed": closed}


def close_position(op, price, reason, now, quote_time, market="SIN DATOS"):
    """The only fill-to-close path, used by live and historical simulation."""
    now = timestamp(now)
    if op["estado"] != "ABIERTA" or not can_sell(op["fecha_entrada"], now):
        return False
    mark(op, price)
    op.update({"estado": "CERRADA", "fecha_cierre": now.astimezone(NY).date().isoformat(),
               "exit_timestamp": now.isoformat(), "exit_quote_timestamp": quote_time,
               "precio_cierre": price, "ganancia_pct_final": op["ganancia_pct"], "tipo_cierre": reason,
               "resultado": "GANADA" if op["pnl_usd_estimado"] > 0 else "PERDIDA",
               "exit_cost_usd": op["acciones_estimadas"] * price * op["cost_rate_per_side"],
               "valor_cartera_usd": 0, "mercado_cierre": market,
               "dias_abierta": holding_sessions(op["fecha_entrada"], now)})
    return True


def streaks(closed):
    current = wins = losses = max_w = max_l = 0
    kind = ""
    for op in sorted(closed, key=lambda o: (o.get("exit_timestamp", o.get("fecha_cierre", "")), o["id"])):
        win = op["pnl_usd_estimado"] > 0
        wins = wins + 1 if win else 0
        losses = losses + 1 if not win else 0
        max_w, max_l = max(max_w, wins), max(max_l, losses)
        current, kind = (wins, "GANADAS") if win else (losses, "PERDIDAS")
    return {"racha_actual": current, "racha_actual_tipo": kind, "racha_max_ganadas": max_w,
            "racha_max_perdidas": max_l}


def drawdown(book, equity):
    peak = max(book["accounting"].get("peak_equity", equity), equity)
    return (peak - equity) / peak * 100 if peak > 0 else 100


def grouped(closed, field):
    groups = {}
    for op in closed:
        groups.setdefault(op.get(field) or "SIN DATOS", []).append(op)
    result = []
    for name, ops in groups.items():
        pnl = sum(o["pnl_usd_estimado"] for o in ops)
        basis = sum(o["posicion_usd_estimada"] for o in ops)
        wins = sum(o["pnl_usd_estimado"] > 0 for o in ops)
        profit = sum(max(o["pnl_usd_estimado"], 0) for o in ops)
        loss = -sum(min(o["pnl_usd_estimado"], 0) for o in ops)
        result.append({"grupo": name, "operaciones": len(ops), "ganadas": wins, "perdidas": len(ops)-wins,
                       "win_rate": wins / len(ops) * 100, "pnl_usd": pnl,
                       "rentabilidad_neta_pct": pnl / basis * 100 if basis else None,
                       "profit_factor": profit / loss if loss else None,
                       "return_basis": "P&L / suma de importes; no retorno de cartera"})
    return sorted(result, key=lambda x: x["pnl_usd"], reverse=True)


def summarize(book, config, now, blocked=None, warnings=None):
    b = balances(book)
    eq, initial = b["equity"], b["initial"]
    closed, opened = b["closed"], b["opened"]
    stats = streaks(closed)
    dd = drawdown(book, eq)
    exp_pct = b["exposure"] / eq * 100 if eq > 0 else 100
    risk_pct = b["risk"] / eq * 100 if eq > 0 else 100
    pnl = [o["pnl_usd_estimado"] for o in closed]
    wins, losses = [p for p in pnl if p > 0], [-p for p in pnl if p <= 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    gate = portfolio_gate(config, eq, dd, stats["racha_actual"] if stats["racha_actual_tipo"] == "PERDIDAS" else 0, len(opened))
    if any(o.get("quote_stale") for o in opened):
        gate = "Entradas bloqueadas: faltan cotizaciones actuales de cartera"
    alerts = list(warnings or [])
    if book["accounting"].get("legacy_operations"):
        alerts.append("Historial anterior a V5 no reconciliado; el saldo heredado no está certificado.")
    alerts.append("No se vende el día de compra. El stop no limita pérdidas overnight ni gaps.")
    if b["cash"] < -0.01:
        gate = "Caja negativa heredada: entradas bloqueadas hasta reconciliar"
        alerts.append(gate)
    state = "BLOQUEADO" if gate and not gate.startswith("Modo defensivo") else "DEFENSIVO" if gate else "NORMAL"
    curve = [{"n": i, "fecha": p["fecha"], "capital": p["equity"], "drawdown_pct": p["drawdown_pct"]}
             for i, p in enumerate(book.get("daily_equity", []))]
    ratios = {"sharpe_ratio": None, "sortino_ratio": None, "calmar_ratio": None, "cagr_pct": None}
    # Do not annualize per-trade returns or mix incomparable legacy reconstructed equity.
    completed = [p for p in book.get("daily_equity", []) if p.get("session_final")]
    if len(completed) >= 20:
        from backtest.metrics import calcular_metricas_backtest
        computed = calcular_metricas_backtest(completed, [], completed[0]["equity"])
        ratios.update({k: computed.get(k) for k in ratios})
    max_dd = max([book["accounting"].get("legacy_max_drawdown_pct", 0), dd] +
                 [p["drawdown_pct"] for p in book.get("daily_equity", [])])
    return {
        "total_operaciones": len(book["operaciones"]), "abiertas": len(opened), "cerradas": len(closed),
        "ganadas": len(wins), "perdidas": len(losses), "win_rate": len(wins) / len(pnl) * 100 if pnl else 0,
        "nuevas_bloqueadas": blocked or [], "config_simulacion": config,
        "simulacion": {
            "capital_inicial": initial, "capital_actual_cerrado": initial + b["realized"],
            "capital_actual_total_estimado": eq, "ganancia_neta_usd": b["realized"],
            "ganancia_total_estimada_usd": eq - initial, "rentabilidad_neta_pct": b["realized"] / initial * 100,
            "rentabilidad_total_estimada_pct": (eq / initial - 1) * 100,
            "costos_totales_usd": sum(o.get("costo_usd_estimado", 0) for o in closed) + sum(o["entry_cost_usd"] for o in opened),
            "costo_total_estimado_pct_por_operacion": side_cost(config) * 200,
            "ganancia_abierta_neta_usd": b["open_pnl"], "valor_total_en_cartera_usd": b["net_value"],
            "caja_comprometida_usd": b["committed"], "caja_disponible_usd": b["cash"],
            "caja_disponible_pct": b["cash"] / eq * 100 if eq > 0 else 0,
            "max_nueva_posicion_usd": max(0, min(b["cash"] / (1 + side_cost(config)), eq * config["max_posicion_pct"] / 100,
                                                  eq * config["max_exposicion_total_pct"] / 100 - b["exposure"])),
            "modo": "SIMULACIÓN", "accounting": book["accounting"],
        },
        "riesgo": {**stats, "max_drawdown_pct": max_dd, "drawdown_actual_pct": dd,
                   "max_drawdown_usd": book["accounting"].get("peak_equity", initial) * max_dd / 100,
                   "exposicion_abierta_usd": b["exposure"], "exposicion_abierta_pct": exp_pct,
                   "riesgo_total_abierto_usd": b["risk"], "riesgo_total_abierto_pct": risk_pct,
                   "operaciones_abiertas": len(opened), "max_operaciones_abiertas": config["max_operaciones_abiertas"],
                   "denominator": "equity_neta_actual", "stop_is_guaranteed": False},
        "metricas": {"profit_factor": sum(wins) / sum(losses) if sum(losses) else None,
                     "total_ganado_usd": sum(wins), "total_perdido_usd": sum(losses),
                     "ganancia_promedio_pct": sum(o["ganancia_pct_neta_estimada"] for o in closed if o["pnl_usd_estimado"] > 0) / len(wins) if wins else 0,
                     "perdida_promedio_pct": sum(o["ganancia_pct_neta_estimada"] for o in closed if o["pnl_usd_estimado"] <= 0) / len(losses) if losses else 0,
                     "expectancy_usd": sum(pnl) / len(pnl) if pnl else 0,
                     "expectativa_pct_por_operacion": sum(o["ganancia_pct_neta_estimada"] for o in closed) / len(closed) if closed else 0,
                     "payoff_ratio": avg_win / avg_loss if avg_loss else None,
                     "ratio_ganancia_perdida": avg_win / avg_loss if avg_loss else None,
                     "avg_win_usd": avg_win, "avg_loss_usd": avg_loss,
                     "avg_holding_dias": sum(o.get("dias_abierta", 0) for o in closed) / len(closed) if closed else 0,
                     "ratios_basis": "Sesiones completas observadas desde V5; mínimo 20, sin interpolar faltantes", **ratios},
        "equity_curve": curve, "resumen_diario": book.get("daily_equity", []),
        "rendimiento_por_sector": grouped(closed, "sector"), "rendimiento_por_mercado": grouped(closed, "mercado_entrada"),
        "mejores_operaciones": sorted(closed, key=lambda o: o["pnl_usd_estimado"], reverse=True)[:10],
        "peores_operaciones": sorted(closed, key=lambda o: o["pnl_usd_estimado"])[:10],
        "reglas_operativas": {"version": VERSION, "estado": state, "drawdown_pct": dd,
                              "session_open": market_session(now)["is_open"],
                              "exposicion_abierta_pct": exp_pct, "riesgo_abierto_pct": risk_pct,
                              "max_exposicion_total_pct": config["max_exposicion_total_pct"],
                              "max_riesgo_total_abierto_pct": config["max_riesgo_total_abierto_pct"],
                              "bloqueos_generados": len(blocked or []), "motivo_principal": gate or "SIN BLOQUEO GLOBAL"},
        "diagnostico_bot": {"modo": state, "riesgo_sistema": "ALTO" if gate else "MEDIO", "alertas": alerts},
        "nota": "Libro continuo: no recorta ni redimensiona operaciones. P&L neto de costos estimados; no es una cuenta real.",
    }


def update(book, signals, market, config, now, quotes):
    now = timestamp(now)
    book = migrate(deepcopy(book), config, now)
    today = now.astimezone(NY).date().isoformat()
    by_ticker = {s["Accion"]: s for s in signals}
    warnings, blocked = [], []
    stale_positions = False
    session = market_session(now)
    for op in book["operaciones"]:
        if op["estado"] != "ABIERTA":
            continue
        tk = op["accion"]
        sig, quote = by_ticker.get(tk, {}), quotes.get(tk, {})
        fresh = fresh_quote(quote, now, config.get("max_quote_age_seconds", 180))
        closing_mark = False
        if session["market_close"] and now >= timestamp(session["market_close"]):
            try:
                close_time = timestamp(session["market_close"])
                closing_mark = (close_time - timedelta(seconds=90) <= timestamp(quote["timestamp"]) < close_time
                                and number(quote["price"]) > 0)
            except (KeyError, ValueError, TypeError):
                pass
        price = quote["price"] if fresh or closing_mark else op.get("precio_actual", op["precio_entrada"])
        mark(op, price)
        op["quote_stale"] = not (fresh or closing_mark)
        op["closing_mark_confirmed"] = closing_mark
        op["sale_locked"] = not can_sell(op["fecha_entrada"], now)
        op["sell_eligible_at"] = next_sell_at(op["fecha_entrada"])
        op["dias_abierta"] = holding_sessions(op["fecha_entrada"], now)
        if fresh or closing_mark:
            op["quote_timestamp"] = quote["timestamp"]
        else:
            stale_positions = True
            warnings.append(f"{tk}: sin cotización reciente; no se ejecuta y se bloquean nuevas entradas.")
        for source, dest in (("Senal Bot", "senal_bot_actual"), ("Riesgo", "riesgo_actual"), ("Score calidad", "score_calidad_actual")):
            if source in sig:
                op[dest] = sig[source]
        reason = exit_reason(op, price, sig.get("Senal Bot"), now, config) if fresh else ""
        if reason:
            close_position(op, price, reason, now, quote["timestamp"], market.get("estado", "SIN DATOS"))
    initial_balance = balances(book)
    book["accounting"]["peak_equity"] = max(book["accounting"].get("peak_equity", 0), initial_balance["equity"])
    for rank, sig in enumerate(signals, 1):
        sig["rank"] = rank
        sig["eligible"] = False
        tk = sig["Accion"]
        if sig.get("Senal Bot") not in ("BUY", "BUY STRONG"):
            sig["decision_reason"] = "Sin señal de compra"
            continue
        b = balances(book)
        quote = quotes.get(tk, {})
        price = quote.get("price", sig["Precio actual"])
        recent = fresh_quote(quote, now, config.get("max_quote_age_seconds", 180))
        reason = entry_filter(sig, config, price)
        if not session["is_open"]:
            reason = "Bolsa cerrada (force no permite operar fuera de sesión)"
        elif stale_positions:
            reason = "Posiciones abiertas con cotizaciones desactualizadas"
        elif not recent:
            reason = "Cotización ausente/desactualizada"
        elif sig.get("bar_session") != today:
            reason = "Señal no corresponde a la sesión actual"
        elif any(o["accion"] == tk and o["estado"] == "ABIERTA" for o in book["operaciones"]):
            reason = "Ya en cartera"
        elif any(o["accion"] == tk and (o["fecha_entrada"] == today or o.get("fecha_cierre") == today) for o in book["operaciones"]):
            reason = "Cooldown: ya operada hoy"
        stats = streaks(b["closed"])
        losing = stats["racha_actual"] if stats["racha_actual_tipo"] == "PERDIDAS" else 0
        reason = reason or portfolio_gate(config, b["equity"], drawdown(book, b["equity"]), losing, len(b["opened"]), sig["Senal Bot"] == "BUY STRONG")
        sector_exp = sum(o["market_value_gross_usd"] for o in b["opened"] if o.get("sector") == sig.get("Sector"))
        dim = None if reason else position_size(b["equity"], b["cash"], price, sig["Stop loss"], config, b["exposure"], b["risk"], sector_exp)
        if not reason and not dim:
            reason = "Sin capacidad de caja/exposición/riesgo/sector"
        sig["decision_reason"] = reason or "Compra simulada ejecutada"
        if reason:
            blocked.append({"fecha": today, "accion": tk, "senal_bot": sig["Senal Bot"], "motivo": reason,
                            "rr": sig.get("R/R"), "riesgo": sig.get("Riesgo"), "score": sig.get("Score calidad"),
                            "precio": price, "regla_operativa": True})
            continue
        op = {"id": f"{today}-{tk}", "accion": tk, "sector": sig.get("Sector", "Otro"),
              "fecha_entrada": today, "entry_timestamp": now.isoformat(), "signal_timestamp": sig.get("signal_timestamp"),
              "entry_quote_timestamp": quote["timestamp"], "quote_timestamp": quote["timestamp"],
              "precio_entrada": price, "acciones_estimadas": dim["quantity"], "posicion_usd_estimada": dim["notional"],
              "entry_cost_usd": dim["entry_cost"], "cost_rate_per_side": side_cost(config),
              "costo_total_estimado_pct": side_cost(config) * 200, "stop": sig["Stop loss"], "objetivo": sig["Objetivo"],
              "rr": (sig["Objetivo"] - price) / (price - sig["Stop loss"]),
              "estado": "ABIERTA", "resultado": "EN SEGUIMIENTO", "dias_abierta": 0,
              "strategy_version": VERSION, "config_hash": config_hash(config), "config_at_entry": deepcopy(config),
              "accounting_quality": "V5", "senal_bot_entrada": sig["Senal Bot"], "senal_bot_actual": sig["Senal Bot"],
              "riesgo_entrada": sig["Riesgo"], "riesgo_actual": sig["Riesgo"],
              "score_calidad_entrada": sig.get("Score calidad", 0), "score_calidad_actual": sig.get("Score calidad", 0),
              "mercado_entrada": sig["Mercado"], "contexto_sector_entrada": sig.get("Contexto sector"),
              "sell_eligible_at": next_sell_at(today), "sale_locked": True, "quote_stale": False,
              "riesgo_inicial_usd": dim["risk"], "perdida_maxima_stop_usd": dim["risk"]}
        op["entry_fingerprint"] = entry_fingerprint(op)
        mark(op, price)
        book["operaciones"].append(op)
        sig["eligible"] = True
    validate(book)
    b = balances(book)
    dd = drawdown(book, b["equity"])
    # Observed marks, never invented daily closes; keep date-level points and running max.
    point = {"fecha": today, "timestamp": now.isoformat(), "equity": b["equity"],
             "drawdown_pct": dd, "session_final": False}
    completed = bool(session["market_close"] and now >= timestamp(session["market_close"])
                     and all(o.get("closing_mark_confirmed") for o in b["opened"]))
    point["session_final"] = completed
    if session["is_open"] or completed:
        curve = book.setdefault("daily_equity", [])
        if curve and curve[-1]["fecha"] == today:
            point["drawdown_pct"] = max(dd, curve[-1]["drawdown_pct"])
            curve[-1] = point
        else:
            curve.append(point)
    book["actualizado"] = now.astimezone(NY).strftime("%d-%m-%Y %I:%M %p Nueva York")
    book["generated_at"] = now.isoformat()
    book["run_id"] = f"{now.strftime('%Y%m%dT%H%M%S%fZ')}-{config_hash(config)[:8]}"
    book["resumen"] = summarize(book, config, now, blocked, warnings)
    book["market_session"] = session
    return book
