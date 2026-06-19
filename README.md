# BOT-ARQ v3 - Real migrado desde V2

Sistema automatizado de análisis técnico, señales simuladas y seguimiento de cartera.

Esta versión V3 conserva el motor real de V2 y agrega estructura profesional para evolucionar hacia:
- arquitectura modular
- risk engine más fuerte
- paper trading
- futura conexión con broker real

## Estado

✅ Dashboard GitHub Pages  
✅ GitHub Actions cada 5 minutos en horario de mercado  
✅ Análisis con yfinance  
✅ Ranking técnico  
✅ Señales BUY / SELL / HOLD  
✅ Simulación de cartera  
✅ Historial de señales  
✅ Métricas avanzadas  
✅ Preparación inicial para broker adapter  

## Archivos principales

- `analizador_acciones.py` → motor real del bot
- `datos_acciones.json` → datos para dashboard
- `historial_senales.json` → historial de simulación
- `index.html` → dashboard
- `script.js` → lógica visual del dashboard
- `style.css` → estilos
- `.github/workflows/analizar.yml` → automatización

## Carpetas nuevas V3

- `docs/` → arquitectura y guía de implementación
- `config/` → configuración base
- `engine/` → preparación para modularizar el motor
- `execution/` → preparación para broker/paper trading
- `scripts/` → ejecución local

## Importante

Este sistema NO ejecuta órdenes reales.  
Las señales son simuladas.  
Antes de dinero real, debe validarse durante varios meses en paper trading.

## Implementación

Ver:

- `docs/PASO_A_PASO_IMPLEMENTACION.md`
- `docs/ARQUITECTURA_V3.md`
