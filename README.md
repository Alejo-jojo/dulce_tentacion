# Dulce Tentación

Punto de venta hecho con Flet + SQLite.

## Estructura
- `src/main.py` – interfaz (punto de entrada)
- `src/database.py` – base de datos (SQLite), contraseñas con hash
- `src/reporte_pdf.py` – generador de PDF sin dependencias externas
- `pyproject.toml` – configuración de Flet (`[tool.flet.app] path = "src"`)
- `.github/workflows/build-apk.yml` – compila el APK en GitHub Actions y lo prueba en un emulador (artefacto `diagnostico-emulador`: captura de pantalla + registros)
- `tools/probar_emulador.sh` – script que usa el emulador

## Probar en PC
    pip install flet==0.28.3
    flet run src/main.py

## Generar el APK
Sube el proyecto a GitHub → pestaña **Actions** → **Build APK** → **Run workflow**.
El APK queda en *Artifacts* (`dulce-tentacion-apk`).

## Acceso inicial
Usuario `admin`, contraseña `1234`. **Cámbiala** (o crea otro administrador) antes de entregar la app.
La base de datos se crea sola al primer arranque; en Android vive en la carpeta privada de la app.
