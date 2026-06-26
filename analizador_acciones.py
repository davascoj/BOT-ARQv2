import json
import os
import time
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
try:
    from engine.paper_trading_engine import export_paper_state
except Exception as e:
    export_paper_state = None
    PAPER_ENGINE_IMPORT_ERROR = str(e)
else:
    PAPER_ENGINE_IMPORT_ERROR = ""

# ============================================================
# BOT-ARQ V4.2 - CONFIGURACIÓN REAL DEL MOTOR
# Carga config/system_config.json y la aplica al motor actual.
# ============================================================
try:
    from engine.config_loader import (
        cargar_config_sistema,
        cargar_config_simulacion,
        resumen_config_operativa,
    )
except Exception as e:
    cargar_config_sistema = None
    cargar_config_simulacion = None
    resumen_config_operativa = None
    CONFIG_LOADER_IMPORT_ERROR = str(e)
else:
    CONFIG_LOADER_IMPORT_ERROR = ""


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
}

# CONFIG_SIMULACION real usada por el motor.
# En V4.2 se carga desde config/system_config.json.
# Si el archivo falla, usa DEFAULT_CONFIG_SIMULACION.
if cargar_config_sistema and cargar_config_simulacion:
    CONFIG_SISTEMA = cargar_config_sistema()
    CONFIG_SIMULACION = cargar_config_simulacion(DEFAULT_CONFIG_SIMULACION, CONFIG_SISTEMA)
else:
    CONFIG_SISTEMA = {}
    CONFIG_SIMULACION = dict(DEFAULT_CONFIG_SIMULACION)

if CONFIG_LOADER_IMPORT_ERROR:
    print("ADVERTENCIA: config loader no disponible:", CONFIG_LOADER_IMPORT_ERROR)
else:
    print("CONFIG BOT-ARQ cargada:", CONFIG_SISTEMA.get("version", "default"))



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
        if hasattr(valor, "iloc"):
            return float(valor.iloc[0])
        return float(valor)
    except Exception:
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
    df = yf.download(
        ticker,
        period=periodo,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    return limpiar_df(df)


def rsi_real(close, periodo=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(periodo).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(periodo).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


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
    """Evalúa un ETF/índice/activo externo como QQQ, SOXX, XLE, BTC-USD, ETH-USD o petróleo."""
    try:
        df = descargar(ticker, "1y")
        if df.empty or len(df) < 80:
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
    """Calcula contexto general y contexto por sectores clave."""
    try:
        drivers = {}
        tickers_unicos = sorted({t for lista in DRIVERS_CONTEXTO.values() for t in lista})

        for ticker in tickers_unicos:
            drivers[ticker] = evaluar_driver(ticker)
            time.sleep(0.2)

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
        stop = round(precio - (atr * 1.35), 2)
        objetivo = round(precio + (atr * 2.2), 2)
        relacion_rr = round((objetivo - precio) / max(precio - stop, 0.01), 2)

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
    if not os.path.exists(HISTORIAL_FILE):
        return {"version": 1, "actualizado": "", "operaciones": [], "resumen": {}}

    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            data = {}

        if not isinstance(data.get("operaciones"), list):
            data["operaciones"] = []

        data.setdefault("version", 1)
        data.setdefault("resumen", {})

        return data

    except Exception as e:
        print(f"No se pudo leer historial: {e}")
        return {"version": 1, "actualizado": "", "operaciones": [], "resumen": {}}


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
    """Calcula tamaño de posición para no superar el riesgo configurado."""
    capital = float(capital or CONFIG_SIMULACION["capital_inicial"])
    d_stop = distancia_stop_pct(precio_entrada, stop)
    riesgo_usd = capital * (CONFIG_SIMULACION["riesgo_por_operacion_pct"] / 100)
    max_posicion_usd = capital * (CONFIG_SIMULACION["max_posicion_pct"] / 100)

    if d_stop <= 0:
        posicion_usd = max_posicion_usd
        riesgo_real_usd = 0.0
    else:
        posicion_usd = riesgo_usd / (d_stop / 100)
        posicion_usd = min(posicion_usd, max_posicion_usd)
        riesgo_real_usd = posicion_usd * (d_stop / 100)

    acciones_estimadas = 0.0
    try:
        precio = float(precio_entrada or 0)
        if precio > 0:
            acciones_estimadas = posicion_usd / precio
    except Exception:
        acciones_estimadas = 0.0

    return {
        "posicion_usd": round(posicion_usd, 2),
        "posicion_pct_cuenta": round((posicion_usd / capital) * 100, 2) if capital else 0,
        "riesgo_usd": round(riesgo_real_usd, 2),
        "riesgo_pct_cuenta": round((riesgo_real_usd / capital) * 100, 2) if capital else 0,
        "distancia_stop_pct": round(d_stop, 2),
        "acciones_estimadas": round(acciones_estimadas, 4),
    }



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
    return op.get("fecha_cierre") or op.get("fecha_entrada") or "1900-01-01"


def es_ganada(op):
    if str(op.get("resultado", "")).startswith("GANADA"):
        return True
    try:
        return float(op.get("ganancia_pct_final") or op.get("ganancia_pct") or 0) > 0
    except Exception:
        return False


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


def resumen_grupo_operaciones(ops, campo):
    grupos = {}
    costo_pct = costo_total_estimado_pct()

    for op in ops:
        clave = op.get(campo) or "SIN DATOS"
        grupos.setdefault(clave, {
            "grupo": clave,
            "operaciones": 0,
            "ganadas": 0,
            "perdidas": 0,
            "rentabilidad_bruta_pct": 0.0,
            "rentabilidad_neta_pct": 0.0,
            "total_ganado_pct": 0.0,
            "total_perdido_pct": 0.0,
        })
        g = grupos[clave]
        bruto = float(op.get("ganancia_pct_final") or 0)
        neto = bruto - costo_pct
        g["operaciones"] += 1
        g["rentabilidad_bruta_pct"] += bruto
        g["rentabilidad_neta_pct"] += neto
        if neto >= 0:
            g["ganadas"] += 1
            g["total_ganado_pct"] += neto
        else:
            g["perdidas"] += 1
            g["total_perdido_pct"] += abs(neto)

    salida = []
    for g in grupos.values():
        ops_n = g["operaciones"] or 1
        perdido = g["total_perdido_pct"]
        salida.append({
            "grupo": g["grupo"],
            "operaciones": g["operaciones"],
            "ganadas": g["ganadas"],
            "perdidas": g["perdidas"],
            "win_rate": round((g["ganadas"] / ops_n) * 100, 2),
            "rentabilidad_bruta_pct": round(g["rentabilidad_bruta_pct"], 2),
            "rentabilidad_neta_pct": round(g["rentabilidad_neta_pct"], 2),
            "profit_factor": round(g["total_ganado_pct"] / perdido, 2) if perdido else None,
        })

    return sorted(salida, key=lambda x: x["rentabilidad_neta_pct"], reverse=True)


def _calcular_ratios_pro(cerradas, max_dd_pct, rentabilidad_neta_pct, capital_inicial):
    """V4.6: Sharpe, Sortino, Calmar, win rate, expectancy y winrate por sector."""
    if not cerradas:
        return {}

    retornos = [float(op.get("ganancia_pct_neta_estimada") or 0) for op in cerradas]
    pnls_usd = [float(op.get("pnl_usd_estimado") or 0) for op in cerradas]
    dias_list = [float(op.get("dias_abierta") or 1) for op in cerradas]
    n = len(retornos)

    mu = sum(retornos) / n
    varianza = sum((r - mu) ** 2 for r in retornos) / max(n - 1, 1)
    sigma = varianza ** 0.5
    avg_dias = sum(dias_list) / n if n else 1

    # Factor de anualización según el periodo medio de tenencia
    factor = (252 / max(avg_dias, 1)) ** 0.5

    sharpe = round((mu / sigma) * factor, 3) if sigma > 0 else None

    negativos = [r for r in retornos if r < 0]
    if len(negativos) > 1:
        mu_neg = sum(negativos) / len(negativos)
        var_neg = sum((r - mu_neg) ** 2 for r in negativos) / max(len(negativos) - 1, 1)
        downside = var_neg ** 0.5
        sortino = round((mu / downside) * factor, 3) if downside > 0 else None
    else:
        sortino = None

    # CAGR usando fecha primera / última operación cerrada.
    # Solo se anualiza con >= 90 días de historial; con menos, anualizar infla el dato
    # de forma engañosa (p. ej. 30 días daría CAGR de cientos de %).
    fechas = sorted([op.get("fecha_cierre") or op.get("fecha_entrada") or "" for op in cerradas])
    cagr = None
    periodo_dias = None
    try:
        d0 = datetime.strptime(fechas[0], "%Y-%m-%d")
        d1 = datetime.strptime(fechas[-1], "%Y-%m-%d")
        periodo_dias = max((d1 - d0).days, 1)
        if periodo_dias >= 90:
            cagr = round(((1 + rentabilidad_neta_pct / 100) ** (365 / periodo_dias) - 1) * 100, 2)
    except Exception:
        pass

    calmar = round(cagr / max_dd_pct, 3) if (cagr is not None and max_dd_pct and max_dd_pct > 0) else None

    # Win rate y expectancy en USD
    wins_usd = [p for p in pnls_usd if p > 0]
    loss_usd = [p for p in pnls_usd if p <= 0]
    win_rate = round(len(wins_usd) / n * 100, 2) if n else 0
    avg_win_usd = round(sum(wins_usd) / len(wins_usd), 2) if wins_usd else 0
    avg_loss_usd = round(abs(sum(loss_usd) / len(loss_usd)), 2) if loss_usd else 0
    expectancy_usd = round((win_rate / 100) * avg_win_usd - (1 - win_rate / 100) * avg_loss_usd, 2)
    payoff = round(avg_win_usd / avg_loss_usd, 2) if avg_loss_usd else None

    # Win rate por sector (mínimo 2 trades)
    sector_map = {}
    for op in cerradas:
        s = str(op.get("sector") or "Sin sector").strip() or "Sin sector"
        pnl = float(op.get("pnl_usd_estimado") or 0)
        if s not in sector_map:
            sector_map[s] = {"wins": 0, "total": 0, "pnl_usd": 0.0}
        sector_map[s]["total"] += 1
        sector_map[s]["pnl_usd"] = round(sector_map[s]["pnl_usd"] + pnl, 2)
        if pnl > 0:
            sector_map[s]["wins"] += 1

    winrate_por_sector = sorted(
        [{"sector": s,
          "trades": v["total"],
          "win_rate_pct": round(v["wins"] / v["total"] * 100, 1),
          "pnl_usd": v["pnl_usd"]}
         for s, v in sector_map.items() if v["total"] >= 2],
        key=lambda x: x["pnl_usd"], reverse=True
    )

    return {
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "cagr_estimado_pct": cagr,
        "periodo_dias": periodo_dias,
        "win_rate_pct": win_rate,
        "avg_win_usd": avg_win_usd,
        "avg_loss_usd": avg_loss_usd,
        "expectancy_usd": expectancy_usd,
        "payoff_ratio": payoff,
        "avg_holding_dias": round(avg_dias, 1),
        "winrate_por_sector": winrate_por_sector,
    }


def calcular_metricas_avanzadas(operaciones, mercado=None):
    """Genera curva de capital, drawdown, costos, profit factor, exposición y diagnóstico."""
    capital_inicial = float(CONFIG_SIMULACION["capital_inicial"])
    capital = capital_inicial
    costo_pct = costo_total_estimado_pct()
    cerradas = [op for op in operaciones if op.get("estado") == "CERRADA"]
    abiertas = [op for op in operaciones if op.get("estado") == "ABIERTA"]
    cerradas_ordenadas = sorted(cerradas, key=fecha_orden_operacion)

    equity_curve = []
    peak = capital_inicial
    max_dd_pct = 0.0
    max_dd_usd = 0.0
    total_costos = 0.0
    ganancias_usd = 0.0
    perdidas_usd = 0.0
    ganancias_pct = []
    perdidas_pct = []
    suma_bruta_pct = 0.0
    suma_neta_pct = 0.0

    for i, op in enumerate(cerradas_ordenadas, start=1):
        bruto_pct = float(op.get("ganancia_pct_final") or 0)
        neto_pct = bruto_pct - costo_pct
        capital_antes = capital
        pos = calcular_posicion(capital_antes, op.get("precio_entrada"), op.get("stop"))
        posicion_usd = pos["posicion_usd"]
        costo_usd = posicion_usd * (costo_pct / 100)
        pnl_usd = posicion_usd * (neto_pct / 100)
        capital += pnl_usd
        peak = max(peak, capital)
        dd_usd = max(0.0, peak - capital)
        dd_pct = (dd_usd / peak) * 100 if peak else 0.0
        max_dd_usd = max(max_dd_usd, dd_usd)
        max_dd_pct = max(max_dd_pct, dd_pct)
        total_costos += costo_usd
        suma_bruta_pct += bruto_pct
        suma_neta_pct += neto_pct

        if pnl_usd >= 0:
            ganancias_usd += pnl_usd
            ganancias_pct.append(neto_pct)
        else:
            perdidas_usd += abs(pnl_usd)
            perdidas_pct.append(neto_pct)

        op["ganancia_pct_neta_estimada"] = round(neto_pct, 2)
        op["pnl_usd_estimado"] = round(pnl_usd, 2)
        op["costo_usd_estimado"] = round(costo_usd, 2)
        op["posicion_usd_estimada"] = pos["posicion_usd"]
        op["valor_cartera_usd"] = 0.0
        op["capital_antes_operacion"] = round(capital_antes, 2)
        op["capital_despues_operacion"] = round(capital, 2)
        op["riesgo_usd_estimado"] = pos["riesgo_usd"]
        op["riesgo_pct_cuenta_estimado"] = pos["riesgo_pct_cuenta"]
        op["perdida_maxima_stop_usd"] = pos["riesgo_usd"]
        op["distancia_stop_pct"] = pos["distancia_stop_pct"]
        op["distancia_stop_actual_pct"] = 0.0
        op["distancia_objetivo_pct"] = 0.0

        equity_curve.append({
            "n": i,
            "fecha": fecha_orden_operacion(op),
            "accion": op.get("accion", ""),
            "capital": round(capital, 2),
            "pnl_usd": round(pnl_usd, 2),
            "retorno_neto_pct": round(neto_pct, 2),
            "drawdown_pct": round(dd_pct, 2),
        })

    # V4.5 Position Sizing Pro: cada posición abierta descuenta caja antes de dimensionar la siguiente.
    # Sin esto, todas las posiciones se dimensionan sobre el capital completo → exposición >100% posible.
    exposicion_usd = 0.0
    riesgo_abierto_usd = 0.0
    ganancia_abierta_neta_usd = 0.0
    caja_disponible = capital  # se reduce conforme se compromete cash en cada posición
    for op in abiertas:
        pos = calcular_posicion(caja_disponible, op.get("precio_entrada"), op.get("stop"))
        bruto_abierto = float(op.get("ganancia_pct") or 0)
        neto_abierto = bruto_abierto - costo_pct
        pnl_abierto = pos["posicion_usd"] * (neto_abierto / 100)
        valor_cartera = pos["posicion_usd"] + pnl_abierto
        exposicion_usd += pos["posicion_usd"]
        riesgo_abierto_usd += pos["riesgo_usd"]
        ganancia_abierta_neta_usd += pnl_abierto
        caja_disponible = max(caja_disponible - pos["posicion_usd"], 0)
        op["ganancia_pct_neta_estimada"] = round(neto_abierto, 2)
        op["pnl_usd_estimado"] = round(pnl_abierto, 2)
        op["ganancia_abierta_usd_estimada"] = round(pnl_abierto, 2)
        op["costo_usd_estimado"] = round(pos["posicion_usd"] * (costo_pct / 100), 2)
        op["posicion_usd_estimada"] = pos["posicion_usd"]
        op["valor_cartera_usd"] = round(valor_cartera, 2)
        op["riesgo_usd_estimado"] = pos["riesgo_usd"]
        op["riesgo_pct_cuenta_estimado"] = pos["riesgo_pct_cuenta"]
        op["perdida_maxima_stop_usd"] = pos["riesgo_usd"]
        op["distancia_stop_pct"] = pos["distancia_stop_pct"]
        op["distancia_stop_actual_pct"] = distancia_stop_actual_pct(op.get("precio_actual"), op.get("stop"))
        op["distancia_objetivo_pct"] = distancia_objetivo_pct(op.get("precio_actual"), op.get("objetivo"))

    # Métricas de caja real V4.5
    caja_comprometida_usd = round(exposicion_usd, 2)
    caja_disponible_usd = round(max(capital - caja_comprometida_usd, 0), 2)
    caja_disponible_pct = round((caja_disponible_usd / capital_inicial * 100), 2) if capital_inicial else 0
    max_nueva_posicion_usd = round(min(
        caja_disponible_usd,
        capital_inicial * (CONFIG_SIMULACION.get("max_posicion_pct", 20) / 100)
    ), 2)

    rachas = calcular_rachas(cerradas_ordenadas)
    profit_factor = round(ganancias_usd / perdidas_usd, 2) if perdidas_usd else None
    gan_prom = round(sum(ganancias_pct) / len(ganancias_pct), 2) if ganancias_pct else 0
    per_prom = round(sum(perdidas_pct) / len(perdidas_pct), 2) if perdidas_pct else 0
    ratio_gp = round(abs(gan_prom / per_prom), 2) if per_prom else None
    expectativa_pct = round(suma_neta_pct / len(cerradas), 2) if cerradas else 0

    capital_total_estimado = capital + ganancia_abierta_neta_usd
    exposicion_pct = round((exposicion_usd / capital) * 100, 2) if capital else 0
    riesgo_abierto_pct = round((riesgo_abierto_usd / capital) * 100, 2) if capital else 0

    mejores = sorted(cerradas, key=lambda x: float(x.get("ganancia_pct_final") or 0), reverse=True)[:10]
    peores = sorted(cerradas, key=lambda x: float(x.get("ganancia_pct_final") or 0))[:10]

    mercado_estado = (mercado or {}).get("estado", "SIN DATOS")
    modo = "ACTIVO"
    alertas = []
    riesgo_sistema = "BAJO"

    if mercado_estado == "DÉBIL":
        modo = "DEFENSIVO"
        alertas.append("Mercado general débil por SPY/QQQ")
    if rachas["racha_actual_tipo"] == "PERDIDAS" and rachas["racha_actual"] >= CONFIG_SIMULACION["pausar_si_perdidas_seguidas"]:
        modo = "DEFENSIVO"
        alertas.append(f"Racha actual de pérdidas: {rachas['racha_actual']}")
    if rachas["racha_actual_tipo"] == "PERDIDAS" and rachas["racha_actual"] >= CONFIG_SIMULACION["bloquear_si_perdidas_seguidas"]:
        modo = "PAUSADO"
        alertas.append("Racha de pérdidas alcanzó límite de bloqueo")
    if len(abiertas) >= CONFIG_SIMULACION["max_operaciones_abiertas"]:
        modo = "DEFENSIVO" if modo != "PAUSADO" else modo
        alertas.append("Máximo de operaciones abiertas alcanzado")
    if exposicion_pct >= CONFIG_SIMULACION["max_exposicion_total_pct"]:
        modo = "DEFENSIVO" if modo != "PAUSADO" else modo
        alertas.append("Exposición abierta alta")

    if max_dd_pct >= 25 or exposicion_pct >= 90 or rachas["racha_max_perdidas"] >= 12:
        riesgo_sistema = "ALTO"
    elif max_dd_pct >= 12 or exposicion_pct >= 70 or rachas["racha_max_perdidas"] >= 8:
        riesgo_sistema = "MEDIO"

    diagnostico = {
        "modo": modo,
        "riesgo_sistema": riesgo_sistema,
        "mercado": mercado_estado,
        "mensaje": "Sistema en simulación con control de riesgo; validar varios meses antes de dinero real.",
        "alertas": alertas[:6],
    }

    simulacion = {
        "capital_inicial": round(capital_inicial, 2),
        "capital_actual_cerrado": round(capital, 2),
        "capital_actual_total_estimado": round(capital_total_estimado, 2),
        "ganancia_neta_usd": round(capital - capital_inicial, 2),
        "ganancia_total_estimada_usd": round(capital_total_estimado - capital_inicial, 2),
        "rentabilidad_neta_pct": round(((capital / capital_inicial) - 1) * 100, 2) if capital_inicial else 0,
        "rentabilidad_total_estimada_pct": round(((capital_total_estimado / capital_inicial) - 1) * 100, 2) if capital_inicial else 0,
        "rentabilidad_bruta_pct": round(suma_bruta_pct, 2),
        "rentabilidad_neta_senales_pct": round(suma_neta_pct, 2),
        "costos_totales_usd": round(total_costos, 2),
        "costo_total_estimado_pct_por_operacion": costo_pct,
        "ganancia_abierta_neta_usd": round(ganancia_abierta_neta_usd, 2),
        "valor_total_en_cartera_usd": round(exposicion_usd + ganancia_abierta_neta_usd, 2),
        "caja_comprometida_usd": caja_comprometida_usd,
        "caja_disponible_usd": caja_disponible_usd,
        "caja_disponible_pct": caja_disponible_pct,
        "max_nueva_posicion_usd": max_nueva_posicion_usd,
        "modo": "SIMULACIÓN",
    }

    benchmark = calcular_benchmark_desde_fecha(
        cerradas_ordenadas[0].get("fecha_entrada") if cerradas_ordenadas else None,
        capital_inicial,
        simulacion.get("rentabilidad_neta_pct", 0),
    )
    resumen_diario = crear_resumen_diario(equity_curve, simulacion)

    riesgo = {
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_usd": round(max_dd_usd, 2),
        "racha_max_perdidas": rachas["racha_max_perdidas"],
        "racha_max_ganadas": rachas["racha_max_ganadas"],
        "racha_actual_tipo": rachas["racha_actual_tipo"],
        "racha_actual": rachas["racha_actual"],
        "exposicion_abierta_usd": round(exposicion_usd, 2),
        "exposicion_abierta_pct": exposicion_pct,
        "riesgo_total_abierto_usd": round(riesgo_abierto_usd, 2),
        "riesgo_total_abierto_pct": riesgo_abierto_pct,
        "operaciones_abiertas": len(abiertas),
        "max_operaciones_abiertas": CONFIG_SIMULACION["max_operaciones_abiertas"],
    }

    ratios_pro = _calcular_ratios_pro(
        cerradas_ordenadas, max_dd_pct,
        simulacion.get("rentabilidad_neta_pct", 0), capital_inicial
    )

    metricas = {
        "profit_factor": profit_factor,
        "ganancia_promedio_pct": gan_prom,
        "perdida_promedio_pct": per_prom,
        "ratio_ganancia_perdida": ratio_gp,
        "expectativa_pct_por_operacion": expectativa_pct,
        "total_ganado_usd": round(ganancias_usd, 2),
        "total_perdido_usd": round(perdidas_usd, 2),
        **ratios_pro,
    }

    return {
        "simulacion": simulacion,
        "riesgo": riesgo,
        "metricas": metricas,
        "equity_curve": equity_curve,
        "resumen_diario": resumen_diario,
        "benchmark": benchmark,
        "rendimiento_por_sector": resumen_grupo_operaciones(cerradas, "sector"),
        "rendimiento_por_mercado": resumen_grupo_operaciones(cerradas, "mercado_entrada"),
        "mejores_operaciones": [resumen_operacion_top(op) for op in mejores],
        "peores_operaciones": [resumen_operacion_top(op) for op in peores],
        "diagnostico_bot": diagnostico,
    }


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



# ============================================================
# BOT-ARQ V4.4 - REGLAS OPERATIVAS
# No duplica el riesgo: convierte métricas existentes en bloqueo real.
# ============================================================

def _num_cfg_(key, default=0.0):
    try: return float(CONFIG_SIMULACION.get(key, default))
    except Exception: return float(default)

def _bool_cfg_(key, default=False):
    v = CONFIG_SIMULACION.get(key, default)
    if isinstance(v, str): return v.strip().lower() in ("true", "1", "si", "sí", "yes", "on")
    return bool(v)

def _safe_num_(value, default=0.0):
    try:
        if value is None or value == "": return float(default)
        return float(value)
    except Exception:
        return float(default)

def calcular_contexto_reglas_operativas_(operaciones, mercado):
    try:
        metricas_previas = calcular_metricas_avanzadas(operaciones, mercado)
    except Exception as e:
        metricas_previas = {}
        print("ADVERTENCIA: no se pudo calcular contexto operativo:", e)

    riesgo = dict(metricas_previas.get("riesgo", {}) or {})
    sim = dict(metricas_previas.get("simulacion", {}) or {})
    diagnostico = dict(metricas_previas.get("diagnostico_bot", {}) or {})
    capital_operativo = _safe_num_(sim.get("capital_actual_cerrado"), CONFIG_SIMULACION.get("capital_inicial", 5000.0))
    if capital_operativo <= 0: capital_operativo = _safe_num_(CONFIG_SIMULACION.get("capital_inicial"), 5000.0)
    exposicion_usd = _safe_num_(riesgo.get("exposicion_abierta_usd"), 0)
    riesgo_usd = _safe_num_(riesgo.get("riesgo_total_abierto_usd"), 0)
    drawdown_pct = _safe_num_(riesgo.get("max_drawdown_pct"), 0)
    return {
        "version":"V4.4", "capital_operativo":capital_operativo,
        "exposicion_abierta_usd":exposicion_usd, "riesgo_abierto_usd":riesgo_usd,
        "exposicion_abierta_pct":round((exposicion_usd/capital_operativo)*100,2) if capital_operativo else 0,
        "riesgo_abierto_pct":round((riesgo_usd/capital_operativo)*100,2) if capital_operativo else 0,
        "drawdown_pct":round(drawdown_pct,2), "modo_previo":diagnostico.get("modo","ACTIVO"),
        "riesgo_sistema_previo":diagnostico.get("riesgo_sistema","SIN DATOS"),
        "max_exposicion_total_pct":_num_cfg_("max_exposicion_total_pct",80),
        "max_riesgo_total_abierto_pct":_num_cfg_("max_riesgo_total_abierto_pct",10),
        "modo_defensivo_drawdown_pct":_num_cfg_("modo_defensivo_drawdown_pct",12),
        "bloquear_entradas_drawdown_pct":_num_cfg_("bloquear_entradas_drawdown_pct",25),
        "activar_reglas_operativas":_bool_cfg_("activar_reglas_operativas",True),
        "usar_exposicion_como_bloqueo":_bool_cfg_("usar_exposicion_como_bloqueo",True),
        "usar_riesgo_abierto_como_bloqueo":_bool_cfg_("usar_riesgo_abierto_como_bloqueo",True),
        "usar_drawdown_como_bloqueo":_bool_cfg_("usar_drawdown_como_bloqueo",True),
        "permitir_buy_strong_en_modo_defensivo_drawdown":_bool_cfg_("permitir_buy_strong_en_modo_defensivo_drawdown",True),
        "permitir_buy_strong_sobre_exposicion":_bool_cfg_("permitir_buy_strong_sobre_exposicion",False),
        "permitir_buy_strong_sobre_riesgo":_bool_cfg_("permitir_buy_strong_sobre_riesgo",False),
        "bloqueos_generados":0, "ultimo_motivo":""
    }

def evaluar_reglas_operativas_candidato_(r, posicion, contexto, senal_bot):
    if not contexto.get("activar_reglas_operativas", True): return ""
    capital = _safe_num_(contexto.get("capital_operativo"), CONFIG_SIMULACION.get("capital_inicial", 5000.0))
    if capital <= 0: return ""
    posicion_usd = _safe_num_(posicion.get("posicion_usd"), 0)
    riesgo_usd = _safe_num_(posicion.get("riesgo_usd"), 0)
    exposicion_actual_usd = _safe_num_(contexto.get("exposicion_abierta_usd"), 0)
    riesgo_actual_usd = _safe_num_(contexto.get("riesgo_abierto_usd"), 0)
    exposicion_actual_pct = (exposicion_actual_usd / capital) * 100
    exposicion_resultante_pct = ((exposicion_actual_usd + posicion_usd) / capital) * 100
    riesgo_actual_pct = (riesgo_actual_usd / capital) * 100
    riesgo_resultante_pct = ((riesgo_actual_usd + riesgo_usd) / capital) * 100
    drawdown_pct = _safe_num_(contexto.get("drawdown_pct"), 0)
    if contexto.get("usar_drawdown_como_bloqueo", True):
        if drawdown_pct >= contexto.get("bloquear_entradas_drawdown_pct", 25):
            return f"Bloqueo operativo por drawdown máximo: {round(drawdown_pct, 2)}%"
        if drawdown_pct >= contexto.get("modo_defensivo_drawdown_pct", 12):
            if senal_bot != "BUY STRONG" or not contexto.get("permitir_buy_strong_en_modo_defensivo_drawdown", True):
                return f"Modo defensivo por drawdown: {round(drawdown_pct, 2)}%"
    if contexto.get("usar_exposicion_como_bloqueo", True):
        max_exp = contexto.get("max_exposicion_total_pct", 80)
        if exposicion_actual_pct >= max_exp and (senal_bot != "BUY STRONG" or not contexto.get("permitir_buy_strong_sobre_exposicion", False)):
            return f"Exposición abierta ya supera límite: {round(exposicion_actual_pct, 2)}%"
        if exposicion_resultante_pct > max_exp and (senal_bot != "BUY STRONG" or not contexto.get("permitir_buy_strong_sobre_exposicion", False)):
            return f"Exposición resultante superaría límite: {round(exposicion_resultante_pct, 2)}%"
    if contexto.get("usar_riesgo_abierto_como_bloqueo", True):
        max_risk = contexto.get("max_riesgo_total_abierto_pct", 10)
        if riesgo_actual_pct >= max_risk and (senal_bot != "BUY STRONG" or not contexto.get("permitir_buy_strong_sobre_riesgo", False)):
            return f"Riesgo abierto ya supera límite: {round(riesgo_actual_pct, 2)}%"
        if riesgo_resultante_pct > max_risk and (senal_bot != "BUY STRONG" or not contexto.get("permitir_buy_strong_sobre_riesgo", False)):
            return f"Riesgo resultante superaría límite: {round(riesgo_resultante_pct, 2)}%"
    return ""

def actualizar_contexto_reglas_operativas_(contexto, posicion):
    capital = _safe_num_(contexto.get("capital_operativo"), CONFIG_SIMULACION.get("capital_inicial", 5000.0))
    contexto["exposicion_abierta_usd"] = _safe_num_(contexto.get("exposicion_abierta_usd"),0) + _safe_num_(posicion.get("posicion_usd"),0)
    contexto["riesgo_abierto_usd"] = _safe_num_(contexto.get("riesgo_abierto_usd"),0) + _safe_num_(posicion.get("riesgo_usd"),0)
    contexto["exposicion_abierta_pct"] = round((contexto["exposicion_abierta_usd"]/capital)*100,2) if capital else 0
    contexto["riesgo_abierto_pct"] = round((contexto["riesgo_abierto_usd"]/capital)*100,2) if capital else 0
    return contexto

def resumen_reglas_operativas_(contexto, bloqueadas):
    motivos = {}
    for b in bloqueadas or []:
        m = str(b.get("motivo","")).strip() or "SIN MOTIVO"
        motivos[m] = motivos.get(m,0)+1
    estado = "NORMAL"
    if contexto.get("drawdown_pct",0) >= contexto.get("bloquear_entradas_drawdown_pct",25): estado = "BLOQUEADO"
    elif (contexto.get("exposicion_abierta_pct",0) >= contexto.get("max_exposicion_total_pct",80) or contexto.get("riesgo_abierto_pct",0) >= contexto.get("max_riesgo_total_abierto_pct",10) or contexto.get("drawdown_pct",0) >= contexto.get("modo_defensivo_drawdown_pct",12)):
        estado = "DEFENSIVO"
    return {
        "version":"V4.4", "estado":estado,
        "exposicion_abierta_pct":round(_safe_num_(contexto.get("exposicion_abierta_pct")),2),
        "riesgo_abierto_pct":round(_safe_num_(contexto.get("riesgo_abierto_pct")),2),
        "drawdown_pct":round(_safe_num_(contexto.get("drawdown_pct")),2),
        "max_exposicion_total_pct":contexto.get("max_exposicion_total_pct"),
        "max_riesgo_total_abierto_pct":contexto.get("max_riesgo_total_abierto_pct"),
        "modo_defensivo_drawdown_pct":contexto.get("modo_defensivo_drawdown_pct"),
        "bloquear_entradas_drawdown_pct":contexto.get("bloquear_entradas_drawdown_pct"),
        "bloqueos_generados":len(bloqueadas or []),
        "motivo_principal":max(motivos, key=motivos.get) if motivos else "SIN BLOQUEOS",
        "reglas_activas":{"exposicion":bool(contexto.get("usar_exposicion_como_bloqueo",True)),"riesgo_abierto":bool(contexto.get("usar_riesgo_abierto_como_bloqueo",True)),"drawdown":bool(contexto.get("usar_drawdown_como_bloqueo",True))},
        "nota":"V4.4 usa métricas existentes como reglas operativas de entrada. No duplica el motor de riesgo."
    }


def actualizar_historial(historial, resultados, mercado):
    """
    Simulación tipo paper tracking:
    - Abre operación cuando aparece BUY STRONG o BUY.
    - Cierra operación si toca stop, objetivo o si la señal se vuelve SELL / EVITAR después de al menos 1 día.
    - No ejecuta órdenes reales. Solo mide si las señales habrían ganado o perdido.
    """

    hoy = hoy_ymd()
    resultados_por_ticker = {r["Accion"]: r for r in resultados}
    operaciones = historial.get("operaciones", [])

    for op in operaciones:
        if op.get("estado") != "ABIERTA":
            continue

        ticker = op.get("accion") or op.get("Accion")
        r = resultados_por_ticker.get(ticker)

        if not r:
            continue

        precio_actual = float(
            r.get("Precio actual", op.get("precio_actual", op.get("precio_entrada", 0))) or 0
        )
        precio_entrada = float(op.get("precio_entrada") or precio_actual or 0)

        if precio_entrada <= 0:
            continue

        ganancia_pct = ((precio_actual / precio_entrada) - 1) * 100

        op["precio_actual"] = round(precio_actual, 2)
        op["ganancia_pct"] = round(ganancia_pct, 2)
        op["dias_abierta"] = dias_desde(op.get("fecha_entrada", hoy))
        op["senal_actual"] = r.get("Senal", "")
        op["senal_bot_actual"] = r.get("Senal Bot", "")
        op["probabilidad_actual"] = r.get("Probabilidad tecnica", 0)
        op["riesgo_actual"] = r.get("Riesgo", "")
        op["mercado_actual"] = r.get("Mercado", mercado.get("estado", "NEUTRO"))
        op["contexto_sector_actual"] = r.get("Contexto sector", "")
        op["volumen_relativo_actual"] = r.get("Volumen relativo", 0)
        op["score_calidad_actual"] = r.get("Score calidad", calcular_score_calidad(r))
        op["max_ganancia_pct"] = round(
            max(float(op.get("max_ganancia_pct", ganancia_pct)), ganancia_pct), 2
        )
        op["max_perdida_pct"] = round(
            min(float(op.get("max_perdida_pct", ganancia_pct)), ganancia_pct), 2
        )

        stop = float(op.get("stop") or 0)
        objetivo = float(op.get("objetivo") or 0)
        senal_bot_actual = r.get("Senal Bot", "")

        cerrar = False
        resultado = "EN SEGUIMIENTO"
        tipo_cierre = ""

        if stop > 0 and precio_actual <= stop:
            cerrar = True
            resultado = "PERDIDA STOP"
            tipo_cierre = "STOP"
        elif objetivo > 0 and precio_actual >= objetivo:
            cerrar = True
            resultado = "GANADA OBJETIVO"
            tipo_cierre = "OBJETIVO"
        elif senal_bot_actual == "SELL / EVITAR" and op.get("dias_abierta", 0) >= 1:
            cerrar = True
            resultado = "GANADA POR SEÑAL" if ganancia_pct >= 0 else "PERDIDA POR SEÑAL"
            tipo_cierre = "SEÑAL SELL"

        if cerrar:
            op["estado"] = "CERRADA"
            op["fecha_cierre"] = hoy
            op["precio_cierre"] = round(precio_actual, 2)
            op["ganancia_pct_final"] = round(ganancia_pct, 2)
            op["resultado"] = resultado
            op["tipo_cierre"] = tipo_cierre
            op["mercado_cierre"] = r.get("Mercado", mercado.get("estado", "NEUTRO"))
            op["contexto_sector_cierre"] = r.get("Contexto sector", "")
        else:
            op["resultado"] = resultado

    abiertas = {op.get("accion") for op in operaciones if op.get("estado") == "ABIERTA"}
    creadas_hoy = {(op.get("accion"), op.get("fecha_entrada")) for op in operaciones}
    cerradas_previas = [op for op in operaciones if op.get("estado") == "CERRADA"]
    rachas_previas = calcular_rachas(cerradas_previas)
    nuevas_bloqueadas = []
    contexto_reglas_operativas = calcular_contexto_reglas_operativas_(operaciones, mercado)

    for r in resultados:
        ticker = r.get("Accion")
        senal_bot = r.get("Senal Bot")
        riesgo = r.get("Riesgo")
        rr = float(r.get("R/R") or 0)

        motivo_bloqueo = ""

        if senal_bot not in ["BUY STRONG", "BUY"]:
            continue

        if ticker in abiertas:
            continue
        elif (ticker, hoy) in creadas_hoy:
            continue

        precio = float(r.get("Precio actual") or 0)
        posicion = calcular_posicion(CONFIG_SIMULACION["capital_inicial"], precio, r.get("Stop loss"))

        if riesgo == "ALTO":
            motivo_bloqueo = "Riesgo alto"
        elif rr < CONFIG_SIMULACION["rr_minimo"]:
            motivo_bloqueo = f"R/R menor a {CONFIG_SIMULACION['rr_minimo']}"
        elif len(abiertas) >= CONFIG_SIMULACION["max_operaciones_abiertas"]:
            motivo_bloqueo = "Máximo de operaciones abiertas alcanzado"
        elif rachas_previas.get("racha_actual_tipo") == "PERDIDAS" and rachas_previas.get("racha_actual", 0) >= CONFIG_SIMULACION["bloquear_si_perdidas_seguidas"]:
            motivo_bloqueo = "Sistema pausado por racha de pérdidas"
        elif rachas_previas.get("racha_actual_tipo") == "PERDIDAS" and rachas_previas.get("racha_actual", 0) >= CONFIG_SIMULACION["pausar_si_perdidas_seguidas"] and senal_bot != "BUY STRONG":
            motivo_bloqueo = "Modo defensivo por racha de pérdidas"
        elif mercado.get("estado") == "DÉBIL" and (senal_bot != "BUY STRONG" or not CONFIG_SIMULACION["permitir_buy_strong_en_mercado_debil"]):
            motivo_bloqueo = "Mercado débil"
        elif float(r.get("Volumen relativo") or 0) < CONFIG_SIMULACION["volumen_relativo_minimo"]:
            motivo_bloqueo = "Volumen relativo bajo"
        elif r.get("Confirmacion") == "BAJA":
            motivo_bloqueo = "Confirmación baja"
        elif r.get("Contexto sector") == "NO ACOMPAÑA":
            motivo_bloqueo = "Sector no acompaña"
        else:
            motivo_bloqueo = evaluar_reglas_operativas_candidato_(r, posicion, contexto_reglas_operativas, senal_bot)

        if motivo_bloqueo:
            nuevas_bloqueadas.append({
                "fecha": hoy,
                "accion": ticker,
                "senal_bot": senal_bot,
                "motivo": motivo_bloqueo,
                "rr": rr,
                "riesgo": riesgo,
                "score": r.get("Score calidad", 0),
                "precio": precio,
                "exposicion_abierta_pct": contexto_reglas_operativas.get("exposicion_abierta_pct", 0),
                "riesgo_abierto_pct": contexto_reglas_operativas.get("riesgo_abierto_pct", 0),
                "drawdown_pct": contexto_reglas_operativas.get("drawdown_pct", 0),
                "regla_operativa": motivo_bloqueo.startswith(("Exposición", "Riesgo", "Bloqueo operativo", "Modo defensivo")),
            })
            continue


        nueva = {
            "id": f"{hoy}-{ticker}",
            "fecha_entrada": hoy,
            "accion": ticker,
            "sector": r.get("Sector", "Otro"),
            "senal_entrada": r.get("Senal", ""),
            "senal_bot_entrada": senal_bot,
            "probabilidad_entrada": r.get("Probabilidad tecnica", 0),
            "riesgo_entrada": riesgo,
            "precio_entrada": round(precio, 2),
            "precio_actual": round(precio, 2),
            "entrada_min": r.get("Entrada min"),
            "entrada_max": r.get("Entrada max"),
            "stop": r.get("Stop loss"),
            "objetivo": r.get("Objetivo"),
            "rr": r.get("R/R"),
            "estado": "ABIERTA",
            "resultado": "EN SEGUIMIENTO",
            "ganancia_pct": 0,
            "ganancia_pct_final": None,
            "max_ganancia_pct": 0,
            "max_perdida_pct": 0,
            "dias_abierta": 0,
            "senal_actual": r.get("Senal", ""),
            "senal_bot_actual": senal_bot,
            "probabilidad_actual": r.get("Probabilidad tecnica", 0),
            "riesgo_actual": riesgo,
            "mercado_entrada": r.get("Mercado", mercado.get("estado", "NEUTRO")),
            "contexto_sector_entrada": r.get("Contexto sector", ""),
            "volumen_relativo_entrada": r.get("Volumen relativo", 0),
            "score_calidad_entrada": r.get("Score calidad", calcular_score_calidad(r)),
            "score_calidad_actual": r.get("Score calidad", calcular_score_calidad(r)),
            "costo_total_estimado_pct": costo_total_estimado_pct(),
            "posicion_usd_estimada": posicion.get("posicion_usd", 0),
            "posicion_pct_cuenta_estimada": posicion.get("posicion_pct_cuenta", 0),
            "riesgo_usd_estimado": posicion.get("riesgo_usd", 0),
            "riesgo_pct_cuenta_estimado": posicion.get("riesgo_pct_cuenta", 0),
            "distancia_stop_pct": posicion.get("distancia_stop_pct", 0),
            "acciones_estimadas": posicion.get("acciones_estimadas", 0),
            "valor_cartera_usd": posicion.get("posicion_usd", 0),
            "ganancia_abierta_usd_estimada": 0.0,
            "perdida_maxima_stop_usd": posicion.get("riesgo_usd", 0),
            "distancia_stop_actual_pct": distancia_stop_actual_pct(precio, r.get("Stop loss")),
            "distancia_objetivo_pct": distancia_objetivo_pct(precio, r.get("Objetivo")),
        }

        operaciones.append(nueva)
        abiertas.add(ticker)
        creadas_hoy.add((ticker, hoy))
        actualizar_contexto_reglas_operativas_(contexto_reglas_operativas, posicion)

    operaciones = sorted(
        operaciones,
        key=lambda x: (
            1 if x.get("estado") == "ABIERTA" else 0,
            x.get("fecha_entrada", ""),
            x.get("accion", ""),
        ),
        reverse=True,
    )[:300]

    cerradas = [op for op in operaciones if op.get("estado") == "CERRADA"]
    abiertas_ops = [op for op in operaciones if op.get("estado") == "ABIERTA"]
    ganadas = [op for op in cerradas if str(op.get("resultado", "")).startswith("GANADA")]
    perdidas = [op for op in cerradas if str(op.get("resultado", "")).startswith("PERDIDA")]

    win_rate = round((len(ganadas) / len(cerradas)) * 100, 2) if cerradas else 0
    rentabilidad_cerrada = round(sum(float(op.get("ganancia_pct_final") or 0) for op in cerradas), 2)
    rentabilidad_abierta = round(sum(float(op.get("ganancia_pct") or 0) for op in abiertas_ops), 2)
    promedio_cerradas = round(rentabilidad_cerrada / len(cerradas), 2) if cerradas else 0

    avanzadas = calcular_metricas_avanzadas(operaciones, mercado)
    reglas_operativas = resumen_reglas_operativas_(contexto_reglas_operativas, nuevas_bloqueadas)

    resumen = {
        "total_operaciones": len(operaciones),
        "abiertas": len(abiertas_ops),
        "cerradas": len(cerradas),
        "ganadas": len(ganadas),
        "perdidas": len(perdidas),
        "win_rate": win_rate,
        "rentabilidad_cerrada_pct": rentabilidad_cerrada,
        "rentabilidad_abierta_pct": rentabilidad_abierta,
        "promedio_cerradas_pct": promedio_cerradas,
        "nuevas_bloqueadas": nuevas_bloqueadas[:50],
        "reglas_operativas": reglas_operativas,
        "config_simulacion": CONFIG_SIMULACION,
        "nota": "Simulación avanzada paper trading: tamaño de posición, costos estimados, drawdown y riesgo. No ejecuta compras reales.",
    }
    resumen.update(avanzadas)

    historial["actualizado"] = fecha_visible()
    historial["operaciones"] = operaciones
    historial["resumen"] = resumen

    return historial


def _df_limpio(data):
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def guardar_historial(historial):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

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
    resultados = []

    mercado = contexto_mercado()
    print(f"Contexto mercado: {mercado}")

    for ticker in ACCIONES:
        print(f"Analizando {ticker}...")
        r = analizar(ticker, mercado)

        if r:
            resultados.append(r)
            print("OK")
        else:
            print("SIN DATOS")

        time.sleep(0.35)

    for r in resultados:
        r["Score calidad"] = calcular_score_calidad(r)

    resultados = sorted(
        resultados,
        key=lambda x: (
            prioridad_senal(x.get("Senal", "")),
            prioridad_riesgo(x.get("Riesgo", "")),
            prioridad_contexto(x.get("Contexto sector", "")),
            len(x.get("Hot Score", "")),
            x.get("Score calidad", 0),
            x.get("Probabilidad tecnica", 0),
            x.get("Fuerza relativa", 0),
            -x.get("ATR %", 99),
        ),
        reverse=True,
    )

    historial = cargar_historial()
    historial = actualizar_historial(historial, resultados, mercado)
    guardar_historial(historial)

    paper_state = None
    if export_paper_state:
        try:
            paper_state = export_paper_state(historial, resultados, mercado, CONFIG_SIMULACION)
            print("PAPER TRADING V4.4.5 EXPORTADO")
        except Exception as e:
            print("ADVERTENCIA: no se pudo exportar paper trading V4:", e)
    else:
        print("ADVERTENCIA: paper trading engine V4 no disponible:", PAPER_ENGINE_IMPORT_ERROR)

    salida = {
        "actualizado": fecha_visible(),
        "version_bot": "V4.6 METRICAS PRO",
        "contexto_mercado": mercado,
        "config_operativa": resumen_config_operativa(CONFIG_SISTEMA, CONFIG_SIMULACION) if resumen_config_operativa else {"simulation_config": CONFIG_SIMULACION},
        "resultados": resultados,
        "paper_trading": paper_state.get("status", {}) if paper_state else {
            "version": "V4",
            "health": "NO_EXPORT",
            "error": PAPER_ENGINE_IMPORT_ERROR
        },
        "historial": {
            "actualizado": historial.get("actualizado", ""),
            "resumen": historial.get("resumen", {}),
            "operaciones": historial.get("operaciones", [])[:120],
        },
    }

    with open("datos_acciones.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    if EXPORT_XLSX:
        pd.DataFrame(resultados).to_excel("analisis_acciones.xlsx", index=False)

    print("ARCHIVOS GENERADOS")


if __name__ == "__main__":
    main()
