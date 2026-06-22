# Paso a paso para implementar BOT-ARQ V4.2

## Opción limpia recomendada

Como quieres borrar adecuadamente el repositorio local y dejar solo esta versión:

1. Abre GitHub Desktop.
2. Asegúrate de tener el repositorio clonado.
3. Abre la carpeta local con:
   `Repository → Show in Explorer`.

## 1. No borrar `.git`

Dentro de la carpeta del repositorio puedes borrar los archivos visibles del proyecto viejo, pero NO borres:

`.git`

Esa carpeta suele estar oculta.

## 2. Limpieza segura

Puedes borrar carpetas/archivos visibles como:

- `.github`
- `config`
- `docs`
- `engine`
- `execution`
- `paper`
- `scripts`
- `analizador_acciones.py`
- `index.html`
- `script.js`
- `style.css`
- `README.md`
- `requirements.txt`
- JSON/XLSX del proyecto

Pero no borres `.git`.

## 3. Pegar V4.2

Descomprime `BOT-ARQv4_2_CONFIGURACION_REAL_MOTOR.zip`.

Entra a la carpeta descomprimida y copia todo su contenido.

Pégalo en la raíz del repositorio local.

Debe quedar así:

- `.github/`
- `config/`
- `docs/`
- `engine/`
- `execution/`
- `paper/`
- `scripts/`
- `analizador_acciones.py`
- `index.html`
- `script.js`
- `style.css`
- `requirements.txt`
- `README.md`

## 4. GitHub Desktop

En GitHub Desktop:

Commit:
`Subir BOT-ARQ V4.2 Configuración Real del Motor`

Luego:
`Push origin`

## 5. Ejecutar Actions

GitHub → Actions → `BOT-ARQ v4.2 - Configuración Real del Motor` → Run workflow → force=true.

## 6. Verificar

Después de correr, revisa:

- `datos_acciones.json` debe incluir `version_bot: V4.2 CONFIGURACION REAL DEL MOTOR`
- `datos_acciones.json` debe incluir `config_operativa`
- la web debe seguir funcionando igual o mejor
- los archivos `paper/*.json` deben actualizarse

## 7. Cambiar configuración

Para cambiar comportamiento del bot, modifica:

`config/system_config.json`

Ejemplo:
- subir o bajar `max_operaciones_abiertas`
- cambiar `rr_minimo`
- cambiar `volumen_relativo_minimo`
- cambiar costos estimados
