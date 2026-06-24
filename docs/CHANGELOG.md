# Changelog

## V4.4.5 Limpieza de repositorio y documentación
- Reportes `*.xlsx` ahora **opt-in** (`BOT_ARQ_EXPORT_XLSX=1`): por defecto el motor no los genera, así CI deja de commitear binarios que causaban conflictos en GitHub Desktop. Se quitaron del versionado con `git rm --cached` y se añadió `*.xlsx` a `.gitignore`. No requiere editar el workflow (si el archivo no existe, el paso `git add` simplemente lo omite).
- `historial_senales.json` se conserva versionado: es el estado persistente que el motor lee entre corridas.
- Archiva la documentación obsoleta de instalación por ZIP en `docs/archive/`.
- README reescrito; ROADMAP y CURRENT_ARCHITECTURE actualizados a la arquitectura real.

## V4.4.4 Rendimiento y refresh inteligente
- Refresh cada 5 minutos (alineado con GitHub Actions) y omisión de repintado si no cambió la fecha de datos.
- Cache-busting por versión para `script.js` y `style.css`; bucket de 5 minutos para los datos (en vez de `Date.now()` por petición).
- Debounce en las búsquedas de ranking e historial.
- `paper_state.json` ligero: ya no embebe los arrays completos de `orders`/`trades` (su detalle vive en `paper_orders.json` y `paper_trades.json`). Pasa de ~556 KB a ~72 KB. Solo cambia la serialización; no toca el risk engine.

## V4.4.3 Profesionalización visual base
- Nuevo layout A–H y jerarquía visual tipo terminal financiera.
- Elimina métricas duplicadas; broker, modo y versión viven solo en la barra superior.
- Nuevo panel "Estado del mercado"; reglas operativas con barras actual vs límite.
- Top oportunidades añade R/R; cartera abierta muestra entrada, precio, stop, objetivo y riesgo.
- Auditoría de bloqueos muestra score, regla operativa, exposición, riesgo y drawdown.
- Formato consistente de moneda/porcentaje/decimales.
- Blindaje de carga (guards null, diagnóstico de carga visible) y coherencia de versión en HTML/JS/config/motor.

## V4.4.1 Hotfix Dashboard Cargando
- Corrige error JS que dejaba la página en Cargando.
- Agrega protección por secciones de renderizado.
- Mantiene intacta la lógica del motor V4.4.

## V4.4 Reglas Operativas
- Exposición, riesgo abierto y drawdown pasan a reglas operativas.
- Nuevo panel `Reglas operativas V4.4`.
- Nuevo archivo `paper/paper_operational_rules.json`.
- No se duplica risk engine; usa métricas existentes.

## V4.3 Auditoría de Bloqueos
- Nuevo paper_audit.json derivado de nuevas_bloqueadas.
- Nuevo panel visual para explicar señales bloqueadas.
- No crea lógica de riesgo paralela.

## V4.2.2 Lazy Render Performance
- Ranking, historial y métricas avanzadas se cargan al abrir.
- Menos DOM inicial y mejor velocidad percibida.

## V4.2.1 Visual Fix Dashboard
- Corrige columnas vacías en Top oportunidades.
- Corrige Score visual.
- No toca motor Python.

## V4.2 Configuración Real del Motor
- Se agregó `config/system_config.json`.
- Se agregó `engine/config_loader.py`.
- `CONFIG_SIMULACION` ahora se carga desde JSON.
- `datos_acciones.json` ahora exporta `config_operativa`.
- Configuraciones antiguas se movieron a `config/archive/`.

## V4.1 Dashboard Cleanup Pro
- Dashboard más limpio.
- Panel ejecutivo.
- Alertas arriba.
- Vistas avanzadas desplegables.

## V4 Paper Trading Engine
- Formalización del paper trading.
- Archivos `paper/*.json`.

## V3
- Migración segura desde V2.
