"""
conexion.py
===========
Módulo CENTRALIZADO de conexión a la base de datos MariaDB / MySQL (XAMPP).

Permite:
1. Conexión dinámica según el usuario autenticado en el login:
   - admin_db   (Administrador de la base de datos)
   - cajero_app (Operador de caja)
   - root       (Superusuario por defecto de XAMPP)
2. Ejecución de consultas de lectura: consultar()
3. Ejecución de instrucciones DML y llamadas a procedimientos: ejecutar(), obtener_conexion()
4. Manejo centralizado y traducción de errores de MariaDB/MySQL a mensajes en español.
"""

# pyrefly: ignore[missing-import]
import mysql.connector
# pyrefly: ignore[missing-import]
from mysql.connector import Error 
# pyrefly: ignore[missing-import]
from mysql.connector.constants import ClientFlag 
from tkinter import messagebox

# Parámetros del servidor MariaDB / MySQL
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "parcial"

# Credenciales de la sesión activa en la aplicación
# (Se establecen dinámicamente tras el inicio de sesión exitoso)
SESION_ACTUAL = {
    "user": "root",
    "password": "",
    "rol": "Administrador"
}


def establecer_sesion(usuario, contrasena, rol):
    """Guarda las credenciales del usuario autenticado para todas las conexiones posteriores."""
    SESION_ACTUAL["user"] = usuario
    SESION_ACTUAL["password"] = contrasena
    SESION_ACTUAL["rol"] = rol


def obtener_sesion_actual():
    """Retorna un diccionario con los datos del usuario MariaDB actualmente conectado."""
    return dict(SESION_ACTUAL)


def probar_conexion(usuario, contrasena):
    """
    Intenta autenticarse contra MariaDB con las credenciales dadas.
    Retorna (True, None) si la conexión fue exitosa, o (False, mensaje_error) si falló.
    """
    try:
        con = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=usuario,
            password=contrasena
        )
        if con.is_connected():
            con.close()
            return True, None
    except Error as e:
        return False, traducir_error(e)
    return False, "No se pudo conectar al servidor."


def obtener_conexion():
    """
    Abre y devuelve una conexión activa a la base de datos usando las credenciales de la sesión.
    Si falla, muestra una alerta y retorna None.
    """
    try:
        conexion = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=SESION_ACTUAL["user"],
            password=SESION_ACTUAL["password"],
            client_flags=[ClientFlag.FOUND_ROWS]
        )
        return conexion
    except Error as e:
        messagebox.showerror(
            "Error de conexión",
            "No se pudo conectar a la base de datos MySQL.\n\n"
            f"Usuario BD: {SESION_ACTUAL['user']}\n"
            f"Detalle: {traducir_error(e)}\n\n"
            "Verifique que XAMPP esté encendido y que el servicio MySQL esté activo."
        )
        return None


def cerrar_conexion(conexion, cursor=None):
    """Cierra de forma segura el cursor y la conexión si están abiertos."""
    if cursor is not None:
        try:
            cursor.close()
        except:
            pass
    if conexion is not None and conexion.is_connected():
        try:
            conexion.close()
        except:
            pass


def consultar(sql, parametros=()):
    """
    Ejecuta una consulta SELECT parametrizada y retorna una lista de tuplas con los resultados.
    Si ocurre un error, muestra una alerta y retorna una lista vacía.
    """
    conexion = obtener_conexion()
    if conexion is None:
        return []

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, parametros)
        return cursor.fetchall()
    except Error as e:
        messagebox.showerror("Error en la consulta SQL", traducir_error(e))
        return []
    finally:
        cerrar_conexion(conexion, cursor)


def ejecutar(sql, parametros=()):
    """
    Ejecuta instrucciones INSERT, UPDATE o DELETE con COMMIT automático y ROLLBACK ante errores.
    Retorna la cantidad de filas afectadas o None si falló.
    """
    conexion = obtener_conexion()
    if conexion is None:
        return None

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, parametros)
        conexion.commit()
        return cursor.rowcount
    except Error as e:
        conexion.rollback()
        messagebox.showerror("No se pudo guardar", traducir_error(e))
        return None
    finally:
        cerrar_conexion(conexion, cursor)


def traducir_error(error):
    """Traduce los códigos de error técnicos de MariaDB/MySQL a mensajes claros en español."""
    codigo = getattr(error, "errno", None)

    if codigo == 1045:
        return "Acceso denegado: Usuario o contraseña de MariaDB incorrectos."
    if codigo == 1044:
        return "Acceso denegado: El usuario no tiene permisos suficientes sobre la base de datos."
    if codigo == 1142:
        return "Permiso denegado: El rol actual no tiene privilegios para realizar esta acción."
    if codigo == 1062:
        return "Ya existe un registro con ese mismo código, cédula o identificador (valor duplicado)."
    if codigo == 1451:
        return "No se puede eliminar o modificar este registro porque otros datos dependen de él."
    if codigo == 1452:
        return "El valor relacionado (categoría, proveedor, bodega, etc.) no existe."
    if codigo in (3819, 4025):
        return "El dato no cumple con una regla de validación de la base de datos (Check constraint)."
    if codigo == 1644:
        # Error personalizado lanzado por SIGNAL en triggers o procedimientos
        return getattr(error, "msg", str(error))

    return str(error)


if __name__ == "__main__":
    exito, err = probar_conexion("root", "")
    print("Prueba root:", exito, err)
    exito, err = probar_conexion("admin_db", "Admin2026*Seguro")
    print("Prueba admin_db:", exito, err)
    exito, err = probar_conexion("cajero_app", "Cajero2026*App")
    print("Prueba cajero_app:", exito, err)
