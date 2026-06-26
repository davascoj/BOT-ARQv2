"""
BOT-ARQ V4.7 - Descarga y cache de OHLCV histórico para el backtest.

Usa yfinance (mismo data source que el live) con auto_adjust=True (precios
ajustados por splits/dividendos) y cachea cada ticker en parquet para que el
backtest sea reproducible y no descargue dos veces lo mismo.
"""
from pathlib import Path

CACHE_DIR = Path("backtest/_cache")


def _normalizar(df):
    """Aplana columnas MultiIndex de yfinance y deja Open/High/Low/Close/Volume."""
    import pandas as pd
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in cols):
        return None
    return df[cols].dropna()


def descargar_ohlcv(tickers, periodo="3y", usar_cache=True, log=print):
    """Descarga OHLCV para una lista de tickers.

    Devuelve dict[ticker -> DataFrame]. Cachea cada ticker en parquet
    (backtest/_cache/<ticker>_<periodo>.parquet). Los tickers que fallan o
    no traen datos se omiten (se informa por log).
    """
    import yfinance as yf
    import pandas as pd
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    omitidos = []
    for tk in tickers:
        cache_file = CACHE_DIR / f"{tk.replace('/', '_').replace('=', '_')}_{periodo}.parquet"
        if usar_cache and cache_file.exists():
            try:
                out[tk] = pd.read_parquet(cache_file)
                continue
            except Exception:
                pass
        try:
            df = yf.download(tk, period=periodo, interval="1d",
                             auto_adjust=True, progress=False, threads=False)
            df = _normalizar(df)
        except Exception as e:
            df = None
            if log:
                log(f"  ! {tk}: error descarga ({e})")
        if df is not None and not df.empty:
            try:
                df.to_parquet(cache_file)
            except Exception:
                pass
            out[tk] = df
        else:
            omitidos.append(tk)
    if omitidos and log:
        log(f"  Omitidos por falta de datos: {len(omitidos)} ({', '.join(omitidos[:8])}{'...' if len(omitidos) > 8 else ''})")
    return out
