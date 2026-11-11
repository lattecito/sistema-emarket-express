# Sistema Integral E-Market Express

Sistema integral de gestión comercial, control de inventario multi-bodega, facturación transaccional y analítica gerencial desarrollado en **Python (Tkinter)** sobre una base de datos **MariaDB / MySQL (XAMPP)**.

Proyecto académico desarrollado para el curso de **Bases de Datos (Cód. 603401)** — **Universidad de los Llanos**.

---

## Características Principales

### 1. Conexión Centralizada y Control de Sesiones (`conexion.py`)
- Gestión unificada de conexiones mediante `mysql-connector-python`, activación automática de roles (`SET ROLE ALL;`) y limpieza de sesión ante cierres o errores de autenticación.
- Manejo transaccional explícito (`COMMIT` / `ROLLBACK`) y traducción centralizada de códigos de error de MariaDB/MySQL (1044, 1045, 1062, 1142, 1264, 1265, 1366, 1370, 1406, 1451, 1452, 1644, 3819, 4025).

### 2. Autenticación Dual, Hashing y Credenciales Seguras (`login.py`, `seguridad.py`, `main.py`)
- **Acceso directo por credenciales de MariaDB**: `admin_db`, `cajero_app` o `root`.
- **Acceso por tabla `usuario` con PBKDF2-HMAC-SHA256**: autenticación mediante **Correo Electrónico o Cédula** verificando hashes con sal aleatoria (`pbkdf2_sha256$120000$...`) en tiempo constante (`hmac.compare_digest`), tanto para registros iniciales como para nuevos cajeros creados desde `cajeros.py`.
- **Cero credenciales quemadas en código**: los parámetros de conexión y cuentas técnicas se cargan desde variables de entorno o `.env` (plantilla segura en `.env.example`, archivo `.env` excluido en `.gitignore`).
- **Segregación de interfaz por rol**:
  - **Administrador (`Administrador_DB`)**: acceso completo a Catálogo y Bodegas (CRUD), Clientes, Pedidos y Transacciones, Reportes Gerenciales con gráficos y Gestión de Cajeros.
  - **Cajero (`Cajero_App`)**: inicia directamente en **Pedidos y Transacciones**, con acceso a **Consulta de Catálogo** (solo lectura) y **Gestión de Clientes**, sin acceso ni visualización de módulos administrativos.

### 3. Transaccionalidad, Procedimientos Almacenados y Triggers (`script base/script.sql`)
- **Procedimientos almacenados transaccionales (`START TRANSACTION`, `COMMIT`, `ROLLBACK`)**:
  - `SP_RegistrarPedidoCompleto`: valida existencias con bloqueo `FOR UPDATE`, inserta 1 cabecera en `pedido`, N ítems en `transaccion` (`AUTO_INCREMENT`), descuenta inventario y genera 1 factura en `factura_pago`.
  - `SP_ModificarPedidoExistente`: reintegra existencias previas, valida el nuevo stock efectivo, reemplaza los detalles, recalcula el total y actualiza la factura vinculada (bloqueado en la UI si el pedido está en estado `entregado`).
  - `SP_ActualizarInventarioBodega`: transfiere unidades entre bodegas validando `cantidad > 0`, bodegas distintas y stock suficiente en origen.
- **Disparadores (Triggers)**:
  - `trg_auditoria_precio_articulo`: registra automáticamente cualquier variación de `precio_unitario` en `auditoria_precio_articulo`.
  - `trg_validar_stock_pedido`: valida existencias antes de insertar detalles en `transaccion`.
  - `trg_stock_inicial_bodega`: asigna a la Bodega 1 (predeterminada) el stock inicial de todo producto nuevo.
  - `trg_sincronizar_stock_bodega`: mantiene sincronizado `productos.cantidad_disponible` con `inventario_bodega` ante ventas, devoluciones o ajustes.

### 4. Integridad Referencial y Validaciones de Negocio
- **Productos y Catálogo (`catalogo.py`)**:
  - `ON DELETE RESTRICT` en `fk_transaccion_producto`: impide eliminar productos que tengan ventas en el historial.
  - Advertencia previa con conteo de productos vinculados al eliminar categorías o proveedores (`ON DELETE SET NULL`).
  - Bloqueo de eliminación de bodegas que aún conserven existencias en `inventario_bodega`.
  - Sincronización bidireccional de existencias entre bodegas y catálogo general.
- **Clientes (`clientes.py`)**:
  - Creación y eliminación de clientes (`usuario` con `rol = 'Cliente'`) tanto desde su pestaña dedicada como desde el modal rápido en ventas.
  - Validación de longitudes, formato de correo y teléfono numérico (7 a 15 dígitos).
  - `ON DELETE RESTRICT` en `fk_pedido_usuario`: bloquea la eliminación de clientes con pedidos registrados (Error 1451).
- **Cajeros (`cajeros.py`)**:
  - Administración exclusiva del Administrador sobre la tabla `usuario` (`WHERE rol = 'Cajero'`), sin ejecutar sentencias DDL en tiempo de ejecución.
- **Pedidos y Facturación (`pedidos.py`)**:
  - Edición de pedidos con cálculo de stock efectivo (`stock_libre + cantidad_original`), gestión logística de estados (`pendiente`, `enviado`, `entregado`), vista de factura detallada en ventana modal adaptable y barras de acción fijas.

### 5. Vistas Analíticas, Reportes e Interfaz Multiplataforma (`reportes.py`, `estilos.py`)
- Consultas a `vista_ventas_por_categoria`, `vista_pedidos_resumen`, `vista_clientes_frecuentes` (`JOIN` + `GROUP BY` + `HAVING`) y `vista_productos_sobre_promedio` (subconsultas sobre `AVG`), además de auditoría de precios e inventario de bajo stock.
- Tres gráficos estadísticos integrados con **Matplotlib** y recarga automática al cambiar de pestaña (`<<NotebookTabChanged>>`).
- Tipografía adaptativa por sistema operativo en `estilos.py` y tablas `Treeview` con desplazamiento vertical y horizontal.

### 6. Seguridad por Mínimo Privilegio (`GRANT` / `REVOKE`) y Backup / Restore (`script base/`)
- **`Cajero_App` / `cajero_app`**: permisos limitados únicamente a las tablas operativas y vistas de pedidos (`SELECT`), escritura acotada a ventas y registro de clientes, `UPDATE` restringido por columna a `productos(cantidad_disponible)` y ejecución exclusiva de `SP_RegistrarPedidoCompleto` y `SP_ModificarPedidoExistente`. Se revocan explícitamente (`REVOKE`) borrados sobre `pedido` y `factura_pago`, ediciones sobre `usuario` y `productos`, y todo acceso a auditoría o transferencias de bodega.
- **`Administrador_DB` / `admin_db`**: administración completa acotada al esquema `parcial.*` (sin privilegios destructivos globales sobre `mysql.*`) más permisos mínimos de respaldo (`PROCESS`, `RELOAD`, `SHOW DATABASES`).
- **Utilidad `script base/backup_restore.bat`**: menú interactivo y comandos CLI para generar respaldos completos (`--single-transaction --routines --triggers --events`), respaldos solo DDL (`--no-data`) y restaurar la base de datos desde `script base/backups/`.

---

## Estructura del Proyecto

```text
├── main.py              # Punto de entrada, barra de pestañas por rol y recarga automática
├── login.py             # Autenticación (MariaDB y tabla usuario por correo/cédula con PBKDF2)
├── seguridad.py         # Carga de .env/entorno y hashing/verificación PBKDF2-HMAC-SHA256
├── conexion.py          # Conexión centralizada, activación de roles y traductor de errores SQL
├── estilos.py           # Configuración de fuentes multiplataforma compartida
├── catalogo.py          # CRUD de productos, categorías, proveedores, bodegas y transferencias
├── clientes.py          # Gestión de clientes (rol = 'Cliente') y modal rápido en ventas
├── cajeros.py           # Gestión de cajeros (rol = 'Cajero' con hash PBKDF2) exclusiva de Admin
├── pedidos.py           # Ventas, edición de pedidos, estados logísticos y factura detallada
├── reportes.py          # Vistas analíticas, auditoría por trigger y gráficos con Matplotlib
├── requirements.txt     # Dependencias Python del proyecto
├── .env.example         # Plantilla de variables de entorno y credenciales por rol
├── script base/
│   ├── script.sql         # Script SQL consolidado (DDL 3FN, DML, Triggers, SP, Vistas, GRANT/REVOKE)
│   └── backup_restore.bat # Utilidad interactiva de Backup y Restore (mysqldump / mysql)
└── .gitignore             # Exclusión de .env, cachés, binarios, respaldos locales y temporales
```

---

## Requisitos e Instalación

### 1. Requisitos Previos
- **Python 3.10 o superior**.
- **XAMPP** (u otro servidor **MariaDB / MySQL** compatible con roles y JSON).

### 2. Configuración de la Base de Datos
1. Inicia **XAMPP** y activa el servicio **MySQL**.
2. Abre **phpMyAdmin** (o el cliente MySQL como `root`) e importa el archivo:
   `script base/script.sql`
   *(Crea la base de datos `parcial` con codificación `utf8mb4`, las 11 tablas en 3FN, datos iniciales, 4 triggers, 3 procedimientos almacenados, 4 vistas analíticas y los roles/usuarios `admin_db` y `cajero_app` con políticas `GRANT`/`REVOKE`).*
3. Para generar o restaurar respaldos en Windows, ejecuta `script base/backup_restore.bat`.

### 3. Instalación de Dependencias
En la carpeta raíz del proyecto, ejecuta:

```bash
pip install -r requirements.txt
```

---

## Ejecución del Sistema

```bash
python main.py
```

### Cuentas de Acceso Disponibles

| Rol | Usuario / Correo | Contraseña | Alcance en el Sistema |
| :--- | :--- | :--- | :--- |
| **Administrador (BD)** | `admin_db` | `Admin2026*Seguro` | Acceso total (Catálogo, Bodegas, Clientes, Pedidos, Reportes y Cajeros) |
| **Cajero (BD)** | `cajero_app` | `Cajero2026*App` | Pedidos y ventas, consulta de catálogo y gestión de clientes |
| **Cajero (Tabla `usuario`)** | `cajero1@emarket.com` | `Cajero2026*App` | Autenticación validada en tabla `usuario` operando bajo rol `Cajero_App` |
| **Superusuario (XAMPP)** | `root` | *(sin contraseña)* | Administración total local |
