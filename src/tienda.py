import flet as ft

from database import (
    inicializar_db,
    verificar_usuario,
    registrar_usuario,
    registrar_empleado_db,
    obtener_metricas,
    obtener_productos,
    insertar_producto,
    actualizar_producto_db,
    eliminar_producto_db,
    registrar_venta_con_pago,
    obtener_ventas_reporte,
)
from reporte_pdf import generar_pdf_ventas

COLOR_PRINCIPAL = "#E91E63"
COLOR_TARJETA = "#FCE4EC"
COLOR_TEXTO = "#333333"

def app_principal(page: ft.Page):
    page.title = "Dulce Tentación"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    inicializar_db()

    def notificar(texto, color=COLOR_PRINCIPAL):
        page.snack_bar = ft.SnackBar(ft.Text(texto), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # Guardado del reporte PDF (en Android abre el selector de archivos del sistema)
    def al_guardar_pdf(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        es_movil = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        try:
            if not es_movil:
                with open(e.path, "wb") as f:
                    f.write(pdf_pendiente["bytes"])
            notificar("Reporte PDF guardado", ft.colors.GREEN_600)
        except OSError:
            notificar("No se pudo guardar el reporte", ft.colors.RED_600)

    pdf_pendiente = {"bytes": b""}
    selector_pdf = ft.FilePicker(on_result=al_guardar_pdf)
    page.overlay.append(selector_pdf)

    usuario_actual = {"id": None, "nombre": None, "id_rol": None}
    carrito = []

    def cambiar_vista(nueva_vista):
        page.clean()
        page.add(nueva_vista)
        page.update()

    # --------------------------------------------------
    # 1. INICIAR SESIÓN
    # --------------------------------------------------
    txt_login_user = ft.TextField(label="Usuario o Email", border_radius=10, width=320)
    txt_login_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_radius=10, width=320)
    lbl_login_msg = ft.Text(color=ft.colors.RED_400, size=12)

    def login_click(e):
        if not txt_login_user.value or not txt_login_pass.value:
            lbl_login_msg.value = "Por favor ingresa todos los campos"
            page.update()
            return

        valido, rol, nombre, user_id = verificar_usuario(txt_login_user.value, txt_login_pass.value)
        if valido:
            usuario_actual["id"] = user_id
            usuario_actual["nombre"] = nombre
            usuario_actual["id_rol"] = int(rol)
            lbl_login_msg.value = ""
            
            # Redirección según Rol (1: Admin, 2: Empleado, 3: Cliente)
            if usuario_actual["id_rol"] in [1, 2]:
                mostrar_panel_gestion()
            else:
                mostrar_tienda_cliente()
        else:
            lbl_login_msg.value = "Usuario o contraseña incorrectos"
            page.update()

    vista_login = ft.Column(
        [
            ft.Container(height=40),
            ft.Text("Iniciar Sesión", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            txt_login_user,
            txt_login_pass,
            lbl_login_msg,
            ft.Container(height=10),
            ft.ElevatedButton(
                "Ingresar",
                on_click=login_click,
                bgcolor=COLOR_PRINCIPAL,
                color=ft.colors.WHITE,
                width=320,
                height=45,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
            ),
            ft.TextButton("¿No tienes cuenta? Regístrate", on_click=lambda e: cambiar_vista(vista_registro)),
            ft.TextButton("Volver al Inicio", on_click=lambda e: mostrar_tienda_cliente()),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --------------------------------------------------
    # 2. REGISTRO CLIENTE
    # --------------------------------------------------
    txt_reg_nombre = ft.TextField(label="Nombre Completo", border_radius=10, width=320)
    txt_reg_usuario = ft.TextField(label="Usuario", border_radius=10, width=320)
    txt_reg_email = ft.TextField(label="Correo electrónico (Gmail)", border_radius=10, width=320, keyboard_type=ft.KeyboardType.EMAIL)
    txt_reg_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_radius=10, width=320)
    lbl_reg_msg = ft.Text(size=12)

    def registrar_click(e):
        if (not txt_reg_nombre.value or not txt_reg_usuario.value
                or not txt_reg_email.value or not txt_reg_pass.value):
            lbl_reg_msg.value = "Por favor completa todos los campos"
            lbl_reg_msg.color = ft.colors.RED_400
            page.update()
            return

        ok, mensaje = registrar_usuario(
            txt_reg_nombre.value, txt_reg_usuario.value, txt_reg_email.value, txt_reg_pass.value
        )
        if ok:
            lbl_reg_msg.value = "¡Cuenta creada! Ya puedes ingresar"
            lbl_reg_msg.color = ft.colors.GREEN_600
            txt_reg_nombre.value = ""
            txt_reg_usuario.value = ""
            txt_reg_email.value = ""
            txt_reg_pass.value = ""
        else:
            lbl_reg_msg.value = mensaje
            lbl_reg_msg.color = ft.colors.RED_400
        page.update()

    vista_registro = ft.Column(
        [
            ft.Container(height=40),
            ft.Text("Registro", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            txt_reg_nombre,
            txt_reg_usuario,
            txt_reg_email,
            txt_reg_pass,
            lbl_reg_msg,
            ft.Container(height=10),
            ft.ElevatedButton(
                "Guardar",
                on_click=registrar_click,
                bgcolor=COLOR_PRINCIPAL,
                color=ft.colors.WHITE,
                width=320,
                height=45,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
            ),
            ft.TextButton("Volver a Iniciar Sesión", on_click=lambda e: cambiar_vista(vista_login)),
            ft.TextButton("Volver al Inicio", on_click=lambda e: mostrar_tienda_cliente()),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # --------------------------------------------------
    # 3. TIENDA CLIENTE
    # --------------------------------------------------
    def mostrar_tienda_cliente():
        lista_productos = obtener_productos() # Retorna: (id, nombre, precio, stock, descripcion, categoria)
        col_tienda = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        txt_contador_carrito = ft.Text(str(len(carrito)), size=12, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL)

        def agregar_carrito(prod):
            en_carrito = sum(1 for item in carrito if item[0] == prod[0])
            if en_carrito >= prod[3]:
                notificar(f"No hay más stock de {prod[1]}", ft.colors.RED_400)
                return
            carrito.append(prod)
            txt_contador_carrito.value = str(len(carrito))
            notificar(f"¡{prod[1]} añadido!")

        for p in lista_productos:
            col_tienda.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column([
                                ft.Text(p[1], weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXTO),
                                ft.Text(f"Categoría: {p[5]} | Stock: {p[3]}", size=11, color=ft.colors.GREY_600),
                                ft.Text(f"${p[2]:,.0f}", size=13, color=COLOR_PRINCIPAL, weight=ft.FontWeight.BOLD),
                            ]),
                            ft.IconButton(
                                icon=ft.icons.ADD_SHOPPING_CART_ROUNDED,
                                icon_color=COLOR_PRINCIPAL,
                                on_click=lambda e, prod=p: agregar_carrito(prod)
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=12,
                    border=ft.border.all(1, COLOR_TARJETA),
                    border_radius=12,
                )
            )

        def abrir_modal_metodos_pago(total_pago):
            rg_metodo = ft.RadioGroup(
                content=ft.Column([
                    ft.Radio(value="Nequi", label="Nequi"),
                    ft.Radio(value="Daviplata", label="Daviplata"),
                    ft.Radio(value="Tarjeta de Crédito", label="Tarjeta de Crédito"),
                    ft.Radio(value="PSE", label="PSE"),
                    ft.Radio(value="Efectivo", label="Efectivo"),
                ]),
                value="Nequi"
            )

            dialogo_pago = ft.AlertDialog(
                title=ft.Text("Selecciona Método de Pago", color=COLOR_PRINCIPAL, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        ft.Text(f"Total a pagar: ${total_pago:,.0f}", weight=ft.FontWeight.BOLD, size=15),
                        ft.Container(height=10),
                        rg_metodo
                    ],
                    tight=True
                )
            )

            def cerrar_pago(e):
                page.close(dialogo_pago)

            def procesar_pago(e):
                metodo_seleccionado = rg_metodo.value
                page.close(dialogo_pago)

                items = [(item[0], 1) for item in carrito]
                ok, mensaje = registrar_venta_con_pago(usuario_actual["id"], metodo_seleccionado, items)

                if ok:
                    carrito.clear()
                    txt_contador_carrito.value = "0"
                    mostrar_tienda_cliente()
                    notificar(f"¡Pago con {metodo_seleccionado} exitoso! Venta registrada 🧁", ft.colors.GREEN_600)
                else:
                    mostrar_tienda_cliente()
                    notificar(mensaje, ft.colors.RED_600)

            dialogo_pago.actions = [
                ft.TextButton("Cancelar", on_click=cerrar_pago),
                ft.ElevatedButton("Pagar", bgcolor=COLOR_PRINCIPAL, color=ft.colors.WHITE, on_click=procesar_pago)
            ]
            page.open(dialogo_pago)

        def abrir_modal_carrito(e):
            col_items = ft.Column(scroll=ft.ScrollMode.AUTO)
            contenedor_items = ft.Container(content=col_items, height=200)
            total = sum(item[2] for item in carrito)

            dialogo_carrito = ft.AlertDialog(
                title=ft.Text("Tu Carrito de Compras", color=COLOR_PRINCIPAL, weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    [
                        contenedor_items,
                        ft.Divider(),
                        ft.Text(f"Total: ${total:,.0f}", weight=ft.FontWeight.BOLD, size=16, color=COLOR_TEXTO)
                    ],
                    tight=True
                )
            )

            def eliminar_item(index):
                carrito.pop(index)
                txt_contador_carrito.value = str(len(carrito))
                page.close(dialogo_carrito)
                abrir_modal_carrito(None)

            if not carrito:
                col_items.controls.append(ft.Text("Tu carrito está vacío"))
            else:
                for idx, item in enumerate(carrito):
                    col_items.controls.append(
                        ft.Row(
                            [
                                ft.Text(f"{item[1]} - ${item[2]:,.0f}", size=13, expand=True),
                                ft.IconButton(
                                    icon=ft.icons.DELETE_OUTLINED,
                                    icon_color=ft.colors.RED_400,
                                    on_click=lambda e, i=idx: eliminar_item(i)
                                )
                            ]
                        )
                    )

            def cerrar_carrito_btn(e):
                page.close(dialogo_carrito)

            def iniciar_compra(e):
                if not carrito:
                    return
                def al_cerrar_dialogo(ev):
                    if not usuario_actual["id"]:
                        cambiar_vista(vista_login)
                    else:
                        abrir_modal_metodos_pago(total)

                dialogo_carrito.on_dismiss = al_cerrar_dialogo
                page.close(dialogo_carrito)

            dialogo_carrito.actions = [
                ft.TextButton("Seguir Comprando", on_click=cerrar_carrito_btn),
                ft.ElevatedButton("Comprar", bgcolor=COLOR_PRINCIPAL, color=ft.colors.WHITE, on_click=iniciar_compra)
            ]
            page.open(dialogo_carrito)

        btn_icono_carrito = ft.Stack(
            [
                ft.IconButton(
                    icon=ft.icons.SHOPPING_CART_ROUNDED,
                    icon_color=COLOR_PRINCIPAL,
                    icon_size=28,
                    on_click=abrir_modal_carrito
                ),
                ft.Container(
                    content=txt_contador_carrito,
                    padding=2,
                    alignment=ft.alignment.center,
                    right=0,
                    top=0
                )
            ]
        )

        def cerrar_sesion():
            usuario_actual["id"] = None
            usuario_actual["nombre"] = None
            usuario_actual["id_rol"] = None
            carrito.clear()
            mostrar_tienda_cliente()

        if usuario_actual["id"]:
            btn_sesion = ft.IconButton(
                icon=ft.icons.LOGOUT_ROUNDED,
                icon_color=COLOR_PRINCIPAL,
                tooltip="Cerrar Sesión",
                on_click=lambda e: cerrar_sesion()
            )
            saludo = f"Hola, {usuario_actual['nombre']}"
        else:
            btn_sesion = ft.TextButton(
                "Iniciar Sesión",
                style=ft.ButtonStyle(color=COLOR_PRINCIPAL),
                on_click=lambda e: cambiar_vista(vista_login)
            )
            saludo = "Dulce Tentación"

        vista_cliente = ft.Column(
            [
                ft.Row(
                    [
                        ft.Row([
                            ft.Container(content=ft.Icon(ft.icons.CAKE, color=COLOR_PRINCIPAL), bgcolor=COLOR_TARJETA, padding=6, border_radius=8),
                            ft.Text(saludo, weight=ft.FontWeight.BOLD, size=16),
                        ]),
                        ft.Row([
                            btn_sesion,
                            btn_icono_carrito,
                        ]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=10),
                ft.Text("CATÁLOGO DE POSTRES", size=13, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL),
                col_tienda,
            ],
            expand=True,
        )
        cambiar_vista(vista_cliente)

    # --------------------------------------------------
    # 4. PANEL DE GESTIÓN (ADMIN Y EMPLEADO)
    # --------------------------------------------------
    def mostrar_panel_gestion():
        prods_count, ventas_count, ingresos_sum = obtener_metricas()
        lista_productos = obtener_productos()

        tarjeta_prod = ft.Container(
            content=ft.Column([ft.Text("Prod", size=11, color=ft.colors.GREY_700), ft.Text(str(prods_count), size=18, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_TARJETA, width=95, height=60, border_radius=8
        )
        tarjeta_ventas = ft.Container(
            content=ft.Column([ft.Text("Ventas", size=11, color=ft.colors.GREY_700), ft.Text(str(ventas_count), size=18, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_TARJETA, width=95, height=60, border_radius=8
        )
        tarjeta_ingresos = ft.Container(
            content=ft.Column([ft.Text("Ingresos", size=11, color=ft.colors.GREY_700), ft.Text(f"${ingresos_sum:,.0f}", size=13, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_TARJETA, width=95, height=60, border_radius=8
        )

        col_prods_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def borrar_prod(id_p):
            ok, mensaje = eliminar_producto_db(id_p)
            mostrar_panel_gestion()
            notificar(mensaje, ft.colors.GREEN_600 if ok else ft.colors.RED_600)

        for p in lista_productos:
            col_prods_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column([
                                ft.Text(p[1], weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXTO),
                                ft.Text(f"Precio: ${p[2]:,.0f} | Stock: {p[3]} | Cat: {p[5]}", size=11, color=ft.colors.GREY_600),
                            ]),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT_OUTLINED,
                                    icon_color=COLOR_PRINCIPAL,
                                    on_click=lambda e, prod=p: mostrar_editar_producto(prod)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE_OUTLINED,
                                    icon_color=ft.colors.RED_400,
                                    on_click=lambda e, id_prod=p[0]: borrar_prod(id_prod)
                                )
                            ])
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=12,
                    border=ft.border.all(1, COLOR_TARJETA),
                    border_radius=10,
                )
            )

        def exportar_pdf_action(e):
            pdf_pendiente["bytes"] = generar_pdf_ventas(obtener_ventas_reporte())
            try:
                selector_pdf.save_file(
                    dialog_title="Guardar reporte de ventas",
                    file_name="reporte_ventas.pdf",
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_pendiente["bytes"],
                )
            except Exception:
                notificar("No se pudo abrir el selector para guardar el PDF", ft.colors.RED_600)

        def cerrar_sesion():
            usuario_actual["id"] = None
            usuario_actual["nombre"] = None
            usuario_actual["id_rol"] = None
            mostrar_tienda_cliente()

        botones_barra = [
            ft.IconButton(icon=ft.icons.ADD_BOX_OUTLINED, icon_color=COLOR_TEXTO, tooltip="Agregar Producto", on_click=lambda e: mostrar_crear_producto()),
            ft.IconButton(icon=ft.icons.INDETERMINATE_CHECK_BOX_OUTLINED, icon_color=COLOR_TEXTO, tooltip="Eliminar Producto", on_click=lambda e: mostrar_eliminar_producto()),
            ft.IconButton(icon=ft.icons.PICTURE_AS_PDF_OUTLINED, icon_color=COLOR_TEXTO, tooltip="Generar Reporte PDF", on_click=exportar_pdf_action),
        ]

        # Solo el ADMIN (rol 1) tiene el botón para registrar Empleados
        if usuario_actual["id_rol"] == 1:
            botones_barra.append(
                ft.IconButton(icon=ft.icons.PERSON_ADD_OUTLINED, icon_color=COLOR_TEXTO, tooltip="Agregar Empleado", on_click=lambda e: mostrar_crear_empleado())
            )

        botones_barra.append(
            ft.IconButton(icon=ft.icons.LOGOUT_ROUNDED, icon_color=COLOR_PRINCIPAL, tooltip="Cerrar Sesión", on_click=lambda e: cerrar_sesion())
        )

        barra_admin = ft.Container(
            content=ft.Row(botones_barra, alignment=ft.MainAxisAlignment.SPACE_AROUND),
            bgcolor=COLOR_TARJETA,
            padding=5,
            border_radius=15,
        )

        titulo_rol = "Panel Admin" if usuario_actual["id_rol"] == 1 else "Panel Empleado"

        vista_panel = ft.Column(
            [
                ft.Row(
                    [
                        ft.Row([
                            ft.Container(content=ft.Icon(ft.icons.CAKE, color=COLOR_PRINCIPAL), bgcolor=COLOR_TARJETA, padding=6, border_radius=8),
                            ft.Text(f"{titulo_rol} ({usuario_actual['nombre']})", weight=ft.FontWeight.BOLD, size=16),
                        ]),
                        ft.Icon(ft.icons.ACCOUNT_CIRCLE, size=30, color=ft.colors.GREY_700),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=10),
                ft.Text("PANEL DE GESTIÓN", size=13, weight=ft.FontWeight.BOLD, color=COLOR_PRINCIPAL),
                # Tarjetas centradas y con espaciado controlado
                ft.Row([tarjeta_prod, tarjeta_ventas, tarjeta_ingresos], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                ft.Container(height=10),
                ft.Text("PRODUCTOS", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                col_prods_list,
                barra_admin,
            ],
            expand=True,
        )
        cambiar_vista(vista_panel)

    # --------------------------------------------------
    # 5. CREAR PRODUCTO
    # --------------------------------------------------
    def mostrar_crear_producto():
        txt_nombre = ft.TextField(label="Nombre del Producto", border_radius=10, width=320)
        txt_precio = ft.TextField(label="Precio", border_radius=10, width=320)
        txt_stock = ft.TextField(label="Stock", border_radius=10, width=320)
        txt_desc = ft.TextField(label="Descripción", border_radius=10, width=320)

        def guardar_prod(e):
            if not txt_nombre.value.strip():
                notificar("Escribe el nombre del producto", ft.colors.RED_400)
                return
            try:
                precio, stock = float(txt_precio.value), int(txt_stock.value)
            except ValueError:
                notificar("Precio y stock deben ser números (el stock, entero)", ft.colors.RED_400)
                return
            ok, mensaje = insertar_producto(txt_nombre.value, precio, stock, txt_desc.value, id_categoria=1)
            if ok:
                mostrar_panel_gestion()
            notificar(mensaje, ft.colors.GREEN_600 if ok else ft.colors.RED_600)

        cambiar_vista(
            ft.Column(
                [
                    ft.Container(height=40),
                    ft.Text("Agregar Producto", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    txt_nombre, txt_precio, txt_stock, txt_desc,
                    ft.Container(height=10),
                    ft.ElevatedButton("Guardar", on_click=guardar_prod, bgcolor=COLOR_PRINCIPAL, color=ft.colors.WHITE, width=320),
                    ft.TextButton("Cancelar", on_click=lambda e: mostrar_panel_gestion()),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    # --------------------------------------------------
    # 6. EDITAR / MODIFICAR PRODUCTO
    # --------------------------------------------------
    def mostrar_editar_producto(prod):
        # prod = (id, nombre, precio, stock, descripcion, categoria)
        txt_nombre = ft.TextField(label="Nombre del Producto", value=str(prod[1]), border_radius=10, width=320)
        txt_precio = ft.TextField(label="Precio", value=str(prod[2]), border_radius=10, width=320)
        txt_stock = ft.TextField(label="Stock", value=str(prod[3]), border_radius=10, width=320)
        txt_desc = ft.TextField(label="Descripción", value=str(prod[4]) if prod[4] else "", border_radius=10, width=320)

        def guardar_cambios(e):
            if not txt_nombre.value.strip():
                notificar("Escribe el nombre del producto", ft.colors.RED_400)
                return
            try:
                precio, stock = float(txt_precio.value), int(txt_stock.value)
            except ValueError:
                notificar("Precio y stock deben ser números (el stock, entero)", ft.colors.RED_400)
                return
            ok, mensaje = actualizar_producto_db(prod[0], txt_nombre.value, precio, stock, txt_desc.value, id_categoria=1)
            if ok:
                mostrar_panel_gestion()
            notificar(mensaje, ft.colors.GREEN_600 if ok else ft.colors.RED_600)

        cambiar_vista(
            ft.Column(
                [
                    ft.Container(height=40),
                    ft.Text("Modificar Producto", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    txt_nombre, txt_precio, txt_stock, txt_desc,
                    ft.Container(height=10),
                    ft.ElevatedButton("Guardar Cambios", on_click=guardar_cambios, bgcolor=COLOR_PRINCIPAL, color=ft.colors.WHITE, width=320),
                    ft.TextButton("Cancelar", on_click=lambda e: mostrar_panel_gestion()),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    # --------------------------------------------------
    # 7. ELIMINAR PRODUCTO
    # --------------------------------------------------
    def mostrar_eliminar_producto():
        lista_prods = obtener_productos()
        opciones = [ft.dropdown.Option(key=str(p[0]), text=f"{p[1]} (${p[2]:,.0f})") for p in lista_prods]
        dd_productos = ft.Dropdown(label="Selecciona el producto a eliminar", options=opciones, width=320, border_radius=10)

        def confirmar_eliminar(e):
            if not dd_productos.value:
                notificar("Selecciona un producto", ft.colors.RED_400)
                return
            ok, mensaje = eliminar_producto_db(int(dd_productos.value))
            mostrar_panel_gestion()
            notificar(mensaje, ft.colors.GREEN_600 if ok else ft.colors.RED_600)

        cambiar_vista(
            ft.Column(
                [
                    ft.Container(height=40),
                    ft.Text("Eliminar Producto", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    dd_productos,
                    ft.Container(height=10),
                    ft.ElevatedButton("Eliminar", on_click=confirmar_eliminar, bgcolor=ft.colors.RED_600, color=ft.colors.WHITE, width=320),
                    ft.TextButton("Cancelar", on_click=lambda e: mostrar_panel_gestion()),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    # --------------------------------------------------
    # 8. REGISTRAR EMPLEADO (EXCLUSIVO ADMIN)
    # --------------------------------------------------
    def mostrar_crear_empleado():
        txt_emp_nombre = ft.TextField(label="Nombre Completo", border_radius=10, width=320)
        txt_emp_user = ft.TextField(label="Usuario", border_radius=10, width=320)
        txt_emp_email = ft.TextField(label="Correo electrónico (Gmail)", border_radius=10, width=320, keyboard_type=ft.KeyboardType.EMAIL)
        txt_emp_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_radius=10, width=320)
        lbl_emp_msg = ft.Text(size=12)

        def guardar_empleado(e):
            if (not txt_emp_nombre.value or not txt_emp_user.value
                    or not txt_emp_email.value or not txt_emp_pass.value):
                lbl_emp_msg.value = "Todos los campos son obligatorios"
                lbl_emp_msg.color = ft.colors.RED_400
                page.update()
                return

            ok, mensaje = registrar_empleado_db(
                txt_emp_nombre.value, txt_emp_user.value, txt_emp_email.value, txt_emp_pass.value
            )
            if ok:
                mostrar_panel_gestion()
                notificar("¡Empleado creado exitosamente!", ft.colors.GREEN_600)
            else:
                lbl_emp_msg.value = mensaje
                lbl_emp_msg.color = ft.colors.RED_400
                page.update()

        cambiar_vista(
            ft.Column(
                [
                    ft.Container(height=40),
                    ft.Text("Registrar Empleado", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    txt_emp_nombre,
                    txt_emp_user,
                    txt_emp_email,
                    txt_emp_pass,
                    lbl_emp_msg,
                    ft.Container(height=10),
                    ft.ElevatedButton("Crear Empleado", on_click=guardar_empleado, bgcolor=COLOR_PRINCIPAL, color=ft.colors.WHITE, width=320),
                    ft.TextButton("Cancelar", on_click=lambda e: mostrar_panel_gestion()),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    mostrar_tienda_cliente()
