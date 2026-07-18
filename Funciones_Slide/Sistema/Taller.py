# MODO TALLER: la dinámica del taller de Tony Stark, en tu PC.
#
# Marco dice "acompáñame" y AIDEN se queda MIRANDO su pantalla mientras trabaja: cada ~90 segundos
# la observa y, SOLO si tiene un comentario de copiloto que sume (un error que ve venir, una
# sugerencia concreta, un dato, una pulla con cariño), lo dice en UNA frase. Si no, calla.
# "Ya terminamos" (o descansar) cierra la sesión; también se cierra sola al agotar el tiempo.
#
# Diseño para NO abrumar: el hilo SOLO existe durante la sesión que Marco pidió (no es un vigilante
# permanente), habla por el VOCERO (presupuesto global, silencios en reunión/gaming), no se repite
# (recuerda sus últimos comentarios), y se apaga solo (default 45 min, con cierre hablado).

import threading
import time
from collections import deque

CICLO = 90                 # cada cuánto mira la pantalla (segundos)
MIN_ENTRE_COMENTARIOS = 150  # aunque vea algo, no comenta dos veces en <2.5 min
DURACION_DEFAULT_MIN = 45  # la sesión se cierra sola tras esto

_activo = False
_hasta = 0.0
_ultimo_comentario = 0.0
_recientes = deque(maxlen=4)   # últimos comentarios (anti-loro, van al prompt)
_hablar = None                 # callback de voz (se fija al iniciar)
_lock = threading.RLock()


def taller_activo():
    return _activo


def _decir(texto, prioridad="normal"):
    try:
        from Nucleo_Slide.Vocero import emitir
        from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
        emitir(_hablar or hablado_del_asistente, texto, origen="taller", prioridad=prioridad)
    except Exception:
        pass


def _comentar_pantalla():
    # Mira la pantalla UNA vez y devuelve el comentario de copiloto (o "" si no aporta).
    try:
        import cv2
        import numpy as np
        from PIL import ImageGrab
        from Funciones_Slide.Info.Vision import _describir_imagen
        img = ImageGrab.grab()
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception:
        return ""
    previos = " | ".join(_recientes) or "(nada aún)"
    instruccion = (
        "Eres AIDEN en MODO TALLER: acompañas a Marco mientras trabaja, como Jarvis acompañaba a "
        "Tony Stark en el taller. Esta es su pantalla AHORA. Si tienes UN comentario de COPILOTO "
        "genuinamente útil — un error que ves, una sugerencia concreta y accionable, un dato que "
        "suma, o una observación aguda con tu chispa — dilo en UNA sola frase corta, hablada, "
        "tratándolo de 'señor'. NO describas la pantalla, NO resumas lo obvio, NO repitas nada "
        f"parecido a lo que ya dijiste (dijiste hace poco: {previos}). "
        "Si no hay nada que realmente sume, responde EXACTAMENTE: NADA"
    )
    try:
        r = _describir_imagen(frame, instruccion)
        r = str(r or "").strip()
        if not r or r.upper().startswith("NADA") or r.startswith("No pude"):
            return ""
        return r.splitlines()[0][:220]
    except Exception:
        return ""


def _bucle_sesion():
    global _activo, _ultimo_comentario
    while True:
        with _lock:
            if not _activo:
                return
            if time.time() >= _hasta:
                _activo = False
                break
        time.sleep(CICLO)
        with _lock:
            if not _activo:
                return
        if time.time() - _ultimo_comentario < MIN_ENTRE_COMENTARIOS:
            continue
        comentario = _comentar_pantalla()
        if comentario:
            _ultimo_comentario = time.time()
            _recientes.append(comentario)
            _decir(comentario)
            try:
                from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
                registrar_evento(f"(taller) {comentario}", "taller")
            except Exception:
                pass
    # tiempo agotado: cierre con clase (prioridad alta para que no lo silencie el presupuesto)
    _decir("Se nos fue el tiempo del taller, señor. Cierro la sesión; si me quiere de vuelta, "
           "dígame 'acompáñame'.", prioridad="alta")


def modo_taller(accion="iniciar", minutos=0):
    """HERRAMIENTA: sesión de copiloto mirando la pantalla de Marco (como Jarvis en el taller).
    accion: 'iniciar' o 'parar'. minutos: duración (0 = 45 por defecto)."""
    global _activo, _hasta, _hablar
    a = str(accion or "").strip().lower()
    if a in ("parar", "detener", "cerrar", "fin", "off", "salir"):
        return detener_taller()
    try:
        mins = int(minutos) or DURACION_DEFAULT_MIN
    except (TypeError, ValueError):
        mins = DURACION_DEFAULT_MIN
    mins = max(5, min(mins, 180))
    with _lock:
        if _activo:
            _hasta = time.time() + mins * 60
            return f"Ya estoy con usted en el taller, señor; extiendo la sesión a {mins} minutos."
        _activo = True
        _hasta = time.time() + mins * 60
    if _hablar is None:
        try:
            from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
            _hablar = hablado_del_asistente
        except Exception:
            pass
    threading.Thread(target=_bucle_sesion, daemon=True).start()
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento, actualizar
        registrar_evento(f"Modo taller iniciado ({mins} min)", "taller")
        actualizar(modo="taller")
    except Exception:
        pass
    return (f"Modo taller activado, señor: le acompaño los próximos {mins} minutos mirando su "
            "pantalla, y solo hablaré cuando tenga algo que valga la pena. Dígame 'ya terminamos' "
            "para cerrar.")


def detener_taller(silencioso=False):
    global _activo
    with _lock:
        estaba = _activo
        _activo = False
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento, actualizar, obtener
        if obtener().get("modo") == "taller":
            actualizar(modo="normal")
        if estaba:
            registrar_evento("Modo taller cerrado", "taller")
    except Exception:
        pass
    if not estaba:
        return "No estábamos en el taller, señor." if not silencioso else ""
    return "" if silencioso else "Cerramos el taller, señor. Un gusto trabajar a su lado."
