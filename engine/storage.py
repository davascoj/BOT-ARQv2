"""Strict durable JSON; corrupt input must stop the run, not reset capital."""
import json
import os
import tempfile
from pathlib import Path


def read_json(path):
    def reject(value):
        raise ValueError(f"Non-finite JSON: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject)


def atomic_json(path, value):
    path = Path(path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
