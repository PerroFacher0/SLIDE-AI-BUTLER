import os
from datetime import datetime

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "notas.txt"
)


def tomar_nota(nota):
    nota = str(nota).strip()
    if not nota:
        return "No me dijiste qué anotar, señor."
    try:
        with open(_RUTA, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {nota}\n")
        return "Nota guardada, señor."
    except Exception as e:
        return f"No pude guardar la nota, señor: {e}"


def leer_notas():
    if not os.path.exists(_RUTA):
        return "No tienes notas guardadas, señor."
    try:
        with open(_RUTA, "r", encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip()]
        if not lineas:
            return "No tienes notas guardadas, señor."
        return "Tus notas:\n" + "\n".join(lineas[-15:])   # las ultimas 15
    except Exception as e:
        return f"No pude leer las notas, señor: {e}"


def notas(accion="leer", texto=""):
    """HERRAMIENTA unificada de notas. accion 'guardar' (con texto) apunta una nota; accion 'leer'
    (por defecto) lee las últimas. Reemplaza tomar_nota + leer_notas sin perder nada."""
    a = str(accion or "").strip().lower()
    if a in ("guardar", "anotar", "apuntar", "toma", "tomar", "agregar", "nueva") or (texto and a != "leer"):
        return tomar_nota(texto)
    return leer_notas()
