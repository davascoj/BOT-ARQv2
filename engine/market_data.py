"""Bounded batched downloads; daily indicators never masquerade as execution quotes."""
import logging
import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def download_batch(tickers, period="1y", interval="1d"):
    tickers = sorted(set(tickers))
    output = {}
    for offset in range(0, len(tickers), 60):
        group = tickers[offset:offset + 60]
        try:
            frame = yf.download(group, period=period, interval=interval, auto_adjust=interval == "1d",
                                group_by="ticker", actions=True, progress=False, threads=4, timeout=15,
                                prepost=False)
        except Exception as error:
            log.warning("Download batch failed: %s", error)
            continue
        for tk in group:
            try:
                data = frame[tk].copy() if isinstance(frame.columns, pd.MultiIndex) else frame.copy()
                data = data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
                if not data.empty:
                    output[tk] = data
            except (KeyError, ValueError):
                log.warning("No usable %s bars for %s", interval, tk)
        # One sequential retry handles transient cache/rate/concurrency failures without hiding omissions.
        for tk in group:
            if tk in output:
                continue
            try:
                retry = yf.download(tk, period=period, interval=interval, auto_adjust=interval == "1d",
                                    actions=True, progress=False, threads=False, timeout=15, prepost=False)
                if isinstance(retry.columns, pd.MultiIndex):
                    retry.columns = retry.columns.get_level_values(0)
                retry = retry.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
                if not retry.empty:
                    output[tk] = retry
            except Exception as error:
                log.warning("Retry failed for %s: %s", tk, error)
    return output


def execution_quotes(tickers):
    bars = download_batch(tickers, period="1d", interval="1m")
    quotes = {}
    for tk, df in bars.items():
        index = pd.Timestamp(df.index[-1])
        if index.tzinfo is None:
            continue  # no assumed timezone for execution data
        quotes[tk] = {"price": float(df.Close.iloc[-1]), "timestamp": index.isoformat(),
                      "source": "yfinance_1m_unadjusted", "granularity_seconds": 60}
    return quotes
