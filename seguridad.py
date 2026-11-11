"""
seguridad.py
============
Módulo centralizado de seguridad y configuración de credenciales:
1. Carga variables de entorno desde '.env' (sin dependencias externas).
2. Provee las credenciales de servicio y parámetros de BD fuera del código fuente.
3. Genera y verifica hashes PBKDF2-HMAC-SHA256 con sal criptográfica aleatoria
   para las contraseñas almacenadas en la tabla 'usuario'.
"""

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

PREFIJO_HASH = "pbkdf2_sha256"
ITERACIONES_PBKDF2 = 120_000
TAMANO_SAL_BYTES = 16

_RUTA_RAIZ = Path(__file__).resolve().parent
_ENTORNO_CARGADO = False


def cargar_entorno(ruta_env=None, forzar=False):
    """Carga pares CLAVE=VALOR desde el archivo '.env' sin sobrescribir variables ya definidas."""
    global _ENTORNO_CARGADO
    if _ENTORNO_CARGADO and not forzar:
        return

    archivo = Path(ruta_env) if ruta_env else (_RUTA_RAIZ / ".env")
    if archivo.is_file():
        with archivo.open("r", encoding="utf-8") as fh:
            for linea_raw in fh:
                linea = linea_raw.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                clave = clave.strip()
                valor = valor.strip()
                if len(valor) >= 2 and ((valor[0] == valor[-1] == '"') or (valor[0] == valor[-1] == "'")):
                    valor = valor[1:-1]
                if clave:
                    os.environ.setdefault(clave, valor)

    _ENTORNO_CARGADO = True


def obtener_config_bd():
    """Retorna host, puerto y nombre de base de datos desde el entorno o valores locales por defecto."""
    cargar_entorno()
    host = os.environ.get("DB_HOST", "localhost").strip() or "localhost"
    try:
        puerto = int(os.environ.get("DB_PORT", "3306"))
    except ValueError:
        puerto = 3306
    nombre = os.environ.get("DB_NAME", "parcial").strip() or "parcial"
    return {"host": host, "port": puerto, "database": nombre}


def obtener_credencial_rol(rol):
    """
    Retorna la tupla (usuario_bd, contrasena_bd) configurada para el rol ('Administrador' o 'Cajero').
    Las contraseñas provienen exclusivamente de variables de entorno o '.env'.
    """
    cargar_entorno()
    if rol == "Administrador":
        usuario = os.environ.get("DB_ADMIN_USER", "admin_db").strip()
        clave = os.environ.get("DB_ADMIN_PASSWORD", "")
        return usuario, clave
    if rol == "Cajero":
        usuario = os.environ.get("DB_CAJERO_USER", "cajero_app").strip()
        clave = os.environ.get("DB_CAJERO_PASSWORD", "")
        return usuario, clave
    return "", ""


def obtener_cuentas_validacion():
    """
    Retorna la lista de cuentas técnicas configuradas en entorno / '.env' para
    autenticar usuarios internos de la tabla 'usuario' sin credenciales quemadas en código.
    """
    cargar_entorno()
    cuentas = []
    for rol in ("Cajero", "Administrador"):
        u, p = obtener_credencial_rol(rol)
        if u and p:
            cuentas.append((u, p))
    return cuentas


def demo_rapida_habilitada():
    """Indica si los accesos rápidos de demostración están habilitados por entorno."""
    cargar_entorno()
    return os.environ.get("ENABLE_DEMO_QUICK_LOGIN", "0").strip().lower() in ("1", "true", "si", "yes")


def _b64_sin_padding(datos):
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _desde_b64_sin_padding(texto):
    faltante = (-len(texto)) % 4
    return base64.urlsafe_b64decode((texto + ("=" * faltante)).encode("ascii"))


def es_hash_pbkdf2(valor):
    """Indica si una cadena ya corresponde a un hash PBKDF2-SHA256 válido."""
    return isinstance(valor, str) and valor.startswith(f"{PREFIJO_HASH}$")


def hashear_contrasena(contrasena_plana, iteraciones=ITERACIONES_PBKDF2):
    """
    Genera un hash PBKDF2-HMAC-SHA256 con sal aleatoria de 16 bytes.
    Formato resultante (87 caracteres): pbkdf2_sha256$<iteraciones>$<sal_b64>$<clave_b64>
    """
    if not isinstance(contrasena_plana, str) or not contrasena_plana:
        raise ValueError("La contraseña a proteger no puede estar vacía.")
    sal = secrets.token_bytes(TAMANO_SAL_BYTES)
    derivada = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena_plana.encode("utf-8"),
        sal,
        iteraciones,
    )
    return f"{PREFIJO_HASH}${iteraciones}${_b64_sin_padding(sal)}${_b64_sin_padding(derivada)}"


def verificar_contrasena(contrasena_plana, valor_almacenado):
    """
    Verifica una contraseña ingresada frente al valor almacenado en BD usando comparación constante.
    Soporta hashes PBKDF2-SHA256 y, por compatibilidad transitoria, registros previos sin migrar.
    """
    if not contrasena_plana or not isinstance(valor_almacenado, str) or not valor_almacenado:
        return False

    if es_hash_pbkdf2(valor_almacenado):
        partes = valor_almacenado.split("$")
        if len(partes) != 4:
            return False
        _, iter_str, sal_b64, clave_b64 = partes
        try:
            iteraciones = int(iter_str)
            if iteraciones <= 0:
                return False
            sal = _desde_b64_sin_padding(sal_b64)
            clave_esperada = _desde_b64_sin_padding(clave_b64)
        except Exception:
            return False

        derivada = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena_plana.encode("utf-8"),
            sal,
            iteraciones,
        )
        return hmac.compare_digest(derivada, clave_esperada)

    return hmac.compare_digest(contrasena_plana, valor_almacenado)

