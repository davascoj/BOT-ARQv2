import json
import os
import time
import math
from pathlib import Path
from datetime import timezone
from engine.storage import read_json, atomic_json
from engine.policy import VERSION, number, position_size
from engine.ledger import update as update_ledger, validate as validate_ledger, migrate, summarize, config_hash
from engine.market_data import download_batch, execution_quotes
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

ZONA_HORARIA = ZoneInfo("America/Bogota")
HISTORIAL_FILE = "historial_senales.json"
HISTORIAL_XLSX = "historial_senales.xlsx"

# Reportes Excel: OFF por defecto para no versionar binarios pesados en CI/GitHub.
# Los datos viven en los JSON. Para generarlos localmente: BOT_ARQ_EXPORT_XLSX=1
EXPORT_XLSX = os.getenv("BOT_ARQ_EXPORT_XLSX", "0").strip().lower() in ("1", "true", "yes", "on")

# ============================================================
# BOT-ARQ V4 - PAPER TRADING ENGINE
# Exporta el estado del paper trading a archivos JSON separados,
# sin ejecutar órdenes reales ni romper la simulación existente.
# ============================================================
from engine.paper_trading_engine import export_paper_state
from engine.config_loader import cargar_config_sistema, cargar_config_simulacion, resumen_config_operativa
DAILY_DATA = {}



ACCIONES_INFO = {
    # Tecnología, IA y software
    "NVDA": "IA / Chips", "AMD": "IA / Chips", "MSFT": "Tecnología",
    "AVGO": "IA / Chips", "AAPL": "Tecnología", "META": "Tecnología",
    "AMZN": "Tecnología", "GOOGL": "Tecnología", "TSLA": "Autos / Tech",
    "ORCL": "Tecnología", "CRM": "Tecnología", "NOW": "Tecnología",
    "SNOW": "Tecnología", "DDOG": "Tecnología", "NET": "Tecnología",
    "APP": "Tecnología", "UBER": "Tecnología", "NFLX": "Tecnología",
    "ADBE": "Tecnología", "SHOP": "Tecnología", "RDDT": "Tecnología",
    "IBM": "Tecnología", "ACN": "Tecnología", "INTU": "Tecnología",
    "TEAM": "Tecnología", "HUBS": "Tecnología", "TTD": "Tecnología",
    "DELL": "Tecnología",

    # IA, datos, ciberseguridad y crecimiento
    "PLTR": "IA / Software", "SMCI": "Servidores IA", "SOUN": "IA",
    "AI": "IA", "UPST": "Fintech IA", "CRWD": "Ciberseguridad",
    "PANW": "Ciberseguridad", "ZS": "Ciberseguridad", "FTNT": "Ciberseguridad",
    "OKTA": "Ciberseguridad", "CHKP": "Ciberseguridad", "MDB": "Datos / Software",
    "ANET": "Redes / IA",

    # Semiconductores y equipos de chips
    "MU": "Memoria / Chips", "ARM": "Chips", "QCOM": "Chips", "INTC": "Chips",
    "TSM": "Chips", "ASML": "Chips", "AMAT": "Equipos chips",
    "LRCX": "Equipos chips", "KLAC": "Equipos chips", "MRVL": "Chips",
    "ON": "Chips", "NXPI": "Chips", "MPWR": "Chips", "TXN": "Chips",
    "ADI": "Chips", "MCHP": "Chips",

    # Finanzas, pagos, trading y cripto relacionadas
    "SOFI": "Fintech", "COIN": "Cripto / Trading", "HOOD": "Trading",
    "PYPL": "Pagos", "XYZ": "Pagos", "V": "Pagos", "MA": "Pagos",
    "JPM": "Finanzas", "GS": "Finanzas", "BAC": "Finanzas", "MS": "Finanzas",
    "C": "Finanzas", "WFC": "Finanzas", "BLK": "Finanzas", "SCHW": "Finanzas",
    "IBKR": "Trading", "MSTR": "Cripto / Trading", "MARA": "Cripto / Trading",
    "RIOT": "Cripto / Trading",

    # Energía e industrial
    "XOM": "Energía", "CVX": "Energía", "OXY": "Energía", "SLB": "Energía",
    "COP": "Energía", "LNG": "Energía", "EOG": "Energía", "FANG": "Energía",
    "DVN": "Energía", "HAL": "Energía", "GE": "Industrial", "CAT": "Industrial",
    "BA": "Industrial", "DE": "Industrial",

    # Salud y consumo defensivo
    "LLY": "Salud", "NVO": "Salud", "UNH": "Salud", "ABBV": "Salud",
    "JNJ": "Salud", "PFE": "Salud", "MRK": "Salud", "TMO": "Salud",
    "ABT": "Salud", "COST": "Consumo", "WMT": "Consumo", "MCD": "Consumo",
    "HD": "Consumo", "LOW": "Consumo", "SBUX": "Consumo",

    # ETFs y mercado general
    "SPY": "ETF Mercado", "QQQ": "ETF Nasdaq", "VOO": "ETF Mercado",
    "SOXX": "ETF Chips", "SMH": "ETF Chips", "XLK": "ETF Tecnología",
    "VGT": "ETF Tecnología", "IWM": "ETF Russell", "DIA": "ETF Dow",
    "XLE": "ETF Energía", "XLF": "ETF Finanzas", "XLV": "ETF Salud",
    "ARKK": "ETF Innovación",

    # Temáticas de alta volatilidad / innovación
    "RKLB": "Espacial", "IONQ": "Computación cuántica", "QBTS": "Computación cuántica",
    "RGTI": "Computación cuántica", "JOBY": "Movilidad aérea", "ACHR": "Movilidad aérea",

    # Ampliación ARQ - más acciones para analizar
    # Tecnología / nube / software
    "CSCO": "Tecnología", "HPE": "Tecnología", "HPQ": "Tecnología",
    "FSLY": "Tecnología", "TWLO": "Tecnología",
    "DOCU": "Tecnología", "ZM": "Tecnología", "PATH": "IA / Software",
    "U": "Software", "ESTC": "Datos / Software", "DT": "Software",
    "GTLB": "Software", "S": "Ciberseguridad", "TENB": "Ciberseguridad",
    "CYBR": "Ciberseguridad", "GEN": "Ciberseguridad",

    # Chips, data centers y hardware IA
    "VRT": "Data Center / IA", "COHR": "Fotónica / IA", "LITE": "Fotónica / IA",
    "CIEN": "Redes / IA", "WDC": "Almacenamiento", "STX": "Almacenamiento",
    "SNDK": "Almacenamiento", "GFS": "Chips", "TER": "Equipos chips",
    "ENTG": "Equipos chips", "WOLF": "Chips", "ALAB": "Data Center / IA",

    # IA especulativa, robótica y automatización
    "BBAI": "IA", "SERV": "Robótica", "SYM": "Robótica",
    "ISRG": "Robótica / Salud", "ROK": "Automatización", "ABBNY": "Automatización",

    # Autos eléctricos, movilidad y baterías
    "RIVN": "Autos eléctricos", "LCID": "Autos eléctricos", "NIO": "Autos eléctricos",
    "LI": "Autos eléctricos", "XPEV": "Autos eléctricos", "BYDDY": "Autos eléctricos",
    "GM": "Autos", "F": "Autos", "TM": "Autos", "HMC": "Autos",
    "QS": "Baterías", "ENVX": "Baterías", "ALB": "Litio", "LAC": "Litio",

    # Fintech, bancos, seguros y mercados
    "AXP": "Pagos", "FI": "Pagos", "FIS": "Pagos", "GPN": "Pagos",
    "NU": "Fintech", "AFRM": "Fintech", "TOST": "Fintech", "BILL": "Fintech",
    "KKR": "Finanzas", "ARES": "Finanzas", "BX": "Finanzas", "APO": "Finanzas",
    "CME": "Trading", "ICE": "Trading", "SPGI": "Finanzas", "MCO": "Finanzas",
    "AFL": "Seguros", "TRV": "Seguros", "PGR": "Seguros",

    # Energía tradicional y renovables
    "VLO": "Energía", "MPC": "Energía", "PSX": "Energía", "KMI": "Energía",
    "WMB": "Energía", "OKE": "Energía", "BKR": "Energía", "RIG": "Energía",
    "NEE": "Energía renovable", "ENPH": "Energía renovable", "SEDG": "Energía renovable",
    "FSLR": "Energía renovable", "RUN": "Energía renovable", "BE": "Energía renovable",

    # Salud, biotecnología y farmacéuticas
    "VRTX": "Salud", "REGN": "Salud", "AMGN": "Salud", "GILD": "Salud",
    "SYK": "Salud", "MDT": "Salud", "BSX": "Salud",
    "DHR": "Salud", "ZTS": "Salud", "HIMS": "Salud", "TDOC": "Salud",
    "VEEV": "Salud / Software", "ALNY": "Biotecnología", "MRNA": "Biotecnología",

    # Consumo, retail, viajes y entretenimiento
    "DIS": "Entretenimiento", "ROKU": "Entretenimiento", "SPOT": "Entretenimiento",
    "ABNB": "Viajes", "BKNG": "Viajes", "EXPE": "Viajes", "DAL": "Aerolíneas",
    "UAL": "Aerolíneas", "AAL": "Aerolíneas", "CCL": "Cruceros", "RCL": "Cruceros",
    "NKE": "Consumo", "LULU": "Consumo", "TGT": "Consumo", "TJX": "Consumo",
    "CMG": "Consumo", "YUM": "Consumo", "PEP": "Consumo", "KO": "Consumo",
    "PG": "Consumo defensivo", "PM": "Consumo defensivo",

    # Industrial, defensa, infraestructura y construcción
    "LMT": "Defensa", "RTX": "Defensa", "NOC": "Defensa", "GD": "Defensa",
    "HON": "Industrial", "ETN": "Industrial", "PH": "Industrial", "EMR": "Industrial",
    "FIX": "Construcción", "URI": "Construcción", "BLDR": "Construcción", "VMC": "Materiales",
    "MLM": "Materiales", "CRH": "Materiales", "NEM": "Oro", "FCX": "Minería",

    # ETFs adicionales para ver mercado / sectores
    "XLU": "ETF Utilities", "XLI": "ETF Industrial", "XLY": "ETF Consumo",
    "XLP": "ETF Consumo defensivo", "XLC": "ETF Comunicaciones", "XLRE": "ETF Real Estate",
    "XLB": "ETF Materiales", "IBB": "ETF Biotech", "XBI": "ETF Biotech",
    "BOTZ": "ETF Robótica", "ROBO": "ETF Robótica", "CIBR": "ETF Ciberseguridad",
    "HACK": "ETF Ciberseguridad", "TAN": "ETF Solar", "ICLN": "ETF Energía limpia",
    "URA": "ETF Uranio", "GLD": "ETF Oro", "SLV": "ETF Plata", "TLT": "ETF Bonos",
    "HYG": "ETF Bonos", "VTI": "ETF Mercado", "SCHD": "ETF Dividendos"

}

ACCIONES = list(ACCIONES_INFO.keys())

# ============================================================
# CONFIGURACIÓN PROFESIONAL DE SIMULACIÓN / RIESGO
# Ajusta estos valores si quieres volver el sistema más conservador o agresivo.
# El bot sigue siendo PAPER TRADING: no ejecuta compras reales.
# ============================================================
DEFAULT_CONFIG_SIMULACION = {
    "capital_inicial": 5000.0,
    "riesgo_por_operacion_pct": 1.0,      # Riesgo máximo de cuenta por operación.
    "max_posicion_pct": 20.0,             # No usar más de este % del capital en una sola operación.
    "max_operaciones_abiertas": 20,
    "max_exposicion_total_pct": 80.0,
    "comision_por_operacion_pct": 0.05,   # Entrada y salida.
    "slippage_pct": 0.05,                 # Entrada y salida.
    "spread_pct": 0.03,                   # Costo estimado total por spread.
    "pausar_si_perdidas_seguidas": 8,
    "bloquear_si_perdidas_seguidas": 12,
    "rr_minimo": 1.50,
    "volumen_relativo_minimo": 0.80,
    "permitir_buy_strong_en_mercado_debil": False,

    # V4.4 - Reglas operativas reales usando métricas existentes.
    "max_riesgo_total_abierto_pct": 10.0,
    "modo_defensivo_drawdown_pct": 12.0,
    "bloquear_entradas_drawdown_pct": 25.0,
    "activar_reglas_operativas": True,
    "usar_exposicion_como_bloqueo": True,
    "usar_riesgo_abierto_como_bloqueo": True,
    "usar_drawdown_como_bloqueo": True,
    "permitir_buy_strong_en_modo_defensivo_drawdown": True,
    "permitir_buy_strong_sobre_exposicion": False,
    "permitir_buy_strong_sobre_riesgo": False,
    "max_dias_holding": 99,  # V4.9: forzar cierre en N días si hay ganancia; 99 = desactivado
}

CONFIG_SISTEMA = cargar_config_sistema()
CONFIG_SIMULACION = cargar_config_simulacion(DEFAULT_CONFIG_SIMULACION, CONFIG_SISTEMA)



# Contexto externo por tipo de acción.
# Estos tickers no necesariamente se muestran en tabla; son drivers para confirmar si el sector acompaña.
DRIVERS_CONTEXTO = {
    "chips": ["SOXX", "QQQ"],
    "energia": ["XLE", "CL=F"],
    "cripto": ["BTC-USD", "ETH-USD"],
    "tech_ia": ["QQQ", "ARKK", "SPY"],
}


def numero(valor):
    try:
        return number(valor.iloc[0] if hasattr(valor, "iloc") else valor)
    except (ValueError, TypeError, IndexError):
        return None

def hoy_ymd():
    return datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d")


def fecha_visible():
    return datetime.now(ZONA_HORARIA).strftime("%d-%m-%Y %I:%M %p Colombia")


def limpiar_df(df):
    if df is None or df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


def descargar(ticker, periodo="1y"):
    if ticker in DAILY_DATA and periodo == "1y":
        return DAILY_DATA[ticker]
    df = yf.download(ticker, period=periodo, interval="1d", auto_adjust=True,
                     progress=False, threads=False, timeout=15)
    return limpiar_df(df)

def rsi_real(close, periodo=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(periodo).mean()
    loss = (-delta.clip(upper=0)).rolling(periodo).mean()
    result = 100 - 100 / (1 + gain / loss.replace(0, float("nan")))
    result = result.mask((loss == 0) & (gain > 0), 100)
    return result.mask((loss == 0) & (gain == 0), 50)

def calcular_atr(high, low, close, periodo=14):
    cierre_anterior = close.shift(1)
    tr1 = high - low
    tr2 = (high - cierre_anterior).abs()
    tr3 = (low - cierre_anterior).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(periodo).mean()


def cambio_pct(close, dias):
    if len(close) <= dias:
        return 0
    actual = numero(close.iloc[-1])
    anterior = numero(close.iloc[-(dias + 1)])
    if not actual or not anterior:
        return 0
    return ((actual / anterior) - 1) * 100


def unir_unicos(items, limite=5):
    vistos = []
    for item in items:
        if not item:
            continue
        texto = str(item).strip()
        if texto and texto not in vistos:
            vistos.append(texto)
    return "; ".join(vistos[:limite])


def evaluar_driver(ticker):
    """Live: descarga datos y delega en compute_driver() (lógica pura compartida con el backtest)."""
    try:
        df = descargar(ticker, "1y")
    except Exception as e:
        print(f"ERROR driver {ticker}: {e}")
        return {"ticker": ticker, "estado": "SIN DATOS", "score": 0, "mom20": 0, "mom5": 0}
    return compute_driver(df, ticker)


def compute_driver(df, ticker):
    """V4.7: evaluación pura de un driver (ETF/índice) sobre un DataFrame point-in-time.
    La comparten el live (evaluar_driver) y el backtest (reconstrucción del mercado),
    para que el contexto de mercado del backtest use EXACTAMENTE la misma lógica."""
    try:
        if df is None or df.empty or len(df) < 80:
            return {"ticker": ticker, "estado": "SIN DATOS", "score": 0, "mom20": 0, "mom5": 0}

        close = df["Close"]
        precio = numero(close.iloc[-1])
        ma20 = numero(close.rolling(20).mean().iloc[-1])
        ma50 = numero(close.rolling(50).mean().iloc[-1])
        mom5 = cambio_pct(close, 5)
        mom20 = cambio_pct(close, 20)

        pts = 0
        if precio and ma20 and precio > ma20:
            pts += 1
        if ma20 and ma50 and ma20 > ma50:
            pts += 1
        if mom5 > 0:
            pts += 1
        if mom20 > 0:
            pts += 1

        if pts >= 4:
            estado = "FUERTE"
            score = 6
        elif pts == 3:
            estado = "POSITIVO"
            score = 3
        elif pts == 2:
            estado = "NEUTRO"
            score = 0
        else:
            estado = "DÉBIL"
            score = -6

        return {
            "ticker": ticker,
            "estado": estado,
            "score": score,
            "mom20": round(mom20, 2),
            "mom5": round(mom5, 2),
        }

    except Exception as e:
        print(f"ERROR driver {ticker}: {e}")
        return {"ticker": ticker, "estado": "SIN DATOS", "score": 0, "mom20": 0, "mom5": 0}


def contexto_mercado():
    """Live: evalúa los drivers (con descarga) y delega el armado en armar_contexto_mercado()."""
    drivers = {}
    try:
        tickers_unicos = sorted({t for lista in DRIVERS_CONTEXTO.values() for t in lista})
        for ticker in tickers_unicos:
            drivers[ticker] = evaluar_driver(ticker)
            time.sleep(0.2)
    except Exception as e:
        print(f"ERROR evaluando drivers: {e}")
    return armar_contexto_mercado(drivers)


def armar_contexto_mercado(drivers):
    """V4.7: arma el contexto de mercado (estado general + sectores) desde un dict de
    drivers ya evaluados. Pura: la comparten el live (contexto_mercado) y el backtest
    (reconstrucción point-in-time), garantizando el mismo contexto que ve el live."""
    try:
        spy = drivers.get("SPY", {"score": 0, "mom20": 0, "estado": "NEUTRO"})
        qqq = drivers.get("QQQ", {"score": 0, "mom20": 0, "estado": "NEUTRO"})
        total_base = spy.get("score", 0) + qqq.get("score", 0)

        if total_base >= 9:
            estado = "ALCISTA"
            score = 8
        elif total_base >= 3:
            estado = "NEUTRO +"
            score = 4
        elif total_base > -6:
            estado = "NEUTRO"
            score = 0
        else:
            estado = "DÉBIL"
            score = -8

        def crear_contexto(nombre, tickers):
            datos = [
                drivers[t]
                for t in tickers
                if t in drivers and drivers[t].get("estado") != "SIN DATOS"
            ]

            if not datos:
                return {
                    "estado": "SIN DATOS",
                    "score": 0,
                    "detalle": "",
                    "drivers": tickers,
                }

            score_prom = sum(d.get("score", 0) for d in datos) / len(datos)
            mom_prom = sum(d.get("mom20", 0) for d in datos) / len(datos)

            if score_prom >= 4:
                estado_ctx = "ACOMPAÑA"
                ajuste = 7
            elif score_prom >= 1:
                estado_ctx = "NEUTRO +"
                ajuste = 3
            elif score_prom > -3:
                estado_ctx = "NEUTRO"
                ajuste = 0
            else:
                estado_ctx = "NO ACOMPAÑA"
                ajuste = -8

            detalle = " · ".join([f"{d['ticker']} {d['mom20']}%" for d in datos])

            return {
                "estado": estado_ctx,
                "score": ajuste,
                "mom20_prom": round(mom_prom, 2),
                "detalle": detalle,
                "drivers": tickers,
            }

        sectores = {
            "chips": crear_contexto("chips", DRIVERS_CONTEXTO["chips"]),
            "energia": crear_contexto("energia", DRIVERS_CONTEXTO["energia"]),
            "cripto": crear_contexto("cripto", DRIVERS_CONTEXTO["cripto"]),
            "tech_ia": crear_contexto("tech_ia", DRIVERS_CONTEXTO["tech_ia"]),
        }

        return {
            "estado": estado,
            "score": score,
            "spy20": round(spy.get("mom20", 0), 2),
            "qqq20": round(qqq.get("mom20", 0), 2),
            "drivers": drivers,
            "sectores": sectores,
        }

    except Exception as e:
        print(f"ERROR contexto mercado: {e}")
        return {
            "estado": "NEUTRO",
            "score": 0,
            "spy20": 0,
            "qqq20": 0,
            "drivers": {},
            "sectores": {},
        }


def tipo_contexto_por_accion(ticker, sector):
    """Define qué contexto externo debe confirmar cada acción."""
    sector_txt = str(sector or "")

    if ticker in ["COIN", "MSTR", "MARA", "RIOT"] or "Cripto" in sector_txt:
        return "cripto"

    if ticker in ["XOM", "CVX", "SLB", "OXY", "COP", "LNG", "EOG", "FANG", "DVN", "HAL"] or "Energía" in sector_txt:
        return "energia"

    if ticker in ["NVDA", "AMD", "MU", "AVGO", "KLAC", "AMAT"] or "Chips" in sector_txt or "Memoria" in sector_txt:
        return "chips"

    if (
        "Tecnología" in sector_txt
        or "IA" in sector_txt
        or "Software" in sector_txt
        or "Ciberseguridad" in sector_txt
        or "Computación" in sector_txt
        or ticker in ["PLTR", "TSLA", "SOUN", "AI", "ARKK"]
    ):
        return "tech_ia"

    return "general"


def aplicar_contexto_sector(ticker, sector, mercado, razones, alertas):
    """Devuelve ajuste de score y descripción del contexto sectorial."""
    tipo = tipo_contexto_por_accion(ticker, sector)

    if tipo == "general":
        return 0, "GENERAL", "SPY/QQQ"

    ctx = mercado.get("sectores", {}).get(tipo)
    if not ctx:
        return 0, "SIN DATOS", ""

    estado = ctx.get("estado", "NEUTRO")
    ajuste = ctx.get("score", 0)
    detalle = ctx.get("detalle", "")

    if estado == "ACOMPAÑA":
        razones.append(f"Sector acompaña: {detalle}")
    elif estado == "NO ACOMPAÑA":
        alertas.append(f"Sector no acompaña: {detalle}")
    elif estado == "NEUTRO +":
        razones.append(f"Sector ligeramente positivo: {detalle}")

    ajuste = max(-8, min(7, ajuste))

    return ajuste, estado, detalle


def analizar(ticker, mercado):
    """Live: descarga datos y delega el cálculo puro en compute_signal()."""
    try:
        df = descargar(ticker, "1y")
    except Exception as e:
        print(f"ERROR con {ticker}: {e}")
        return None
    return compute_signal(df, ticker, mercado)


def compute_signal(df, ticker, mercado):
    """V4.7: lógica pura de señal sobre un DataFrame OHLCV point-in-time.
    No descarga datos: la comparten el live (analizar) y el futuro backtest,
    garantizando EXACTAMENTE la misma lógica de indicadores, scoring y señal.
    Para backtest: pasar df.loc[:dia_T] (datos del día T hacia atrás, sin look-ahead)."""
    try:
        if df is None or df.empty or len(df) < 220:
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        precio = numero(close.iloc[-1])
        ma10 = numero(close.rolling(10).mean().iloc[-1])
        ma20 = numero(close.rolling(20).mean().iloc[-1])
        ma50 = numero(close.rolling(50).mean().iloc[-1])
        ma200 = numero(close.rolling(200).mean().iloc[-1])
        rsi = numero(rsi_real(close).iloc[-1])
        volumen_actual = numero(volume.iloc[-1])
        volumen_prom = numero(volume.rolling(20).mean().iloc[-1])
        max20 = numero(high.rolling(20).max().iloc[-1])
        min20 = numero(low.rolling(20).min().iloc[-1])
        atr = numero(calcular_atr(high, low, close).iloc[-1])

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal

        macd_val = numero(macd.iloc[-1])
        macd_sig = numero(macd_signal.iloc[-1])
        macd_hist_val = numero(macd_hist.iloc[-1])
        macd_hist_prev = numero(macd_hist.iloc[-2])

        necesarios = [
            precio, ma10, ma20, ma50, ma200, rsi, volumen_actual,
            volumen_prom, max20, min20, atr, macd_val, macd_sig,
            macd_hist_val, macd_hist_prev
        ]

        if any(v is None for v in necesarios):
            return None

        momentum_5d = cambio_pct(close, 5)
        momentum_20d = cambio_pct(close, 20)
        momentum_60d = cambio_pct(close, 60)
        atr_pct = (atr / precio) * 100 if precio and atr else 0
        volumen_relativo = volumen_actual / volumen_prom if volumen_prom else 0
        distancia_ma20 = ((precio / ma20) - 1) * 100 if ma20 else 0
        distancia_max20 = ((precio / max20) - 1) * 100 if max20 else 0
        posicion_rango20 = ((precio - min20) / (max20 - min20)) * 100 if max20 != min20 else 50

        fuerza_relativa = momentum_20d - mercado.get("qqq20", 0)

        score = 45
        razones = []
        alertas = []
        sector = ACCIONES_INFO.get(ticker, "Otro")

        score += mercado.get("score", 0)

        if mercado.get("estado") in ["ALCISTA", "NEUTRO +"]:
            razones.append(f"Mercado {mercado.get('estado')}")
        elif mercado.get("estado") == "DÉBIL":
            alertas.append("Mercado débil")

        ajuste_sector, contexto_sector, detalle_sector = aplicar_contexto_sector(
            ticker, sector, mercado, razones, alertas
        )
        score += ajuste_sector

        if precio > ma20:
            score += 7
            razones.append("Precio sobre MA20")
        else:
            score -= 6
            alertas.append("Precio bajo MA20")

        if ma20 > ma50:
            score += 9
            razones.append("MA20 sobre MA50")
        else:
            score -= 4

        if ma50 > ma200:
            score += 9
            razones.append("Tendencia larga positiva")
        else:
            score -= 6
            alertas.append("Tendencia larga débil")

        if 48 <= rsi <= 65:
            score += 12
            razones.append("RSI saludable")
        elif 65 < rsi <= 72:
            score += 5
            alertas.append("RSI algo alto")
        elif rsi > 72:
            score -= 12
            alertas.append("RSI sobrecomprado")
        elif rsi < 38:
            score -= 10
            alertas.append("RSI débil")
        elif 38 <= rsi < 48:
            score -= 2

        if macd_val > macd_sig and macd_hist_val > 0:
            score += 10
            razones.append("MACD positivo")
        elif macd_val > macd_sig:
            score += 5
        else:
            score -= 5
            alertas.append("MACD sin confirmar")

        if macd_hist_val > macd_hist_prev:
            score += 4
            razones.append("MACD mejorando")
        else:
            score -= 2

        if volumen_relativo >= 1.8 and momentum_5d > 0:
            score += 10
            razones.append("Volumen fuerte")
        elif volumen_relativo >= 1.25 and momentum_5d > 0:
            score += 7
            razones.append("Volumen confirma")
        elif volumen_relativo < 0.75:
            score -= 4
            alertas.append("Volumen bajo")

        if 1 <= momentum_5d <= 6:
            score += 8
            razones.append("Momentum 5D sano")
        elif 6 < momentum_5d <= 10:
            score += 3
            alertas.append("Momentum 5D extendido")
        elif momentum_5d > 10:
            score -= 8
            alertas.append("Subida muy extendida 5D")
        elif momentum_5d < -3:
            score -= 7
            alertas.append("Momentum negativo")

        if momentum_20d > 0:
            score += 5
        else:
            score -= 4

        if fuerza_relativa > 2:
            score += 7
            razones.append("Fuerte vs QQQ")
        elif fuerza_relativa < -3:
            score -= 6
            alertas.append("Débil vs QQQ")

        confirmacion = "MEDIA"

        if precio >= max20 * 0.985 and posicion_rango20 >= 75 and volumen_relativo >= 1.1:
            score += 9
            confirmacion = "ALTA"
            razones.append("Ruptura confirmada")
        elif precio >= max20 * 0.97:
            score += 3
            confirmacion = "MEDIA"
        elif posicion_rango20 < 40:
            score -= 5
            confirmacion = "BAJA"
            alertas.append("Lejos del máximo 20D")

        if distancia_ma20 > 12:
            score -= 10
            alertas.append("Muy alejada de MA20")
        elif distancia_ma20 > 7:
            score -= 5
            alertas.append("Algo extendida sobre MA20")

        if atr_pct > 9:
            score -= 10
            alertas.append("Volatilidad muy alta")
        elif atr_pct > 6:
            score -= 5
            alertas.append("Volatilidad alta")
        elif 2 <= atr_pct <= 5.5:
            score += 4

        score = max(0, min(96, score))

        riesgo = "BAJO"

        if rsi > 72 or momentum_5d > 10 or atr_pct > 9 or distancia_ma20 > 12:
            riesgo = "ALTO"
        elif rsi > 65 or momentum_5d > 6 or atr_pct > 6 or distancia_ma20 > 7:
            riesgo = "MEDIO"

        if contexto_sector == "NO ACOMPAÑA" and riesgo == "BAJO":
            riesgo = "MEDIO"

        hot_score = 0

        if score >= 82:
            hot_score += 1
        if volumen_relativo >= 1.25:
            hot_score += 1
        if 1 <= momentum_5d <= 8:
            hot_score += 1
        if fuerza_relativa > 0:
            hot_score += 1
        if contexto_sector in ["ACOMPAÑA", "NEUTRO +"]:
            hot_score += 1
        if riesgo != "ALTO":
            hot_score += 1

        if hot_score >= 6:
            hot = "🔥🔥🔥"
        elif hot_score >= 4:
            hot = "🔥🔥"
        elif hot_score == 3:
            hot = "🔥"
        else:
            hot = ""

        entrada_min = round(precio - (atr * 0.35), 2)
        entrada_max = round(precio + (atr * 0.15), 2)
        stop = round(precio - (atr * 0.8), 2)      # V4.9.1: 0.8×ATR — sobrevive ruido normal de 1 día (0.5 era demasiado ajustado)
        objetivo = math.ceil(max(precio + atr * 1.2, round(precio, 2) + CONFIG_SIMULACION["rr_minimo"] * (round(precio, 2) - stop)) * 100) / 100
        relacion_rr = (objetivo - round(precio, 2)) / max(round(precio, 2) - stop, 0.0001)

        if (
            score >= 84
            and riesgo != "ALTO"
            and confirmacion == "ALTA"
            and mercado.get("estado") != "DÉBIL"
            and contexto_sector != "NO ACOMPAÑA"
        ):
            senal = "COMPRA FUERTE"
            senal_bot = "BUY STRONG"
        elif (
            score >= 74
            and riesgo != "ALTO"
            and mercado.get("estado") != "DÉBIL"
            and contexto_sector != "NO ACOMPAÑA"
        ):
            senal = "POSIBLE COMPRA"
            senal_bot = "BUY"
        elif score >= 60:
            senal = "VIGILAR"
            senal_bot = "HOLD"
        else:
            senal = "NO COMPRAR"
            senal_bot = "SELL / EVITAR"

        return {
            "Accion": ticker,
            "Sector": sector,
            "Precio actual": round(precio, 2),
            "Probabilidad tecnica": round(score, 1),
            "Momentum": round(momentum_5d, 2),
            "Momentum 20D": round(momentum_20d, 2),
            "Momentum 60D": round(momentum_60d, 2),
            "Fuerza relativa": round(fuerza_relativa, 2),
            "Volumen relativo": round(volumen_relativo, 2),
            "ATR": round(atr, 2),
            "ATR %": round(atr_pct, 2),
            "Entrada min": entrada_min,
            "Entrada max": entrada_max,
            "Stop loss": stop,
            "Objetivo": objetivo,
            "R/R": relacion_rr,
            "RSI": round(rsi, 2),
            "Distancia MA20 %": round(distancia_ma20, 2),
            "Distancia Max20 %": round(distancia_max20, 2),
            "Confirmacion": confirmacion,
            "Mercado": mercado.get("estado", "NEUTRO"),
            "Contexto sector": contexto_sector,
            "Drivers sector": detalle_sector,
            "Riesgo": riesgo,
            "Hot Score": hot,
            "Senal": senal,
            "Senal Bot": senal_bot,
            "Razones": unir_unicos(razones, 5),
            "Alertas": unir_unicos(alertas, 5),
        }

    except Exception as e:
        print(f"ERROR con {ticker}: {e}")
        return None


def prioridad_senal(senal):
    if senal == "COMPRA FUERTE":
        return 3
    if senal == "POSIBLE COMPRA":
        return 2
    if senal == "VIGILAR":
        return 1
    return 0


def prioridad_riesgo(riesgo):
    if riesgo == "BAJO":
        return 2
    if riesgo == "MEDIO":
        return 1
    return 0


def prioridad_contexto(ctx):
    if ctx == "ACOMPAÑA":
        return 3
    if ctx == "NEUTRO +":
        return 2
    if ctx in ["NEUTRO", "GENERAL"]:
        return 1
    return 0


def cargar_historial():
    data = read_json(HISTORIAL_FILE)
    validate_ledger(data)
    return data

def dias_desde(fecha_entrada):
    try:
        inicio = datetime.strptime(fecha_entrada, "%Y-%m-%d").date()
        actual = datetime.now(ZONA_HORARIA).date()
        return max(0, (actual - inicio).days)
    except Exception:
        return 0


def costo_total_estimado_pct():
    """Costo porcentual estimado por operación completa: entrada + salida + spread."""
    return round(
        (CONFIG_SIMULACION["comision_por_operacion_pct"] * 2)
        + (CONFIG_SIMULACION["slippage_pct"] * 2)
        + CONFIG_SIMULACION["spread_pct"],
        4,
    )


def distancia_stop_pct(precio_entrada, stop):
    try:
        precio_entrada = float(precio_entrada or 0)
        stop = float(stop or 0)
        if precio_entrada <= 0 or stop <= 0 or stop >= precio_entrada:
            return 0.0
        return round(((precio_entrada - stop) / precio_entrada) * 100, 4)
    except Exception:
        return 0.0


def calcular_posicion(capital, precio_entrada, stop):
    dim = position_size(capital, capital, precio_entrada, stop, CONFIG_SIMULACION)
    if not dim:
        return {"posicion_usd": 0, "acciones_estimadas": 0, "riesgo_usd": 0}
    return {"posicion_usd": dim["notional"], "acciones_estimadas": dim["quantity"],
            "riesgo_usd": dim["risk"], "distancia_stop_pct": distancia_stop_pct(precio_entrada, stop),
            "posicion_pct_cuenta": dim["notional"] / capital * 100,
            "riesgo_pct_cuenta": dim["risk"] / capital * 100}

def calcular_score_calidad(r):
    """Score 0-100 para medir calidad de cada señal.
    Combina probabilidad, R/R, momentum, fuerza relativa, riesgo, confirmación, volumen y mercado.
    No garantiza resultados; sirve para ordenar y filtrar señales.
    """
    try:
        prob = max(0.0, min(100.0, float(r.get("Probabilidad tecnica") or 0)))
        rr = max(0.0, min(3.0, float(r.get("R/R") or 0)))
        momentum = max(-10.0, min(10.0, float(r.get("Momentum") or 0)))
        fuerza_rel = max(-10.0, min(10.0, float(r.get("Fuerza relativa") or 0)))
        volumen_rel = max(0.0, min(2.5, float(r.get("Volumen relativo") or 0)))
    except Exception:
        prob, rr, momentum, fuerza_rel, volumen_rel = 0.0, 0.0, 0.0, 0.0, 0.0

    riesgo = str(r.get("Riesgo") or "").upper()
    confirmacion = str(r.get("Confirmacion") or "").upper()
    mercado = str(r.get("Mercado") or "").upper()
    contexto_sector = str(r.get("Contexto sector") or "").upper()
    bot = str(r.get("Senal Bot") or "").upper()

    score = 0.0
    score += prob * 0.34
    score += min(rr / 2.0, 1.0) * 18.0
    score += ((momentum + 10.0) / 20.0) * 12.0
    score += ((fuerza_rel + 10.0) / 20.0) * 10.0
    score += min(volumen_rel / 1.5, 1.0) * 8.0

    if riesgo == "BAJO":
        score += 10.0
    elif riesgo == "MEDIO":
        score += 5.0
    elif riesgo == "ALTO":
        score -= 8.0

    if confirmacion == "ALTA":
        score += 6.0
    elif confirmacion == "BAJA":
        score -= 6.0

    if "ALCISTA" in mercado or "NEUTRO +" in mercado:
        score += 6.0
    elif "DÉBIL" in mercado or "DEBIL" in mercado:
        score -= 10.0

    if contexto_sector == "ACOMPAÑA":
        score += 4.0
    elif contexto_sector == "NO ACOMPAÑA":
        score -= 6.0

    if bot == "BUY STRONG":
        score += 4.0
    elif bot == "SELL / EVITAR":
        score -= 8.0

    return round(max(0.0, min(100.0, score)), 1)


def distancia_objetivo_pct(precio_actual, objetivo):
    try:
        precio_actual = float(precio_actual or 0)
        objetivo = float(objetivo or 0)
        if precio_actual <= 0 or objetivo <= 0:
            return 0.0
        return round(((objetivo - precio_actual) / precio_actual) * 100, 2)
    except Exception:
        return 0.0


def distancia_stop_actual_pct(precio_actual, stop):
    try:
        precio_actual = float(precio_actual or 0)
        stop = float(stop or 0)
        if precio_actual <= 0 or stop <= 0:
            return 0.0
        return round(((precio_actual - stop) / precio_actual) * 100, 2)
    except Exception:
        return 0.0


def calcular_benchmark_desde_fecha(fecha_inicio, capital_inicial, bot_rentabilidad_pct):
    """Compara el bot contra SPY y QQQ desde la primera operación registrada."""
    salida = {
        "fecha_inicio": fecha_inicio or "SIN DATOS",
        "bot_rentabilidad_neta_pct": round(float(bot_rentabilidad_pct or 0), 2),
        "spy_rentabilidad_pct": None,
        "qqq_rentabilidad_pct": None,
        "bot_vs_spy_alpha_pct": None,
        "bot_vs_qqq_alpha_pct": None,
        "capital_si_spy_usd": None,
        "capital_si_qqq_usd": None,
    }

    if not fecha_inicio:
        return salida

    for ticker, prefijo in [("SPY", "spy"), ("QQQ", "qqq")]:
        try:
            df = descargar(ticker, periodo="1y")
            if df is None or df.empty or "Close" not in df:
                continue
            df = df[df.index.strftime("%Y-%m-%d") >= fecha_inicio]
            if df.empty:
                continue
            inicial = numero(df["Close"].iloc[0])
            final = numero(df["Close"].iloc[-1])
            if inicial and final and inicial > 0:
                ret = round(((final / inicial) - 1) * 100, 2)
                salida[f"{prefijo}_rentabilidad_pct"] = ret
                salida[f"capital_si_{prefijo}_usd"] = round(capital_inicial * (1 + ret / 100), 2)
        except Exception:
            continue

    if salida["spy_rentabilidad_pct"] is not None:
        salida["bot_vs_spy_alpha_pct"] = round(salida["bot_rentabilidad_neta_pct"] - salida["spy_rentabilidad_pct"], 2)
    if salida["qqq_rentabilidad_pct"] is not None:
        salida["bot_vs_qqq_alpha_pct"] = round(salida["bot_rentabilidad_neta_pct"] - salida["qqq_rentabilidad_pct"], 2)

    return salida


def crear_resumen_diario(equity_curve, resumen_base):
    """Resumen diario de capital usando la última operación cerrada de cada fecha."""
    dias = {}
    for p in equity_curve:
        fecha = p.get("fecha") or "SIN FECHA"
        dias[fecha] = {
            "fecha": fecha,
            "capital_cerrado_usd": p.get("capital", 0),
            "pnl_ultimo_cierre_usd": p.get("pnl_usd", 0),
            "drawdown_pct": p.get("drawdown_pct", 0),
            "ultima_accion_cerrada": p.get("accion", ""),
        }

    hoy = hoy_ymd()
    actual = dict(dias.get(hoy, {"fecha": hoy}))
    actual.update({
        "fecha": hoy,
        "capital_cerrado_usd": resumen_base.get("capital_actual_cerrado", actual.get("capital_cerrado_usd", 0)),
        "capital_total_estimado_usd": resumen_base.get("capital_actual_total_estimado", 0),
        "ganancia_total_estimada_usd": resumen_base.get("ganancia_total_estimada_usd", 0),
        "rentabilidad_total_estimada_pct": resumen_base.get("rentabilidad_total_estimada_pct", 0),
    })
    dias[hoy] = actual

    return [dias[k] for k in sorted(dias.keys())]

def fecha_orden_operacion(op):
    return op.get("exit_timestamp") or op.get("fecha_cierre") or op.get("entry_timestamp") or op.get("fecha_entrada") or ""

def es_ganada(op):
    return number(op["pnl_usd_estimado"]) > 0

def calcular_rachas(cerradas):
    max_perdidas = max_ganadas = actual_perdidas = actual_ganadas = 0
    racha_actual_tipo = ""
    racha_actual = 0

    for op in sorted(cerradas, key=fecha_orden_operacion):
        ganada = es_ganada(op)
        if ganada:
            actual_ganadas += 1
            actual_perdidas = 0
            racha_actual_tipo = "GANADAS"
            racha_actual = actual_ganadas
        else:
            actual_perdidas += 1
            actual_ganadas = 0
            racha_actual_tipo = "PERDIDAS"
            racha_actual = actual_perdidas
        max_perdidas = max(max_perdidas, actual_perdidas)
        max_ganadas = max(max_ganadas, actual_ganadas)

    return {
        "racha_max_perdidas": max_perdidas,
        "racha_max_ganadas": max_ganadas,
        "racha_actual_tipo": racha_actual_tipo,
        "racha_actual": racha_actual,
    }


def calcular_metricas_avanzadas(operaciones, mercado=None):
    # Compatibility read-only helper; main computes from the complete versioned book.
    from engine.ledger import mark
    now = datetime.now(timezone.utc)
    book = migrate({"operaciones": __import__("copy").deepcopy(operaciones)}, CONFIG_SIMULACION, now)
    for op in book["operaciones"]:
        if op["estado"] == "ABIERTA":
            mark(op, op.get("precio_actual", op["precio_entrada"]))
    return summarize(book, CONFIG_SIMULACION, now)


def resumen_operacion_top(op):
    return {
        "accion": op.get("accion", ""),
        "sector": op.get("sector", ""),
        "fecha_entrada": op.get("fecha_entrada", ""),
        "fecha_cierre": op.get("fecha_cierre", ""),
        "resultado": op.get("resultado", ""),
        "tipo_cierre": op.get("tipo_cierre", ""),
        "ganancia_pct_final": round(float(op.get("ganancia_pct_final") or 0), 2),
        "ganancia_pct_neta_estimada": round(float(op.get("ganancia_pct_neta_estimada") or 0), 2),
        "pnl_usd_estimado": round(float(op.get("pnl_usd_estimado") or 0), 2),
    }



def actualizar_historial(historial, resultados, mercado, now=None, quotes=None):
    now = now or datetime.now(timezone.utc)
    return update_ledger(historial, resultados, mercado, CONFIG_SIMULACION, now, quotes or {})


def _df_limpio(data):
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def guardar_historial(historial):
    atomic_json(HISTORIAL_FILE, historial)
    if not EXPORT_XLSX:
        return

    ops = historial.get("operaciones", [])
    resumen = historial.get("resumen", {})
    cerradas = [op for op in ops if op.get("estado") == "CERRADA"]
    abiertas = [op for op in ops if op.get("estado") == "ABIERTA"]

    columnas_prioritarias = [
        "estado", "accion", "sector", "fecha_entrada", "fecha_cierre", "dias_abierta",
        "precio_entrada", "precio_actual", "precio_cierre", "ganancia_pct", "ganancia_pct_final",
        "ganancia_pct_neta_estimada", "pnl_usd_estimado", "ganancia_abierta_usd_estimada",
        "posicion_usd_estimada", "valor_cartera_usd", "riesgo_usd_estimado",
        "riesgo_pct_cuenta_estimado", "perdida_maxima_stop_usd", "costo_usd_estimado",
        "acciones_estimadas", "distancia_stop_pct", "distancia_stop_actual_pct", "distancia_objetivo_pct",
        "stop", "objetivo", "rr", "resultado", "tipo_cierre",
        "score_calidad_entrada", "score_calidad_actual", "senal_bot_entrada", "senal_bot_actual",
        "probabilidad_entrada", "probabilidad_actual", "riesgo_entrada", "riesgo_actual",
        "mercado_entrada", "mercado_actual", "mercado_cierre",
        "contexto_sector_entrada", "contexto_sector_actual", "contexto_sector_cierre",
        "volumen_relativo_entrada", "volumen_relativo_actual",
    ]

    def ordenar_columnas(df):
        if df.empty:
            return df
        primeras = [c for c in columnas_prioritarias if c in df.columns]
        otras = [c for c in df.columns if c not in primeras]
        return df[primeras + otras]

    df_ops = ordenar_columnas(_df_limpio(ops))
    if df_ops.empty:
        df_ops = pd.DataFrame(columns=["fecha_entrada", "accion", "estado", "resultado"])

    df_abiertas = ordenar_columnas(_df_limpio(abiertas))
    df_cerradas = ordenar_columnas(_df_limpio(cerradas))

    costos = [{
        "capital_inicial": resumen.get("simulacion", {}).get("capital_inicial"),
        "capital_actual_cerrado": resumen.get("simulacion", {}).get("capital_actual_cerrado"),
        "capital_actual_total_estimado": resumen.get("simulacion", {}).get("capital_actual_total_estimado"),
        "costos_totales_usd": resumen.get("simulacion", {}).get("costos_totales_usd"),
        "costo_pct_por_operacion": resumen.get("simulacion", {}).get("costo_total_estimado_pct_por_operacion"),
        "comision_pct_por_lado": CONFIG_SIMULACION.get("comision_por_operacion_pct"),
        "slippage_pct_por_lado": CONFIG_SIMULACION.get("slippage_pct"),
        "spread_pct_total": CONFIG_SIMULACION.get("spread_pct"),
        "riesgo_por_operacion_pct": CONFIG_SIMULACION.get("riesgo_por_operacion_pct"),
        "max_posicion_pct": CONFIG_SIMULACION.get("max_posicion_pct"),
        "max_operaciones_abiertas": CONFIG_SIMULACION.get("max_operaciones_abiertas"),
        "max_exposicion_total_pct": CONFIG_SIMULACION.get("max_exposicion_total_pct"),
    }]

    if not EXPORT_XLSX:
        return
    with pd.ExcelWriter(HISTORIAL_XLSX, engine="openpyxl") as writer:
        df_ops.to_excel(writer, sheet_name="Historial completo", index=False)
        _df_limpio(resumen.get("resumen_diario", [])).to_excel(writer, sheet_name="Resumen diario", index=False)
        _df_limpio(resumen.get("equity_curve", [])).to_excel(writer, sheet_name="Capital equity curve", index=False)
        df_abiertas.to_excel(writer, sheet_name="Operaciones abiertas", index=False)
        df_cerradas.to_excel(writer, sheet_name="Operaciones cerradas", index=False)
        _df_limpio(resumen.get("rendimiento_por_sector", [])).to_excel(writer, sheet_name="Rendimiento sector", index=False)
        _df_limpio(resumen.get("rendimiento_por_mercado", [])).to_excel(writer, sheet_name="Rendimiento mercado", index=False)
        _df_limpio(resumen.get("mejores_operaciones", [])).to_excel(writer, sheet_name="Mejores operaciones", index=False)
        _df_limpio(resumen.get("peores_operaciones", [])).to_excel(writer, sheet_name="Peores operaciones", index=False)
        pd.DataFrame(costos).to_excel(writer, sheet_name="Costos simulados", index=False)
        pd.DataFrame([resumen.get("benchmark", {})]).to_excel(writer, sheet_name="Benchmark SPY QQQ", index=False)

        # Formato básico: congelar encabezados y ajustar anchos.
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col[:80]:
                    try:
                        max_len = max(max_len, len(str(cell.value or "")))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 28)


def main():
    started = time.perf_counter()
    historial = cargar_historial()  # validate BEFORE any download/write
    original = __import__("copy").deepcopy(historial)
    driver_tickers = {t for group in DRIVERS_CONTEXTO.values() for t in group}
    DAILY_DATA.clear()
    DAILY_DATA.update(download_batch(set(ACCIONES) | driver_tickers))
    drivers = {t: compute_driver(DAILY_DATA.get(t), t) for t in driver_tickers}
    mercado = armar_contexto_mercado(drivers)
    if any(drivers.get(t, {}).get("estado") == "SIN DATOS" for t in ("SPY", "QQQ")):
        mercado["estado"] = "SIN DATOS"
    resultados = []
    signal_time = datetime.now(timezone.utc).isoformat()
    for ticker in ACCIONES:
        frame = DAILY_DATA.get(ticker)
        r = compute_signal(frame, ticker, mercado)
        if r:
            r["Score calidad"] = calcular_score_calidad(r)
            r["signal_timestamp"] = signal_time
            r["bar_session"] = str(frame.index[-1].date())
            resultados.append(r)
    resultados.sort(key=lambda x: (
        prioridad_senal(x.get("Senal", "")), prioridad_riesgo(x.get("Riesgo", "")),
        prioridad_contexto(x.get("Contexto sector", "")), x.get("Score calidad", 0),
        x.get("Probabilidad tecnica", 0), x.get("Fuerza relativa", 0),
        -x.get("ATR %", 99), x["Accion"]), reverse=True)
    quote_tickers = {o["accion"] for o in historial["operaciones"] if o["estado"] == "ABIERTA"}
    quote_tickers.update(r["Accion"] for r in resultados if r["Senal Bot"] in ("BUY", "BUY STRONG"))
    quotes = execution_quotes(quote_tickers)
    # Never trade through an unprocessed split on an existing position.
    corporate_actions = []
    for op in historial["operaciones"]:
        if op["estado"] != "ABIERTA":
            continue
        frame = DAILY_DATA.get(op["accion"])
        if frame is not None and "Stock Splits" in frame:
            later = frame[frame.index.strftime("%Y-%m-%d") > op["fecha_entrada"]]
            if later["Stock Splits"].fillna(0).ne(0).any():
                quotes.pop(op["accion"], None)
                corporate_actions.append(op["accion"])
    now = datetime.now(timezone.utc)  # includes entire scan latency; session gate cannot be bypassed
    historial = actualizar_historial(historial, resultados, mercado, now, quotes)
    historial["resumen"]["benchmark"] = calcular_benchmark_desde_fecha(
        min((o["fecha_entrada"] for o in historial["operaciones"]), default=None),
        CONFIG_SIMULACION["capital_inicial"],
        historial["resumen"]["simulacion"]["rentabilidad_total_estimada_pct"])
    historial["resumen"]["benchmark"]["nota"] = "Comparación orientativa con saldo legacy no certificado; cierres diarios."
    missing_drivers = [t for t in driver_tickers if t not in DAILY_DATA]
    telemetry = {
        "duration_seconds": round(time.perf_counter() - started, 3),
        "signals_available": len(resultados), "universe_size": len(ACCIONES),
        "missing_symbols": sorted(set(ACCIONES) - {r["Accion"] for r in resultados}),
        "missing_drivers": missing_drivers, "corporate_actions_pending": corporate_actions,
        "quote_source": "yfinance 1m; simulación muestreada, no ticks ni ejecución garantizada",
    }
    # Freeze the unmodified first legacy snapshot for audit/rollback before changing the ledger.
    if original.get("schema_version") != 2:
        legacy_path = Path("paper/legacy") / (config_hash(original) + ".json")
        if not legacy_path.exists():
            atomic_json(legacy_path, original)
    paper_state = export_paper_state(historial, resultados, mercado, CONFIG_SIMULACION)
    paper_state["run_id"] = historial["run_id"]
    salida = {
        "actualizado": historial["actualizado"], "generated_at": historial["generated_at"],
        "run_id": historial["run_id"], "schema_version": 2, "version_bot": VERSION,
        "market_session": historial["market_session"], "telemetry": telemetry,
        "contexto_mercado": mercado, "config_operativa": resumen_config_operativa(CONFIG_SISTEMA, CONFIG_SIMULACION),
        "resultados": resultados, "paper_trading": paper_state["status"],
        "paper_state": paper_state,  # one coherent dashboard snapshot, no cross-file race
        "historial": {"actualizado": historial["actualizado"], "resumen": historial["resumen"],
                     "total_operaciones": len(historial["operaciones"]),
                     "operaciones": sorted(historial["operaciones"], key=lambda o: (o["estado"] == "ABIERTA", o.get("entry_timestamp", o["fecha_entrada"])), reverse=True)},
    }
    guardar_historial(historial)
    atomic_json("datos_acciones.json", salida)  # publish manifest last; workflow commits all files together
    if EXPORT_XLSX:
        pd.DataFrame(resultados).to_excel("analisis_acciones.xlsx", index=False)
    print(json.dumps(telemetry, ensure_ascii=False))


if __name__ == "__main__":
    main()
