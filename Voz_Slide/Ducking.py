# AGACHAR EL RESTO DEL AUDIO MIENTRAS AIDEN HABLA O ESCUCHA.
#
# Con música puesta, la voz de AIDEN compite con Spotify y el micrófono capta las dos cosas. Hasta
# ahora la única salida era que Marco bajara el volumen a mano antes de hablarle — justo la clase de
# gesto que un mayordomo debería ahorrarte.
#
# ── POR QUÉ NO SE LLAMA A LA HERRAMIENTA QUE YA EXISTE ────────────────────────
# `perifericos(accion="volumen_app")` hace algo parecido, pero no sirve aquí: busca UNA app POR SU
# NOMBRE y devuelve una frase para decirle a Marco ("Bajé el volumen de Spotify al 20%, señor").
# Aquí hacen falta las tres cosas que esa no da: recorrer TODAS las sesiones, GUARDAR el nivel
# exacto de cada una, y devolverlas después a ese nivel. Lo que sí se reusa es el mecanismo —
# pycaw, GetAllSessions e ISimpleAudioVolume, idéntico al de allá.
#
# ── LAS TRES COSAS QUE HAY QUE HACER BIEN ────────────────────────────────────
#
# 1. NO AGACHAR A AIDEN. Kokoro suena por el mismo proceso de Python: agachar "todo lo que suena"
#    incluiría su propia voz, y el efecto sería el contrario del que se busca.
#
# 2. PORCENTAJE, NO VALOR FIJO. Bajar todo a un 20 % absoluto le SUBIRÍA el volumen a algo que
#    Marco tenía al 5 %. Se baja al 20 % de lo que cada una tenía.
#
# 3. NO GUARDAR DOS VECES EL "ORIGINAL". Si se agacha estando ya agachado, lo que se guardaría como
#    nivel original sería el nivel agachado — y al restaurar la música se quedaría baja para
#    siempre. Por eso el nivel se guarda SOLO en la primera bajada, y el resto son anidamientos.

import os
import threading

FACTOR_HABLA = 0.20      # mientras AIDEN habla: bien abajo, su voz es lo que importa
FACTOR_ESCUCHA = 0.45    # mientras escucha: lo justo para que el micrófono no compita
_MINIMO_RESPETADO = 0.02  # por debajo de esto, Marco ya lo tenía casi mudo: no se toca

_lock = threading.RLock()
_guardados = {}          # sesión -> volumen que tenía antes
_profundidad = 0         # anidamientos activos (hablar dentro de escuchar, etc.)
_pausado = False


def pausar_ducking(pausar=True):
    """Modo gaming lo apaga: ahí el juego manda sobre la claridad de la voz de AIDEN, igual que el
    resto de las pausas del modo. Si estaba agachado, se restaura antes de apagarse."""
    global _pausado
    with _lock:
        _pausado = bool(pausar)
        if _pausado and _guardados:
            _restaurar_ahora()
    return True


def _sesiones():
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    try:
        from comtypes import CoInitialize
        CoInitialize()
    except Exception:
        pass
    yo = os.getpid()
    for s in AudioUtilities.GetAllSessions():
        if not s.Process:
            continue
        try:
            if s.Process.pid == yo:
                continue                    # la voz de AIDEN no se agacha a sí misma
            yield s, s._ctl.QueryInterface(ISimpleAudioVolume)
        except Exception:
            continue


def agachar(factor=FACTOR_HABLA):
    """Baja el resto del audio. Anidable: solo la primera llamada guarda los niveles."""
    global _profundidad
    with _lock:
        if _pausado:
            return False
        _profundidad += 1
        if _profundidad > 1:
            return True                     # ya estaba agachado; no se vuelve a guardar nada
        try:
            for s, ctl in _sesiones():
                try:
                    if ctl.GetMute():
                        continue            # Marco lo silenció él: no se toca
                    nivel = ctl.GetMasterVolume()
                    if nivel <= _MINIMO_RESPETADO:
                        continue
                    _guardados[s.Process.pid] = (ctl, nivel)
                    ctl.SetMasterVolume(nivel * factor, None)
                except Exception:
                    continue
        except Exception:
            # Sin pycaw, sin sesiones o sin mezclador: no hay nada que agachar y no pasa nada.
            return False
    return True


def restaurar():
    """Devuelve cada app a su nivel EXACTO. Solo cuando se cierra el último anidamiento."""
    global _profundidad
    with _lock:
        _profundidad = max(0, _profundidad - 1)
        if _profundidad > 0:
            return True                     # todavía hay alguien hablando o escuchando
        return _restaurar_ahora()


def _restaurar_ahora():
    for _pid, (ctl, nivel) in list(_guardados.items()):
        try:
            ctl.SetMasterVolume(nivel, None)
        except Exception:
            pass                            # la app se cerró: no hay nada que devolver
    _guardados.clear()
    return True


class mientras:
    """with Ducking.mientras(Ducking.FACTOR_HABLA): ...

    Context manager porque el `finally` es obligatorio: si AIDEN revienta a media frase y no se
    restaura, Marco se queda con la música al 20 % y sin saber por qué."""

    def __init__(self, factor=FACTOR_HABLA):
        self.factor = factor

    def __enter__(self):
        agachar(self.factor)
        return self

    def __exit__(self, *exc):
        restaurar()
        return False
