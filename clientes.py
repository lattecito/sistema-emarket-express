"""
clientes.py
===========
Módulo de GESTIÓN DE CLIENTES (Crear y Eliminar) para Administradores y Cajeros.

Permite:
1. Registrar nuevos clientes en la tabla 'usuario' de MariaDB (Cédula, Nombre, Apellido, Correo, Teléfono).
2. Listar clientes con búsqueda en tiempo real y conteo de pedidos acumulados.
3. Eliminar clientes con confirmación segura y advertencia de pedidos asociados en cascada.
4. Diálogo emergente rápido ( Nuevo Cliente) para utilizar directamente mientras se registra una venta.
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox
# pyrefly: ignore[missing-import]
from mysql.connector import Error

from conexion import (
    consultar, ejecutar, obtener_conexion, cerrar_conexion, traducir_error
)


def crear_cliente_db(cedula, nombre, apellido, correo, telefono):
    """
    Inserta un nuevo cliente en la tabla 'usuario' asignando rol = 'Cliente'.
    Calcula id_usuario = MAX(id_usuario) + 1 para compatibilidad.
    Retorna (True, nuevo_id) o (False, mensaje_error).
    """
    # Validar que cédula sea entero
    try:
        cedula_int = int(cedula)
        if cedula_int <= 0:
            return False, "La cédula debe ser un número positivo."
    except ValueError:
        return False, "La cédula debe contener exclusivamente números."

    # Validar nombres
    if not nombre.strip():
        return False, "El nombre del cliente no puede estar vacío."
    if not apellido.strip():
        return False, "El apellido del cliente no puede estar vacío."

    # Validar correo
    correo_limpio = correo.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo_limpio):
        return False, "Por favor ingresa un correo electrónico válido (ej: cliente@correo.com)."

    # Validar teléfono (compatible con VARCHAR(20) e INT)
    tel_limpio = re.sub(r"[^\d+]", "", str(telefono).strip())
    if not tel_limpio:
        return False, "El teléfono no puede estar vacío y debe contener dígitos válidos."
    if len(tel_limpio) > 20:
        return False, "El teléfono no puede superar los 20 caracteres."

    # Verificar si la cédula ya existe
    existe_cedula = consultar("SELECT id_usuario FROM usuario WHERE cedula = %s;", (cedula_int,), mostrar_error=False)
    if existe_cedula:
        return False, f"Ya existe un cliente registrado con la cédula {cedula_int}."

    # Verificar si el correo ya existe
    existe_correo = consultar("SELECT id_usuario FROM usuario WHERE LOWER(correo) = %s;", (correo_limpio,), mostrar_error=False)
    if existe_correo:
        return False, f"Ya existe un cliente registrado con el correo '{correo_limpio}'."

    # Obtener el siguiente ID de usuario disponible
    fila_id = consultar("SELECT IFNULL(MAX(id_usuario), 0) + 1 FROM usuario;", mostrar_error=False)
    nuevo_id = fila_id[0][0] if fila_id else 1

    sql = """
        INSERT INTO usuario (id_usuario, cedula, nombre, apellido, correo, telefono, rol)
        VALUES (%s, %s, %s, %s, %s, %s, 'Cliente');
    """
    resultado = ejecutar(
        sql,
        (nuevo_id, cedula_int, nombre.strip(), apellido.strip(), correo_limpio, tel_limpio),
        mostrar_error=False
    )

    if resultado is None:
        sql_auto = """
            INSERT INTO usuario (cedula, nombre, apellido, correo, telefono, rol)
            VALUES (%s, %s, %s, %s, %s, 'Cliente');
        """
        resultado = ejecutar(
            sql_auto,
            (cedula_int, nombre.strip(), apellido.strip(), correo_limpio, tel_limpio),
            mostrar_error=False
        )

    if resultado is not None:
        return True, nuevo_id
    else:
        return False, "No se pudo registrar el cliente en la base de datos."


def eliminar_cliente_db(id_usuario):
    """
    Elimina un cliente de la tabla 'usuario' (rol = 'Cliente').
    Captura el error 1451 de MySQL (ON DELETE RESTRICT) si el cliente tiene compras asociadas.
    Retorna (True, None) o (False, mensaje_error).
    """
    # 1. Verificar si el cliente existe y es de rol Cliente
    filas = consultar(
        "SELECT nombre, apellido FROM usuario WHERE id_usuario = %s AND (rol = 'Cliente' OR rol IS NULL OR rol = '');",
        (id_usuario,),
        mostrar_error=False
    )
    if not filas:
        return False, f"El cliente con ID {id_usuario} no fue encontrado o no tiene rol de Cliente."
    nom_cli = f"{filas[0][0]} {filas[0][1]}"

    # 2. Validación preventiva de compras existentes (ON DELETE RESTRICT)
    filas_ped = consultar(
        "SELECT COUNT(*) FROM pedido WHERE usuario_pedido = %s;",
        (id_usuario,),
        mostrar_error=False
    )
    if filas_ped and filas_ped[0][0] > 0:
        cant_ped = filas_ped[0][0]
        return False, (
            f"Acción Bloqueada (Error 1451 - Restricción de Clave Foránea RESTRICT):\n\n"
            f"No es posible eliminar al cliente '{nom_cli}' porque tiene {cant_ped} pedido(s) registrado(s).\n\n"
            f"La llave foránea 'fk_pedido_usuario' con regla 'ON DELETE RESTRICT' impide eliminar clientes "
            f"con compras asociadas para preservar la integridad histórica de las ventas."
        )

    # 3. Ejecución directa con captura de error 1451
    conexion = obtener_conexion()
    if not conexion:
        return False, "No se pudo conectar a la base de datos."

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "DELETE FROM usuario WHERE id_usuario = %s AND (rol = 'Cliente' OR rol IS NULL OR rol = '');",
            (id_usuario,)
        )
        conexion.commit()
        if cursor.rowcount > 0:
            return True, None
        else:
            return False, "No se pudo eliminar el cliente."
    except Error as e:
        conexion.rollback()
        if getattr(e, "errno", None) == 1451 or "1451" in str(e):
            return False, (
                "Acción Bloqueada (Error 1451 - Restricción de Clave Foránea RESTRICT):\n\n"
                f"No es posible eliminar al cliente '{nom_cli}' porque tiene pedidos vinculados en la tabla 'pedido'.\n"
                f"La regla ON DELETE RESTRICT protege la integridad referencial."
            )
        return False, traducir_error(e)
    finally:
        cerrar_conexion(conexion, cursor)


def listar_clientes_db(busqueda=""):
    """
    Retorna la lista de clientes con su información y conteo de pedidos asociados,
    asegurando filtrar exclusivamente los registros con rol = 'Cliente'.
    """
    termino = f"%{busqueda.strip().lower()}%"
    sql = """
        SELECT u.id_usuario, u.cedula, u.nombre, u.apellido, u.correo, u.telefono,
               COUNT(p.id_pedido) AS total_pedidos
        FROM usuario u
        LEFT JOIN pedido p ON u.id_usuario = p.usuario_pedido
        WHERE (u.rol = 'Cliente' OR u.rol IS NULL OR u.rol = '')
          AND (LOWER(u.nombre) LIKE %s 
           OR LOWER(u.apellido) LIKE %s 
           OR CAST(u.cedula AS CHAR) LIKE %s 
           OR LOWER(u.correo) LIKE %s)
        GROUP BY u.id_usuario, u.cedula, u.nombre, u.apellido, u.correo, u.telefono
        ORDER BY u.nombre ASC, u.apellido ASC;
    """
    return consultar(sql, (termino, termino, termino, termino))


def crear_tabla(padre, columnas, anchos=None, alto=12):
    """Crea un Treeview ttk estilizado con barra de desplazamiento vertical."""
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


def llenar_tabla(tabla, filas):
    """Limpia y llena los datos en el Treeview."""
    tabla.delete(*tabla.get_children())
    for fila in filas:
        valores = ["" if val is None else str(val) for val in fila]
        tabla.insert("", "end", iid=str(fila[0]), values=valores)


def abrir_dialogo_nuevo_cliente(padre, al_guardar_exitoso=None):
    """
    Ventana modal emergente para registrar rápidamente un cliente desde cualquier módulo.
    Ideal para crearlo en el momento de la venta en 'Pedidos y Transacciones'.
    """
    modal = tk.Toplevel(padre)
    modal.title("Registrar Nuevo Cliente")
    modal.resizable(False, False)
    modal.grab_set()

    ancho, alto = 420, 410
    x = padre.winfo_rootx() + (padre.winfo_width() - ancho) // 2
    y = padre.winfo_rooty() + (padre.winfo_height() - alto) // 2
    modal.geometry(f"{ancho}x{alto}+{x}+{y}")

    estilo = ttk.Style(modal)
    estilo.configure("EncabezadoModal.TFrame", background="#1e3a5f")
    estilo.configure("EncabezadoModal.TLabel", background="#1e3a5f", foreground="white", font=("Segoe UI", 11, "bold"))

    enc = ttk.Frame(modal, style="EncabezadoModal.TFrame", padding=12)
    enc.pack(fill="x")
    ttk.Label(enc, text=" Nuevo Cliente", style="EncabezadoModal.TLabel").pack()

    cuerpo = ttk.Frame(modal, padding=16)
    cuerpo.pack(fill="both", expand=True)

    ttk.Label(cuerpo, text="Cédula / Identificación:").pack(anchor="w")
    ent_cedula = ttk.Entry(cuerpo, width=36)
    ent_cedula.pack(fill="x", pady=(2, 8))
    ent_cedula.focus()

    ttk.Label(cuerpo, text="Nombre:").pack(anchor="w")
    ent_nombre = ttk.Entry(cuerpo, width=36)
    ent_nombre.pack(fill="x", pady=(2, 8))

    ttk.Label(cuerpo, text="Apellido:").pack(anchor="w")
    ent_apellido = ttk.Entry(cuerpo, width=36)
    ent_apellido.pack(fill="x", pady=(2, 8))

    ttk.Label(cuerpo, text="Correo Electrónico:").pack(anchor="w")
    ent_correo = ttk.Entry(cuerpo, width=36)
    ent_correo.pack(fill="x", pady=(2, 8))

    ttk.Label(cuerpo, text="Teléfono de Contacto:").pack(anchor="w")
    ent_telefono = ttk.Entry(cuerpo, width=36)
    ent_telefono.pack(fill="x", pady=(2, 14))

    def guardar():
        ced = ent_cedula.get().strip()
        nom = ent_nombre.get().strip()
        ape = ent_apellido.get().strip()
        cor = ent_correo.get().strip()
        tel = ent_telefono.get().strip()

        exito, resultado = crear_cliente_db(ced, nom, ape, cor, tel)
        if exito:
            messagebox.showinfo(
                "Cliente Registrado",
                f"¡Cliente {nom} {ape} registrado con éxito en el sistema!\nID asignado: {resultado}"
            )
            modal.destroy()
            if al_guardar_exitoso:
                al_guardar_exitoso(resultado)
        else:
            messagebox.showerror("Error al Guardar Cliente", resultado)

    btn_guardar = ttk.Button(cuerpo, text="Guardar Cliente", style="Exito.TButton", command=guardar)
    btn_guardar.pack(fill="x", ipady=3)

    ttk.Button(cuerpo, text="Cancelar", command=modal.destroy).pack(fill="x", pady=(6, 0))


def abrir_dialogo_gestionar_clientes(padre, al_cerrar=None):
    """
    Ventana modal completa para administrar (ver, crear y eliminar) clientes.
    """
    modal = tk.Toplevel(padre)
    modal.title("Gestión de Clientes (Administrador y Cajeros)")
    modal.minsize(980, 560)
    modal.grab_set()

    x = padre.winfo_rootx() + (padre.winfo_width() - 1000) // 2
    y = padre.winfo_rooty() + (padre.winfo_height() - 580) // 2
    modal.geometry(f"1000x580+{max(x, 50)}+{max(y, 50)}")

    def al_terminar():
        modal.destroy()
        if al_cerrar:
            al_cerrar()

    crear_modulo_clientes(modal, al_modificar_clientes=al_cerrar)
    modal.protocol("WM_DELETE_WINDOW", al_terminar)


def crear_modulo_clientes(padre, al_modificar_clientes=None):
    """
    Construye la interfaz completa de gestión de clientes (Crear y Eliminar)
    para ser incrustada en pestañas o ventanas modales.
    """
    contenedor = ttk.Frame(padre, padding=12)
    contenedor.pack(fill="both", expand=True)

    # Columna izquierda: Formulario de Creación
    izq = ttk.Frame(contenedor, width=320)
    izq.pack(side="left", fill="y", padx=(0, 12))

    # Columna derecha: Lista de clientes y búsqueda
    der = ttk.Frame(contenedor)
    der.pack(side="left", fill="both", expand=True)

    # PANEL IZQUIERDO: FORMULARIO
    marco_form = ttk.LabelFrame(izq, text="Registrar Nuevo Cliente", padding=12)
    marco_form.pack(fill="x")

    ttk.Label(marco_form, text="Cédula:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_cedula = ttk.Entry(marco_form, width=30)
    ent_cedula.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Nombre:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_nombre = ttk.Entry(marco_form, width=30)
    ent_nombre.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Apellido:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_apellido = ttk.Entry(marco_form, width=30)
    ent_apellido.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Correo Electrónico:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_correo = ttk.Entry(marco_form, width=30)
    ent_correo.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Teléfono:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_telefono = ttk.Entry(marco_form, width=30)
    ent_telefono.pack(fill="x", pady=(0, 12))

    def limpiar_form():
        ent_cedula.delete(0, "end")
        ent_nombre.delete(0, "end")
        ent_apellido.delete(0, "end")
        ent_correo.delete(0, "end")
        ent_telefono.delete(0, "end")
        ent_cedula.focus()

    def guardar_cliente():
        ced = ent_cedula.get().strip()
        nom = ent_nombre.get().strip()
        ape = ent_apellido.get().strip()
        cor = ent_correo.get().strip()
        tel = ent_telefono.get().strip()

        exito, resultado = crear_cliente_db(ced, nom, ape, cor, tel)
        if exito:
            messagebox.showinfo(
                "Cliente Creado",
                f"¡Cliente {nom} {ape} (C.C. {ced}) registrado con éxito en MariaDB!\n"
                f"ID en base de datos: {resultado}"
            )
            limpiar_form()
            cargar_clientes()
            if al_modificar_clientes:
                al_modificar_clientes()
        else:
            messagebox.showerror("Error al Crear Cliente", resultado)

    btn_crear = ttk.Button(marco_form, text="GUARDAR CLIENTE", style="Exito.TButton", command=guardar_cliente)
    btn_crear.pack(fill="x", pady=(4, 6), ipady=3)

    btn_limpiar = ttk.Button(marco_form, text="Limpiar Formulario", command=limpiar_form)
    btn_limpiar.pack(fill="x")

    # Tarjeta informativa
    info_tarjeta = ttk.LabelFrame(izq, text="Permisos de Cliente", padding=10)
    info_tarjeta.pack(fill="x", pady=(14, 0))
    ttk.Label(
        info_tarjeta,
        text="• Autorizado para Administradores y Cajeros.\n"
             "• Permite registrar clientes antes de la venta.\n"
             "• La eliminación verifica pedidos existentes.",
        foreground="#4a5568",
        font=("Segoe UI", 9)
    ).pack(anchor="w")

    # PANEL DERECHO: BÚSQUEDA Y TABLA
    marco_lista = ttk.LabelFrame(der, text="Clientes Registrados en MariaDB", padding=10)
    marco_lista.pack(fill="both", expand=True)

    # Barra superior de búsqueda
    barra_busqueda = ttk.Frame(marco_lista)
    barra_busqueda.pack(fill="x", pady=(0, 8))

    ttk.Label(barra_busqueda, text="Buscar:").pack(side="left", padx=(0, 5))
    ent_busqueda = ttk.Entry(barra_busqueda, width=28)
    ent_busqueda.pack(side="left", padx=(0, 6))

    ttk.Button(barra_busqueda, text="Buscar", command=lambda: cargar_clientes()).pack(side="left")
    ttk.Button(barra_busqueda, text="Limpiar Filtro", command=lambda: (ent_busqueda.delete(0, "end"), cargar_clientes())).pack(side="left", padx=5)

    lbl_total = ttk.Label(barra_busqueda, text="Total: 0 cliente(s)", font=("Segoe UI", 9, "italic"), foreground="#5a6b7d")
    lbl_total.pack(side="right")

    # Tabla de clientes
    marco_tabla, tabla_clientes = crear_tabla(
        marco_lista,
        ("ID", "Cédula", "Nombre", "Apellido", "Correo Electrónico", "Teléfono", "Pedidos Acumulados"),
        (50, 100, 130, 130, 180, 100, 120),
        alto=16
    )
    marco_tabla.pack(fill="both", expand=True)

    def cargar_clientes():
        busqueda = ent_busqueda.get()
        filas = listar_clientes_db(busqueda)
        llenar_tabla(tabla_clientes, filas)
        lbl_total.configure(text=f"Total: {len(filas)} cliente(s)")

    ent_busqueda.bind("<KeyRelease>", lambda e: cargar_clientes())

    # Barra inferior de acciones
    barra_inferior = ttk.Frame(marco_lista)
    barra_inferior.pack(fill="x", pady=(8, 0))

    def eliminar_cliente_seleccionado():
        seleccion = tabla_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Seleccionar Cliente", "Por favor selecciona un cliente de la tabla para eliminarlo.")
            return

        id_usuario = seleccion[0]
        item = tabla_clientes.item(id_usuario)
        valores = item.get("values", [])
        if not valores or len(valores) < 4:
            return

        cedula, nombre, apellido = valores[1], valores[2], valores[3]
        total_pedidos = 0
        try:
            total_pedidos = int(valores[6])
        except:
            pass

        if total_pedidos > 0:
            messagebox.showerror(
                "Eliminación Bloqueada (Error 1451)",
                f"No es posible eliminar al cliente '{nombre} {apellido}' (C.C. {cedula}).\n\n"
                f"Tiene {total_pedidos} pedido(s) registrado(s) en la base de datos.\n"
                f"La restricción de integridad referencial 'ON DELETE RESTRICT' en 'pedido' "
                f"bloquea la eliminación de clientes con compras asociadas."
            )
            return

        mensaje_aviso = (
            f"¿Estás seguro de ELIMINAR al cliente '{nombre} {apellido}' (C.C. {cedula})?\n\n"
            f"Esta acción eliminará físicamente al cliente de la base de datos MariaDB.\n\n"
            f"¿Deseas continuar?"
        )

        if not messagebox.askyesno("Confirmar Eliminación", mensaje_aviso):
            return

        exito, error_msg = eliminar_cliente_db(id_usuario)
        if exito:
            messagebox.showinfo(
                "Cliente Eliminado",
                f"El cliente '{nombre} {apellido}' ha sido eliminado exitosamente de MariaDB."
            )
            cargar_clientes()
            if al_modificar_clientes:
                al_modificar_clientes()
        else:
            messagebox.showerror("Error al Eliminar Cliente", error_msg)

    btn_eliminar = ttk.Button(
        barra_inferior,
        text="Eliminar Cliente Seleccionado",
        style="Peligro.TButton",
        command=eliminar_cliente_seleccionado
    )
    btn_eliminar.pack(side="left", padx=(0, 6))

    btn_recargar = ttk.Button(
        barra_inferior,
        text="Recargar Lista",
        command=cargar_clientes
    )
    btn_recargar.pack(side="left")

    cargar_clientes()

