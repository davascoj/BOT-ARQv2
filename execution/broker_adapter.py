"""
BOT-ARQ v3 - Broker Adapter

Este archivo es un punto de preparación para conexión futura con broker real.
Por seguridad, NO ejecuta órdenes reales.

Flujo futuro:
1. El motor genera señal BUY / SELL.
2. El risk engine valida si se permite operar.
3. Este adaptador enviaría la orden al broker en modo paper trading.
4. Solo después de meses de validación se habilitaría dinero real.

Brokers posibles:
- Alpaca Paper Trading
- Interactive Brokers
- Tradier

Estado actual:
- Simulación solamente.
"""

class BrokerAdapter:
    def __init__(self, mode="paper"):
        self.mode = mode

    def buy(self, ticker, qty, limit_price=None):
        raise NotImplementedError("Trading real no habilitado. Usar primero paper trading.")

    def sell(self, ticker, qty, limit_price=None):
        raise NotImplementedError("Trading real no habilitado. Usar primero paper trading.")
