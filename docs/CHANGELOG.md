# Changelog

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
- Workflow actualizado a V4.2.

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
