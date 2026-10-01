import os
import hmac
import hashlib
import sqlite3
from contextlib import contextmanager

DB_FILENAME = "dulce_tentacion.db"
_ITERACIONES = 120_000


# --------------------------------------------------
# RUTA DE LA BASE DE DATOS
# --------------------------------------------------

def ruta_db():
    """
    En Android/iOS la app solo puede escribir en el directorio de datos propio,
    que Flet expone en FLET_APP_STORAGE_DATA. En PC se usa la carpeta del código.
    """
    base = os.environ.get("FLET_APP_STORAGE_DATA") or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, DB_FILENAME)


@contextmanager
def conexion():
    """Conexión con claves foráneas, commit/rollback automático y cierre garantizado."""
    conn = sqlite3.connect(ruta_db())
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------
# CONTRASEÑAS (hash con sal)
# --------------------------------------------------

def _pbkdf2(contrasena, sal, iteraciones):
    """PBKDF2-HMAC-SHA256 (32 bytes). Usa OpenSSL si existe; si no, una versión en Python puro."""
    clave = contrasena.encode("utf-8")
    try:
        return hashlib.pbkdf2_hmac("sha256", clave, sal, iteraciones)
    except (AttributeError, ValueError):
        u = hmac.new(clave, sal + b"\x00\x00\x00\x01", hashlib.sha256).digest()
        acumulado = int.from_bytes(u, "big")
        for _ in range(iteraciones - 1):
            u = hmac.new(clave, u, hashlib.sha256).digest()
            acumulado ^= int.from_bytes(u, "big")
        return acumulado.to_bytes(32, "big")


def hashear_contrasena(contrasena):
    sal = os.urandom(16)
    h = _pbkdf2(contrasena, sal, _ITERACIONES)
    return f"pbkdf2${_ITERACIONES}${sal.hex()}${h.hex()}"


def _verificar_hash(contrasena, almacenada):
    try:
        _, iteraciones, sal_hex, hash_hex = almacenada.split("$")
        h = _pbkdf2(contrasena, bytes.fromhex(sal_hex), int(iteraciones))
        return hmac.compare_digest(h.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


# --------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS (SCHEMA)
# --------------------------------------------------

def inicializar_db():
    """Crea las tablas, hace las migraciones necesarias y los registros iniciales."""
    with conexion() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                usuario TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                contraseña TEXT NOT NULL,
                id_rol INTEGER NOT NULL DEFAULT 3,
                FOREIGN KEY (id_rol) REFERENCES roles(id) ON DELETE RESTRICT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL CHECK(precio >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                descripcion TEXT,
                id_categoria INTEGER,
                activo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (id_categoria) REFERENCES categorias(id) ON DELETE SET NULL
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS carrito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_usuario INTEGER NOT NULL,
                id_producto INTEGER NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1 CHECK(cantidad > 0),
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE CASCADE
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_usuario INTEGER NOT NULL,
                total REAL NOT NULL CHECK(total >= 0),
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE RESTRICT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_venta INTEGER NOT NULL,
                id_producto INTEGER NOT NULL,
                cantidad INTEGER NOT NULL CHECK(cantidad > 0),
                precio_unitario REAL NOT NULL CHECK(precio_unitario >= 0),
                subtotal REAL NOT NULL CHECK(subtotal >= 0),
                FOREIGN KEY (id_venta) REFERENCES ventas(id) ON DELETE CASCADE,
                FOREIGN KEY (id_producto) REFERENCES productos(id) ON DELETE RESTRICT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_venta INTEGER NOT NULL,
                metodo_pago TEXT NOT NULL,
                monto REAL NOT NULL CHECK(monto >= 0),
                fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_venta) REFERENCES ventas(id) ON DELETE CASCADE
            );
        """)

        # Migración: bases creadas con la versión anterior no tienen la columna "activo"
        columnas = [row[1] for row in c.execute("PRAGMA table_info(productos)")]
        if "activo" not in columnas:
            c.execute("ALTER TABLE productos ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")

        # Datos iniciales
        c.execute("SELECT COUNT(*) FROM roles")
        if c.fetchone()[0] == 0:
            c.executemany("INSERT INTO roles (id, nombre) VALUES (?, ?)", [
                (1, "Administrador"), (2, "Empleado"), (3, "Cliente")
            ])

        c.execute("SELECT COUNT(*) FROM categorias")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO categorias (id, nombre, descripcion) VALUES (1, 'General', 'Categoría por defecto')")

        c.execute("SELECT COUNT(*) FROM usuarios WHERE id_rol = 1")
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO usuarios (nombre, usuario, email, contraseña, id_rol) VALUES (?, ?, ?, ?, 1)",
                ("Ezequiel", "admin", "ezequiel@dulcetentacion.com", hashear_contrasena("1234")),
            )


# --------------------------------------------------
# AUTENTICACIÓN Y USUARIOS
# --------------------------------------------------

def verificar_usuario(usuario_o_email, contrasena):
    """Retorna (valido, id_rol, nombre, id_usuario)."""
    with conexion() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, nombre, id_rol, contraseña FROM usuarios "
            "WHERE LOWER(usuario) = LOWER(?) OR LOWER(email) = LOWER(?)",
            (usuario_o_email.strip(), usuario_o_email.strip()),
        )
        user = c.fetchone()
        if not user:
            return False, None, None, None

        id_user, nombre, id_rol, almacenada = user
        if almacenada.startswith("pbkdf2$"):
            valido = _verificar_hash(contrasena, almacenada)
        else:
            # Contraseña antigua en texto plano: se valida y se convierte a hash
            valido = hmac.compare_digest(almacenada, contrasena)
            if valido:
                c.execute("UPDATE usuarios SET contraseña = ? WHERE id = ?",
                          (hashear_contrasena(contrasena), id_user))

        if valido:
            return True, id_rol, nombre, id_user
        return False, None, None, None


def _crear_usuario(nombre, usuario, email, contrasena, id_rol):
    """Retorna (ok, mensaje)."""
    nombre, usuario, email = nombre.strip(), usuario.strip(), email.strip().lower()

    if not nombre or not usuario or not email or not contrasena:
        return False, "Completa todos los campos"
    if " " in usuario:
        return False, "El usuario no puede tener espacios"
    if "@" not in email or "." not in email.split("@")[-1] or " " in email:
        return False, "Escribe un correo válido (ejemplo: nombre@gmail.com)"

    try:
        with conexion() as conn:
            if conn.execute("SELECT 1 FROM usuarios WHERE LOWER(usuario) = LOWER(?)", (usuario,)).fetchone():
                return False, "Ese nombre de usuario ya está en uso"
            if conn.execute("SELECT 1 FROM usuarios WHERE LOWER(email) = ?", (email,)).fetchone():
                return False, "Ese correo ya está registrado"
            conn.execute(
                "INSERT INTO usuarios (nombre, usuario, email, contraseña, id_rol) VALUES (?, ?, ?, ?, ?)",
                (nombre, usuario, email, hashear_contrasena(contrasena), id_rol),
            )
        return True, "Cuenta creada"
    except sqlite3.Error as e:
        print(f"Error al registrar usuario: {e}")
        return False, "No se pudo crear la cuenta"


def registrar_usuario(nombre, usuario, email, contrasena):
    """Registra un cliente (rol 3). Retorna (ok, mensaje)."""
    return _crear_usuario(nombre, usuario, email, contrasena, 3)


def registrar_empleado_db(nombre, usuario, email, contrasena):
    """Registra un empleado (rol 2). Acción restringida al administrador. Retorna (ok, mensaje)."""
    return _crear_usuario(nombre, usuario, email, contrasena, 2)


# --------------------------------------------------
# PRODUCTOS (CRUD)
# --------------------------------------------------

def obtener_productos():
    """(id, nombre, precio, stock, descripcion, categoria) de los productos activos."""
    with conexion() as conn:
        return conn.execute("""
            SELECT p.id, p.nombre, p.precio, p.stock, p.descripcion, COALESCE(c.nombre, 'Sin Categoría')
            FROM productos p
            LEFT JOIN categorias c ON p.id_categoria = c.id
            WHERE p.activo = 1
            ORDER BY p.nombre
        """).fetchall()


def insertar_producto(nombre, precio, stock, descripcion="", id_categoria=1):
    """Retorna (ok, mensaje)."""
    try:
        with conexion() as conn:
            conn.execute(
                "INSERT INTO productos (nombre, precio, stock, descripcion, id_categoria) VALUES (?, ?, ?, ?, ?)",
                (nombre.strip(), float(precio), int(stock), descripcion, id_categoria),
            )
        return True, "Producto creado"
    except (sqlite3.Error, ValueError) as e:
        print(f"Error al insertar producto: {e}")
        return False, "No se pudo crear el producto. Revisa precio y stock (no pueden ser negativos)."


def actualizar_producto_db(id_prod, nombre, precio, stock, descripcion="", id_categoria=1):
    """Retorna (ok, mensaje)."""
    try:
        with conexion() as conn:
            conn.execute(
                "UPDATE productos SET nombre = ?, precio = ?, stock = ?, descripcion = ?, id_categoria = ? WHERE id = ?",
                (nombre.strip(), float(precio), int(stock), descripcion, id_categoria, id_prod),
            )
        return True, "Producto actualizado"
    except (sqlite3.Error, ValueError) as e:
        print(f"Error al actualizar producto: {e}")
        return False, "No se pudo actualizar el producto. Revisa precio y stock (no pueden ser negativos)."


def eliminar_producto_db(id_prod):
    """
    Elimina el producto. Si ya tiene ventas registradas no se puede borrar sin
    perder el historial, así que se desactiva (deja de aparecer en el catálogo).
    Retorna (ok, mensaje).
    """
    try:
        with conexion() as conn:
            existe = conn.execute(
                "SELECT 1 FROM detalle_ventas WHERE id_producto = ? LIMIT 1", (id_prod,)
            ).fetchone()
            if existe:
                conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (id_prod,))
                return True, "El producto tiene ventas registradas: se ocultó del catálogo"
            conn.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
            return True, "Producto eliminado"
    except sqlite3.Error as e:
        print(f"Error al eliminar producto: {e}")
        return False, "No se pudo eliminar el producto"


# --------------------------------------------------
# VENTAS, PAGOS Y MÉTRICAS
# --------------------------------------------------

def registrar_venta_con_pago(id_usuario, metodo_pago, items):
    """
    Registra venta, pago y detalle en una sola transacción, validando el stock.
    items: lista de (id_producto, cantidad). El precio se toma de la base de datos.
    Retorna (ok, mensaje).
    """
    if not items:
        return False, "El carrito está vacío"

    # Agrupar cantidades por producto
    cantidades = {}
    for id_prod, cant in items:
        cantidades[id_prod] = cantidades.get(id_prod, 0) + cant

    try:
        with conexion() as conn:
            c = conn.cursor()
            lineas = []
            total = 0.0
            for id_prod, cant in cantidades.items():
                fila = c.execute(
                    "SELECT nombre, precio, stock FROM productos WHERE id = ? AND activo = 1", (id_prod,)
                ).fetchone()
                if not fila:
                    raise ValueError("Un producto del carrito ya no está disponible")
                nombre, precio, stock = fila
                if stock < cant:
                    raise ValueError(f"Stock insuficiente de {nombre} (quedan {stock})")
                lineas.append((id_prod, cant, precio))
                total += precio * cant

            c.execute("INSERT INTO ventas (id_usuario, total) VALUES (?, ?)", (id_usuario, total))
            id_venta = c.lastrowid
            c.execute("INSERT INTO pagos (id_venta, metodo_pago, monto) VALUES (?, ?, ?)",
                      (id_venta, metodo_pago, total))

            for id_prod, cant, precio in lineas:
                c.execute(
                    "INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario, subtotal) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (id_venta, id_prod, cant, precio, precio * cant),
                )
                c.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cant, id_prod))

        return True, "Venta registrada"
    except ValueError as e:
        return False, str(e)
    except sqlite3.Error as e:
        print(f"Error en transacción de venta: {e}")
        return False, "No se pudo registrar la venta"


def obtener_metricas():
    """(cantidad de productos activos, cantidad de ventas, ingresos totales)."""
    with conexion() as conn:
        c = conn.cursor()
        prods = c.execute("SELECT COUNT(*) FROM productos WHERE activo = 1").fetchone()[0] or 0
        ventas = c.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] or 0
        ingresos = c.execute("SELECT SUM(total) FROM ventas").fetchone()[0]
        return prods, ventas, float(ingresos) if ingresos else 0.0


def obtener_ventas_reporte():
    """(id, cliente, total, fecha, método de pago) ordenado por fecha."""
    with conexion() as conn:
        return conn.execute("""
            SELECT v.id, u.nombre, v.total, v.fecha, COALESCE(p.metodo_pago, 'Sin especificar')
            FROM ventas v
            JOIN usuarios u ON v.id_usuario = u.id
            LEFT JOIN pagos p ON p.id_venta = v.id
            ORDER BY v.fecha DESC
        """).fetchall()
