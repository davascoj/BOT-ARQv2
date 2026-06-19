"""
BOT-ARQ V4.2 - Config Loader

Carga la configuración real del motor desde config/system_config.json.

Objetivo:
- Mantener valores por defecto seguros.
- Permitir modificar parámetros del bot sin editar analizador_acciones.py.
- No romper el sistema si el JSON no existe o está mal escrito.
"""

from pathlib import Path
import json
import copy

DEFAULT_CONFIG_PATH = Path("config/system_config.json")


def _safe_read_json(path):
    try:
        path = Path(path)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def deep_merge(base, override):
    result = copy.deepcopy(base)
    if not isinstance(override, dict):
        return result

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def cargar_config_sistema(path=DEFAULT_CONFIG_PATH):
    cfg = _safe_read_json(path)
    if not isinstance(cfg, dict):
        return {}
    return cfg


def cargar_config_simulacion(default_config, system_config=None):
    """
    Devuelve la configuración plana que ya usa el motor actual:
    CONFIG_SIMULACION.

    Prioridad:
    1. Valores por defecto definidos en analizador_acciones.py.
    2. config/system_config.json -> simulation_config.
    3. Compatibilidad con formatos anteriores si existen.
    """

    result = dict(default_config or {})
    system_config = system_config if isinstance(system_config, dict) else {}

    # Formato V4.2 recomendado
    sim = system_config.get("simulation_config", {})
    if isinstance(sim, dict):
        for key, value in sim.items():
            if key in result:
                result[key] = value

    # Compatibilidad con posibles formatos previos o alternos
    aliases = {
        "capital_inicial": ["capital_inicial", "capital"],
        "riesgo_por_operacion_pct": ["riesgo_por_operacion_pct", "risk_per_trade_pct", "riesgo_por_operacion"],
        "max_posicion_pct": ["max_posicion_pct", "max_position_pct"],
        "max_operaciones_abiertas": ["max_operaciones_abiertas", "max_open_positions"],
        "max_exposicion_total_pct": ["max_exposicion_total_pct", "max_total_exposure_pct"],
        "comision_por_operacion_pct": ["comision_por_operacion_pct", "commission_pct"],
        "slippage_pct": ["slippage_pct"],
        "spread_pct": ["spread_pct"],
        "pausar_si_perdidas_seguidas": ["pausar_si_perdidas_seguidas", "pause_after_consecutive_losses"],
        "bloquear_si_perdidas_seguidas": ["bloquear_si_perdidas_seguidas", "block_after_consecutive_losses"],
        "rr_minimo": ["rr_minimo", "min_rr"],
        "volumen_relativo_minimo": ["volumen_relativo_minimo", "min_relative_volume"],
        "permitir_buy_strong_en_mercado_debil": ["permitir_buy_strong_en_mercado_debil", "allow_buy_strong_weak_market"],
        "max_riesgo_total_abierto_pct": ["max_riesgo_total_abierto_pct", "max_total_open_risk_pct"],
        "modo_defensivo_drawdown_pct": ["modo_defensivo_drawdown_pct", "defensive_drawdown_pct"],
        "bloquear_entradas_drawdown_pct": ["bloquear_entradas_drawdown_pct", "block_entries_drawdown_pct"],
        "activar_reglas_operativas": ["activar_reglas_operativas", "enable_operational_rules"],
        "usar_exposicion_como_bloqueo": ["usar_exposicion_como_bloqueo", "use_exposure_as_block"],
        "usar_riesgo_abierto_como_bloqueo": ["usar_riesgo_abierto_como_bloqueo", "use_open_risk_as_block"],
        "usar_drawdown_como_bloqueo": ["usar_drawdown_como_bloqueo", "use_drawdown_as_block"],
        "permitir_buy_strong_en_modo_defensivo_drawdown": ["permitir_buy_strong_en_modo_defensivo_drawdown", "allow_buy_strong_defensive_drawdown"],
        "permitir_buy_strong_sobre_exposicion": ["permitir_buy_strong_sobre_exposicion", "allow_buy_strong_over_exposure"],
        "permitir_buy_strong_sobre_riesgo": ["permitir_buy_strong_sobre_riesgo", "allow_buy_strong_over_risk"],
    }

    # Revisa top-level y secciones conocidas.
    sections = [
        system_config,
        system_config.get("simulation", {}),
        system_config.get("risk_controls", {}),
        system_config.get("position_sizing", {}),
        system_config.get("costs", {}),
        system_config.get("entry_filters", {}),
    ]

    for target_key, possible_keys in aliases.items():
        for section in sections:
            if not isinstance(section, dict):
                continue
            for key in possible_keys:
                if key in section and section[key] not in (None, ""):
                    result[target_key] = section[key]

    # Normalización simple de tipos para evitar errores por texto.
    int_keys = {"max_operaciones_abiertas", "pausar_si_perdidas_seguidas", "bloquear_si_perdidas_seguidas"}
    bool_keys = {
        "permitir_buy_strong_en_mercado_debil",
        "activar_reglas_operativas",
        "usar_exposicion_como_bloqueo",
        "usar_riesgo_abierto_como_bloqueo",
        "usar_drawdown_como_bloqueo",
        "permitir_buy_strong_en_modo_defensivo_drawdown",
        "permitir_buy_strong_sobre_exposicion",
        "permitir_buy_strong_sobre_riesgo",
    }

    for key in list(result.keys()):
        if key in bool_keys:
            if isinstance(result[key], str):
                result[key] = result[key].strip().lower() in ("true", "1", "si", "sí", "yes")
        elif key in int_keys:
            try:
                result[key] = int(result[key])
            except Exception:
                result[key] = int(default_config.get(key, 0))
        else:
            try:
                result[key] = float(result[key])
            except Exception:
                result[key] = default_config.get(key)

    return result


def resumen_config_operativa(system_config, config_simulacion):
    return {
        "version_config": str(system_config.get("version", "default")),
        "mode": system_config.get("mode", "PAPER_TRADING_SIMULATED"),
        "source": str(DEFAULT_CONFIG_PATH),
        "simulation_config": config_simulacion,
        "paper_trading": system_config.get("paper_trading", {}),
        "automation": system_config.get("automation", {}),
    }
