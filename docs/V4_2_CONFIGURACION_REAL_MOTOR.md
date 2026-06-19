# BOT-ARQ V4.2 - Configuración Real del Motor

## Objetivo

Antes de V4.2, los parámetros reales del motor estaban principalmente dentro de `analizador_acciones.py` en `CONFIG_SIMULACION`.

En V4.2, el motor carga su configuración desde:

`config/system_config.json`

Esto permite cambiar parámetros sin tocar el código principal.

## Qué controla ahora `system_config.json`

La sección principal es:

`simulation_config`

Controla:

- `capital_inicial`
- `riesgo_por_operacion_pct`
- `max_posicion_pct`
- `max_operaciones_abiertas`
- `max_exposicion_total_pct`
- `comision_por_operacion_pct`
- `slippage_pct`
- `spread_pct`
- `pausar_si_perdidas_seguidas`
- `bloquear_si_perdidas_seguidas`
- `rr_minimo`
- `volumen_relativo_minimo`
- `permitir_buy_strong_en_mercado_debil`

## Seguridad

Si el archivo no existe o tiene errores, el bot usa valores por defecto seguros definidos en `DEFAULT_CONFIG_SIMULACION`.

## Qué NO cambia

V4.2 no crea un motor paralelo.
No duplica señales.
No duplica paper trading.
No cambia dinero real.

Solo hace que la configuración existente sea realmente operativa.
