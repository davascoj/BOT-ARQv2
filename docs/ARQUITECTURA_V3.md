# BOT-ARQ v3 - Arquitectura real migrada desde V2

## Objetivo

Evolucionar el repositorio V2 sin perder funcionalidad.

Esta V3 conserva el motor real que ya funciona:

- `analizador_acciones.py`
- `datos_acciones.json`
- `historial_senales.json`
- `index.html`
- `script.js`
- `style.css`
- `.github/workflows/analizar.yml`

Y agrega estructura profesional para crecer hacia:

- motor modular
- gestión de riesgo más robusta
- paper trading
- conexión futura con broker real

## Flujo actual

GitHub Actions
→ ejecuta `analizador_acciones.py`
→ descarga datos con yfinance
→ calcula señales y ranking
→ actualiza `datos_acciones.json`
→ actualiza historial
→ GitHub Pages muestra `index.html`

## Capas del sistema

### 1. Data Layer

Actualmente dentro de `analizador_acciones.py`.

Responsable de:
- descargar precios
- calcular contexto de mercado
- usar SPY/QQQ
- evaluar sectores

### 2. Strategy Engine

Actualmente dentro de `analizador_acciones.py`.

Responsable de:
- score
- BUY / SELL / HOLD
- COMPRA FUERTE
- VIGILAR
- NO COMPRAR

### 3. Risk Engine

Actualmente mezclado en el motor.

Responsable de:
- stop
- objetivo
- R/R
- riesgo por operación
- exposición abierta

### 4. Portfolio / Simulation

Actualmente usa:
- `historial_senales.json`
- `historial_senales.xlsx`

Responsable de:
- operaciones abiertas
- operaciones cerradas
- profit factor
- drawdown
- rentabilidad
- cartera abierta

### 5. Dashboard

Actualmente:
- `index.html`
- `script.js`
- `style.css`

Responsable de:
- mostrar resultados
- filtros
- resumen de cartera
- historial
- métricas avanzadas

## Por qué no se partió todo el código todavía

Porque el archivo `analizador_acciones.py` ya es el motor productivo de la V2.
Moverlo sin pruebas podría romper GitHub Actions y la página actual.

La V3 real se entrega como migración segura:
- conserva lo que ya funciona
- agrega estructura profesional
- deja lista la fase de refactor modular
