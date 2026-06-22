# BOT-ARQ · V4.4.5

Sistema gratuito de análisis técnico de acciones con **señales BUY / HOLD / SELL**, **paper trading simulado**, **reglas operativas de riesgo** y un **dashboard web**. Funciona con GitHub Pages + GitHub Actions + Python + JSON + JavaScript. **No ejecuta dinero real.**

> ⚠️ Esta herramienta no garantiza ganancias. Las señales son simuladas y no ejecutan órdenes reales. Confirma siempre precio, volumen y noticias antes de operar, y usa stop loss.

---

## ¿Cómo funciona?

```
GitHub Actions (cada 5 min, mercado abierto)
        │
        ▼
analizador_acciones.py  ──carga──►  config/system_config.json
        │
        ├─ analiza el mercado y las acciones (yfinance)
        ├─ actualiza el historial persistente (historial_senales.json)
        ├─ exporta el paper trading (engine/paper_trading_engine.py → paper/*.json)
        └─ escribe datos_acciones.json
        │
        ▼
GitHub Pages sirve index.html + script.js + style.css
        │
        ▼
El dashboard lee datos_acciones.json y paper/paper_state.json
```

El **dashboard solo consume dos archivos**: `datos_acciones.json` y `paper/paper_state.json`. El resto de `paper/*.json` son derivados para auditoría/trazabilidad.

---

## Estructura del dashboard (layout A–H)

| Bloque | Contenido |
|--------|-----------|
| A. Barra superior | nombre, versión, modo paper, broker OFF, estado de carga, reloj de mercado |
| B. Panel ejecutivo | capital total, G/P total, operaciones abiertas, exposición, riesgo, estado operativo |
| C. Estado del mercado | SPY, QQQ, tendencia, score |
| D. Reglas operativas V4.4 | exposición / riesgo / drawdown actual vs límite (con barras) + motivo |
| Alertas | alertas críticas y warnings |
| E. Top oportunidades | mejores BUY/BUY STRONG con riesgo bajo/medio (incluye R/R) |
| F. Cartera abierta | posiciones paper: entrada, precio, G/P, stop, objetivo, riesgo |
| G. Auditoría de bloqueos | señales BUY que el bot no abrió y por qué |
| Riesgo y desempeño | profit factor, win rate, drawdown, diagnóstico |
| H. Vistas avanzadas | Paper Trading Engine, curva de capital, métricas, ranking, historial, configuración técnica |

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `analizador_acciones.py` | Motor principal de análisis y señales |
| `engine/config_loader.py` | Carga la configuración real del motor |
| `engine/paper_trading_engine.py` | Exporta el paper trading a `paper/*.json` |
| `config/system_config.json` | Configuración operativa (capital, riesgo, límites) |
| `config/VERSION_ACTUAL.json` | Versión y cambios de la versión vigente |
| `index.html`, `script.js`, `style.css` | Dashboard web |
| `.github/workflows/analizar.yml` | Automatización (cron + manual) |

### Datos generados

- **Se versionan:** `datos_acciones.json`, `historial_senales.json` (estado persistente del motor) y `paper/*.json`.
- **`*.xlsx`:** se generan en cada corrida pero la web no los usa. **Recomendado dejar de versionarlos** (requiere una edición manual del workflow; ver `docs/CHANGELOG.md`).
- **No editar a mano** ningún archivo generado: los reescribe GitHub Actions.

---

## Uso

El sistema es automático: GitHub Actions corre cada 5 minutos en horario de mercado (NYSE) y publica los datos. Para forzar una actualización manual: pestaña **Actions → "BOT-ARQ" → Run workflow** con `force=true`.

---

## Seguridad

- No ejecuta dinero real. **Broker real: OFF.**
- Todo es paper trading / simulación.
- Las reglas operativas V4.4 usan métricas existentes; no hay un risk engine paralelo.

Roadmap y detalle de cambios: `docs/ROADMAP.md` y `docs/CHANGELOG.md`.
