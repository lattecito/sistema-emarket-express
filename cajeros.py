"""
cajeros.py
==========
Módulo EXCLUSIVO para el Administrador: Gestión de Cajeros en la tabla 'usuario'.

Requerimiento:
1. Administra los cajeros almacenados directamente en la tabla 'usuario' con rol = 'Cajero'.
2. Listar cajeros:
   SELECT id_usuario, cedula, nombre, apellido, correo, telefono 
   FROM usuario 
   WHERE rol = 'Cajero';
3. Crear nuevo cajero:
   INSERT INTO usuario (cedula, nombre, apellido, correo, telefono, contrasena, rol) 
   VALUES (%s, %s, %s, %s, %s, %s, 'Cajero');
4. Eliminar cajero:
   DELETE FROM usuario WHERE id_usuario = %s AND rol = 'Cajero';
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox
# pyrefly: ignore[missing-import]
from mysql.connector import Error

from conexion import (
    consultar, ejecutar, obtener_conexion, cerrar_conexion, traducir_error
)


def asegurar_estructura_usuario():
    """
    Garantiza que la tabla usuario cuente con los campos 'contrasena' y 'rol',
    y elimina la tabla obsoleta 'cajeros_app' si aún existe en la base de datos.
    Solo se ejecuta bajo privilegios de Administrador.
    """
    from conexion import obtener_sesion_actual
    sesion = obtener_sesion_actual()
    if sesion.get("rol") != "Administrador":
        return

    try:
        # 1. Eliminar la tabla obsoleta cajeros_app
        ejecutar("DROP TABLE IF EXISTS cajeros_app;", mostrar_error=False)
    except:
        pass

    try:
        # 2. Verificar y agregar columnas necesarias en usuario
        columnas = [c[0].lower() for c in consultar("SHOW COLUMNS FROM usuario;", mostrar_error=False)]
        if "contrasena" not in columnas:
            ejecutar("ALTER TABLE usuario ADD COLUMN contrasena VARCHAR(100) NULL AFTER telefono;", mostrar_error=False)
        if "rol" not in columnas:
            ejecutar("ALTER TABLE usuario ADD COLUMN rol VARCHAR(30) NOT NULL DEFAULT 'Cliente' AFTER contrasena;", mostrar_error=False)
            ejecutar("UPDATE usuario SET rol = 'Cliente' WHERE rol IS NULL OR rol = '';", mostrar_error=False)

        # 3. Intentar configurar AUTO_INCREMENT en id_usuario si no lo tiene
        try:
            ejecutar("ALTER TABLE usuario MODIFY id_usuario INT(11) NOT NULL AUTO_INCREMENT;", mostrar_error=False)
        except:
            pass
    except:
        pass


def listar_cajeros_db(busqueda=""):
    """
    Consulta y lista los cajeros registrados en la tabla 'usuario' (rol = 'Cajero').
    """
    asegurar_estructura_usuario()
    if busqueda.strip():
        termino = f"%{busqueda.strip().lower()}%"
        sql = """
            SELECT id_usuario, cedula, nombre, apellido, correo, telefono 
            FROM usuario 
            WHERE rol = 'Cajero'
              AND (LOWER(nombre) LIKE %s 
               OR LOWER(apellido) LIKE %s 
               OR CAST(cedula AS CHAR) LIKE %s 
               OR LOWER(correo) LIKE %s)
            ORDER BY id_usuario ASC;
        """
        return consultar(sql, (termino, termino, termino, termino))
    else:
        sql = """
            SELECT id_usuario, cedula, nombre, apellido, correo, telefono 
            FROM usuario 
            WHERE rol = 'Cajero'
            ORDER BY id_usuario ASC;
        """
        return consultar(sql)


def crear_cajero_db(cedula, nombre, apellido, correo, telefono, contrasena):
    """
    Inserta un nuevo operador cajero en la tabla 'usuario' con rol = 'Cajero'.
    """
    asegurar_estructura_usuario()

    # Validar cédula
    try:
        cedula_int = int(cedula)
        if cedula_int <= 0:
            return False, "La cédula debe ser un número positivo."
    except ValueError:
        return False, "La cédula debe contener solo números."

    # Validar nombres
    if not nombre.strip():
        return False, "El nombre del cajero es obligatorio."
    if not apellido.strip():
        return False, "El apellido del cajero es obligatorio."

    # Validar correo
    correo_limpio = correo.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo_limpio):
        return False, "Ingresa un correo electrónico válido (ej: cajero@emarket.com)."

    # Validar teléfono (compatible con VARCHAR(20) e INT)
    tel_limpio = re.sub(r"[^\d+]", "", str(telefono).strip())
    if not tel_limpio:
        return False, "El teléfono no puede estar vacío y debe contener dígitos válidos."
    if len(tel_limpio) > 20:
        return False, "El teléfono no puede superar los 20 caracteres."

    # Validar contraseña
    if not contrasena or len(contrasena) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."

    # Verificar cédula duplicada
    existe_ced = consultar("SELECT id_usuario FROM usuario WHERE cedula = %s;", (cedula_int,))
    if existe_ced:
        return False, f"Ya existe un usuario o cajero registrado con la cédula {cedula_int}."

    # Verificar correo duplicado
    existe_cor = consultar("SELECT id_usuario FROM usuario WHERE LOWER(correo) = %s;", (correo_limpio,))
    if existe_cor:
        return False, f"Ya existe un usuario o cajero registrado con el correo '{correo_limpio}'."

    # Inserción en la tabla usuario con rol = 'Cajero'
    sql = """
        INSERT INTO usuario (cedula, nombre, apellido, correo, telefono, contrasena, rol) 
        VALUES (%s, %s, %s, %s, %s, %s, 'Cajero');
    """
    res = ejecutar(sql, (cedula_int, nombre.strip(), apellido.strip(), correo_limpio, tel_limpio, contrasena))

    # Si la tabla no tiene AUTO_INCREMENT en id_usuario, insertamos calculando el id manualmente
    if res is None:
        sql_fallback = """
            INSERT INTO usuario (id_usuario, cedula, nombre, apellido, correo, telefono, contrasena, rol) 
            VALUES ((SELECT IFNULL(MAX(u2.id_usuario), 0) + 1 FROM usuario u2), %s, %s, %s, %s, %s, %s, 'Cajero');
        """
        res = ejecutar(sql_fallback, (cedula_int, nombre.strip(), apellido.strip(), correo_limpio, tel_limpio, contrasena))

    if res is not None:
        return True, None
    else:
        return False, "No se pudo registrar el cajero en la tabla 'usuario'."


def eliminar_cajero_db(id_usuario):
    """
    Elimina físicamente el registro del cajero de la tabla usuario donde rol = 'Cajero'.
    """
    asegurar_estructura_usuario()
    try:
        sql = "DELETE FROM usuario WHERE id_usuario = %s AND rol = 'Cajero';"
        res = ejecutar(sql, (id_usuario,))
        if res is not None and res > 0:
            return True, None
        elif res == 0:
            return False, f"No se encontró un cajero con ID {id_usuario}."
        else:
            return False, "No se pudo eliminar el cajero de la base de datos."
    except Error as e:
        return False, traducir_error(e)


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
        valores = ["" if val is None else str(val) for val in fila]
        if usar_primera_columna_como_id:
            tabla.insert("", "end", iid=str(fila[0]), values=valores)
        else:
            tabla.insert("", "end", values=valores)


def crear_modulo_cajeros(padre):
    """Construye la interfaz visual para la administración de usuarios cajeros en la tabla usuario."""
    asegurar_estructura_usuario()

    contenedor = ttk.Frame(padre, padding=12)
    contenedor.pack(fill="both", expand=True)

    # División en dos columnas
    izquierda = ttk.Frame(contenedor, width=340)
    izquierda.pack(side="left", fill="y", padx=(0, 14))

    derecha = ttk.Frame(contenedor)
    derecha.pack(side="left", fill="both", expand=True)

    # PANEL IZQUIERDO: Formulario de Creación
    marco_form = ttk.LabelFrame(izquierda, text="Registrar Nuevo Cajero", padding=14)
    marco_form.pack(fill="x")

    ttk.Label(marco_form, text="Cédula:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_cedula = ttk.Entry(marco_form, width=32)
    ent_cedula.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Nombre:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_nombre = ttk.Entry(marco_form, width=32)
    ent_nombre.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Apellido:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_apellido = ttk.Entry(marco_form, width=32)
    ent_apellido.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Correo Electrónico (Login):", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_correo = ttk.Entry(marco_form, width=32)
    ent_correo.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Teléfono:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_telefono = ttk.Entry(marco_form, width=32)
    ent_telefono.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Contraseña:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_clave = ttk.Entry(marco_form, width=32, show="•")
    ent_clave.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Confirmar Contraseña:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_clave_conf = ttk.Entry(marco_form, width=32, show="•")
    ent_clave_conf.pack(fill="x", pady=(0, 6))

    var_mostrar = tk.BooleanVar(value=False)
    def conmutar_clave():
        caracter = "" if var_mostrar.get() else "•"
        ent_clave.configure(show=caracter)
        ent_clave_conf.configure(show=caracter)

    chk_mostrar = ttk.Checkbutton(marco_form, text="Mostrar contraseñas", variable=var_mostrar, command=conmutar_clave)
    chk_mostrar.pack(anchor="w", pady=(0, 10))

    # Tarjeta informativa sobre permisos
    tarjeta_info = ttk.LabelFrame(izquierda, text="Información de Rol (Cajero)", padding=10)
    tarjeta_info.pack(fill="x", pady=(12, 0))

    info_texto = (
        "• Almacenado en tabla 'usuario' (rol = 'Cajero').\n"
        "• Acceso a pedidos, ventas y consulta de catálogo.\n"
        "• Conexión a MariaDB bajo rol seguro Cajero_App.\n"
        "• Sin acceso a reportes ni gestión de cajeros."
    )
    ttk.Label(tarjeta_info, text=info_texto, foreground="#34495e", font=("Segoe UI", 9)).pack(anchor="w")

    # PANEL DERECHO: Lista de Cajeros
    marco_lista = ttk.LabelFrame(derecha, text="Cajeros Registrados (tabla usuario WHERE rol = 'Cajero')", padding=12)
    marco_lista.pack(fill="both", expand=True)

    # Buscador superior
    barra_busq = ttk.Frame(marco_lista)
    barra_busq.pack(fill="x", pady=(0, 8))
    ttk.Label(barra_busq, text="Buscar:").pack(side="left", padx=(0, 5))
    ent_busq = ttk.Entry(barra_busq, width=25)
    ent_busq.pack(side="left", padx=(0, 6))

    lbl_total_cajeros = ttk.Label(barra_busq, text="Total: 0 cajero(s)", font=("Segoe UI", 10, "italic"), foreground="#5a6b7d")
    lbl_total_cajeros.pack(side="right", padx=5)

    marco_tabla, tabla_cajeros = crear_tabla(
        marco_lista,
        ("ID", "Cédula", "Nombre", "Apellido", "Correo Electrónico", "Teléfono"),
        (50, 100, 130, 130, 200, 110),
        alto=16
    )
    marco_tabla.pack(fill="both", expand=True)

    barra_acciones = ttk.Frame(marco_lista)
    barra_acciones.pack(fill="x", pady=(10, 0))

    def cargar_cajeros():
        asegurar_estructura_usuario()
        busqueda = ent_busq.get()
        filas = listar_cajeros_db(busqueda)
        llenar_tabla(tabla_cajeros, filas, usar_primera_columna_como_id=True)
        lbl_total_cajeros.configure(text=f"Total: {len(filas)} cajero(s)")

    ent_busq.bind("<KeyRelease>", lambda e: cargar_cajeros())

    def limpiar_formulario():
        ent_cedula.delete(0, "end")
        ent_nombre.delete(0, "end")
        ent_apellido.delete(0, "end")
        ent_correo.delete(0, "end")
        ent_telefono.delete(0, "end")
        ent_clave.delete(0, "end")
        ent_clave_conf.delete(0, "end")
        ent_cedula.focus()

    def registrar_cajero():
        ced = ent_cedula.get().strip()
        nom = ent_nombre.get().strip()
        ape = ent_apellido.get().strip()
        cor = ent_correo.get().strip()
        tel = ent_telefono.get().strip()
        clave = ent_clave.get().strip()
        clave_conf = ent_clave_conf.get().strip()

        if not ced or not nom or not ape or not cor or not tel or not clave:
            messagebox.showwarning("Campos Requeridos", "Por favor completa todos los campos del formulario.")
            return

        if clave != clave_conf:
            messagebox.showerror("Contraseñas no coinciden", "Las contraseñas ingresadas no coinciden.")
            ent_clave_conf.focus()
            return

        confirmar = messagebox.askyesno(
            "Confirmar Creación de Cajero",
            f"¿Deseas registrar al siguiente cajero en la tabla 'usuario'?\n\n"
            f"Nombre: {nom} {ape}\n"
            f"Cédula: {ced}\n"
            f"Correo: {cor}\n"
            f"Rol: Cajero\n\n"
            f"El cajero podrá iniciar sesión de inmediato con estas credenciales."
        )
        if not confirmar:
            return

        exito, error_msg = crear_cajero_db(ced, nom, ape, cor, tel, clave)
        if exito:
            messagebox.showinfo(
                "Cajero Registrado con Éxito",
                f"¡Cajero '{nom} {ape}' registrado exitosamente en la tabla 'usuario'!\n\n"
                f"Rol asignado: Cajero\n"
                f"Correo de acceso: {cor}\n\n"
                f"Ya puede iniciar sesión en la aplicación."
            )
            limpiar_formulario()
            cargar_cajeros()
        else:
            messagebox.showerror(
                "Error al Crear Cajero",
                f"No se pudo crear el cajero:\n\n{error_msg}"
            )

    def eliminar_cajero():
        seleccion = tabla_cajeros.selection()
        if not seleccion:
            messagebox.showwarning("Seleccionar Cajero", "Por favor selecciona un cajero de la lista para eliminar.")
            return

        id_usuario = seleccion[0]
        item = tabla_cajeros.item(id_usuario)
        valores = item.get("values", [])
        if not valores or len(valores) < 4:
            return

        cedula, nombre, apellido = valores[1], valores[2], valores[3]

        confirmar = messagebox.askyesno(
            "Confirmar Eliminación de Cajero",
            f"¿Estás seguro de ELIMINAR al cajero '{nombre} {apellido}' (C.C. {cedula})?\n\n"
            f"Esta acción eliminará físicamente el registro de la tabla usuario (WHERE rol = 'Cajero').\n\n"
            f"¿Deseas continuar?"
        )
        if not confirmar:
            return

        exito, error_msg = eliminar_cajero_db(id_usuario)
        if exito:
            messagebox.showinfo(
                "Cajero Eliminado",
                f"El cajero '{nombre} {apellido}' ha sido eliminado exitosamente de la base de datos."
            )
            cargar_cajeros()
        else:
            messagebox.showerror(
                "Error al Eliminar Cajero",
                f"No se pudo eliminar el cajero:\n\n{error_msg}"
            )

    # Botones en formulario izquierdo
    btn_crear = ttk.Button(marco_form, text="REGISTRAR CAJERO", style="Exito.TButton", command=registrar_cajero)
    btn_crear.pack(fill="x", pady=(6, 4), ipady=4)

    btn_limpiar = ttk.Button(marco_form, text="Limpiar Formulario", command=limpiar_formulario)
    btn_limpiar.pack(fill="x")

    # Botones en panel derecho
    btn_eliminar = ttk.Button(barra_acciones, text="Eliminar Cajero Seleccionado", style="Peligro.TButton", command=eliminar_cajero)
    btn_eliminar.pack(side="left", padx=(0, 6))

    btn_recargar = ttk.Button(barra_acciones, text="Recargar Lista", command=cargar_cajeros)
    btn_recargar.pack(side="left")

    cargar_cajeros()
