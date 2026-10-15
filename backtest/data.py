"""Versioned daily cache with expiry, explicit adjustment semantics and provenance."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from engine.storage import atomic_json, read_json

CACHE_DIR = Path("backtest/_cache")
CACHE_TTL_SECONDS = 86400


def _normalizar(df):
    import pandas as pd
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df for c in cols):
        return None
    return df[cols].dropna().sort_index()


def descargar_ohlcv(tickers, periodo="3y", usar_cache=True, log=print):
    import pandas as pd
    import yfinance as yf
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = {}
    for tk in sorted(set(tickers)):
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tk)
        if not re.fullmatch(r"(1mo|3mo|6mo|1y|2y|3y|5y|10y|max)", periodo):
            raise ValueError("Periodo no admitido")
        path = CACHE_DIR / f"{safe}_{periodo}_adjusted_v5.parquet"
        meta = path.with_suffix(".meta.json")
        if usar_cache and path.exists() and meta.exists():
            info = read_json(meta)
            if (time.time() - info["downloaded_epoch"] < CACHE_TTL_SECONDS
                    and info["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()):
                output[tk] = pd.read_parquet(path)
                continue
        df = _normalizar(yf.download(tk, period=periodo, interval="1d", auto_adjust=True,
                                    progress=False, threads=False, timeout=15))
        if df is None or df.empty:
            if log:
                log(f"Sin datos: {tk}")
            continue
        # Cache failure is explicit: results must not silently pretend to be reproducible.
        df.to_parquet(path, index=True)
        atomic_json(meta, {"ticker": tk, "period": periodo, "interval": "1d", "auto_adjust": True,
                           "downloaded_at": datetime.now(timezone.utc).isoformat(),
                           "downloaded_epoch": time.time(), "source": "yfinance", "version": yf.__version__,
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        output[tk] = df
    return output
