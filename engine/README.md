# Engine BOT-ARQ v3

Esta carpeta queda preparada para la evolución modular del motor.

En esta versión V3 real migrada, el motor productivo se conserva en:

- `../analizador_acciones.py`

No se movió todavía para evitar romper:
- GitHub Actions
- GitHub Pages
- generación de `datos_acciones.json`
- generación de `historial_senales.json`
- generación de archivos Excel

## Fase siguiente recomendada

Separar `analizador_acciones.py` en módulos:

- `market_data.py`
- `indicators.py`
- `strategy.py`
- `risk.py`
- `portfolio.py`
- `history.py`
- `exporter.py`
