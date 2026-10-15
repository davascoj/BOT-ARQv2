"""Strict configuration: invalid or missing production settings stop the run."""
from pathlib import Path
from copy import deepcopy
from engine.storage import read_json
from engine.policy import number

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config/system_config.json"


def _safe_read_json(path):
    return read_json(path)


def deep_merge(base, override):
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = deep_merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def cargar_config_sistema(path=DEFAULT_CONFIG_PATH):
    cfg = read_json(path)
    if not isinstance(cfg, dict) or not isinstance(cfg.get("simulation_config"), dict):
        raise ValueError("Falta simulation_config")
    if cfg.get("paper_trading", {}).get("real_broker_enabled") is not False:
        raise ValueError("Esta versión solo permite simulación, broker real deshabilitado")
    return cfg


def cargar_config_simulacion(default_config, system_config=None):
    cfg = dict(default_config)
    sim = (system_config or {}).get("simulation_config", {})
    allowed = set(default_config) | {"rr_neto_minimo", "max_exposicion_sector_pct", "min_posicion_usd", "max_quote_age_seconds"}
    if set(sim) - allowed:
        raise ValueError(f"Parámetros desconocidos: {set(sim) - allowed}")
    cfg.update(sim)
    cfg.setdefault("rr_neto_minimo", 1.0)
    cfg.setdefault("max_exposicion_sector_pct", 35.0)
    cfg.setdefault("min_posicion_usd", 10.0)
    cfg.setdefault("max_quote_age_seconds", 180)
    ints = {"max_operaciones_abiertas", "pausar_si_perdidas_seguidas", "bloquear_si_perdidas_seguidas", "max_dias_holding", "max_quote_age_seconds"}
    bools = {k for k, v in default_config.items() if isinstance(v, bool)}
    for key, value in cfg.items():
        if key in bools:
            if type(value) is not bool:
                raise ValueError(f"{key}: debe ser booleano")
            continue
        value = number(value)
        if value < 0 or (key in ints and (not value.is_integer() or value < 1)):
            raise ValueError(f"{key}: fuera de rango")
        if key.endswith("_pct") and value > 100:
            raise ValueError(f"{key}: porcentaje superior a 100")
        cfg[key] = int(value) if key in ints else value
    for key in ("capital_inicial", "riesgo_por_operacion_pct", "max_posicion_pct", "rr_minimo", "rr_neto_minimo", "max_exposicion_total_pct", "max_riesgo_total_abierto_pct", "min_posicion_usd"):
        if cfg[key] <= 0:
            raise ValueError(f"{key}: debe ser positivo")
    if cfg["modo_defensivo_drawdown_pct"] >= cfg["bloquear_entradas_drawdown_pct"]:
        raise ValueError("Drawdown defensivo debe ser menor al bloqueo")
    if cfg["pausar_si_perdidas_seguidas"] > cfg["bloquear_si_perdidas_seguidas"]:
        raise ValueError("Rachas de defensa/bloqueo inconsistentes")
    if cfg["max_quote_age_seconds"] > 900 or cfg["max_exposicion_sector_pct"] > cfg["max_exposicion_total_pct"]:
        raise ValueError("Límite de datos/sector inválido")
    if cfg["comision_por_operacion_pct"] + cfg["slippage_pct"] + cfg["spread_pct"] / 2 >= 10:
        raise ValueError("Costos por lado inválidos")
    return cfg


def resumen_config_operativa(system_config, config_simulacion):
    return {"version_config": system_config["version"], "mode": system_config["mode"],
            "source": "config/system_config.json", "simulation_config": config_simulacion,
            "paper_trading": system_config.get("paper_trading", {}), "automation": system_config.get("automation", {}),
            "dashboard": system_config.get("dashboard", {})}
