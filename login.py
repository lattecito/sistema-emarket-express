"""
login.py
========
Módulo de Autenticación e Inicio de Sesión sobre MariaDB / MySQL.

¿Cómo funciona este módulo?
1. El usuario ingresa su cuenta de MariaDB o su correo/cédula de la tabla 'usuario'.
2. Se prueba primero si corresponde a una cuenta directa de MariaDB contra el servidor.
3. De lo contrario, consulta la tabla 'usuario' usando las cuentas técnicas definidas
   en variables de entorno / '.env' (sin credenciales maestras quemadas en el código)
   y verifica el hash PBKDF2-SHA256 en tiempo constante.
4. Si la autenticación es exitosa, activa la sesión con el rol correspondiente
   (Administrador o Cajero) en conexion.establecer_sesion(...).
"""

import tkinter as tk
from tkinter import ttk, messagebox

from conexion import probar_conexion, establecer_sesion, consultar, limpiar_sesion
from estilos import FUENTE
from seguridad import (
    demo_rapida_habilitada,
    obtener_credencial_rol,
    obtener_cuentas_validacion,
    verificar_contrasena,
)


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
    ventana.title("E-Market Express - Autenticación")
    ventana.resizable(False, False)
    ventana.configure(bg="#f4f6f9")
    mostrar_demo = demo_rapida_habilitada() and bool(obtener_cuentas_validacion())
    centrar_ventana(ventana, 460, 520 if mostrar_demo else 390)

    # Estilos visuales con ttk
    estilo = ttk.Style(ventana)
    estilo.theme_use("clam")
    estilo.configure(".", font=(FUENTE, 10), background="#f4f6f9")
    estilo.configure("Encabezado.TFrame", background="#1e3a5f")
    estilo.configure("Encabezado.TLabel", background="#1e3a5f", foreground="white", font=(FUENTE, 14, "bold"))
    estilo.configure("SubEncabezado.TLabel", background="#1e3a5f", foreground="#cfd8e3")
    estilo.configure("BotonLogin.TButton", background="#2e86de", foreground="white", font=(FUENTE, 10, "bold"), padding=6)
    estilo.map("BotonLogin.TButton", background=[("active", "#1b6fc2")])

    # Banner superior
    encabezado = ttk.Frame(ventana, style="Encabezado.TFrame", padding=18)
    encabezado.pack(fill="x")
    ttk.Label(encabezado, text="E-Market Express", style="Encabezado.TLabel").pack()
    ttk.Label(encabezado, text="Autenticación", style="SubEncabezado.TLabel").pack()

    # Formulario central
    cuerpo = ttk.Frame(ventana, padding=(40, 20))
    cuerpo.pack(fill="both", expand=True)

    ttk.Label(cuerpo, text="Usuario o correo:").pack(anchor="w")
    entrada_usuario = ttk.Entry(cuerpo, width=40, font=(FUENTE, 11))
    entrada_usuario.pack(fill="x", pady=(2, 12), ipady=3)
    # E5: Los campos inician VACÍOS (sin credenciales de prueba precargadas)

    ttk.Label(cuerpo, text="Contraseña:").pack(anchor="w")
    entrada_contrasena = ttk.Entry(cuerpo, width=40, show="•", font=(FUENTE, 11))
    entrada_contrasena.pack(fill="x", pady=(2, 16), ipady=3)

    def autenticar():
        """Valida las credenciales contra MariaDB o la tabla usuario en tiempo real."""
        usuario = entrada_usuario.get().strip()
        contrasena = entrada_contrasena.get().strip()

        if not usuario or not contrasena:
            messagebox.showwarning("Campos vacíos", "Por favor ingresa el usuario (correo o cédula) y la contraseña.")
            return

        # 1. Probar credenciales directas de MariaDB (admin_db, cajero_app, root)
        exito_db, mensaje_error = probar_conexion(usuario, contrasena)

        es_usuario_registrado = False
        registro_usuario = None
        nombre_display = "Operador de Caja"
        rol = "Cajero"

        # 2. Si no es conexión directa a MariaDB, validamos contra la tabla 'usuario'
        #    usando las cuentas técnicas de entorno/.env y hash PBKDF2-SHA256.
        #    E14: SOLO se permite identificarse por correo electrónico o cédula (no por nombre).
        sin_config_servicio = False
        if not exito_db:
            cuentas_servicio = obtener_cuentas_validacion()
            if not cuentas_servicio:
                sin_config_servicio = True
            for u_serv, p_serv in cuentas_servicio:
                try:
                    establecer_sesion(u_serv, p_serv, "Cajero")
                    filas = consultar(
                        """
                        SELECT id_usuario, cedula, nombre, apellido, correo, rol, contrasena
                        FROM usuario
                        WHERE (LOWER(correo) = %s OR CAST(cedula AS CHAR) = %s)
                        LIMIT 1;
                        """,
                        (usuario.lower(), usuario),
                        mostrar_error=False
                    )
                    if filas:
                        u_hash = filas[0][6]
                        if verificar_contrasena(contrasena, u_hash):
                            es_usuario_registrado = True
                            registro_usuario = filas[0][:6]
                        break
                except Exception:
                    continue

        if not exito_db and not es_usuario_registrado:
            # E14: No dejar privilegios residuales de la sesión de servicio usada para validar
            limpiar_sesion()
            if sin_config_servicio and ("@" in usuario or usuario.isdigit()):
                messagebox.showerror(
                    "Configuración Requerida",
                    "No se encontraron credenciales de servicio en '.env' ni en variables de entorno\n"
                    "para validar usuarios de la tabla 'usuario'.\n\n"
                    "Configura '.env' (ver '.env.example') o ingresa directamente con tu usuario MariaDB."
                )
            else:
                messagebox.showerror(
                    "Error de Autenticación",
                    f"No se pudo iniciar sesión con '{usuario}'.\n\n"
                    f"Verifica que el correo/cédula y la contraseña sean correctos."
                )
            return

        # 3. Determinación de rol y sesión según la autenticación
        if es_usuario_registrado and registro_usuario:
            u_id, u_ced, u_nom, u_ape, u_cor, u_rol = registro_usuario
            nombre_display = f"{u_nom} {u_ape}"
            rol_detectado = str(u_rol).strip() if u_rol else "Cajero"

            if rol_detectado in ("Administrador", "Cajero"):
                u_bd, p_bd = obtener_credencial_rol(rol_detectado)
                if not u_bd or not p_bd:
                    limpiar_sesion()
                    messagebox.showerror(
                        "Configuración Incompleta",
                        f"No hay credenciales técnicas configuradas en '.env' para el rol '{rol_detectado}'."
                    )
                    return
                rol = rol_detectado
                establecer_sesion(u_bd, p_bd, rol)
            else:
                limpiar_sesion()
                messagebox.showwarning(
                    "Acceso No Autorizado",
                    f"El usuario '{u_nom} {u_ape}' tiene rol '{rol_detectado}'.\n"
                    f"Solo los roles 'Administrador' y 'Cajero' pueden acceder al sistema."
                )
                return
        else:
            # Conexión directa como usuario MariaDB predefinido
            if usuario.lower() in ("admin_db", "root"):
                rol = "Administrador"
                nombre_display = "Administrador General"
            else:
                rol = "Cajero"
                nombre_display = "Operador de Caja Principal"

            establecer_sesion(usuario, contrasena, rol)

        usuario_autenticado.update({
            "usuario": usuario,
            "nombre": nombre_display,
            "apellido": f"({usuario})",
            "rol": rol
        })

        messagebox.showinfo(
            "Acceso Concedido",
            f"¡Conexión exitosa!\n\n"
            f"Usuario: {usuario}\n"
            f"Nombre: {nombre_display}\n"
            f"Rol Asignado: {rol}\n"
            f"Base de Datos: parcial"
        )
        ventana.destroy()

    btn_login = ttk.Button(cuerpo, text="Iniciar Sesión", style="BotonLogin.TButton", command=autenticar)
    btn_login.pack(fill="x", ipady=4)

    # Accesos directos (solo visibles si ENABLE_DEMO_QUICK_LOGIN=1 en '.env', sin claves quemadas)
    if mostrar_demo:
        u_adm, p_adm = obtener_credencial_rol("Administrador")
        u_caj, p_caj = obtener_credencial_rol("Cajero")

        marco_rapido = ttk.LabelFrame(cuerpo, text="Cuentas de demostración (Acceso rápido):", padding=10)
        marco_rapido.pack(fill="x", pady=(20, 0))

        def cargar_cuenta(u, c):
            entrada_usuario.delete(0, "end")
            entrada_usuario.insert(0, u)
            entrada_contrasena.delete(0, "end")
            entrada_contrasena.insert(0, c)

        if u_adm and p_adm:
            btn_admin = ttk.Button(
                marco_rapido,
                text=f"Administrador ({u_adm})",
                command=lambda u=u_adm, p=p_adm: cargar_cuenta(u, p)
            )
            btn_admin.pack(fill="x", pady=2)

        if u_caj and p_caj:
            btn_cajero = ttk.Button(
                marco_rapido,
                text=f"Cajero ({u_caj})",
                command=lambda u=u_caj, p=p_caj: cargar_cuenta(u, p)
            )
            btn_cajero.pack(fill="x", pady=2)

    # Atajos de teclado con tecla Enter
    entrada_usuario.bind("<Return>", lambda e: entrada_contrasena.focus())
    entrada_contrasena.bind("<Return>", lambda e: autenticar())
    entrada_usuario.focus()

    ventana.mainloop()
    return usuario_autenticado if usuario_autenticado else None


if __name__ == "__main__":
    u = pedir_login()
    print("Usuario autenticado:", u)