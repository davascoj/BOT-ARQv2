"""
BOT-ARQ V4.7 - Reconstrucción del contexto de mercado point-in-time.

Para cada fecha T del backtest, evalúa los drivers (SPY, QQQ, SOXX, XLE, ...)
con datos SOLO hasta T y arma el contexto con la MISMA lógica del live
(compute_driver + armar_contexto_mercado del motor). Así el backtest ve
exactamente el contexto de mercado que habría visto el live ese día, sin
look-ahead.
"""


def reconstruir_mercado_fn(precios_drivers, motor):
    """Devuelve mercado_fn(T) que reconstruye el contexto de mercado en la fecha T.

    precios_drivers: dict[ticker_driver -> DataFrame OHLCV con DatetimeIndex]
    motor          : módulo del motor live (expone compute_driver y armar_contexto_mercado)

    El resultado se cachea por fecha para no recalcular en cada ticker del mismo día.
    """
    cache = {}

    def mercado_fn(T):
        key = T
        if key in cache:
            return cache[key]
        drivers = {}
        for tk, df in precios_drivers.items():
            df_t = df.loc[:T]
            if len(df_t) >= 80:
                drivers[tk] = motor.compute_driver(df_t, tk)
        ctx = motor.armar_contexto_mercado(drivers)
        cache[key] = ctx
        return ctx

    return mercado_fn
