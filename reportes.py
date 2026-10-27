"""
reportes.py
===========
Módulo de REPORTES GERENCIALES y GRÁFICOS ESTADÍSTICOS (solo Administrador).

Requerimiento:
- Los reportes consultan directamente las VISTAS ANALÍTICAS creadas en MariaDB:
  1. vista_ventas_por_categoria (categoría, cantidad_ventas, total_recaudado)
  2. vista_pedidos_resumen      (id_pedido, cliente, fecha_transaccion, total, estado_pedido, metodo_pago, estado_pago)
- Incorpora gráficos estadísticos con matplotlib integrados directamente en la GUI.
- Muestra el registro histórico generado por el trigger 'trg_auditoria_precio_articulo'.
"""

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
# pyrefly: ignore[missing-import]
from matplotlib.figure import Figure
# pyrefly: ignore[missing-import]
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from conexion import consultar

COLOR_PRIMARIO = "#1e3a5f"
COLORES_GRAFICOS = ["#2e86de", "#27ae60", "#f39c12", "#c0392b", "#8e44ad", "#16a085", "#d35400"]


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


# =============================================================================
#  CONSULTAS DIRECTAS A LAS VISTAS ANALÍTICAS
# =============================================================================

# 1. Consulta directa a vista_ventas_por_categoria
SQL_VISTA_CATEGORIAS = """
    SELECT categoria, cantidad_ventas, total_recaudado
    FROM vista_ventas_por_categoria
    ORDER BY total_recaudado DESC
"""

# 2. Consulta directa a vista_pedidos_resumen
SQL_VISTA_PEDIDOS_RESUMEN = """
    SELECT id_pedido, cliente, fecha_transaccion, total, estado_pedido,
           IFNULL(metodo_pago, 'Sin factura'),
           IFNULL(estado_pago, 'Sin factura')
    FROM vista_pedidos_resumen
    ORDER BY id_pedido DESC
"""

# 3. Agrupación analítica sobre vista_pedidos_resumen por estado
SQL_ESTADOS_DESDE_VISTA = """
    SELECT estado_pedido,
           COUNT(*)           AS total_pedidos,
           IFNULL(SUM(total), 0) AS total_dinero
    FROM vista_pedidos_resumen
    GROUP BY estado_pedido
    ORDER BY total_dinero DESC
"""

# 4. Agrupación analítica sobre vista_pedidos_resumen por método de pago
SQL_METODOS_DESDE_VISTA = """
    SELECT IFNULL(metodo_pago, 'Sin registrar') AS metodo,
           COUNT(*)                              AS transacciones,
           IFNULL(SUM(total), 0)                 AS valor_total
    FROM vista_pedidos_resumen
    GROUP BY metodo_pago
    ORDER BY valor_total DESC
"""

# 5. Artículos con bajo stock
SQL_BAJO_STOCK = """
    SELECT p.codigo, p.nombre, p.cantidad_disponible,
           IFNULL(c.nombre, 'Sin categoría'),
           IFNULL(pr.nombre, 'Sin proveedor'),
           IFNULL(pr.contacto, '-')
    FROM productos p
    LEFT JOIN categoria c  ON c.id_categoria = p.id_categoria
    LEFT JOIN proveedor pr ON pr.nit = p.nit_proveedor
    WHERE p.cantidad_disponible <= %s
    ORDER BY p.cantidad_disponible ASC
"""

# 6. Historial de auditoría alimentado automáticamente por el Trigger
SQL_AUDITORIA_TRIGGER = """
    SELECT a.id_auditoria, a.codigo_articulo, IFNULL(p.nombre, '(eliminado)'),
           a.precio_anterior, a.precio_nuevo, a.fecha_modificacion, a.usuario_bd
    FROM auditoria_precio_articulo a
    LEFT JOIN productos p ON p.codigo = a.codigo_articulo
    ORDER BY a.fecha_modificacion DESC
"""


# =============================================================================
#  CONSTRUCCIÓN DEL MÓDULO VISUAL
# =============================================================================

def crear_modulo_reportes(padre):
    """Construye las pestañas de reportes apoyadas directamente en las vistas."""
    cuaderno = ttk.Notebook(padre)
    cuaderno.pack(fill="both", expand=True, padx=5, pady=5)

    # Vista 1: Ventas por categoría
    crear_pestana_reporte(
        cuaderno, "Ventas por Categoría",
        "Consulta directa a la vista 'vista_ventas_por_categoria'.",
        ("Categoría", "Cantidad Ventas", "Total Recaudado ($)"),
        (220, 160, 200),
        SQL_VISTA_CATEGORIAS
    )

    # Vista 2: Resumen integral de pedidos
    crear_pestana_reporte(
        cuaderno, "Resumen de Pedidos",
        "Consulta directa a la vista 'vista_pedidos_resumen'.",
        ("ID Pedido", "Cliente", "Fecha", "Total", "Estado Pedido", "Método Pago", "Estado Pago"),
        (80, 180, 100, 120, 110, 120, 120),
        SQL_VISTA_PEDIDOS_RESUMEN
    )

    # Vista 3: Análisis por estado del pedido
    crear_pestana_reporte(
        cuaderno, "Pedidos por Estado",
        "Agrupación de ventas calculada a partir de 'vista_pedidos_resumen'.",
        ("Estado del Pedido", "N° de Pedidos", "Total Facturado ($)"),
        (200, 150, 200),
        SQL_ESTADOS_DESDE_VISTA
    )

    # Vista 4: Análisis por método de pago
    crear_pestana_reporte(
        cuaderno, "Por Método de Pago",
        "Distribución de pagos calculada a partir de 'vista_pedidos_resumen'.",
        ("Método de Pago", "N° Transacciones", "Total Pagado ($)"),
        (200, 160, 200),
        SQL_METODOS_DESDE_VISTA
    )

    # Pestaña de bajo stock
    crear_pestana_bajo_stock(cuaderno)

    # Pestaña de auditoría por trigger
    crear_pestana_reporte(
        cuaderno, "Auditoría por Trigger",
        "Historial registrado automáticamente por el trigger 'trg_auditoria_precio_articulo'.",
        ("ID", "Cód. Producto", "Nombre Producto", "Precio Anterior", "Precio Nuevo", "Fecha / Hora", "Usuario BD"),
        (60, 110, 180, 120, 120, 160, 180),
        SQL_AUDITORIA_TRIGGER
    )

    # Pestaña de gráficos con matplotlib
    crear_pestana_graficos(cuaderno)


def crear_pestana_reporte(cuaderno, titulo, descripcion, columnas, anchos, sql):
    pestana = ttk.Frame(cuaderno, padding=15)
    cuaderno.add(pestana, text=titulo)

    encabezado = ttk.Frame(pestana)
    encabezado.pack(fill="x", pady=(0, 10))
    ttk.Label(encabezado, text=titulo, style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(encabezado, text=descripcion, style="Descripcion.TLabel").pack(anchor="w")

    marco_tabla, tabla = crear_tabla(pestana, columnas, anchos, alto=16)
    marco_tabla.pack(fill="both", expand=True)

    def recargar():
        llenar_tabla(tabla, consultar(sql), usar_primera_columna_como_id=False)

    ttk.Button(pestana, text="Recargar reporte", style="Primario.TButton", command=recargar).pack(anchor="e", pady=(10, 0))
    recargar()


def crear_pestana_bajo_stock(cuaderno):
    pestana = ttk.Frame(cuaderno, padding=15)
    cuaderno.add(pestana, text="Bajo Stock")

    ttk.Label(pestana, text="Artículos con Bajo Stock", style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(pestana, text="Filtra productos cuya cantidad disponible es menor o igual al límite.", style="Descripcion.TLabel").pack(anchor="w")

    barra = ttk.Frame(pestana)
    barra.pack(fill="x", pady=10)
    ttk.Label(barra, text="Límite de unidades:").pack(side="left")
    spn_limite = ttk.Spinbox(barra, from_=0, to=10000, width=8)
    spn_limite.set(10)
    spn_limite.pack(side="left", padx=5)

    marco_tabla, tabla = crear_tabla(
        pestana,
        ("Código", "Producto", "Disponible", "Categoría", "Proveedor", "Contacto Proveedor"),
        (90, 180, 100, 150, 180, 160),
        alto=15
    )
    marco_tabla.pack(fill="both", expand=True)

    def consultar_stock():
        try:
            limite = int(spn_limite.get())
        except ValueError:
            limite = 10
            spn_limite.set(10)
        llenar_tabla(tabla, consultar(SQL_BAJO_STOCK, (limite,)))

    ttk.Button(barra, text="Consultar", style="Primario.TButton", command=consultar_stock).pack(side="left", padx=5)
    consultar_stock()


def crear_pestana_graficos(cuaderno):
    pestana = ttk.Frame(cuaderno, padding=15)
    cuaderno.add(pestana, text="Gráficos Estadísticos")

    barra = ttk.Frame(pestana)
    barra.pack(fill="x")
    ttk.Label(barra, text="Visualización Gráfica (Alimentada por las Vistas)", style="Titulo.TLabel").pack(side="left")

    figura = Figure(figsize=(13, 5), dpi=90, facecolor="white")
    lienzo = FigureCanvasTkAgg(figura, master=pestana)
    lienzo.get_tk_widget().pack(fill="both", expand=True, pady=10)

    def generar_graficos():
        figura.clear()

        # Gráfico 1: Ventas por Categoría desde 'vista_ventas_por_categoria'
        eje1 = figura.add_subplot(1, 3, 1)
        datos_cat = consultar("SELECT categoria, total_recaudado FROM vista_ventas_por_categoria WHERE total_recaudado > 0")
        if datos_cat:
            cats = [fila[0] for fila in datos_cat]
            montos = [float(fila[1]) for fila in datos_cat]
            barras = eje1.bar(cats, montos, color=COLORES_GRAFICOS[:len(cats)])
            eje1.bar_label(barras, fmt="%.0f")
            eje1.set_ylabel("Total Recaudado ($)")
            eje1.tick_params(axis="x", rotation=20)
        else:
            eje1.text(0.5, 0.5, "Sin ventas registradas", ha="center", va="center", color="gray")
            eje1.axis("off")
        eje1.set_title("Recaudación por Categoría\n(vista_ventas_por_categoria)", color=COLOR_PRIMARIO, fontweight="bold", fontsize=10)

        # Gráfico 2: Pedidos por Estado desde 'vista_pedidos_resumen'
        eje2 = figura.add_subplot(1, 3, 2)
        datos_est = consultar("SELECT estado_pedido, COUNT(*) FROM vista_pedidos_resumen GROUP BY estado_pedido")
        if datos_est:
            eje2.pie(
                [f[1] for f in datos_est],
                labels=[f[0].capitalize() for f in datos_est],
                autopct="%1.1f%%",
                startangle=90,
                colors=COLORES_GRAFICOS[:len(datos_est)],
                wedgeprops={"edgecolor": "white", "linewidth": 2}
            )
            eje2.axis("equal")
        else:
            eje2.text(0.5, 0.5, "Sin pedidos", ha="center", va="center", color="gray")
            eje2.axis("off")
        eje2.set_title("Distribución por Estado\n(vista_pedidos_resumen)", color=COLOR_PRIMARIO, fontweight="bold", fontsize=10)

        # Gráfico 3: Ventas por Método de Pago desde 'vista_pedidos_resumen'
        eje3 = figura.add_subplot(1, 3, 3)
        datos_met = consultar("SELECT IFNULL(metodo_pago, 'Sin pago'), COUNT(*) FROM vista_pedidos_resumen GROUP BY metodo_pago")
        if datos_met:
            eje3.pie(
                [f[1] for f in datos_met],
                labels=[f[0] for f in datos_met],
                autopct="%1.1f%%",
                startangle=90,
                colors=COLORES_GRAFICOS[:len(datos_met)],
                wedgeprops={"edgecolor": "white", "linewidth": 2}
            )
            eje3.axis("equal")
        else:
            eje3.text(0.5, 0.5, "Sin pagos", ha="center", va="center", color="gray")
            eje3.axis("off")
        eje3.set_title("Métodos de Pago\n(vista_pedidos_resumen)", color=COLOR_PRIMARIO, fontweight="bold", fontsize=10)

        figura.tight_layout()
        lienzo.draw()

    ttk.Button(barra, text="Actualizar Gráficos", style="Exito.TButton", command=generar_graficos).pack(side="right")
    generar_graficos()
