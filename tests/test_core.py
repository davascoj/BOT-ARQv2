from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import math

import pandas as pd
import pytest

import analizador_acciones as analyzer
from engine.policy import (can_sell, market_session, next_sell_at, fresh_quote, position_size,
                           entry_filter, holding_sessions, side_cost, portfolio_gate)
from engine.ledger import update, validate, balances, migrate, close_position
from engine.config_loader import cargar_config_simulacion, cargar_config_sistema
from engine.storage import atomic_json, read_json
from engine.paper_trading_engine import build_paper_state
from backtest.engine import run_backtest
from backtest.metrics import calcular_metricas_backtest


@pytest.fixture
def cfg():
    return dict(analyzer.CONFIG_SIMULACION)


def when(value="2026-10-14T15:00:00+00:00"):
    return datetime.fromisoformat(value)


def signal(tk="AAA", now=None, price=100):
    now = now or when()
    return {"Accion": tk, "Sector": tk, "Precio actual": price, "Stop loss": 95,
            "Objetivo": 110, "Senal Bot": "BUY", "Riesgo": "BAJO", "Mercado": "NEUTRO",
            "Confirmacion": "ALTA", "Contexto sector": "ACOMPAÑA", "Volumen relativo": 1,
            "Score calidad": 80, "signal_timestamp": now.isoformat(), "bar_session": str(now.date())}


def quote(price=100, now=None):
    return {"price": price, "timestamp": (now or when()).isoformat()}


def opened(cfg, tk="AAA"):
    return update({"operaciones": [], "resumen": {}}, [signal(tk)], {"estado": "NEUTRO"}, cfg, when(), {tk: quote()})


@pytest.mark.parametrize("entry,now,allowed", [
    ("2026-10-14", "2026-10-14T19:59:59+00:00", False),
    ("2026-10-14", "2026-10-15T13:29:59+00:00", False),
    ("2026-10-14", "2026-10-15T13:30:00+00:00", True),
    ("2026-10-14", "2026-10-15T20:00:00+00:00", False),
    ("2026-10-16", "2026-10-17T15:00:00+00:00", False),
    ("2026-10-16", "2026-10-19T13:30:00+00:00", True),
    ("2026-11-25", "2026-11-26T16:00:00+00:00", False),
    ("2026-11-25", "2026-11-27T17:59:59+00:00", True),
    ("2026-11-25", "2026-11-27T18:00:00+00:00", False),
    ("2026-03-06", "2026-03-09T13:30:00+00:00", True),
    ("2026-10-30", "2026-11-02T14:29:59+00:00", False),
    ("2026-10-30", "2026-11-02T14:30:00+00:00", True),
])
def test_calendar_sale_lock(entry, now, allowed):
    assert can_sell(entry, when(now)) is allowed


@pytest.mark.parametrize("price,bot", [(90, "HOLD"), (120, "HOLD"), (100, "SELL / EVITAR")])
def test_all_exit_types_blocked_on_entry_day(cfg, price, bot):
    book = opened(cfg)
    sig = signal(); sig["Senal Bot"] = bot
    result = update(book, [sig], {}, cfg, when(), {"AAA": quote(price)})
    assert result["operaciones"][0]["estado"] == "ABIERTA"
    assert result["operaciones"][0]["sale_locked"] is True


@pytest.mark.parametrize("price,bot,reason", [(90, "HOLD", "STOP"), (120, "HOLD", "OBJETIVO"), (100, "SELL / EVITAR", "SEÑAL SELL")])
def test_exit_next_session(cfg, price, bot, reason):
    book = opened(cfg)
    now = when("2026-10-15T14:00:00+00:00")
    sig = signal(now=now); sig["Senal Bot"] = bot
    result = update(book, [sig], {}, cfg, now, {"AAA": quote(price, now)})
    op = result["operaciones"][0]
    assert op["estado"] == "CERRADA"
    assert op["tipo_cierre"] == reason
    assert op["pnl_usd_estimado"] == pytest.approx(op["acciones_estimadas"] * price * (1 - side_cost(cfg)) - op["posicion_usd_estimada"] - op["entry_cost_usd"])


def test_max_holding_exits_loser_on_session_not_calendar(cfg):
    result = update(opened(cfg), [], {}, cfg, when("2026-10-16T15:00:00+00:00"), {"AAA": quote(99, when("2026-10-16T15:00:00+00:00"))})
    assert result["operaciones"][0]["tipo_cierre"] == "TIEMPO MAXIMO"
    assert result["operaciones"][0]["resultado"] == "PERDIDA"
    assert holding_sessions("2026-10-16", when("2026-10-19T15:00:00+00:00")) == 1


@pytest.mark.parametrize("now", ["2026-10-15T12:00:00+00:00", "2026-10-15T20:00:00+00:00", "2026-10-17T15:00:00+00:00"])
def test_forced_run_never_trades_off_hours(cfg, now):
    now = when(now)
    result = update(opened(cfg), [signal("BBB", now)], {}, cfg, now, {"AAA": quote(90, now), "BBB": quote(100, now)})
    assert len(result["operaciones"]) == 1
    assert result["operaciones"][0]["estado"] == "ABIERTA"


def test_missing_signal_does_not_prevent_stop(cfg):
    now = when("2026-10-15T15:00:00+00:00")
    result = update(opened(cfg), [], {}, cfg, now, {"AAA": quote(90, now)})
    assert result["operaciones"][0]["tipo_cierre"] == "STOP"


@pytest.mark.parametrize("q", [{}, {"price": 100, "timestamp": "2026-10-13T15:00:00+00:00"}, {"price": math.nan, "timestamp": "2026-10-14T15:00:00+00:00"}, {"price": 100, "timestamp": "2026-10-14T15:00:01+00:00"}])
def test_stale_and_invalid_quotes_fail_closed(cfg, q):
    assert not fresh_quote(q, when())
    result = update(opened(cfg), [signal("BBB")], {}, cfg, when(), {"AAA": q, "BBB": quote()})
    assert len(result["operaciones"]) == 1


def test_entry_facts_immutable_and_idempotent(cfg):
    book = opened(cfg)
    original = deepcopy(book)
    for _ in range(3):
        book = update(book, [signal()], {}, cfg, when(), {"AAA": quote(101)})
    assert len(book["operaciones"]) == 1
    for key in ("acciones_estimadas", "precio_entrada", "posicion_usd_estimada", "entry_cost_usd", "entry_fingerprint"):
        assert book["operaciones"][0][key] == original["operaciones"][0][key]
    tampered = deepcopy(book); tampered["operaciones"][0]["acciones_estimadas"] += 1
    with pytest.raises(ValueError):
        validate(tampered)


def test_closed_pnl_never_recomputed_with_new_config(cfg):
    now = when("2026-10-15T15:00:00+00:00")
    closed = update(opened(cfg), [], {}, cfg, now, {"AAA": quote(120, now)})
    original = deepcopy(closed["operaciones"][0])
    cfg["comision_por_operacion_pct"] = 1
    after = update(closed, [], {}, cfg, now, {})
    assert after["operaciones"][0] == original


def test_reordering_open_positions_cannot_change_equity(cfg):
    book = update(opened(cfg), [signal("BBB")], {}, cfg, when(), {"AAA": quote(), "BBB": quote()})
    reverse = deepcopy(book); reverse["operaciones"].reverse()
    assert balances(book)["equity"] == pytest.approx(balances(reverse)["equity"])
    assert balances(book)["cash"] + balances(book)["net_value"] == pytest.approx(balances(book)["equity"])


def test_open_loss_in_drawdown_and_paper_agrees(cfg):
    book = update(opened(cfg), [], {}, cfg, when(), {"AAA": quote(80)})
    assert book["resumen"]["riesgo"]["drawdown_actual_pct"] > 0
    state = build_paper_state(book, [], {}, cfg)
    sim = book["resumen"]["simulacion"]
    assert state["portfolio"]["cash_available_usd"] == sim["caja_disponible_usd"]
    assert state["portfolio"]["exposure_pct"] == pytest.approx(round(book["resumen"]["riesgo"]["exposicion_abierta_pct"], 2))


def test_block_audit_records_risk_at_decision_and_published_threshold(cfg):
    book = opened(cfg)
    result = update(book, [signal()], {}, cfg, when(), {"AAA": quote()})
    risk = result["resumen"]["riesgo"]
    blocked = result["resumen"]["nuevas_bloqueadas"][0]
    assert blocked["exposicion_abierta_pct"] == risk["exposicion_abierta_pct"]
    assert blocked["riesgo_abierto_pct"] == risk["riesgo_total_abierto_pct"]
    assert blocked["drawdown_pct"] == risk["drawdown_actual_pct"]
    assert result["resumen"]["reglas_operativas"]["bloquear_entradas_drawdown_pct"] == 35
    state = build_paper_state(result, [], {}, cfg)
    assert state["audit"]["blocked_signals"][0]["exposure_pct"] == round(blocked["exposicion_abierta_pct"], 2)


def test_legacy_block_audit_does_not_fabricate_zero_risk(cfg):
    book = opened(cfg)
    book["resumen"]["nuevas_bloqueadas"] = [{"accion": "AAA", "motivo": "Sin dato legado"}]
    audit = build_paper_state(book, [], {}, cfg)["audit"]["blocked_signals"][0]
    assert audit["exposure_pct"] is None
    assert audit["open_risk_pct"] is None
    assert audit["drawdown_pct"] is None


def test_no_300_trade_retention(cfg):
    closed = {"id": "1", "accion": "X", "estado": "CERRADA", "fecha_entrada": "2026-01-02", "fecha_cierre": "2026-01-05",
              "precio_entrada": 100, "posicion_usd_estimada": 100, "pnl_usd_estimado": 1, "ganancia_pct_neta_estimada": 1}
    book = {"operaciones": [{**closed, "id": str(i)} for i in range(501)]}
    after = update(book, [], {}, cfg, when(), {})
    assert len(after["operaciones"]) == 501
    assert balances(after)["equity"] == 5501


def test_legacy_migration_preserves_closed_records_and_freezes_open_basis(cfg):
    # The checked-in live data is an integration fixture; never write it in tests.
    original = read_json(Path(__file__).parents[1] / "historial_senales.json")
    result = update(original, [], {}, cfg, when(), {})
    for before, after in zip(original["operaciones"], result["operaciones"]):
        if before["estado"] == "CERRADA":
            for key, val in before.items():
                assert after[key] == val
        else:
            assert after["posicion_usd_estimada"] == before["posicion_usd_estimada"]
            assert after["acciones_estimadas"] * after["precio_entrada"] == pytest.approx(after["posicion_usd_estimada"])
    assert result["accounting"]["legacy_certified"] is False
    again = update(result, [], {}, cfg, when(), {})
    assert result["accounting"] == again["accounting"]


@pytest.mark.parametrize("capital,price,stop", [(0, 100, 95), (-100, 100, 95), (5000, 100, 101), (5000, 0, 0)])
def test_bad_position_rejected(cfg, capital, price, stop):
    assert position_size(capital, max(capital, 0), price, stop, cfg) is None


def test_sizing_reserves_costs_and_post_trade_limits(cfg):
    cfg["max_exposicion_total_pct"] = 30
    cfg["max_exposicion_sector_pct"] = 30
    first = position_size(5000, 5000, 100, 95, cfg)
    eq = 5000 - 2 * first["entry_cost"]
    cash = 5000 - first["notional"] - first["entry_cost"]
    second = position_size(eq, cash, 100, 95, cfg, first["notional"], first["risk"])
    final_eq = eq - 2 * second["entry_cost"]
    assert first["notional"] + second["notional"] <= final_eq * .30 + 1e-7
    assert cash - second["notional"] - second["entry_cost"] >= 0


@pytest.mark.parametrize("key,value", [("riesgo_por_operacion_pct", -1), ("max_posicion_pct", 500), ("slippage_pct", math.nan), ("max_dias_holding", 0), ("max_operaciones_abiertas", 1.1), ("usar_drawdown_como_bloqueo", "nonsense")])
def test_invalid_config_rejected(key, value):
    config = deepcopy(analyzer.CONFIG_SISTEMA)
    config["simulation_config"][key] = value
    with pytest.raises(ValueError):
        cargar_config_simulacion(analyzer.DEFAULT_CONFIG_SIMULACION, config)


def test_corrupt_files_fail_closed_and_atomic_write(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken")
    with pytest.raises(ValueError):
        read_json(path)
    with pytest.raises(ValueError):
        cargar_config_sistema(path)
    atomic_json(path, {"valid": 1})
    with pytest.raises(ValueError):
        atomic_json(path, {"bad": math.nan})
    assert read_json(path) == {"valid": 1}


def test_rsi_edges():
    assert analyzer.rsi_real(pd.Series(range(30))).iloc[-1] == 100
    assert analyzer.rsi_real(pd.Series([100] * 30)).iloc[-1] == 50
    assert analyzer.rsi_real(pd.Series(range(30, 0, -1))).iloc[-1] == 0
    assert analyzer.numero(math.nan) is None


def price_frame(extra=4):
    from engine.policy import schedule
    days = schedule("2025-01-01", "2026-12-31").index[:220 + extra]
    return pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000.0}, index=days)


def test_backtest_has_no_future_close_sizing(cfg):
    cfg["max_dias_holding"] = 99
    a, b = price_frame(), price_frame()
    def sig(df, tk, market):
        size = len(df)
        if (tk == "AAA" and size == 220) or (tk == "BBB" and size == 221):
            result = signal(tk); result["Stop loss"] = 50; result["Objetivo"] = 300
            return result
    # Risk cap, not a future mark, determines BBB quantity at the open.
    one = run_backtest({"AAA": a, "BBB": b}, sig, lambda t: {"estado": "NEUTRO"}, cfg)
    a.iloc[222, a.columns.get_loc("Close")] = 200
    a.iloc[222, a.columns.get_loc("High")] = 201
    two = run_backtest({"AAA": a, "BBB": b}, sig, lambda t: {"estado": "NEUTRO"}, cfg)
    def qty(res):
        return next(o["acciones_estimadas"] for o in res["trades"] + res["posiciones_abiertas"] if o["accion"] == "BBB")
    assert qty(one) == qty(two)


def test_backtest_final_day_purchase_stays_open_and_accounts_costs(cfg):
    df = price_frame(1)
    result = run_backtest({"AAA": df}, lambda d, t, m: signal(t), lambda t: {"estado": "NEUTRO"}, cfg)
    assert len(result["posiciones_abiertas"]) == 1
    assert not result["trades"]
    assert result["resumen"]["capital_final"] < 5000
    assert result["resumen"]["capital_final"] == result["equity_curve"][-1]["equity"]


def test_backtest_lock_and_shared_volume_filter(cfg):
    df = price_frame(2)
    df.iloc[220, df.columns.get_loc("Low")] = 80
    result = run_backtest({"AAA": df}, lambda d, t, m: signal(t), lambda t: {"estado": "NEUTRO"}, cfg)
    assert all(t["fecha_entrada"] != t["fecha_cierre"] for t in result["trades"])
    assert not any(t.get("tipo_cierre", "").startswith("STOP") for t in result["trades"])
    def no_volume(d, t, m):
        s = signal(t); s["Volumen relativo"] = 0
        return s
    denied = run_backtest({"AAA": df}, no_volume, lambda t: {"estado": "NEUTRO"}, cfg)
    assert not denied["trades"] and not denied["posiciones_abiertas"]


def test_sortino_constant_negative_returns_is_defined():
    curve = [{"equity": 100 * .99 ** i} for i in range(10)]
    assert calcular_metricas_backtest(curve, [], 100)["sortino_ratio"] < 0


def test_early_close_valuation_does_not_sell(cfg):
    entry = when("2026-11-25T15:00:00+00:00")
    book = update({"operaciones": []}, [signal(now=entry)], {}, cfg, entry, {"AAA": quote(100, entry)})
    after = when("2026-11-27T18:05:00+00:00")
    last_bar = when("2026-11-27T17:59:00+00:00")
    result = update(book, [], {}, cfg, after, {"AAA": quote(90, last_bar)})
    assert result["operaciones"][0]["estado"] == "ABIERTA"
    assert result["operaciones"][0]["precio_actual"] == 90
    assert result["daily_equity"][-1]["session_final"] is True


def test_drawdown_uses_current_not_maximum_for_gate(cfg):
    book = opened(cfg)
    book["accounting"]["legacy_max_drawdown_pct"] = 90
    result = update(book, [signal("BBB")], {}, cfg, when(), {"AAA": quote(100), "BBB": quote(100)})
    assert len(result["operaciones"]) == 2
    assert result["resumen"]["riesgo"]["max_drawdown_pct"] == 90
    assert result["resumen"]["riesgo"]["drawdown_actual_pct"] < 1


def test_same_day_reentry_denied(cfg):
    now = when("2026-10-15T15:00:00+00:00")
    closed = update(opened(cfg), [], {}, cfg, now, {"AAA": quote(120, now)})
    again = update(closed, [signal(now=now)], {}, cfg, now, {"AAA": quote(100, now)})
    assert len(again["operaciones"]) == 1
    assert "Cooldown" in again["resumen"]["nuevas_bloqueadas"][0]["motivo"]


def test_net_costs_control_win_classification(cfg):
    now = when("2026-10-15T15:00:00+00:00")
    s = signal(now=now); s["Senal Bot"] = "SELL / EVITAR"
    book = update(opened(cfg), [s], {}, cfg, now, {"AAA": quote(100.1, now)})
    op = book["operaciones"][0]
    assert op["ganancia_pct_final"] > 0 and op["pnl_usd_estimado"] < 0
    assert book["resumen"]["ganadas"] == 0
    assert book["resumen"]["riesgo"]["racha_actual_tipo"] == "PERDIDAS"


def test_sector_cap_and_no_cash_rejected(cfg):
    assert position_size(5000, 0, 100, 95, cfg) is None
    assert position_size(5000, 1000, 100, 95, cfg, sector_exposure=1800) is None


def test_missing_market_cannot_bypass_with_strong_signal(cfg):
    cfg["permitir_buy_strong_en_mercado_debil"] = True
    s = signal(); s["Mercado"] = "SIN DATOS"; s["Senal Bot"] = "BUY STRONG"
    assert entry_filter(s, cfg) == "Mercado sin datos"


def test_end_to_end_snapshot_without_network(tmp_path, monkeypatch, cfg):
    from engine.policy import schedule
    from scripts.validate_snapshot import main as check_snapshot
    from engine import paper_trading_engine
    original = {"operaciones": [], "resumen": {}}
    atomic_json(tmp_path / "historial_senales.json", original)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(analyzer, "ACCIONES", ["AAA"])
    monkeypatch.setattr(analyzer, "DRIVERS_CONTEXTO", {"test": ["SPY", "QQQ"]})
    monkeypatch.setattr(analyzer, "download_batch", lambda tickers: {t: price_frame() for t in tickers})
    monkeypatch.setattr(analyzer, "execution_quotes", lambda tickers: {})
    monkeypatch.setattr(analyzer, "calcular_benchmark_desde_fecha", lambda *args: {})
    analyzer.main()
    check_snapshot()
    book = read_json("historial_senales.json")
    assert book["schema_version"] == 2
    assert len(list((tmp_path / "paper/legacy").glob("*.json"))) == 1
    analyzer.main()
    check_snapshot()
    assert len(list((tmp_path / "paper/legacy").glob("*.json"))) == 1

