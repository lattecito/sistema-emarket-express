"""
catalogo.py
===========
Módulo de GESTIÓN DE CATÁLOGO Y BODEGAS (CRUD).

Incluye:
1. Productos: Formulario con selección obligatoria de Categoría (id_categoria)
   y Proveedor (nit_proveedor).
   * Al modificar precios, el TRIGGER 'trg_auditoria_precio_articulo' en MariaDB
     registra la auditoría automáticamente.
2. Categorías: Gestión de familias de artículos.
3. Proveedores: Registro de proveedores por NIT.
4. Bodegas: Gestión de instalaciones de almacenamiento.
5. Stock en bodegas y Transferencias:
   * Control de stock actual por bodega.
   * Transferencia entre bodegas mediante el procedimiento almacenado:
     SP_ActualizarInventarioBodega(p_id_articulo, p_bodega_origen, p_bodega_destino, p_cantidad)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
# pyrefly: ignore[missing-import]
from mysql.connector import Error

from conexion import consultar, ejecutar, obtener_conexion, cerrar_conexion, traducir_error

SIN_SELECCION = "(Ninguno)"


def crear_tabla(padre, columnas, anchos=None, alto=12):
    """Crea una tabla visual ttk.Treeview con su barra de desplazamiento vertical."""
    marco = ttk.Frame(padre)
    ids = [f"c{i}" for i in range(len(columnas))]
    tabla = ttk.Treeview(marco, columns=ids, show="headings", height=alto)

    for i, titulo in enumerate(columnas):
        ancho = anchos[i] if anchos else 120
        tabla.heading(ids[i], text=titulo)
        tabla.column(ids[i], width=ancho, minwidth=50, anchor="center")

    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)

    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return marco, tabla


def llenar_tabla(tabla, filas, usar_primera_columna_como_id=True):
    """Limpia el contenido previo de la tabla y la llena con las filas de la base de datos."""
    tabla.delete(*tabla.get_children())
    for fila in filas:
        valores = []
        for val in fila:
            if val is None:
                valores.append("")
            elif isinstance(val, Decimal):
                valores.append(f"{val:,.2f}")
            else:
                valores.append(val)

        if usar_primera_columna_como_id:
            tabla.insert("", "end", iid=str(fila[0]), values=valores)
        else:
            tabla.insert("", "end", values=valores)


def crear_campo(formulario, fila, texto, tipo="entry", solo_lectura=False):
    """Crea una etiqueta y un campo de entrada (Entry o Combobox) en el formulario."""
    ttk.Label(formulario, text=texto).grid(row=fila, column=0, sticky="w", padx=4, pady=5)
    if tipo == "combo":
        campo = ttk.Combobox(formulario, width=28, state="readonly")
    else:
        campo = ttk.Entry(formulario, width=30)
        if solo_lectura:
            campo.configure(state="readonly")
    campo.grid(row=fila, column=1, sticky="ew", padx=4, pady=5)
    return campo


def poner_texto(campo, valor):
    """Establece el valor en un widget Entry o Combobox respetando su estado."""
    if isinstance(campo, ttk.Combobox):
        campo.set(valor)
        return
    estado_previo = str(campo.cget("state"))
    campo.configure(state="normal")
    campo.delete(0, "end")
    campo.insert(0, str(valor))
    campo.configure(state=estado_previo)


def limpiar_campos(campos):
    """Limpia todos los campos de texto del formulario."""
    for c in campos:
        poner_texto(c, "")


def leer_entero(texto, nombre_campo):
    try:
        return int(str(texto).strip())
    except ValueError:
        messagebox.showwarning("Dato Inválido", f"El campo '{nombre_campo}' debe ser un número entero.")
        return None


def leer_decimal(texto, nombre_campo):
    try:
        return float(str(texto).replace(",", "").strip())
    except ValueError:
        messagebox.showwarning("Dato Inválido", f"El campo '{nombre_campo}' debe ser un valor numérico.")
        return None


def id_desde_combo(texto):
    """Extrae el ID o NIT de un texto de combobox como '1100 - Jean' -> '1100'."""
    if not texto or texto == SIN_SELECCION:
        return None
    return texto.split(" - ")[0]


def crear_botones(padre, solo_lectura, agregar, actualizar, eliminar, limpiar, recargar):
    """Genera la barra estándar de botones CRUD."""
    marco = ttk.Frame(padre)
    if not solo_lectura:
        ttk.Button(marco, text="Agregar", style="Exito.TButton", command=agregar).pack(fill="x", pady=2)
        ttk.Button(marco, text="Actualizar", style="Primario.TButton", command=actualizar).pack(fill="x", pady=2)
        ttk.Button(marco, text="Eliminar", style="Peligro.TButton", command=eliminar).pack(fill="x", pady=2)
        ttk.Button(marco, text="Limpiar formulario", command=limpiar).pack(fill="x", pady=2)
    ttk.Button(marco, text="Recargar datos", command=recargar).pack(fill="x", pady=2)
    return marco


def crear_estructura_pestana(cuaderno, titulo_pestana, titulo_formulario, columnas, anchos):
    """Genera la división estándar de formulario a la izquierda y tabla a la derecha."""
    pestana = ttk.Frame(cuaderno, padding=10)
    cuaderno.add(pestana, text=titulo_pestana)

    panel_izquierdo = ttk.Frame(pestana)
    panel_izquierdo.pack(side="left", fill="y", padx=(0, 10))

    formulario = ttk.LabelFrame(panel_izquierdo, text=titulo_formulario, padding=10)
    formulario.pack(fill="x")

    marco_tabla, tabla = crear_tabla(pestana, columnas, anchos, alto=20)
    marco_tabla.pack(side="left", fill="both", expand=True)

    return formulario, tabla, panel_izquierdo


def confirmar_eliminacion(descripcion):
    return messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar {descripcion}?")


def crear_modulo_catalogo(padre, solo_lectura=False):
    """Construye las pestañas del catálogo de artículos y bodegas."""
    cuaderno = ttk.Notebook(padre)
    cuaderno.pack(fill="both", expand=True, padx=5, pady=5)

    crear_pestana_productos(cuaderno, solo_lectura)
    crear_pestana_categorias(cuaderno, solo_lectura)
    crear_pestana_proveedores(cuaderno, solo_lectura)
    crear_pestana_bodegas(cuaderno, solo_lectura)
    crear_pestana_inventario(cuaderno, solo_lectura)


# =============================================================================
#  PESTAÑA 1: PRODUCTOS (con selección de Categoría y Proveedor)
# =============================================================================

def crear_pestana_productos(cuaderno, solo_lectura):
    columnas = ("Código", "Nombre", "Precio Unitario", "Cantidad Disponible", "Categoría", "Proveedor")
    anchos = (80, 160, 120, 120, 160, 190)
    formulario, tabla, panel = crear_estructura_pestana(
        cuaderno, "Productos", "Gestión de Artículos / Productos", columnas, anchos
    )

    txt_codigo = crear_campo(formulario, 0, "Código:")
    txt_nombre = crear_campo(formulario, 1, "Nombre:")
    txt_precio = crear_campo(formulario, 2, "Precio unitario:")
    txt_cantidad = crear_campo(formulario, 3, "Cantidad disponible:")
    cmb_categoria = crear_campo(formulario, 4, "Categoría (id_categoria):", tipo="combo")
    cmb_proveedor = crear_campo(formulario, 5, "Proveedor (nit_proveedor):", tipo="combo")
    campos = [txt_codigo, txt_nombre, txt_precio, txt_cantidad, cmb_categoria, cmb_proveedor]

    def cargar_combos():
        cats = consultar("SELECT id_categoria, nombre FROM categoria ORDER BY nombre")
        cmb_categoria["values"] = [SIN_SELECCION] + [f"{c[0]} - {c[1]}" for c in cats]
        provs = consultar("SELECT nit, nombre FROM proveedor ORDER BY nombre")
        cmb_proveedor["values"] = [SIN_SELECCION] + [f"{p[0]} - {p[1]}" for p in provs]

    def cargar_datos():
        sql = """
            SELECT p.codigo, p.nombre, p.precio_unitario, p.cantidad_disponible,
                   CONCAT(c.id_categoria, ' - ', c.nombre),
                   CONCAT(pr.nit, ' - ', pr.nombre)
            FROM productos p
            LEFT JOIN categoria c  ON c.id_categoria = p.id_categoria
            LEFT JOIN proveedor pr ON pr.nit = p.nit_proveedor
            ORDER BY p.codigo
        """
        llenar_tabla(tabla, consultar(sql))
        cargar_combos()

    def al_seleccionar(evento):
        seleccion = tabla.selection()
        if not seleccion:
            return
        vals = tabla.item(seleccion[0], "values")
        for campo, val in zip(campos, vals):
            poner_texto(campo, val)
        if not vals[4]:
            cmb_categoria.set(SIN_SELECCION)
        if not vals[5]:
            cmb_proveedor.set(SIN_SELECCION)

    def leer_formulario():
        codigo = leer_entero(txt_codigo.get(), "Código")
        if codigo is None:
            return None
        nombre = txt_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Dato Faltante", "El nombre del producto es obligatorio.")
            return None
        precio = leer_decimal(txt_precio.get(), "Precio unitario")
        if precio is None:
            return None
        cantidad = leer_entero(txt_cantidad.get(), "Cantidad disponible")
        if cantidad is None:
            return None
        if precio <= 0 or cantidad < 0:
            messagebox.showwarning("Dato Inválido", "El precio debe ser > 0 y la cantidad >= 0.")
            return None

        id_categoria = id_desde_combo(cmb_categoria.get())
        nit_proveedor = id_desde_combo(cmb_proveedor.get())
        return codigo, nombre, precio, cantidad, id_categoria, nit_proveedor

    def agregar():
        datos = leer_formulario()
        if datos is None:
            return
        sql = """
            INSERT INTO productos (codigo, nombre, precio_unitario, cantidad_disponible,
                                   id_categoria, nit_proveedor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        if ejecutar(sql, datos) is not None:
            messagebox.showinfo("Éxito", "Producto registrado correctamente.")
            cargar_datos()
            limpiar_campos(campos)

    def actualizar():
        """
        Actualiza el producto. Si el precio cambia, el trigger
        'trg_auditoria_precio_articulo' en MariaDB se encarga de guardar la auditoría.
        """
        datos = leer_formulario()
        if datos is None:
            return
        codigo, nombre, precio, cantidad, id_categoria, nit_proveedor = datos

        sql = """
            UPDATE productos
            SET nombre = %s, precio_unitario = %s, cantidad_disponible = %s,
                id_categoria = %s, nit_proveedor = %s
            WHERE codigo = %s
        """
        filas = ejecutar(sql, (nombre, precio, cantidad, id_categoria, nit_proveedor, codigo))
        if filas is not None:
            messagebox.showinfo(
                "Éxito",
                "Producto actualizado correctamente.\n"
                "(Si el precio cambió, el trigger en MariaDB registró la auditoría automáticamente)."
            )
            cargar_datos()

    def eliminar():
        codigo = leer_entero(txt_codigo.get(), "Código")
        if codigo is None or not confirmar_eliminacion(f"el producto {codigo}"):
            return
        if ejecutar("DELETE FROM productos WHERE codigo = %s", (codigo,)):
            messagebox.showinfo("Éxito", "Producto eliminado.")
            cargar_datos()
            limpiar_campos(campos)

    tabla.bind("<<TreeviewSelect>>", al_seleccionar)
    crear_botones(panel, solo_lectura, agregar, actualizar, eliminar,
                  lambda: limpiar_campos(campos), cargar_datos).pack(fill="x", pady=10)
    cargar_datos()


# =============================================================================
#  PESTAÑA 2: CATEGORÍAS
# =============================================================================

def crear_pestana_categorias(cuaderno, solo_lectura):
    formulario, tabla, panel = crear_estructura_pestana(
        cuaderno, "Categorías", "Datos de la categoría",
        ("ID", "Nombre", "Descripción"), (70, 200, 420)
    )

    txt_id = crear_campo(formulario, 0, "ID (automático):", solo_lectura=True)
    txt_nombre = crear_campo(formulario, 1, "Nombre:")
    txt_desc = crear_campo(formulario, 2, "Descripción:")
    campos = [txt_id, txt_nombre, txt_desc]

    def cargar_datos():
        llenar_tabla(tabla, consultar("SELECT id_categoria, nombre, descripcion FROM categoria ORDER BY id_categoria"))

    def al_seleccionar(evento):
        seleccion = tabla.selection()
        if seleccion:
            for campo, valor in zip(campos, tabla.item(seleccion[0], "values")):
                poner_texto(campo, valor)

    def agregar():
        nombre = txt_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Dato faltante", "El nombre es obligatorio.")
            return
        if ejecutar("INSERT INTO categoria (nombre, descripcion) VALUES (%s, %s)", (nombre, txt_desc.get().strip() or None)) is not None:
            messagebox.showinfo("Éxito", "Categoría agregada.")
            cargar_datos()
            limpiar_campos(campos)

    def actualizar():
        if not txt_id.get():
            messagebox.showwarning("Seleccione", "Selecciona una categoría de la tabla.")
            return
        nombre = txt_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Dato faltante", "El nombre es obligatorio.")
            return
        if ejecutar("UPDATE categoria SET nombre = %s, descripcion = %s WHERE id_categoria = %s",
                    (nombre, txt_desc.get().strip() or None, txt_id.get())):
            messagebox.showinfo("Éxito", "Categoría actualizada.")
            cargar_datos()

    def eliminar():
        if not txt_id.get() or not confirmar_eliminacion(f"la categoría '{txt_nombre.get()}'"):
            return
        if ejecutar("DELETE FROM categoria WHERE id_categoria = %s", (txt_id.get(),)):
            messagebox.showinfo("Éxito", "Categoría eliminada.")
            cargar_datos()
            limpiar_campos(campos)

    tabla.bind("<<TreeviewSelect>>", al_seleccionar)
    crear_botones(panel, solo_lectura, agregar, actualizar, eliminar,
                  lambda: limpiar_campos(campos), cargar_datos).pack(fill="x", pady=10)
    cargar_datos()


# =============================================================================
#  PESTAÑA 3: PROVEEDORES
# =============================================================================

def crear_pestana_proveedores(cuaderno, solo_lectura):
    formulario, tabla, panel = crear_estructura_pestana(
        cuaderno, "Proveedores", "Datos del proveedor",
        ("NIT", "Nombre", "Contacto", "Ciudad"), (120, 220, 180, 150)
    )

    txt_nit = crear_campo(formulario, 0, "NIT:")
    txt_nombre = crear_campo(formulario, 1, "Nombre:")
    txt_contacto = crear_campo(formulario, 2, "Contacto:")
    txt_ciudad = crear_campo(formulario, 3, "Ciudad:")
    campos = [txt_nit, txt_nombre, txt_contacto, txt_ciudad]

    def cargar_datos():
        llenar_tabla(tabla, consultar("SELECT nit, nombre, contacto, ciudad FROM proveedor ORDER BY nombre"))

    def al_seleccionar(evento):
        seleccion = tabla.selection()
        if seleccion:
            for campo, valor in zip(campos, tabla.item(seleccion[0], "values")):
                poner_texto(campo, valor)
            poner_texto(txt_nit, seleccion[0])

    def agregar():
        nit = txt_nit.get().strip()
        nombre = txt_nombre.get().strip()
        if not nit or not nombre:
            messagebox.showwarning("Faltan datos", "NIT y Nombre son obligatorios.")
            return
        if ejecutar("INSERT INTO proveedor (nit, nombre, contacto, ciudad) VALUES (%s, %s, %s, %s)",
                    (nit, nombre, txt_contacto.get().strip(), txt_ciudad.get().strip())) is not None:
            messagebox.showinfo("Éxito", "Proveedor registrado.")
            cargar_datos()
            limpiar_campos(campos)

    def actualizar():
        nit = txt_nit.get().strip()
        nombre = txt_nombre.get().strip()
        if not nit or not nombre:
            messagebox.showwarning("Faltan datos", "NIT y Nombre son obligatorios.")
            return
        if ejecutar("UPDATE proveedor SET nombre = %s, contacto = %s, ciudad = %s WHERE nit = %s",
                    (nombre, txt_contacto.get().strip(), txt_ciudad.get().strip(), nit)):
            messagebox.showinfo("Éxito", "Proveedor actualizado.")
            cargar_datos()

    def eliminar():
        nit = txt_nit.get().strip()
        if not nit or not confirmar_eliminacion(f"el proveedor {nit}"):
            return
        if ejecutar("DELETE FROM proveedor WHERE nit = %s", (nit,)):
            messagebox.showinfo("Éxito", "Proveedor eliminado.")
            cargar_datos()
            limpiar_campos(campos)

    tabla.bind("<<TreeviewSelect>>", al_seleccionar)
    crear_botones(panel, solo_lectura, agregar, actualizar, eliminar,
                  lambda: limpiar_campos(campos), cargar_datos).pack(fill="x", pady=10)
    cargar_datos()


# =============================================================================
#  PESTAÑA 4: BODEGAS
# =============================================================================

def crear_pestana_bodegas(cuaderno, solo_lectura):
    formulario, tabla, panel = crear_estructura_pestana(
        cuaderno, "Bodegas", "Datos de la bodega",
        ("ID", "Nombre", "Ubicación", "Artículos Distintos", "Total Unidades"),
        (60, 180, 260, 140, 130)
    )

    txt_id = crear_campo(formulario, 0, "ID (automático):", solo_lectura=True)
    txt_nombre = crear_campo(formulario, 1, "Nombre:")
    txt_ubicacion = crear_campo(formulario, 2, "Ubicación:")
    campos = [txt_id, txt_nombre, txt_ubicacion]

    def cargar_datos():
        sql = """
            SELECT b.id_bodega, b.nombre, b.ubicacion,
                   COUNT(ib.id_articulo), IFNULL(SUM(ib.stock_actual), 0)
            FROM bodega b
            LEFT JOIN inventario_bodega ib ON ib.id_bodega = b.id_bodega
            GROUP BY b.id_bodega, b.nombre, b.ubicacion
            ORDER BY b.id_bodega
        """
        llenar_tabla(tabla, consultar(sql))

    def al_seleccionar(evento):
        seleccion = tabla.selection()
        if seleccion:
            for campo, valor in zip(campos, tabla.item(seleccion[0], "values")):
                poner_texto(campo, valor)

    def agregar():
        nombre = txt_nombre.get().strip()
        ubicacion = txt_ubicacion.get().strip()
        if not nombre or not ubicacion:
            messagebox.showwarning("Faltan datos", "Nombre y ubicación son obligatorios.")
            return
        if ejecutar("INSERT INTO bodega (nombre, ubicacion) VALUES (%s, %s)", (nombre, ubicacion)) is not None:
            messagebox.showinfo("Éxito", "Bodega agregada.")
            cargar_datos()
            limpiar_campos(campos)

    def actualizar():
        if not txt_id.get():
            messagebox.showwarning("Seleccione", "Selecciona una bodega de la tabla.")
            return
        nombre = txt_nombre.get().strip()
        ubicacion = txt_ubicacion.get().strip()
        if not nombre or not ubicacion:
            messagebox.showwarning("Faltan datos", "Nombre y ubicación son obligatorios.")
            return
        if ejecutar("UPDATE bodega SET nombre = %s, ubicacion = %s WHERE id_bodega = %s", (nombre, ubicacion, txt_id.get())):
            messagebox.showinfo("Éxito", "Bodega actualizada.")
            cargar_datos()

    def eliminar():
        if not txt_id.get() or not confirmar_eliminacion(f"la bodega '{txt_nombre.get()}'"):
            return
        if ejecutar("DELETE FROM bodega WHERE id_bodega = %s", (txt_id.get(),)):
            messagebox.showinfo("Éxito", "Bodega eliminada.")
            cargar_datos()
            limpiar_campos(campos)

    tabla.bind("<<TreeviewSelect>>", al_seleccionar)
    crear_botones(panel, solo_lectura, agregar, actualizar, eliminar,
                  lambda: limpiar_campos(campos), cargar_datos).pack(fill="x", pady=10)
    cargar_datos()


# =============================================================================
#  PESTAÑA 5: STOCK E INVENTARIO (con SP_ActualizarInventarioBodega)
# =============================================================================

def crear_pestana_inventario(cuaderno, solo_lectura):
    pestana = ttk.Frame(cuaderno, padding=10)
    cuaderno.add(pestana, text="Stock en Bodegas")

    panel_izq = ttk.Frame(pestana)
    panel_izq.pack(side="left", fill="y", padx=(0, 10))

    # Formulario 1: Asignar Stock Directo
    form_stock = ttk.LabelFrame(panel_izq, text="Asignar Stock a Bodega", padding=10)
    form_stock.pack(fill="x")

    cmb_prod = crear_campo(form_stock, 0, "Producto:", tipo="combo")
    cmb_bod = crear_campo(form_stock, 1, "Bodega:", tipo="combo")
    txt_stock = crear_campo(form_stock, 2, "Stock actual:")

    # Formulario 2: Transferencia entre bodegas mediante SP_ActualizarInventarioBodega
    form_transf = ttk.LabelFrame(panel_izq, text="Transferir con SP_ActualizarInventarioBodega", padding=10)
    form_transf.pack(fill="x", pady=(12, 0))

    cmb_tr_prod = crear_campo(form_transf, 0, "Producto:", tipo="combo")
    cmb_tr_orig = crear_campo(form_transf, 1, "Bodega Origen:", tipo="combo")
    cmb_tr_dest = crear_campo(form_transf, 2, "Bodega Destino:", tipo="combo")
    txt_tr_cant = crear_campo(form_transf, 3, "Cantidad:")

    marco_tabla, tabla = crear_tabla(
        pestana,
        ("Cód. Producto", "Producto", "ID Bodega", "Bodega", "Stock Actual"),
        (100, 200, 90, 200, 110),
        alto=20
    )
    marco_tabla.pack(side="left", fill="both", expand=True)

    def cargar_combos():
        prods = [f"{p[0]} - {p[1]}" for p in consultar("SELECT codigo, nombre FROM productos ORDER BY nombre")]
        bods = [f"{b[0]} - {b[1]}" for b in consultar("SELECT id_bodega, nombre FROM bodega ORDER BY nombre")]
        cmb_prod["values"] = prods
        cmb_tr_prod["values"] = prods
        cmb_bod["values"] = bods
        cmb_tr_orig["values"] = bods
        cmb_tr_dest["values"] = bods

    def cargar_datos():
        sql = """
            SELECT ib.id_articulo, p.nombre, ib.id_bodega, b.nombre, ib.stock_actual
            FROM inventario_bodega ib
            INNER JOIN productos p ON p.codigo = ib.id_articulo
            INNER JOIN bodega b    ON b.id_bodega = ib.id_bodega
            ORDER BY b.nombre, p.nombre
        """
        llenar_tabla(tabla, consultar(sql), usar_primera_columna_como_id=False)
        cargar_combos()

    def guardar_stock():
        id_art = id_desde_combo(cmb_prod.get())
        id_b = id_desde_combo(cmb_bod.get())
        cant = leer_entero(txt_stock.get(), "Stock actual")
        if id_art is None or id_b is None or cant is None:
            return
        sql = """
            INSERT INTO inventario_bodega (id_articulo, id_bodega, stock_actual)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE stock_actual = %s
        """
        if ejecutar(sql, (id_art, id_b, cant, cant)) is not None:
            messagebox.showinfo("Éxito", "Stock registrado en la bodega.")
            cargar_datos()

    def ejecutar_transferencia():
        """Llama al procedimiento almacenado SP_ActualizarInventarioBodega."""
        id_art = id_desde_combo(cmb_tr_prod.get())
        id_orig = id_desde_combo(cmb_tr_orig.get())
        id_dest = id_desde_combo(cmb_tr_dest.get())
        cant = leer_entero(txt_tr_cant.get(), "Cantidad")

        if not id_art or not id_orig or not id_dest or cant is None:
            messagebox.showwarning("Campos incompletos", "Diligencia todos los campos de la transferencia.")
            return

        if id_orig == id_dest:
            messagebox.showwarning("Error", "La bodega de origen y destino deben ser distintas.")
            return

        con = obtener_conexion()
        if not con:
            return
        cur = None
        try:
            cur = con.cursor()
            cur.callproc("SP_ActualizarInventarioBodega", (int(id_art), int(id_orig), int(id_dest), cant))
            con.commit()
            messagebox.showinfo("Transferencia Exitosa", "¡Inventario transferido correctamente mediante el procedimiento SP_ActualizarInventarioBodega!")
            cargar_datos()
        except Error as e:
            con.rollback()
            messagebox.showerror("Error en Transferencia", f"Fallo al transferir: {traducir_error(e)}")
        finally:
            cerrar_conexion(con, cur)

    # Botones
    if not solo_lectura:
        ttk.Button(form_stock, text="Guardar Stock", style="Exito.TButton", command=guardar_stock).grid(row=3, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Button(form_transf, text="EJECUTAR SP_ActualizarInventarioBodega", style="Primario.TButton", command=ejecutar_transferencia).grid(row=4, column=0, columnspan=2, sticky="ew", pady=6)

    ttk.Button(panel_izq, text="Recargar inventario", command=cargar_datos).pack(fill="x", pady=10)
    cargar_datos()
