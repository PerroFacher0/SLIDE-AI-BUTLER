# FRENO DE EMERGENCIA: parar a AIDEN a mitad de una acción larga.
#
# El problema que resuelve: cuando AIDEN arranca un PowerShell pesado o una secuencia de clics,
# antes no había forma de detenerlo — te tocaba esperar el timeout completo mirando cómo hacía algo
# que ya no querías. El barge-in de la voz (Herramientas_del_asistente) solo corta el AUDIO; no
# detiene lo que se está EJECUTANDO.
#
# Cómo se para una acción, por orden de fiabilidad:
#   1. ATAJO DE TECLADO Ctrl+Alt+P ("Parar") — el canal confiable. Funciona aunque AIDEN esté
#      hablando, aunque el micrófono esté ocupado y aunque la app en foco se haya tragado el resto
#      de la entrada. Sin dependencias: se sondea GetAsyncKeyState de Windows.
#   2. La herramienta `cancelar` — para Telegram (corre en su propio hilo, sin tocar el micrófono).
#
# Deliberadamente NO se escucha el micrófono aquí: el VAD y el vigía de barge-in ya lo tienen
# abierto, y un tercer consumidor del mismo dispositivo provoca conflictos y lecturas fallidas. El
# atajo cubre el caso real sin pelearse por el hardware.

import ctypes
import threading
import time

_evento = threading.Event()
_lock = threading.RLock()
_operacion = None      # descripción de lo que corre ahora (None = nada en curso)
_motivo = ""
_vigia = None

# Ctrl + Alt + P — combinación libre en Windows (no choca con nada del sistema).
_VK_CONTROL, _VK_ALT, _VK_P = 0x11, 0x12, 0x50
_SONDEO = 0.05         # cada cuánto se mira el teclado (50 ms: reacciona al instante, gasta nada)


class Cancelado(Exception):
    """Se lanza dentro de una operación cancelable cuando Marco pidió parar."""


def _tecla(vk):
    try:
        # bit alto encendido = la tecla está presionada AHORA mismo.
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def _vigilar_atajo():
    # Sondea el teclado mientras haya una operación en curso.
    while True:
        with _lock:
            if _operacion is None:
                return
        if _tecla(_VK_CONTROL) and _tecla(_VK_ALT) and _tecla(_VK_P):
            pedir_cancelar("atajo Ctrl+Alt+P")
            return
        time.sleep(_SONDEO)


def pedir_cancelar(motivo=""):
    """Levanta la bandera: la operación en curso debe detenerse cuanto antes."""
    global _motivo
    with _lock:
        if _operacion is None:
            return False
        _motivo = motivo or "petición de Marco"
    _evento.set()
    return True


def cancelado():
    """True si se pidió cancelar la operación en curso."""
    return _evento.is_set()


def motivo():
    with _lock:
        return _motivo


def revisar():
    """Punto de control: llámalo dentro de bucles largos. Lanza Cancelado si Marco pidió parar."""
    if _evento.is_set():
        raise Cancelado(_motivo or "cancelado")


def operacion_en_curso():
    with _lock:
        return _operacion


class operacion:
    """Context manager que marca un bloque como cancelable.

        with operacion("instalando dependencias"):
            ...  # llamar revisar() o cancelado() de tanto en tanto

    Al entrar limpia la bandera y arranca el vigía del atajo; al salir lo apaga."""

    def __init__(self, descripcion=""):
        self.descripcion = str(descripcion or "acción")

    def __enter__(self):
        global _operacion, _motivo, _vigia
        with _lock:
            # Anidada: la de afuera manda, no se reinicia nada.
            self._anidada = _operacion is not None
            if self._anidada:
                return self
            _evento.clear()
            _motivo = ""
            _operacion = self.descripcion
        _vigia = threading.Thread(target=_vigilar_atajo, daemon=True)
        _vigia.start()
        return self

    def __exit__(self, *exc):
        global _operacion
        if not self._anidada:
            with _lock:
                _operacion = None       # esto también apaga el hilo vigía
        return False                     # nunca se traga la excepción


def cancelar(motivo=""):
    """HERRAMIENTA: detiene lo que AIDEN esté ejecutando ahora mismo (comando largo, secuencia de
    clics, ajuste visual). Úsala cuando Marco diga 'para', 'detente', 'cancela', 'ya no'."""
    actual = operacion_en_curso()
    if actual is None:
        return "No estoy ejecutando nada ahora mismo, señor."
    pedir_cancelar(motivo or "Marco pidió parar")
    return f"Detengo lo que estaba haciendo, señor: {actual}."
