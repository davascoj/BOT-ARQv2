import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "analizador_acciones.py"

print("Ejecutando BOT-ARQ v4 Paper Trading Engine desde:", ROOT)
result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
raise SystemExit(result.returncode)
