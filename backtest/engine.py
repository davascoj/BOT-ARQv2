"""
BOT-ARQ V4.7 - Backtest Engine (event-driven).

Recorre el histórico día a día. En cada día T:
  1. Ejecuta en la APERTURA de T las órdenes decididas el día anterior (T-1).
  2. Evalúa stops/objetivos de las posiciones abiertas con el rango (high/low) de T.
  3. Decide nuevas entradas con el CIERRE de T (sin look-ahead) -> se ejecutan en T+1.
  4. Registra la equity (caja + valor de mercado de las posiciones) al cierre de T.

Sin look-ahead: la decisión usa solo datos hasta T inclusive; la ejecución
ocurre en la apertura de T+1. Caja real (V4.5): cada compra descuenta efectivo,
cada venta lo devuelve. Costos reales (comisión + slippage + spread) en ambos
lados, tomados de config/system_config.json.
"""


def _pct(x):
    return (x or 0) / 100.0


def dimensionar_posicion(capital, caja_disponible, entrada, stop, config):
    """Mismo criterio que el motor live (calcular_posicion):
    riesgo fijo % del capital, con tope por max_posicion_pct y por la caja
    disponible (V4.5). Devuelve None si no se puede dimensionar."""
    entrada = float(entrada or 0)
    stop = float(stop or 0)
    if entrada <= 0 or stop <= 0 or stop >= entrada:
        return None
    riesgo_usd = capital * _pct(config.get("riesgo_por_operacion_pct", 1.0))
    dist_stop = (entrada - stop) / entrada
    posicion_usd = riesgo_usd / dist_stop
    tope_posicion = capital * _pct(config.get("max_posicion_pct", 20.0))
    posicion_usd = min(posicion_usd, tope_posicion, caja_disponible)
    if posicion_usd <= 0:
        return None
    cantidad = posicion_usd / entrada
    return {
        "posicion_usd": posicion_usd,
        "cantidad": cantidad,
        "riesgo_usd": cantidad * (entrada - stop),
    }


def precio_compra_efectivo(precio, config):
    """Compra: paga slippage + medio spread por encima."""
    return precio * (1 + _pct(config.get("slippage_pct", 0)) + _pct(config.get("spread_pct", 0)) / 2)


def precio_venta_efectivo(precio, config):
    """Venta: recibe slippage + medio spread por debajo."""
    return precio * (1 - _pct(config.get("slippage_pct", 0)) - _pct(config.get("spread_pct", 0)) / 2)


def comision(monto, config):
    return abs(monto) * _pct(config.get("comision_por_operacion_pct", 0))


def _fila(df, fecha):
    """Devuelve la fila (Open/High/Low/Close) de un df en una fecha, o None."""
    try:
        if fecha in df.index:
            r = df.loc[fecha]
            return {
                "open": float(r["Open"]),
                "high": float(r["High"]),
                "low": float(r["Low"]),
                "close": float(r["Close"]),
            }
    except Exception:
        return None
    return None


def run_backtest(precios, signal_fn, mercado_fn, config, sectores=None, log=None):
    """
    precios   : dict[ticker -> DataFrame con DatetimeIndex y columnas Open/High/Low/Close/Volume]
    signal_fn : (df_hasta_T_inclusive, ticker, mercado) -> dict señal | None  (compute_signal)
    mercado_fn: (fecha_T) -> dict contexto de mercado en T
    config    : simulation_config (capital, costos, riesgo, topes)
    sectores  : dict[ticker -> sector] opcional, para desglose por sector
    Devuelve  : dict con trades[], equity_curve[], posiciones_abiertas[], resumen{}
    """
    sectores = sectores or {}
    capital_inicial = float(config.get("capital_inicial", 5000))
    max_pos = int(config.get("max_operaciones_abiertas", 20))
    max_exp_pct = float(config.get("max_exposicion_total_pct", 80))
    rr_min = float(config.get("rr_minimo", 1.5))

    # Calendario de trading: unión ordenada de todas las fechas
    fechas = sorted(set().union(*[set(df.index) for df in precios.values()])) if precios else []

    caja = capital_inicial
    posiciones = {}        # ticker -> dict posición abierta
    pendientes = []        # órdenes decididas en T-1, a ejecutar en la apertura de T
    trades = []
    equity_curve = []

    def equity_actual(fecha):
        valor_pos = 0.0
        for tk, p in posiciones.items():
            fila = _fila(precios[tk], fecha)
            ref = fila["close"] if fila else p["entrada_precio"]
            valor_pos += p["cantidad"] * ref
        return caja + valor_pos

    for i, T in enumerate(fechas):
        mercado = mercado_fn(T) if mercado_fn else {}

        # --- 1. Ejecutar órdenes pendientes en la APERTURA de T ---
        nuevas_pendientes = []
        for orden in pendientes:
            tk = orden["ticker"]
            if tk in posiciones:
                continue  # ya abierta
            fila = _fila(precios.get(tk), T)
            if not fila:
                continue  # sin datos ese día -> se descarta la orden
            entrada_exec = precio_compra_efectivo(fila["open"], config)
            stop = orden["stop"]
            objetivo = orden["objetivo"]
            if stop >= entrada_exec:
                continue
            capital_actual = equity_actual(T)
            exposicion_actual = sum(p["posicion_usd"] for p in posiciones.values())
            if exposicion_actual >= capital_inicial * _pct(max_exp_pct):
                continue
            if len(posiciones) >= max_pos:
                continue
            dim = dimensionar_posicion(capital_actual, caja, entrada_exec, stop, config)
            if not dim:
                continue
            costo_in = comision(dim["posicion_usd"], config)
            if dim["posicion_usd"] + costo_in > caja:
                continue
            caja -= dim["posicion_usd"] + costo_in
            posiciones[tk] = {
                "ticker": tk,
                "sector": sectores.get(tk, "Otro"),
                "entrada_fecha": T,
                "entrada_precio": entrada_exec,
                "cantidad": dim["cantidad"],
                "posicion_usd": dim["posicion_usd"],
                "stop": stop,
                "objetivo": objetivo,
                "riesgo_usd": dim["riesgo_usd"],
                "costo_entrada": costo_in,
                "senal_entrada": orden["senal"],
            }
        pendientes = nuevas_pendientes

        # --- 2. Evaluar stops/objetivos con el rango de T ---
        for tk in list(posiciones.keys()):
            p = posiciones[tk]
            if p["entrada_fecha"] == T:
                continue  # no evaluar el mismo día que se abrió
            fila = _fila(precios.get(tk), T)
            if not fila:
                continue
            salida_precio = None
            tipo = None
            # Conservador: si abre cruzando el nivel, ejecuta a la apertura.
            if fila["open"] <= p["stop"]:
                salida_precio, tipo = fila["open"], "STOP_GAP"
            elif fila["open"] >= p["objetivo"]:
                salida_precio, tipo = fila["open"], "OBJETIVO_GAP"
            elif fila["low"] <= p["stop"]:
                salida_precio, tipo = p["stop"], "STOP"
            elif fila["high"] >= p["objetivo"]:
                salida_precio, tipo = p["objetivo"], "OBJETIVO"
            if salida_precio is not None:
                _cerrar(p, T, salida_precio, tipo, config, trades)
                caja += p["_neto_salida"]
                del posiciones[tk]

        # --- 3. Decidir nuevas entradas con el CIERRE de T (ejecución en T+1) ---
        ya_pedidos = {o["ticker"] for o in pendientes}
        for tk, df in precios.items():
            if tk in posiciones or tk in ya_pedidos:
                continue
            df_t = df.loc[:T]
            if len(df_t) < 220:
                continue
            try:
                señal = signal_fn(df_t, tk, mercado)
            except Exception:
                señal = None
            if not señal:
                continue
            bot = señal.get("Senal Bot", "")
            if bot not in ("BUY", "BUY STRONG"):
                continue
            entrada_ref = float(señal.get("Precio actual") or df_t["Close"].iloc[-1])
            stop = float(señal.get("Stop loss") or 0)
            objetivo = float(señal.get("Objetivo") or 0)
            rr = float(señal.get("R/R") or 0)
            if stop <= 0 or objetivo <= 0 or stop >= entrada_ref or rr < rr_min:
                continue
            pendientes.append({
                "ticker": tk, "stop": stop, "objetivo": objetivo, "senal": bot,
            })

        # --- 4. Registrar equity al cierre de T ---
        eq = equity_actual(T)
        equity_curve.append({
            "fecha": T.strftime("%Y-%m-%d") if hasattr(T, "strftime") else str(T),
            "equity": round(eq, 2),
            "caja": round(caja, 2),
            "posiciones_abiertas": len(posiciones),
        })

    # Cierre forzado de posiciones abiertas al final (al último cierre disponible)
    if fechas:
        T_fin = fechas[-1]
        for tk in list(posiciones.keys()):
            p = posiciones[tk]
            fila = _fila(precios.get(tk), T_fin)
            ref = fila["close"] if fila else p["entrada_precio"]
            _cerrar(p, T_fin, ref, "FIN_BACKTEST", config, trades)
            caja += p["_neto_salida"]
            del posiciones[tk]

    resumen = _resumen(capital_inicial, caja, trades, equity_curve)
    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "resumen": resumen,
        "config_usada": dict(config),
    }


def _cerrar(p, fecha, salida_precio, tipo, config, trades):
    """Cierra una posición, calcula PnL neto de costos y lo anexa a trades.
    Guarda en p['_neto_salida'] el efectivo que vuelve a caja."""
    salida_exec = precio_venta_efectivo(salida_precio, config)
    valor_salida = p["cantidad"] * salida_exec
    costo_out = comision(valor_salida, config)
    neto_salida = valor_salida - costo_out
    pnl_usd = neto_salida - p["posicion_usd"] - p["costo_entrada"]
    pnl_pct = (pnl_usd / p["posicion_usd"] * 100) if p["posicion_usd"] else 0
    dias = (fecha - p["entrada_fecha"]).days if hasattr(fecha, "__sub__") else 0
    p["_neto_salida"] = neto_salida
    trades.append({
        "ticker": p["ticker"],
        "sector": p["sector"],
        "fecha_entrada": p["entrada_fecha"].strftime("%Y-%m-%d") if hasattr(p["entrada_fecha"], "strftime") else str(p["entrada_fecha"]),
        "fecha_cierre": fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha),
        "entrada_precio": round(p["entrada_precio"], 4),
        "salida_precio": round(salida_exec, 4),
        "cantidad": round(p["cantidad"], 6),
        "posicion_usd_estimada": round(p["posicion_usd"], 2),
        "pnl_usd_estimado": round(pnl_usd, 2),
        "ganancia_pct_neta_estimada": round(pnl_pct, 2),
        "ganancia_pct_final": round(pnl_pct, 2),
        "costo_usd_estimado": round(p["costo_entrada"] + costo_out, 2),
        "dias_abierta": max(dias, 0),
        "tipo_cierre": tipo,
        "resultado": "GANADA" if pnl_usd > 0 else "PERDIDA",
        "senal_bot_entrada": p["senal_entrada"],
    })


def _resumen(capital_inicial, caja_final, trades, equity_curve):
    equity_fin = equity_curve[-1]["equity"] if equity_curve else capital_inicial
    ganadas = [t for t in trades if t["pnl_usd_estimado"] > 0]
    perdidas = [t for t in trades if t["pnl_usd_estimado"] <= 0]
    return {
        "capital_inicial": round(capital_inicial, 2),
        "capital_final": round(equity_fin, 2),
        "retorno_total_pct": round((equity_fin / capital_inicial - 1) * 100, 2) if capital_inicial else 0,
        "trades_total": len(trades),
        "trades_ganados": len(ganadas),
        "trades_perdidos": len(perdidas),
        "win_rate_pct": round(len(ganadas) / len(trades) * 100, 2) if trades else 0,
        "dias_simulados": len(equity_curve),
    }
