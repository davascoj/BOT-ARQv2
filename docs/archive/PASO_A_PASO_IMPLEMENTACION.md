# Paso a paso para implementar BOT-ARQ v3 real

## Opción recomendada: crear repositorio nuevo

1. Crear un repositorio nuevo en GitHub, por ejemplo:
   `BOT-ARQv3`

2. Descomprimir este ZIP en tu computador.

3. Subir TODO el contenido descomprimido al repositorio.
   No subas el ZIP como archivo único.

4. Verificar que existan estos archivos en la raíz:
   - `index.html`
   - `script.js`
   - `style.css`
   - `analizador_acciones.py`
   - `datos_acciones.json`
   - `historial_senales.json`
   - `.github/workflows/analizar.yml`
   - `requirements.txt`

5. Ir a GitHub → Settings → Pages.

6. Configurar:
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /root

7. Ir a Actions y habilitar workflows si GitHub lo solicita.

8. Ejecutar manualmente:
   Actions → BOT-ARQ v3 - Analizar acciones → Run workflow
   Activar `force = true` si quieres probar fuera del horario de mercado.

## Si usas GitHub Desktop

1. Clona el repo nuevo.
2. Copia dentro de la carpeta local todo el contenido de este ZIP.
3. Commit:
   `Subir BOT-ARQ v3 real migrado desde V2`
4. Push.

## Si usas consola

```bash
git clone https://github.com/TU_USUARIO/BOT-ARQv3.git
cd BOT-ARQv3
# copia aquí los archivos del ZIP
git add .
git commit -m "Subir BOT-ARQ v3 real migrado desde V2"
git push
```

## Importante

El workflow usa `secrets.ARQ_PAT`, igual que tu V2.

Si tu V2 ya funcionaba con ese secreto, en el repo nuevo debes crearlo también:

Settings → Secrets and variables → Actions → New repository secret

Nombre:
`ARQ_PAT`

Valor:
tu token de GitHub.

## Prueba local opcional

En tu PC, desde la carpeta del repo:

```bash
pip install -r requirements.txt
python scripts/run_local.py
```
