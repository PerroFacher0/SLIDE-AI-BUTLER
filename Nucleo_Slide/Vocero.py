# VOCERO: coordinador central de la voz PROACTIVA de AIDEN.
#
# Problema que resuelve: ahora AIDEN tiene MUCHOS comportamientos de fondo que hablan por su cuenta
# (conciencia, seguimiento de metas, presencia, vigilantes de pantalla/portapapeles/llamadas). Si
# cada uno habla cuando quiere, juntos vuelven a AIDEN un loro insoportable. El Vocero hace que toda
# la voz proactiva pase por UN solo punto que habla CON INTENCIÓN:
#   - Presupuesto GLOBAL: máx MAX_POR_HORA mensajes proactivos por hora, con GAP_MINIMO entre dos.
#   - No repite lo mismo (dedup).
#   - Se CALLA si Marco está en reunión, gaming o ausente (lee Estado_Del_Mundo).
#   - Las URGENCIAS (llamada entrante) saltan el límite (prioridad 'alta').
#   - Lo que NO se dice queda registrado en el hilo de conciencia (no se pierde la info).
#
# Módulo casi-hoja (stdlib + Estado_Del_Mundo, que es hoja). Las RESPUESTAS directas a Marco NO pasan
# por aquí (esas siempre se dicen); el Vocero es SOLO para lo proactivo/no solicitado.

import threading
import time
from collections import deque

# ── Parámetros ajustables ─────────────────────────────────────────────────────
MAX_POR_HORA = 8      # tope GLOBAL de intervenciones proactivas por hora (subido: más presente)
GAP_MINIMO = 60       # segundos mínimos entre dos intervenciones proactivas

_lock = threading.RLock()
_marcas = deque(maxlen=MAX_POR_HORA)   # timestamps de lo dicho en la última hora
_ultimo = 0                            # timestamp de la última intervención
_recientes = deque(maxlen=8)           # textos recientes (dedup)


def _estado():
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        return obtener()
    except Exception:
        return {}


def _registrar_silenciado(texto, origen):
    # No se dijo en voz, pero queda en el hilo de conciencia (no se pierde la info).
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"(callado para no molestar) {texto}", origen or "vocero")
    except Exception:
        pass


def emitir(hablar, texto, origen="", prioridad="normal"):
    """Punto único de la voz PROACTIVA. Devuelve True si se dijo, False si se silenció.
    `hablar` es el callback real (hablado_del_asistente). prioridad 'alta' salta el presupuesto."""
    global _ultimo
    texto = str(texto or "").strip()
    if not texto:
        return False
    urgente = str(prioridad).lower() in ("alta", "urgente")

    with _lock:
        ahora = time.time()
        if not urgente:
            est = _estado()
            if est.get("en_reunion") or est.get("modo") == "gaming" or not est.get("marco_presente", True):
                _registrar_silenciado(texto, origen)
                return False
            if texto in _recientes:                      # ya lo dije hace poco
                return False
            while _marcas and ahora - _marcas[0] > 3600:  # limpia la ventana de 1h
                _marcas.popleft()
            if (ahora - _ultimo) < GAP_MINIMO or len(_marcas) >= MAX_POR_HORA:
                _registrar_silenciado(texto, origen)      # presupuesto agotado / muy seguido
                return False
        _ultimo = ahora
        _marcas.append(ahora)
        _recientes.append(texto)

    try:
        hablar(texto)
    except Exception:
        pass
    return True
