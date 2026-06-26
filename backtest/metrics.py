"""
BOT-ARQ V4.7 - Métricas de backtest.

Calcula las métricas sobre la EQUITY CURVE DIARIA (estándar de la industria
para backtests), no solo sobre trades. Sharpe/Sortino se anualizan con
sqrt(252). El CAGR usa el periodo real; Calmar = CAGR / MaxDrawdown.

Coherente con los ratios de V4.6 del dashboard, pero medido sobre la curva
de capital diaria simulada (más riguroso que medir solo por trade).
"""


def _stdev(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return (sum((x - mu) ** 2 for x in xs) / (n - 1)) ** 0.5


def calcular_metricas_backtest(equity_curve, trades, capital_inicial):
    """Devuelve un dict con métricas riesgo/retorno del backtest."""
    if not equity_curve:
        return {}

    equities = [e["equity"] for e in equity_curve]
    n = len(equities)

    # Retornos diarios de la equity
    rets = []
    for i in range(1, n):
        prev = equities[i - 1]
        if prev > 0:
            rets.append(equities[i] / prev - 1)

    mu = sum(rets) / len(rets) if rets else 0.0
    sigma = _stdev(rets)
    sharpe = round(mu / sigma * (252 ** 0.5), 3) if sigma > 0 else None

    negativos = [r for r in rets if r < 0]
    downside = _stdev(negativos) if len(negativos) > 1 else 0.0
    sortino = round(mu / downside * (252 ** 0.5), 3) if downside > 0 else None

    # Max drawdown sobre la curva de equity
    peak = equities[0]
    max_dd = 0.0
    for eq in equities:
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak * 100)

    # CAGR usando el número de días simulados
    equity_fin = equities[-1]
    dias = n
    cagr = None
    if dias >= 90 and capital_inicial > 0 and equity_fin > 0:
        cagr = round(((equity_fin / capital_inicial) ** (252 / dias) - 1) * 100, 2)
    calmar = round(cagr / max_dd, 3) if (cagr is not None and max_dd > 0) else None

    # Métricas de trades
    pnls = [t["pnl_usd_estimado"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = round(len(wins) / len(pnls) * 100, 2) if pnls else 0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0
    avg_loss = round(abs(sum(losses) / len(losses)), 2) if losses else 0
    expectancy = round((win_rate / 100) * avg_win - (1 - win_rate / 100) * avg_loss, 2)
    payoff = round(avg_win / avg_loss, 2) if avg_loss else None
    profit_factor = round(sum(wins) / abs(sum(losses)), 2) if losses and sum(losses) != 0 else None
    holding = round(sum(t["dias_abierta"] for t in trades) / len(trades), 1) if trades else 0

    return {
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "cagr_pct": cagr,
        "max_drawdown_pct": round(max_dd, 2),
        "retorno_total_pct": round((equity_fin / capital_inicial - 1) * 100, 2) if capital_inicial else 0,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "expectancy_usd": expectancy,
        "payoff_ratio": payoff,
        "avg_win_usd": avg_win,
        "avg_loss_usd": avg_loss,
        "avg_holding_dias": holding,
        "trades_total": len(trades),
        "dias_simulados": dias,
    }


def winrate_por_sector(trades):
    """Desglose win rate + PnL por sector (mín. 2 trades), igual idea que V4.6."""
    m = {}
    for t in trades:
        s = t.get("sector") or "Sin sector"
        if s not in m:
            m[s] = {"wins": 0, "total": 0, "pnl_usd": 0.0}
        m[s]["total"] += 1
        m[s]["pnl_usd"] = round(m[s]["pnl_usd"] + t["pnl_usd_estimado"], 2)
        if t["pnl_usd_estimado"] > 0:
            m[s]["wins"] += 1
    return sorted(
        [{"sector": s, "trades": v["total"],
          "win_rate_pct": round(v["wins"] / v["total"] * 100, 1),
          "pnl_usd": v["pnl_usd"]}
         for s, v in m.items() if v["total"] >= 2],
        key=lambda x: x["pnl_usd"], reverse=True,
    )
