# EL ÚLTIMO ERROR, EN TEXTO, ESPERANDO A QUE MARCO PREGUNTE.
#
# Cuando AIDEN ejecuta algo y falla, el texto exacto del error YA lo tiene en la mano — stderr,
# entero, sin ambigüedad. Pero se lo daba al modelo en ese turno y se perdía. Si Marco preguntaba
# medio minuto después "¿y por qué falló?", AIDEN acababa haciendo una captura de pantalla y
# mandándosela a Gemini Vision para leer un texto que había tenido literalmente en una variable.
#
# Esto lo guarda. Y guardar es lo único que hace.
#
# ── LAS TRES REGLAS QUE LO MANTIENEN INOFENSIVO ──────────────────────────────
#
# 1. UNA SOLA ENTRADA. El error nuevo pisa al viejo. No es un historial: si fuera una lista, en un
#    día de trabajo sería un registro de todo lo que le ha salido mal a Marco, que es justo lo que
#    este proyecto decidió no tener.
# 2. NUNCA TOCA EL DISCO. Vive en memoria y muere con el proceso. Nada que rebuscar después, nada
#    que acabe en una copia de seguridad, nada que se suba a ningún sitio.
# 3. CADUCA. Pasados unos minutos, el error de antes probablemente ya no es del que Marco habla, y
#    contestarle sobre el equivocado con toda seguridad es peor que decirle que mire.

import threading
import time

VIDA = 300.0        # s: 5 minutos. Más viejo que eso y ya casi seguro no es de lo que habla.
_MAX = 1200         # caracteres: un traceback entero cabe; un volcado de miles de líneas no.

_lock = threading.RLock()
_ultimo = {"texto": "", "en": 0.0, "de": ""}


def recordar(texto, de="ejecutar_en_pc"):
    """Guarda el error. Lo llama quien lo tiene en la mano, justo cuando lo tiene."""
    texto = str(texto or "").strip()
    if not texto:
        return False
    with _lock:
        _ultimo["texto"] = texto[:_MAX]
        _ultimo["en"] = time.time()
        _ultimo["de"] = str(de)
    return True


def reciente(segundos=VIDA):
    """(texto, de, hace_cuantos_segundos) si aún vale, o None."""
    with _lock:
        if not _ultimo["texto"]:
            return None
        edad = time.time() - _ultimo["en"]
        if edad > segundos:
            return None
        return _ultimo["texto"], _ultimo["de"], edad


def olvidar():
    with _lock:
        _ultimo["texto"], _ultimo["en"], _ultimo["de"] = "", 0.0, ""
    return True
