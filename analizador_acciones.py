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

ACCIONES_INFO = {
    "NVDA": "IA / Chips", "AMD": "IA / Chips", "MSFT": "Tecnología",
    "AVGO": "IA / Chips", "AAPL": "Tecnología", "META": "Tecnología",
    "AMZN": "Tecnología", "GOOGL": "Tecnología", "TSLA": "Autos / Tech",
    "PLTR": "IA / Software", "SMCI": "Servidores IA", "MU": "Memoria / Chips",
    "ARM": "Chips", "QCOM": "Chips", "INTC": "Chips", "TSM": "Chips",
    "ASML": "Chips", "AMAT": "Equipos chips", "LRCX": "Equipos chips",
    "KLAC": "Equipos chips", "SOFI": "Fintech", "COIN": "Cripto / Trading",
    "HOOD": "Trading", "PYPL": "Pagos", "SQ": "Pagos", "XOM": "Energía",
    "CVX": "Energía", "OXY": "Energía", "SLB": "Energía",
    "SPY": "ETF Mercado", "QQQ": "ETF Nasdaq", "SOXX": "ETF Chips",
    "RKLB": "Espacial", "IONQ": "Computación cuántica",
    "SOUN": "IA", "AI": "IA", "UPST": "Fintech IA"
}

ACCIONES = list(ACCIONES_INFO.keys())


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


def contexto_mercado():
    """Calcula un filtro general de mercado usando SPY y QQQ."""
    try:
        spy = descargar("SPY", "1y")
        qqq = descargar("QQQ", "1y")
        if spy.empty or qqq.empty or len(spy) < 220 or len(qqq) < 220:
            return {"estado": "NEUTRO", "score": 0, "spy20": 0, "qqq20": 0}

        def evaluar(df):
            close = df["Close"]
            precio = numero(close.iloc[-1])
            ma20 = numero(close.rolling(20).mean().iloc[-1])
            ma50 = numero(close.rolling(50).mean().iloc[-1])
            ma200 = numero(close.rolling(200).mean().iloc[-1])
            mom20 = cambio_pct(close, 20)
            pts = 0
            if precio > ma20:
                pts += 1
            if ma20 > ma50:
                pts += 1
            if ma50 > ma200:
                pts += 1
            if mom20 > 0:
                pts += 1
            return pts, mom20

        spy_pts, spy20 = evaluar(spy)
        qqq_pts, qqq20 = evaluar(qqq)
        total = spy_pts + qqq_pts

        if total >= 7:
            estado = "ALCISTA"
            score = 8
        elif total >= 5:
            estado = "NEUTRO +"
            score = 4
        elif total >= 3:
            estado = "NEUTRO"
            score = 0
        else:
            estado = "DÉBIL"
            score = -8

        return {
            "estado": estado,
            "score": score,
            "spy20": round(spy20, 2),
            "qqq20": round(qqq20, 2),
        }
    except Exception as e:
        print(f"ERROR contexto mercado: {e}")
        return {"estado": "NEUTRO", "score": 0, "spy20": 0, "qqq20": 0}


def analizar(ticker, mercado):
    try:
        df = descargar(ticker, "1y")
        if df.empty or len(df) < 220:
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

        necesarios = [precio, ma10, ma20, ma50, ma200, rsi, volumen_actual, volumen_prom, max20, min20, atr, macd_val, macd_sig, macd_hist_val, macd_hist_prev]
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

        score += mercado.get("score", 0)
        if mercado.get("estado") in ["ALCISTA", "NEUTRO +"]:
            razones.append(f"Mercado {mercado.get('estado')}")
        elif mercado.get("estado") == "DÉBIL":
            alertas.append("Mercado débil")

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
            razones.append("MACD mejorando")
        else:
            score -= 5
            alertas.append("MACD sin confirmar")

        if macd_hist_val > macd_hist_prev:
            score += 4
            razones.append("Histograma MACD mejora")
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

        hot_score = 0
        if score >= 82:
            hot_score += 1
        if volumen_relativo >= 1.25:
            hot_score += 1
        if 1 <= momentum_5d <= 8:
            hot_score += 1
        if fuerza_relativa > 0:
            hot_score += 1
        if riesgo != "ALTO":
            hot_score += 1

        if hot_score >= 5:
            hot = "🔥🔥🔥"
        elif hot_score == 4:
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

        if score >= 84 and riesgo != "ALTO" and confirmacion == "ALTA" and mercado.get("estado") != "DÉBIL":
            senal = "COMPRA FUERTE"
            senal_bot = "BUY STRONG"
        elif score >= 74 and riesgo != "ALTO" and mercado.get("estado") != "DÉBIL":
            senal = "POSIBLE COMPRA"
            senal_bot = "BUY"
        elif score >= 58:
            senal = "VIGILAR"
            senal_bot = "HOLD"
        else:
            senal = "NO COMPRAR"
            senal_bot = "SELL / EVITAR"

        return {
            "Accion": ticker,
            "Sector": ACCIONES_INFO.get(ticker, "Otro"),
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


def actualizar_historial(historial, resultados):
    """
    Simulación tipo paper tracking:
    - Abre operación cuando aparece BUY STRONG o BUY.
    - Cierra operación si toca stop, objetivo o si la señal se vuelve SELL / EVITAR después de al menos 1 día.
    - No ejecuta órdenes reales. Solo mide si las señales habrían ganado o perdido.
    """
    hoy = hoy_ymd()
    resultados_por_ticker = {r["Accion"]: r for r in resultados}
    operaciones = historial.get("operaciones", [])

    # Actualizar operaciones abiertas.
    for op in operaciones:
        if op.get("estado") != "ABIERTA":
            continue

        ticker = op.get("accion") or op.get("Accion")
        r = resultados_por_ticker.get(ticker)
        if not r:
            continue

        precio_actual = float(r.get("Precio actual", op.get("precio_actual", op.get("precio_entrada", 0))) or 0)
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
        op["max_ganancia_pct"] = round(max(float(op.get("max_ganancia_pct", ganancia_pct)), ganancia_pct), 2)
        op["max_perdida_pct"] = round(min(float(op.get("max_perdida_pct", ganancia_pct)), ganancia_pct), 2)

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
        else:
            op["resultado"] = resultado

    abiertas = {op.get("accion") for op in operaciones if op.get("estado") == "ABIERTA"}
    creadas_hoy = {(op.get("accion"), op.get("fecha_entrada")) for op in operaciones}

    # Crear nuevas operaciones simuladas con señales BUY.
    for r in resultados:
        ticker = r.get("Accion")
        senal_bot = r.get("Senal Bot")
        riesgo = r.get("Riesgo")
        rr = float(r.get("R/R") or 0)

        if senal_bot not in ["BUY STRONG", "BUY"]:
            continue
        if riesgo == "ALTO":
            continue
        if rr < 1.30:
            continue
        if ticker in abiertas:
            continue
        if (ticker, hoy) in creadas_hoy:
            continue

        precio = float(r.get("Precio actual") or 0)
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
        }
        operaciones.append(nueva)
        abiertas.add(ticker)
        creadas_hoy.add((ticker, hoy))

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
        "nota": "Simulación con una unidad igual por operación; no ejecuta compras reales.",
    }

    historial["actualizado"] = fecha_visible()
    historial["operaciones"] = operaciones
    historial["resumen"] = resumen
    return historial


def guardar_historial(historial):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

    ops = historial.get("operaciones", [])
    if ops:
        pd.DataFrame(ops).to_excel(HISTORIAL_XLSX, index=False)
    else:
        pd.DataFrame(columns=["fecha_entrada", "accion", "estado", "resultado"]).to_excel(HISTORIAL_XLSX, index=False)


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
        time.sleep(1)

    resultados = sorted(
        resultados,
        key=lambda x: (
            prioridad_senal(x.get("Senal", "")),
            prioridad_riesgo(x.get("Riesgo", "")),
            len(x.get("Hot Score", "")),
            x.get("Probabilidad tecnica", 0),
            x.get("Fuerza relativa", 0),
            -x.get("ATR %", 99),
        ),
        reverse=True,
    )

    historial = cargar_historial()
    historial = actualizar_historial(historial, resultados)
    guardar_historial(historial)

    salida = {
        "actualizado": fecha_visible(),
        "contexto_mercado": mercado,
        "resultados": resultados,
        "historial": {
            "actualizado": historial.get("actualizado", ""),
            "resumen": historial.get("resumen", {}),
            "operaciones": historial.get("operaciones", [])[:120],
        },
    }

    with open("datos_acciones.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    pd.DataFrame(resultados).to_excel("analisis_acciones.xlsx", index=False)
    print("ARCHIVOS GENERADOS")


if __name__ == "__main__":
    main()
