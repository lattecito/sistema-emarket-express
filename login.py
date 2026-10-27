"""
login.py
========
Módulo de Autenticación e Inicio de Sesión sobre MariaDB / MySQL.

Cuentas configuradas en la base de datos MariaDB:
- admin_db   (Clave: Admin2026*Seguro) -> Rol: Administrador
- cajero_app (Clave: Cajero2026*App)   -> Rol: Cajero
- root       (Sin clave por defecto)  -> Rol: Administrador

¿Cómo funciona este módulo?
1. El usuario ingresa su cuenta y contraseña de MariaDB (o pulsa un acceso rápido).
2. Se prueba la autenticación en tiempo real conectándose al servidor MySQL en el puerto 3306.
3. Si la conexión es exitosa:
   - Se identifica el rol asignado (Administrador o Cajero).
   - Se configuran las credenciales en conexion.establecer_sesion(...) para que toda la
     aplicación opere bajo los privilegios correspondientes de MariaDB.
4. Si las credenciales fallan, se muestra el error de acceso denegado.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from conexion import probar_conexion, establecer_sesion


def centrar_ventana(ventana, ancho, alto):
    """Ubica la ventana en el centro de la pantalla según la resolución del monitor."""
    x = (ventana.winfo_screenwidth() - ancho) // 2
    y = (ventana.winfo_screenheight() - alto) // 3
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


def pedir_login():
    """
    Despliega la ventana de autenticación de MariaDB.
    Retorna un diccionario con {usuario, rol} si inicia sesión con éxito, o None si cancela.
    """
    usuario_autenticado = {}

    ventana = tk.Tk()
    ventana.title("E-Market Express - Autenticación MariaDB")
    ventana.resizable(False, False)
    ventana.configure(bg="#f4f6f9")
    centrar_ventana(ventana, 460, 520)

    # Estilos visuales con ttk
    estilo = ttk.Style(ventana)
    estilo.theme_use("clam")
    estilo.configure(".", font=("Segoe UI", 10), background="#f4f6f9")
    estilo.configure("Encabezado.TFrame", background="#1e3a5f")
    estilo.configure("Encabezado.TLabel", background="#1e3a5f", foreground="white", font=("Segoe UI", 14, "bold"))
    estilo.configure("SubEncabezado.TLabel", background="#1e3a5f", foreground="#cfd8e3")
    estilo.configure("BotonLogin.TButton", background="#2e86de", foreground="white", font=("Segoe UI", 10, "bold"), padding=6)
    estilo.map("BotonLogin.TButton", background=[("active", "#1b6fc2")])

    # Banner superior
    encabezado = ttk.Frame(ventana, style="Encabezado.TFrame", padding=18)
    encabezado.pack(fill="x")
    ttk.Label(encabezado, text="E-Market Express", style="Encabezado.TLabel").pack()
    ttk.Label(encabezado, text="Autenticación", style="SubEncabezado.TLabel").pack()

    # Formulario central
    cuerpo = ttk.Frame(ventana, padding=(40, 20))
    cuerpo.pack(fill="both", expand=True)

    ttk.Label(cuerpo, text="Usuario:").pack(anchor="w")
    entrada_usuario = ttk.Entry(cuerpo, width=40, font=("Segoe UI", 11))
    entrada_usuario.pack(fill="x", pady=(2, 12), ipady=3)
    entrada_usuario.insert(0, "admin_db")  # Sugerencia inicial

    ttk.Label(cuerpo, text="Contraseña:").pack(anchor="w")
    entrada_contrasena = ttk.Entry(cuerpo, width=40, show="•", font=("Segoe UI", 11))
    entrada_contrasena.pack(fill="x", pady=(2, 16), ipady=3)
    entrada_contrasena.insert(0, "Admin2026*Seguro")

    def autenticar():
        """Valida las credenciales contra MariaDB en tiempo real."""
        usuario = entrada_usuario.get().strip()
        contrasena = entrada_contrasena.get().strip()

        if not usuario:
            messagebox.showwarning("Campo vacío", "Por favor ingresa el usuario correcto.")
            return

        # Intentamos conectar a MariaDB
        exito, mensaje_error = probar_conexion(usuario, contrasena)

        if not exito:
            messagebox.showerror(
                "Error de Autenticación",
                f"No se pudo conectar a MariaDB con el usuario '{usuario}'.\n\n"
                f"Detalle: {mensaje_error}"
            )
            return

        # Asignamos el rol según la cuenta de MariaDB conectada
        if usuario.lower() in ("admin_db", "root"):
            rol = "Administrador"
        elif usuario.lower() == "cajero_app":
            rol = "Cajero"
        else:
            rol = "Administrador"

        # Configuramos la sesión activa en conexion.py
        establecer_sesion(usuario, contrasena, rol)

        usuario_autenticado.update({
            "usuario": usuario,
            "nombre": "Administrador General" if rol == "Administrador" else "Cajero / Operador",
            "apellido": f"({usuario})",
            "rol": rol
        })

        messagebox.showinfo(
            "Acceso Concedido",
            f"¡Conexión exitosa!\n\n"
            f"Usuario: {usuario}\n"
            f"Rol Asignado: {rol}\n"
            f"Base de Datos: parcial"
        )
        ventana.destroy()

    btn_login = ttk.Button(cuerpo, text="Iniciar Sesión", style="BotonLogin.TButton", command=autenticar)
    btn_login.pack(fill="x", ipady=4)

    # Accesos directos para facilitar la sustentación presencial
    marco_rapido = ttk.LabelFrame(cuerpo, text="Cuentas configuradas (Acceso rápido):", padding=10)
    marco_rapido.pack(fill="x", pady=(20, 0))

    def cargar_cuenta(u, c):
        entrada_usuario.delete(0, "end")
        entrada_usuario.insert(0, u)
        entrada_contrasena.delete(0, "end")
        entrada_contrasena.insert(0, c)

    btn_admin = ttk.Button(
        marco_rapido,
        text="Administrador (admin_db)",
        command=lambda: cargar_cuenta("admin_db", "Admin2026*Seguro")
    )
    btn_admin.pack(fill="x", pady=2)

    btn_cajero = ttk.Button(
        marco_rapido,
        text="Cajero (cajero_app)",
        command=lambda: cargar_cuenta("cajero_app", "Cajero2026*App")
    )
    btn_cajero.pack(fill="x", pady=2)

    # Atajos de teclado con tecla Enter
    entrada_usuario.bind("<Return>", lambda e: entrada_contrasena.focus())
    entrada_contrasena.bind("<Return>", lambda e: autenticar())
    entrada_contrasena.focus()

    ventana.mainloop()
    return usuario_autenticado if usuario_autenticado else None


if __name__ == "__main__":
    u = pedir_login()
    print("Usuario autenticado:", u)