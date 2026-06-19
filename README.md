# BOT-ARQ v4.4.1 - Hotfix Dashboard Cargando

Incluye V4.2.1 y V4.2.2. Agrega auditoría visual de señales bloqueadas usando lógica existente del bot.

---


Mejora de rendimiento visual. Incluye V4.2.1. No cambia el motor de trading.

---


Corrección visual del dashboard. No cambia el motor Python; corrige cómo se muestran los datos en Top oportunidades.

---


Sistema automatizado de análisis técnico, señales simuladas, paper trading y dashboard web.

## Estado actual

✅ GitHub Pages  
✅ GitHub Actions cada 5 minutos  
✅ Señales BUY / HOLD / SELL  
✅ Compra y venta simulada  
✅ Cierre por stop / objetivo / señal  
✅ Paper Trading Engine  
✅ Dashboard V4.1 limpio  
✅ Configuración real desde `config/system_config.json`  

## Cambio principal de V4.2

Antes, las reglas del bot estaban principalmente dentro de `analizador_acciones.py`.

Ahora la configuración operativa está en:

`config/system_config.json`

El código mantiene valores por defecto seguros si el archivo falta o tiene error.

## Archivos importantes

- `analizador_acciones.py`: motor principal.
- `engine/config_loader.py`: carga configuración real.
- `engine/paper_trading_engine.py`: exporta paper trading.
- `config/system_config.json`: configuración operativa.
- `paper/*.json`: datos paper derivados.
- `index.html`, `script.js`, `style.css`: dashboard.
- `.github/workflows/analizar.yml`: automatización.

## Documentación

- `docs/V4_2_CONFIGURACION_REAL_MOTOR.md`
- `docs/PASO_A_PASO_V4_2.md`
- `docs/CURRENT_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`

## Seguridad

No ejecuta dinero real.  
Broker real sigue OFF.  
Este sistema continúa en paper trading / simulación.


---

## V4.4 Reglas Operativas

Esta versión convierte métricas existentes en decisiones operativas configurables:

- Exposición abierta.
- Riesgo abierto.
- Drawdown.
- Modo defensivo.
- Bloqueo de entradas.

Nuevo archivo:

- `paper/paper_operational_rules.json`

Nueva sección en dashboard:

- `Reglas operativas V4.4`

No ejecuta dinero real.


---

## V4.4.1 Hotfix Dashboard Cargando

Corrección crítica visual:

- Se corrige un error en `script.js` que podía detener toda la página antes de cargar datos.
- Se elimina una asignación accidental de `operationalRulesV44` antes de su declaración.
- Se agrega protección por secciones para que, si una tarjeta falla, el resto del dashboard siga cargando.

No cambia el motor de análisis ni las reglas operativas V4.4.
