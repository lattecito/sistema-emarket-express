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

from conexion import consultar, ejecutar_seguro, traducir_error
from estilos import FUENTE

# E15: Teléfono con 7 a 15 dígitos numéricos (opcionalmente con un '+' inicial)
PATRON_TELEFONO = re.compile(r"^\+?\d{7,15}$")
LONGITUD_MIN_CLAVE = 4


def listar_cajeros_db(busqueda=""):
    """
    Consulta y lista los cajeros registrados en la tabla 'usuario' (rol = 'Cajero').
    E7: Solo se ejecutan consultas SELECT (sin DDL en tiempo de ejecución).
    """
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

    # E15: Validar teléfono (7 a 15 dígitos numéricos; se ignoran espacios y guiones)
    tel_limpio = re.sub(r"[\s\-()]", "", str(telefono).strip())
    if not PATRON_TELEFONO.match(tel_limpio):
        return False, "El teléfono debe contener entre 7 y 15 dígitos numéricos (ej: 3115559988)."

    # Validar longitudes según la tabla usuario
    if len(nombre.strip()) > 50 or len(apellido.strip()) > 50 or len(correo_limpio) > 50:
        return False, "Nombre, apellido y correo no pueden superar los 50 caracteres."

    # Validar contraseña
    if not contrasena or len(contrasena) < LONGITUD_MIN_CLAVE:
        return False, f"La contraseña debe tener al menos {LONGITUD_MIN_CLAVE} caracteres."

    # Verificar cédula duplicada
    existe_ced = consultar("SELECT id_usuario FROM usuario WHERE cedula = %s;", (cedula_int,))
    if existe_ced:
        return False, f"Ya existe un usuario o cajero registrado con la cédula {cedula_int}."

    # Verificar correo duplicado
    existe_cor = consultar("SELECT id_usuario FROM usuario WHERE LOWER(correo) = %s;", (correo_limpio,))
    if existe_cor:
        return False, f"Ya existe un usuario o cajero registrado con el correo '{correo_limpio}'."

    # Inserción en la tabla usuario con rol = 'Cajero' (id_usuario es AUTO_INCREMENT - E22)
    sql = """
        INSERT INTO usuario (cedula, nombre, apellido, correo, telefono, contrasena, rol) 
        VALUES (%s, %s, %s, %s, %s, %s, 'Cajero');
    """
    res, error = ejecutar_seguro(sql, (cedula_int, nombre.strip(), apellido.strip(), correo_limpio, tel_limpio, contrasena))
    if error is not None:
        return False, traducir_error(error)
    if res is not None:
        return True, None
    return False, "No se pudo registrar el cajero en la tabla 'usuario'."


def eliminar_cajero_db(id_usuario):
    """
    Elimina físicamente el registro del cajero de la tabla usuario donde rol = 'Cajero'.
    """
    res, error = ejecutar_seguro("DELETE FROM usuario WHERE id_usuario = %s AND rol = 'Cajero';", (id_usuario,))
    if error is not None:
        if getattr(error, "errno", None) == 1451:
            return False, "No se puede eliminar el cajero porque tiene pedidos asociados."
        return False, traducir_error(error)
    if res is not None and res > 0:
        return True, None
    if res == 0:
        return False, f"No se encontró un cajero con ID {id_usuario}."
    return False, "No se pudo eliminar el cajero de la base de datos."


def crear_tabla(padre, columnas, anchos=None, alto=12):
    """Crea una tabla ttk.Treeview con barras de desplazamiento vertical y horizontal (E13)."""
    marco = ttk.Frame(padre)
    ids = [f"c{i}" for i in range(len(columnas))]
    tabla = ttk.Treeview(marco, columns=ids, show="headings", height=alto)

    for i, titulo in enumerate(columnas):
        ancho = anchos[i] if anchos else 120
        tabla.heading(ids[i], text=titulo)
        tabla.column(ids[i], width=ancho, minwidth=50, anchor="center", stretch=False)

    barra_v = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    barra_h = ttk.Scrollbar(marco, orient="horizontal", command=tabla.xview)
    tabla.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)

    tabla.grid(row=0, column=0, sticky="nsew")
    barra_v.grid(row=0, column=1, sticky="ns")
    barra_h.grid(row=1, column=0, sticky="ew")
    marco.rowconfigure(0, weight=1)
    marco.columnconfigure(0, weight=1)
    return marco, tabla


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

    ttk.Label(marco_form, text="Cédula:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_cedula = ttk.Entry(marco_form, width=32)
    ent_cedula.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Nombre:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_nombre = ttk.Entry(marco_form, width=32)
    ent_nombre.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Apellido:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_apellido = ttk.Entry(marco_form, width=32)
    ent_apellido.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Correo Electrónico (Login):", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_correo = ttk.Entry(marco_form, width=32)
    ent_correo.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Teléfono:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_telefono = ttk.Entry(marco_form, width=32)
    ent_telefono.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Contraseña:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
    ent_clave = ttk.Entry(marco_form, width=32, show="•")
    ent_clave.pack(fill="x", pady=(0, 8))

    ttk.Label(marco_form, text="Confirmar Contraseña:", font=(FUENTE, 10, "bold")).pack(anchor="w", pady=(0, 2))
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
    ttk.Label(tarjeta_info, text=info_texto, foreground="#34495e", font=(FUENTE, 9)).pack(anchor="w")

    # PANEL DERECHO: Lista de Cajeros
    marco_lista = ttk.LabelFrame(derecha, text="Cajeros Registrados (tabla usuario WHERE rol = 'Cajero')", padding=12)
    marco_lista.pack(fill="both", expand=True)

    # Buscador superior
    barra_busq = ttk.Frame(marco_lista)
    barra_busq.pack(fill="x", pady=(0, 8))
    ttk.Label(barra_busq, text="Buscar:").pack(side="left", padx=(0, 5))
    ent_busq = ttk.Entry(barra_busq, width=25)
    ent_busq.pack(side="left", padx=(0, 6))

    lbl_total_cajeros = ttk.Label(barra_busq, text="Total: 0 cajero(s)", font=(FUENTE, 10, "italic"), foreground="#5a6b7d")
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
        # E7: Solo consulta (SELECT); no se ejecuta DDL al teclear en el buscador
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

        # E17: Validar longitud mínima de la contraseña ANTES de pedir confirmación
        if len(clave) < LONGITUD_MIN_CLAVE:
            messagebox.showwarning(
                "Contraseña muy corta",
                f"La contraseña debe tener al menos {LONGITUD_MIN_CLAVE} caracteres."
            )
            ent_clave.focus()
            return

        # E15: Validar teléfono antes de confirmar
        if not PATRON_TELEFONO.match(re.sub(r"[\s\-()]", "", tel)):
            messagebox.showwarning("Teléfono inválido", "El teléfono debe contener entre 7 y 15 dígitos numéricos.")
            ent_telefono.focus()
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
    btn_eliminar = ttk.Button(barra_acciones, text="Eliminar Cajero", style="Peligro.TButton", command=eliminar_cajero)
    btn_eliminar.pack(side="left", padx=(0, 6))

    btn_recargar = ttk.Button(barra_acciones, text="Recargar Lista", command=cargar_cajeros)
    btn_recargar.pack(side="left")

    cargar_cajeros()
