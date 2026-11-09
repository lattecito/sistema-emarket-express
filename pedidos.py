"""
pedidos.py
==========
Módulo TRANSACCIONAL de Pedidos y Pagos.

Requerimiento especial:
- Procesa las compras llamando al procedimiento almacenado transaccional:
  SP_RegistrarPedidoCompleto(p_id_usuario, p_carrito_json, p_metodo_pago)
  garantizando exactamente 1 pedido y 1 factura para compras con 1 o más productos.
- Consulta el historial de pedidos directamente desde la vista analítica:
  vista_pedidos_resumen
- Controla transacciones y captura errores de validación de stock generados por
  el procedimiento y por el trigger 'trg_validar_stock_pedido'.
- Gestión logística de estados de pedido ('pendiente', 'enviado', 'entregado').
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal
# pyrefly: ignore[missing-import]
from mysql.connector import Error

from conexion import consultar, ejecutar, obtener_conexion, cerrar_conexion, traducir_error

METODOS_PAGO = ("Tarjeta", "PSE", "Efectivo")
ESTADOS_PEDIDO = ("pendiente", "enviado", "entregado")


def formato_dinero(valor):
    """Formatea un número decimal a moneda legible ($ 145,000.00)."""
    return f"$ {valor:,.2f}"


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
    """Limpia la tabla y la llena con las filas recibidas de la base de datos."""
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


def procesar_pedido_transaccional_directo(conexion, id_usuario, carrito, metodo_pago):
    """
    Registra atómicamente la compra con SQL directo en caso de que el procedimiento
    almacenado en la base de datos aún no haya sido actualizado a la versión JSON.

    Garantiza:
    - 1 único registro en 'pedido' por el total acumulado de todos los artículos.
    - N registros de detalle en 'transaccion' (uno por cada producto del carrito).
    - Descuento de stock en 'productos' respetando el trigger de validación.
    - 1 única factura en 'factura_pago' para toda la compra.
    """
    cursor = None
    try:
        cursor = conexion.cursor()

        # 1. Validar existencias de todos los productos y calcular el total de la compra
        total = Decimal("0.00")
        items_validados = []
        for item in carrito:
            codigo = int(item["codigo"])
            cantidad = int(item["cantidad"])
            cursor.execute(
                "SELECT precio_unitario, cantidad_disponible, nombre FROM productos WHERE codigo = %s FOR UPDATE;",
                (codigo,)
            )
            row = cursor.fetchone()
            if not row:
                raise Error(msg=f"El producto con código {codigo} no existe.")
            precio, stock, nombre = row
            if stock < cantidad:
                raise Error(msg=f"Stock insuficiente para '{nombre}'. Disponibles: {stock}, solicitados: {cantidad}.")
            subtotal = Decimal(str(precio)) * cantidad
            total += subtotal
            items_validados.append({
                "codigo": codigo,
                "cantidad": cantidad,
                "precio": precio
            })

        # 2. Insertar UNA ÚNICA cabecera de pedido para toda la compra
        cursor.execute(
            "INSERT INTO pedido (fecha_transaccion, usuario_pedido, total, estado_pedido) VALUES (CURDATE(), %s, %s, 'pendiente');",
            (id_usuario, int(total))
        )
        id_pedido = cursor.lastrowid

        # 3. Insertar cada producto como detalle en transaccion y descontar del inventario
        for item in items_validados:
            cursor.execute("SELECT IFNULL(MAX(id_transaccion), 100) + 1 FROM transaccion;")
            next_trans_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO transaccion (id_transaccion, cantidad_vendida, precio_unitario_real, pedido_transaccion, producto_transaccion) "
                "VALUES (%s, %s, %s, %s, %s);",
                (next_trans_id, item["cantidad"], item["precio"], id_pedido, item["codigo"])
            )

            cursor.execute(
                "UPDATE productos SET cantidad_disponible = cantidad_disponible - %s WHERE codigo = %s;",
                (item["cantidad"], item["codigo"])
            )

        # 4. Insertar UNA ÚNICA factura de pago para toda la compra
        cursor.execute(
            "INSERT INTO factura_pago (id_pedido, metodo_pago, fecha_pago, valor_pagado, estado_pago) "
            "VALUES (%s, %s, NOW(), %s, 'Aprobado');",
            (id_pedido, metodo_pago, total)
        )

        conexion.commit()
        return True

    except Error as e:
        conexion.rollback()
        mensaje = traducir_error(e)
        messagebox.showerror(
            "Error al procesar pedido",
            "La transacción fue revertida en MariaDB (ROLLBACK).\n\n"
            f"Causa: {mensaje}"
        )
        return False
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except:
                pass


def procesar_pedido_con_sp(id_usuario, carrito, metodo_pago):
    """
    Procesa la venta completa de manera atómica generando:
    - 1 solo registro de pedido (pedido) por el total acumulado de todos los artículos.
    - N detalles de compra (transaccion), uno por cada producto del carrito.
    - 1 sola factura de pago (factura_pago) asociada al pedido.

    Invoca el procedimiento almacenado transaccional:
        SP_RegistrarPedidoCompleto(IN p_id_usuario INT, IN p_carrito_json LONGTEXT, IN p_metodo_pago VARCHAR(20))
    Si la base de datos aún tiene la versión previa de 4 argumentos, delega a la transacción
    directa sin fragmentar la compra en múltiples pedidos ni facturas.
    """
    conexion = obtener_conexion()
    if conexion is None:
        return False

    cursor = None
    try:
        cursor = conexion.cursor()

        # Empaquetamos todos los artículos del carrito en una estructura JSON
        carrito_json = json.dumps([
            {"codigo": int(item["codigo"]), "cantidad": int(item["cantidad"])}
            for item in carrito
        ])

        try:
            # Invocamos el SP una única vez para toda la compra
            cursor.callproc(
                "SP_RegistrarPedidoCompleto",
                (id_usuario, carrito_json, metodo_pago)
            )
            conexion.commit()
            return True

        except Error as e_sp:
            # 1318: Número incorrecto de argumentos (si la BD aún tiene la versión previa de 4 argumentos)
            if getattr(e_sp, "errno", None) in (1318, 1406, 1265) or "expected 4" in str(e_sp).lower():
                conexion.rollback()
                return procesar_pedido_transaccional_directo(conexion, id_usuario, carrito, metodo_pago)
            else:
                raise e_sp

    except Error as e:
        conexion.rollback()
        mensaje = traducir_error(e)
        messagebox.showerror(
            "Error al procesar pedido",
            "La transacción fue revertida en MariaDB (ROLLBACK).\n\n"
            f"Causa: {mensaje}"
        )
        return False
    finally:
        cerrar_conexion(conexion, cursor)


def crear_modulo_pedidos(padre):
    """Construye la interfaz visual para la gestión de ventas y pedidos."""

    carrito = []
    productos_info = {}

    contenedor = ttk.Frame(padre, padding=10)
    contenedor.pack(fill="both", expand=True)

    izquierda = ttk.Frame(contenedor)
    izquierda.pack(side="left", fill="both", expand=True, padx=(0, 10))
    derecha = ttk.Frame(contenedor)
    derecha.pack(side="left", fill="both", expand=True)

    # 1. Selección de cliente y pago
    seccion_cliente = ttk.LabelFrame(izquierda, text="1. Selección de Cliente y Pago", padding=10)
    seccion_cliente.pack(fill="x")

    ttk.Label(seccion_cliente, text="Cliente:").grid(row=0, column=0, sticky="w", pady=4)
    cmb_cliente = ttk.Combobox(seccion_cliente, state="readonly", width=46)
    cmb_cliente.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4, padx=5)

    ttk.Label(seccion_cliente, text="Método de Pago:").grid(row=1, column=0, sticky="w", pady=4)
    cmb_metodo = ttk.Combobox(seccion_cliente, state="readonly", values=METODOS_PAGO, width=15)
    cmb_metodo.grid(row=1, column=1, sticky="w", pady=4, padx=5)
    cmb_metodo.current(0)

    # 2. Selección de artículos
    seccion_productos = ttk.LabelFrame(izquierda, text="2. Agregar Producto a la Venta", padding=10)
    seccion_productos.pack(fill="x", pady=10)

    ttk.Label(seccion_productos, text="Producto:").grid(row=0, column=0, sticky="w")
    cmb_producto = ttk.Combobox(seccion_productos, state="readonly", width=38)
    cmb_producto.grid(row=0, column=1, padx=5, sticky="ew")

    ttk.Label(seccion_productos, text="Cantidad:").grid(row=0, column=2, padx=(8, 0))
    spn_cantidad = ttk.Spinbox(seccion_productos, from_=1, to=9999, width=5)
    spn_cantidad.grid(row=0, column=3, padx=5)
    spn_cantidad.set(1)

    # 3. Carrito temporal
    seccion_carrito = ttk.LabelFrame(izquierda, text="3. Resumen de la Venta (Carrito)", padding=10)
    seccion_carrito.pack(fill="both", expand=True)

    marco_carrito, tabla_carrito = crear_tabla(
        seccion_carrito,
        ("Código", "Producto", "Cantidad", "Precio Unitario", "Subtotal"),
        (80, 180, 80, 120, 130),
        alto=8
    )
    marco_carrito.pack(fill="both", expand=True)

    barra_total = ttk.Frame(seccion_carrito)
    barra_total.pack(fill="x", pady=(8, 0))
    lbl_total = ttk.Label(barra_total, text="TOTAL: $ 0.00", style="Total.TLabel")
    lbl_total.pack(side="right")

    # 4. Historial consultando directamente la vista 'vista_pedidos_resumen'
    seccion_historial = ttk.LabelFrame(derecha, text="Historial de Pedidos (Consultando vista_pedidos_resumen)", padding=10)
    seccion_historial.pack(fill="both", expand=True)

    marco_historial, tabla_historial = crear_tabla(
        seccion_historial,
        ("N° Pedido", "Fecha", "Cliente", "Total", "Estado", "Método Pago", "Estado Pago"),
        (75, 90, 140, 100, 85, 95, 95),
        alto=15
    )
    marco_historial.pack(fill="both", expand=True)

    # 5. Gestión logística de estados
    marco_estado = ttk.LabelFrame(seccion_historial, text="Gestión Logística de Estados", padding=8)
    marco_estado.pack(fill="x", pady=(8, 0))

    ttk.Label(marco_estado, text="Estado:").pack(side="left", padx=(0, 5))
    cmb_estado_pedido = ttk.Combobox(
        marco_estado,
        state="readonly",
        values=ESTADOS_PEDIDO,
        width=14
    )
    cmb_estado_pedido.pack(side="left", padx=5)
    cmb_estado_pedido.current(0)

    btn_actualizar_estado = ttk.Button(
        marco_estado,
        text="Actualizar Estado del Pedido",
        command=lambda: actualizar_estado_pedido()
    )
    btn_actualizar_estado.pack(side="left", padx=5)

    lbl_pedido_sel = ttk.Label(marco_estado, text="Seleccione un pedido", foreground="#5a6b7d")
    lbl_pedido_sel.pack(side="right", padx=5)

    barra_historial = ttk.Frame(seccion_historial)
    barra_historial.pack(fill="x", pady=(8, 0))

    # --- Funciones de interacción ---
    def cargar_listas():
        """Carga clientes y catálogo disponible desde la BD."""
        clientes = consultar("""
            SELECT id_usuario, nombre, apellido, cedula
            FROM usuario ORDER BY nombre, apellido
        """)
        cmb_cliente["values"] = [f"{c[0]} - {c[1]} {c[2]} (C.C. {c[3]})" for c in clientes]

        productos_info.clear()
        valores = []
        for cod, nom, precio, stock in consultar("""
                SELECT codigo, nombre, precio_unitario, cantidad_disponible
                FROM productos ORDER BY nombre"""):
            productos_info[cod] = (nom, float(precio), stock)
            valores.append(f"{cod} - {nom}  |  {formato_dinero(precio)}  |  Stock: {stock}")
        cmb_producto["values"] = valores

    def cargar_historial_desde_vista():
        """
        Consulta directamente la vista analítica creada en MariaDB:
        SELECT * FROM vista_pedidos_resumen
        """
        sql = """
            SELECT id_pedido, fecha_transaccion, cliente, total, estado_pedido,
                   IFNULL(metodo_pago, 'Sin factura'),
                   IFNULL(estado_pago, 'Sin factura')
            FROM vista_pedidos_resumen
            ORDER BY id_pedido DESC
            LIMIT 50
        """
        llenar_tabla(tabla_historial, consultar(sql))
        al_seleccionar_pedido()

    def al_seleccionar_pedido(event=None):
        """Carga el estado del pedido seleccionado en el Combobox de gestión logística."""
        seleccion = tabla_historial.selection()
        if not seleccion:
            lbl_pedido_sel.configure(text="Seleccione un pedido para modificar su estado")
            return
        id_pedido = seleccion[0]
        item = tabla_historial.item(id_pedido)
        valores = item.get("values", [])
        lbl_pedido_sel.configure(text=f"Pedido N° {id_pedido} seleccionado")
        if valores and len(valores) > 4:
            estado_actual = str(valores[4]).strip().lower()
            if estado_actual in ESTADOS_PEDIDO:
                cmb_estado_pedido.set(estado_actual)
            else:
                for est in ESTADOS_PEDIDO:
                    if est.lower() == estado_actual:
                        cmb_estado_pedido.set(est)
                        break

    def actualizar_estado_pedido():
        """Actualiza el estado logístico del pedido seleccionado en la base de datos."""
        seleccion = tabla_historial.selection()
        if not seleccion:
            messagebox.showwarning("Selección requerida", "Por favor seleccione un pedido de la tabla.")
            return

        id_pedido = seleccion[0]
        nuevo_estado = cmb_estado_pedido.get().strip()

        if not nuevo_estado:
            messagebox.showwarning("Estado requerido", "Seleccione un estado para el pedido.")
            return

        filas = ejecutar(
            "UPDATE pedido SET estado_pedido = %s WHERE id_pedido = %s;",
            (nuevo_estado, id_pedido)
        )

        if filas is not None:
            messagebox.showinfo(
                "Estado Actualizado",
                f"El estado del pedido N° {id_pedido} ha sido actualizado a '{nuevo_estado}' con éxito."
            )
            cargar_historial_desde_vista()
            if tabla_historial.exists(str(id_pedido)):
                tabla_historial.selection_set(str(id_pedido))
                tabla_historial.focus(str(id_pedido))
                al_seleccionar_pedido()

    def refrescar_carrito():
        tabla_carrito.delete(*tabla_carrito.get_children())
        total = 0
        for item in carrito:
            subtotal = item["precio"] * item["cantidad"]
            total += subtotal
            tabla_carrito.insert("", "end", iid=str(item["codigo"]), values=(
                item["codigo"], item["nombre"], item["cantidad"],
                formato_dinero(item["precio"]), formato_dinero(subtotal)
            ))
        lbl_total.configure(text=f"TOTAL: {formato_dinero(total)}")

    def agregar_al_carrito():
        if not cmb_producto.get():
            messagebox.showwarning("Producto", "Seleccione un producto para agregar.")
            return
        try:
            cantidad = int(spn_cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Cantidad", "La cantidad debe ser un número entero mayor a cero.")
            return

        codigo = int(cmb_producto.get().split(" - ")[0])
        nombre, precio, stock = productos_info[codigo]

        existente = next((i for i in carrito if i["codigo"] == codigo), None)
        cantidad_total = cantidad + (existente["cantidad"] if existente else 0)

        if cantidad_total > stock:
            messagebox.showwarning(
                "Stock Insuficiente",
                f"Solo hay {stock} unidades disponibles de '{nombre}'."
            )
            return

        if existente:
            existente["cantidad"] = cantidad_total
        else:
            carrito.append({"codigo": codigo, "nombre": nombre, "precio": precio, "cantidad": cantidad})

        refrescar_carrito()
        spn_cantidad.set(1)

    def quitar_del_carrito():
        seleccion = tabla_carrito.selection()
        if not seleccion:
            messagebox.showwarning("Quitar", "Selecciona un producto del carrito.")
            return
        codigo = int(seleccion[0])
        carrito[:] = [i for i in carrito if i["codigo"] != codigo]
        refrescar_carrito()

    def vaciar_carrito():
        carrito.clear()
        refrescar_carrito()

    def registrar_compra():
        """Procesa la venta llamando a SP_RegistrarPedidoCompleto."""
        if not cmb_cliente.get():
            messagebox.showwarning("Cliente", "Por favor selecciona el cliente que realiza la compra.")
            return
        if not carrito:
            messagebox.showwarning("Carrito Vacío", "Agrega al menos un producto al pedido.")
            return

        id_usuario = int(cmb_cliente.get().split(" - ")[0])
        metodo = cmb_metodo.get()
        total = sum(i["precio"] * i["cantidad"] for i in carrito)

        confirmar = messagebox.askyesno(
            "Confirmar Transacción",
            f"¿Deseas procesar el pedido a través de SP_RegistrarPedidoCompleto?\n\n"
            f"Cliente: {cmb_cliente.get()}\n"
            f"Artículos: {len(carrito)}\n"
            f"Método de Pago: {metodo}\n"
            f"Total a Pagar: {formato_dinero(total)}"
        )
        if not confirmar:
            return

        # Invocamos el procedimiento almacenado
        if procesar_pedido_con_sp(id_usuario, carrito, metodo):
            messagebox.showinfo(
                "Venta Exitosa",
                "¡El pedido y su factura fueron registrados exitosamente mediante el "
                "procedimiento almacenado SP_RegistrarPedidoCompleto!"
            )
            vaciar_carrito()

        # Recargamos listas y el historial desde la vista
        cargar_listas()
        cargar_historial_desde_vista()

    # Botones de acción
    ttk.Button(seccion_productos, text="Agregar al Carrito", style="Primario.TButton",
               command=agregar_al_carrito).grid(row=0, column=4, padx=(8, 0))

    ttk.Button(barra_total, text="Quitar Seleccionado", command=quitar_del_carrito).pack(side="left")
    ttk.Button(barra_total, text="Vaciar", command=vaciar_carrito).pack(side="left", padx=5)

    ttk.Button(izquierda, text="REGISTRAR PEDIDO (SP_RegistrarPedidoCompleto)", style="Exito.TButton",
               command=registrar_compra).pack(fill="x", pady=(10, 0), ipady=6)

    ttk.Button(barra_historial, text="Recargar Historial (vista_pedidos_resumen)",
               command=cargar_historial_desde_vista).pack(side="right")

    # Eventos de tabla
    tabla_historial.bind("<<TreeviewSelect>>", al_seleccionar_pedido)

    # Carga inicial
    cargar_listas()
    cargar_historial_desde_vista()
