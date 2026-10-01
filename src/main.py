"""
Punto de entrada. Carga la app por pasos y, si algo falla, muestra el error en pantalla
(en lugar de dejar la pantalla en blanco o negra en el celular).
"""
import traceback

import flet as ft

COLOR_PRINCIPAL = "#E91E63"


def main(page: ft.Page):
    page.title = "Dulce Tentación"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    estado = ft.Text("1. Python iniciado", color=COLOR_PRINCIPAL, size=18)
    page.add(
        ft.Text("Dulce Tentación", size=26, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL),
        estado,
    )
    page.update()

    def paso(texto):
        estado.value = texto
        page.update()

    try:
        paso("2. Cargando módulos...")
        import database
        import tienda

        paso("3. Preparando base de datos...")
        database.inicializar_db()

        paso("4. Armando pantalla...")
        page.clean()
        tienda.app_principal(page)
    except Exception:
        page.clean()
        page.add(
            ft.Text("Error al iniciar la app", color=ft.colors.RED_600, size=20, weight=ft.FontWeight.BOLD),
            ft.Text(traceback.format_exc(), selectable=True, size=12, color="#333333"),
        )
        page.update()


# Sin "if __name__ == '__main__'": en el APK, Flet puede importar este archivo en lugar de
# ejecutarlo como programa principal, y con esa condición la app nunca arrancaría (pantalla en blanco).
ft.app(target=main)
