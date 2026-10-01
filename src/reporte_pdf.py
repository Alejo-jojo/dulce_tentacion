"""Generador de PDF sin dependencias externas (funciona igual en PC y Android)."""

ROSA = (0.914, 0.118, 0.388)      # #E91E63
ROSA_CLARO = (0.988, 0.894, 0.925)  # #FCE4EC

ANCHO, ALTO = 595, 842            # A4 en puntos
MARGEN = 40
COLUMNAS = [("ID", 40), ("Cliente", 150), ("Total", 90), ("Método de pago", 130), ("Fecha", 105)]


def _txt(s):
    """Escapa el texto para un string PDF en codificación WinAnsi (cp1252)."""
    b = str(s).encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _recortar(s, ancho, tam):
    s = str(s)
    maximo = max(1, int(ancho / (tam * 0.5)))
    return s if len(s) <= maximo else s[: maximo - 1] + "…"


def generar_pdf_ventas(ventas, titulo="Reporte de Ventas - Dulce Tentación"):
    """ventas: filas (id, cliente, total, fecha, metodo). Retorna bytes del PDF."""
    paginas = []
    ops = []
    y = ALTO - MARGEN

    def texto(x, y_, s, tam=10, bold=False, color=(0.2, 0.2, 0.2)):
        fuente = "F2" if bold else "F1"
        ops.append(b"BT /%s %d Tf %.3f %.3f %.3f rg %d %d Td (" % (
            fuente.encode(), tam, color[0], color[1], color[2], x, y_) + _txt(s) + b") Tj ET")

    def encabezado_tabla(y_):
        ops.append(b"%.3f %.3f %.3f rg %d %d %d %d re f" % (
            ROSA_CLARO[0], ROSA_CLARO[1], ROSA_CLARO[2], MARGEN, y_ - 5, ANCHO - 2 * MARGEN, 20))
        x = MARGEN + 4
        for nombre, ancho in COLUMNAS:
            texto(x, y_, nombre, 10, True, ROSA)
            x += ancho

    def nueva_pagina():
        nonlocal ops, y
        if ops:
            paginas.append(b"\n".join(ops))
        ops = []
        y = ALTO - MARGEN

    texto(MARGEN, y - 10, titulo, 16, True, ROSA)
    y -= 45
    encabezado_tabla(y)
    y -= 24

    total_general = 0.0
    for v in ventas:
        if y < MARGEN + 40:
            nueva_pagina()
            encabezado_tabla(y)
            y -= 24
        total_general += float(v[2])
        celdas = [v[0], v[1] or "Cliente General", f"${float(v[2]):,.0f}", v[4] or "N/A", v[3]]
        x = MARGEN + 4
        for (_, ancho), valor in zip(COLUMNAS, celdas):
            texto(x, y, _recortar(valor, ancho - 6, 9), 9)
            x += ancho
        ops.append(b"0.85 0.85 0.85 RG %d %d m %d %d l S" % (MARGEN, y - 5, ANCHO - MARGEN, y - 5))
        y -= 18

    if y < MARGEN + 40:
        nueva_pagina()
    texto(ANCHO - MARGEN - 190, y - 15, f"Ingresos Totales: ${total_general:,.0f}", 12, True)
    paginas.append(b"\n".join(ops))

    # ---- Ensamblado del archivo PDF ----
    objetos = []  # cada elemento: bytes del contenido del objeto

    n_pag = len(paginas)
    # 1: catálogo, 2: páginas, 3: Helvetica, 4: Helvetica-Bold, luego (página, contenido) por cada página
    ids_pagina = [5 + 2 * i for i in range(n_pag)]
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = b" ".join(b"%d 0 R" % i for i in ids_pagina)
    objetos.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % n_pag)
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for i, contenido in enumerate(paginas):
        id_contenido = ids_pagina[i] + 1
        objetos.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % (ANCHO, ALTO, id_contenido)
        )
        objetos.append(b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream")

    salida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, cuerpo in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += b"%d 0 obj\n" % n + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for off in offsets:
        salida += b"%010d 00000 n \n" % off
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return bytes(salida)
