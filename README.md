# Analizador de Acciones ARQ con GitHub Actions

## Qué hace
Esta app usa GitHub Actions para analizar acciones y actualizar:
- `datos_acciones.json`
- `analisis_acciones.xlsx`

Luego tu página `index.html` muestra los resultados.

## Archivos
- `index.html`
- `style.css`
- `script.js`
- `analizador_acciones.py`
- `.github/workflows/analizar.yml`
- `ejecutar_analisis_github.bat`

## Pasos para instalar en GitHub
1. Sube todos estos archivos a tu repositorio.
2. Asegúrate de subir también la carpeta `.github/workflows/analizar.yml`.
3. En GitHub, entra al repositorio.
4. Ve a Settings > Pages.
5. En Source selecciona `Deploy from a branch`.
6. Branch: `main`.
7. Folder: `/root`.
8. Guarda.

## Para ejecutar el análisis
1. Abre `ejecutar_analisis_github.bat`.
2. Pega tu token.
3. Escribe tu usuario de GitHub.
4. Escribe el nombre del repositorio.
5. Espera 1 a 3 minutos.
6. Abre tu página y toca "Actualizar vista".

## Token recomendado
Tu token debe tener permiso para ejecutar Actions y leer el repositorio.
Si el repositorio es privado, necesita más permisos.

## Importante
Esto no garantiza ganancias. Es solo análisis técnico.
