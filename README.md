# Sistema Integral E-Market Express 🛒📦

Sistema de gestión comercial, inventario en bodegas y facturación transaccional desarrollado en **Python (Tkinter)** conectado a una base de datos **MariaDB / MySQL (XAMPP)**.

Proyecto académico para el curso de **Bases de Datos** - Universidad de los Llanos.

---

## 📋 Características Principales

- **Conexión Centralizada:** Manejo de sesiones y transacciones con `mysql-connector-python`.
- **Autenticación por Roles en MariaDB:**
  - `admin_db` (Rol **Administrador**): Acceso total al catálogo CRUD, transacciones, inventarios y reportes gerenciales.
  - `cajero_app` (Rol **Cajero**): Acceso a transacciones de pedidos y consulta de catálogo en modo solo lectura.
- **Transaccionalidad y Procedimientos Almacenados:**
  - `SP_RegistrarPedidoCompleto`: Inserción atómica de cabecera de pedido, detalle de transacción, descuento de stock y emisión de factura.
  - `SP_ActualizarInventarioBodega`: Transferencia atómica de existencias entre bodegas.
- **Triggers (Disparadores de Base de Datos):**
  - `trg_auditoria_precio_articulo`: Registra cambios de precio de productos automáticamente en `auditoria_precio_articulo`.
  - `trg_validar_stock_pedido`: Valida existencias antes de registrar transacciones.
- **Vistas Analíticas y Reportes Estadísticos:**
  - `vista_ventas_por_categoria` y `vista_pedidos_resumen`.
  - Gráficos estadísticos interactivos con **matplotlib** incrustados en la interfaz Tkinter.

---

## 🗂️ Estructura del Proyecto

```text
├── conexion.py          # Conexión centralizada a MariaDB y manejo de sesión
├── login.py             # Ventana de autenticación de usuarios de base de datos
├── main.py              # Ventana principal y control de navegación por roles
├── catalogo.py          # Módulo CRUD de productos, categorías, proveedores y bodegas
├── pedidos.py           # Módulo transaccional de ventas llamando a SP_RegistrarPedidoCompleto
├── reportes.py          # Consultas a las vistas analíticas y gráficos con Matplotlib
├── requirements.txt     # Librerías Python requeridas
├── script base/
│   └── script.sql       # Script SQL consolidado (DDL, DML, Triggers, SP, Vistas y Roles)
└── .gitignore           # Exclusión de archivos binarios y temporales
```

---

## 🚀 Requisitos e Instalación

### 1. Requisitos Previos
- **Python 3.10 o superior**.
- **XAMPP** con el servicio de MySQL / MariaDB activo.

### 2. Configuración de la Base de Datos
1. Inicia **XAMPP** y activa el módulo **MySQL**.
2. Abre phpMyAdmin o la consola de MySQL e importa el archivo:
   `script base/script.sql`
   *(Esto creará la base de datos `parcial`, las tablas, datos de prueba, procedimientos, triggers, vistas y usuarios `admin_db` y `cajero_app`).*

### 3. Instalación de Dependencias
Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecución del Sistema

Para iniciar la aplicación:

```bash
python main.py
```

### Credenciales de Acceso:
| Rol | Usuario MariaDB | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin_db` | `Admin2026*Seguro` | Acceso total (CRUD, Ventas, Reportes y Gráficos) |
| **Cajero / Operador** | `cajero_app` | `Cajero2026*App` | Venta de pedidos y consulta de catálogo |
| **Superusuario** | `root` | *(sin contraseña)* | Administrador general de XAMPP |
