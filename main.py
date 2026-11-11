"""
main.py
=======
Punto de Entrada Principal de la aplicación E-Market Express.

Para ejecutar el sistema:
    python main.py

Flujo de la aplicación:
1. Abre la ventana de login (`login.py`) para autenticar al usuario.
2. Si el inicio de sesión es exitoso, abre la ventana principal con menú de navegación por pestañas (`ttk.Notebook`).
3. Adapta las opciones según el rol del usuario:
   - Administrador:
       * Módulo de Catálogo y Bodegas (CRUD completo).
       * Módulo de Pedidos y Pagos (Ventas transaccionales).
       * Módulo de Reportes Gerenciales y Gráficos estadísticos con matplotlib.
       * Módulo de Gestión de Cajeros (Creación y revocación de cuentas en MariaDB).
   - Cajero / Operador:
       * Consulta de Catálogo (modo solo lectura para ver precios y existencias).
       * Módulo de Pedidos y Pagos (Ventas transaccionales).
4. Permite cerrar sesión para retornar a la pantalla de login sin salir abruptamente del programa.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from login import pedir_login
from conexion import limpiar_sesion
from estilos import FUENTE
from catalogo import crear_modulo_catalogo
from pedidos import crear_modulo_pedidos
from reportes import crear_modulo_reportes
from cajeros import crear_modulo_cajeros
from clientes import crear_modulo_clientes


def centrar_ventana(ventana, ancho, alto):
    """Calcula las coordenadas x, y para centrar la ventana en la pantalla."""
    x = (ventana.winfo_screenwidth() - ancho) // 2
    y = (ventana.winfo_screenheight() - alto) // 3
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


def aplicar_estilos_generales(ventana):
    """Configura los colores, fuentes y estilos visuales de los componentes ttk."""
    ventana.configure(bg="#f4f6f9")
    estilo = ttk.Style(ventana)
    estilo.theme_use("clam")

    # Fuentes y fondos base (E25: familia multiplataforma desde estilos.py)
    estilo.configure(".", font=(FUENTE, 10), background="#f4f6f9")
    estilo.configure("TFrame", background="#f4f6f9")
    estilo.configure("TLabel", background="#f4f6f9")
    estilo.configure("TLabelframe", background="#f4f6f9")
    estilo.configure("TLabelframe.Label", background="#f4f6f9", foreground="#1e3a5f", font=(FUENTE, 10, "bold"))

    # Textos especiales
    estilo.configure("Titulo.TLabel", font=(FUENTE, 15, "bold"), foreground="#1e3a5f")
    estilo.configure("Descripcion.TLabel", foreground="#5a6b7d")
    estilo.configure("Total.TLabel", font=(FUENTE, 15, "bold"), foreground="#27ae60")

    # Barra superior (Encabezado)
    estilo.configure("Encabezado.TFrame", background="#1e3a5f")
    estilo.configure("Encabezado.TLabel", background="#1e3a5f", foreground="white", font=(FUENTE, 14, "bold"))
    estilo.configure("SubEncabezado.TLabel", background="#1e3a5f", foreground="#cfd8e3")

    # Botones con colores representativos
    estilo.configure("TButton", padding=(10, 5))
    estilo.configure("Primario.TButton", background="#2e86de", foreground="white", font=(FUENTE, 10, "bold"))
    estilo.map("Primario.TButton", background=[("active", "#1b6fc2")])

    estilo.configure("Exito.TButton", background="#27ae60", foreground="white", font=(FUENTE, 10, "bold"))
    estilo.map("Exito.TButton", background=[("active", "#1e8449")])

    estilo.configure("Peligro.TButton", background="#c0392b", foreground="white", font=(FUENTE, 10, "bold"))
    estilo.map("Peligro.TButton", background=[("active", "#922b21")])

    # Tablas (Treeview)
    estilo.configure("Treeview", rowheight=26, background="white", fieldbackground="white")
    estilo.configure("Treeview.Heading", background="#1e3a5f", foreground="white", font=(FUENTE, 10, "bold"), padding=5)
    estilo.map("Treeview.Heading", background=[("active", "#2e86de")])

    # Pestañas (Notebook)
    estilo.configure("TNotebook", background="#f4f6f9", borderwidth=0)
    estilo.configure("TNotebook.Tab", padding=(16, 7), font=(FUENTE, 10, "bold"))
    estilo.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", "#1e3a5f")])


def abrir_ventana_principal(usuario):
    """
    Construye y despliega la ventana principal del sistema según el rol del usuario autenticado.
    Retorna True si el usuario solicita 'Cerrar sesión' para volver al login, o False al salir.
    """
    es_administrador = (usuario["rol"] == "Administrador")
    resultado = {"cerrar_sesion": False}

    ventana = tk.Tk()
    ventana.title("E-Market Express - Sistema Integral")
    ventana.minsize(1150, 680)
    aplicar_estilos_generales(ventana)
    centrar_ventana(ventana, 1300, 760)

    # 1. Barra de encabezado superior con información de la sesión
    encabezado = ttk.Frame(ventana, style="Encabezado.TFrame", padding=(18, 10))
    encabezado.pack(fill="x")

    ttk.Label(encabezado, text="E-Market Express", style="Encabezado.TLabel").pack(side="left")
    ttk.Label(
        encabezado,
        text=f"   |   Usuario MariaDB: {usuario.get('usuario', 'root')}   |   Rol: {usuario['rol']}",
        style="SubEncabezado.TLabel"
    ).pack(side="left", padx=10)

    def accion_cerrar_sesion():
        if messagebox.askyesno("Cerrar Sesión", "¿Estás seguro de que deseas cerrar la sesión actual?"):
            limpiar_sesion()
            resultado["cerrar_sesion"] = True
            ventana.destroy()

    ttk.Button(encabezado, text="Cerrar Sesión", style="Peligro.TButton", command=accion_cerrar_sesion).pack(side="right")

    # 2. Contenedor de pestañas (Notebook) para la navegación entre módulos
    menu_navegacion = ttk.Notebook(ventana)
    menu_navegacion.pack(fill="both", expand=True, padx=10, pady=10)

    recargadores = {}

    if es_administrador:
        # VISTA ADMINISTRADOR: Acceso completo a todos los módulos operativos y gerenciales
        # 1. Catálogo y Bodegas (CRUD completo)
        marco_catalogo = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_catalogo, text="Gestión de Catálogo y Bodegas")
        crear_modulo_catalogo(marco_catalogo, solo_lectura=False)

        # 2. Gestión de Clientes (Crear y Eliminar Clientes)
        marco_clientes = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_clientes, text="Gestión de Clientes")
        crear_modulo_clientes(marco_clientes)

        # 3. Módulo Transaccional de Pedidos y Pagos
        marco_pedidos = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_pedidos, text="Pedidos y Transacciones")
        recargadores[str(marco_pedidos)] = crear_modulo_pedidos(marco_pedidos)

        # 4. Reportes Gerenciales y Gráficos Estadísticos (Exclusivo Administrador)
        marco_reportes = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_reportes, text="Reportes Gerenciales y Gráficos")
        recargadores[str(marco_reportes)] = crear_modulo_reportes(marco_reportes)

        # 5. Gestión de Cajeros (Exclusivo Administrador)
        marco_cajeros = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_cajeros, text="Gestión de Cajeros")
        crear_modulo_cajeros(marco_cajeros)

    else:
        # VISTA CAJERO:
        # Acceso exclusivo a operaciones de venta, consulta de existencias y clientes.
        # Las pestañas de administración (Gestión de Cajeros y Reportes) NO se agregan ni se instancian.

        # 1. Pedidos y Transacciones (Venta) - Pestaña predeterminada al inicio
        marco_pedidos = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_pedidos, text="Pedidos y Transacciones")
        recargadores[str(marco_pedidos)] = crear_modulo_pedidos(marco_pedidos)

        # 2. Consulta de Catálogo (Solo Lectura)
        marco_catalogo = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_catalogo, text="Consulta de Catálogo")
        crear_modulo_catalogo(marco_catalogo, solo_lectura=True)

        # 3. Gestión de Clientes
        marco_clientes = ttk.Frame(menu_navegacion)
        menu_navegacion.add(marco_clientes, text="Gestión de Clientes")
        crear_modulo_clientes(marco_clientes)

    def al_cambiar_pestana(evento=None):
        """E12 / E19: Recarga automáticamente los datos al entrar en Pedidos o Reportes."""
        sel = menu_navegacion.select()
        fn = recargadores.get(str(sel))
        if callable(fn):
            fn()

    menu_navegacion.bind("<<NotebookTabChanged>>", al_cambiar_pestana)

    ventana.mainloop()
    return resultado["cerrar_sesion"]


def main():
    """Bucle principal de la aplicación: Login -> Ventana Principal -> Cierre/Reinicio."""
    while True:
        usuario = pedir_login()
        if not usuario:
            # Si el usuario cierra el login, finaliza el programa
            break

        volver_a_login = abrir_ventana_principal(usuario)
        if not volver_a_login:
            # Si cerró la ventana principal con la X (en lugar de cerrar sesión), termina
            break


if __name__ == "__main__":
    main()
