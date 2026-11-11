"""
estilos.py
==========
Configuración visual compartida (E25: fuentes multiplataforma).

Tkinter NO acepta una tupla de familias alternativas del tipo ("Segoe UI", "Arial", "sans-serif")
dentro de la especificación de fuente (el segundo elemento se interpreta como tamaño).
Por eso se define la lista de preferencia y se elige la familia adecuada según
el sistema operativo, evitando deformaciones visuales fuera de Windows.
Todos los módulos usan la constante FUENTE en lugar de escribir "Segoe UI" directamente.
"""

import sys

FUENTES_PREFERIDAS = ("Segoe UI", "Arial", "sans-serif")

if sys.platform.startswith("win"):
    FUENTE = FUENTES_PREFERIDAS[0]
elif sys.platform == "darwin":
    FUENTE = FUENTES_PREFERIDAS[1]
else:
    FUENTE = "DejaVu Sans"  
