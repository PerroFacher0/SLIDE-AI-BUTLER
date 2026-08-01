# Portapapeles inteligente: AIDEN vigila lo que COPIAS y, si reconoce algo accionable, OFRECE
# ayuda solo (el momento "Jarvis vivo"). Comportamiento de fondo (como Presencia), no una tool.
# Tú aceptas con la palabra clave / manos libres ("sí, explícalo" / "sí, resúmelo").
#
# Diseño ANTI-MOLESTIA:
#   1. Solo reacciona a patrones INEQUÍVOCOS (un error/traceback, un link de YouTube). El texto
#      normal se ignora -> casi nunca habla.
#   2. Dedup (no re-ofrece el mismo contenido) + cooldown.
#   3. Se PAUSA en modo gaming.
#   4. Solo OFRECE; no actúa sin tu permiso.

import re
import threading
import time

try:
    import pyperclip
except Exception:
    pyperclip = None

# ── Parámetros ajustables ─────────────────────────────────────────────────────
INTERVALO = 2     # cada cuántos seg mira el portapapeles
COOLDOWN = 60     # seg entre ofertas (no atosigar)

_pausado = False
_ultimo = ""          # último contenido visto (para detectar cambios)
_ultimo_ofrecido = "" # contenido sobre el que ya ofrecimos (dedup)
_ultimo_aviso = 0

_RX_YOUTUBE = re.compile(r'(youtube\.com/watch|youtu\.be/|youtube\.com/shorts)', re.I)


def pausar_vigilante_portapapeles(pausar=True):
    # Silencia el vigilante (lo usa el modo gaming).
    global _pausado
    _pausado = bool(pausar)


def _es_error(t):
    # Heurística ESTRICTA para no confundir texto normal con un error/traceback.
    low = t.lower()
    if "traceback (most recent call last)" in low:
        return True
    if ("error" in low or "exception" in low) and "\n" in t and (
            'file "' in low or "line " in low or "línea " in low or "  at " in low or ".py" in low):
        return True
    return False


def _clasificar(t):
    # Devuelve la frase a ofrecer, o None si el contenido no amerita.
    t = (t or "").strip()
    if len(t) < 6 or len(t) > 6000:
        return None
    if _RX_YOUTUBE.search(t):
        return "Señor, veo que copió un video de YouTube. ¿Quiere que se lo resuma?"
    if _es_error(t):
        return "Señor, veo que copió un error. ¿Quiere que se lo explique?"
    return None


def _revisar(hablar):
    global _ultimo, _ultimo_ofrecido, _ultimo_aviso
    if _pausado or pyperclip is None:
        return
    try:
        actual = pyperclip.paste()
    except Exception:
        return
    if not actual or actual == _ultimo:
        return
    _ultimo = actual                      # registra el cambio
    # Publica al bus de eventos para que 'esperar_evento' pueda despertar con esto ("espera a que
    # copie el enlace"). Va aquí y no en un sondeo aparte: el portapapeles ya se mira desde este
    # hilo, no tiene sentido que dos vigilantes pregunten lo mismo cada dos segundos.
    try:
        from Funciones_Slide.Sistema.Vigilante_Eventos import publicar
        publicar("portapapeles", "", "", actual[:200])
    except Exception:
        pass
    if actual == _ultimo_ofrecido:        # ya ofrecimos sobre esto
        return
    frase = _clasificar(actual)
    if not frase:
        return
    ahora = time.time()
    if ahora - _ultimo_aviso < COOLDOWN:
        return
    _ultimo_aviso = ahora
    _ultimo_ofrecido = actual
    from Nucleo_Slide.Vocero import emitir
    emitir(hablar, frase, "portapapeles")
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento("Marco copió algo accionable (error o link); ofrecí ayuda.", "portapapeles")
    except Exception:
        pass


def iniciar_vigilante_portapapeles(hablar):
    # Arranca el vigilante del portapapeles en segundo plano.
    def _bucle():
        global _ultimo
        time.sleep(22)                    # deja pasar el arranque/briefing
        if pyperclip is not None:
            try:
                _ultimo = pyperclip.paste()   # ignora lo que YA estaba copiado al arrancar
            except Exception:
                pass
        while True:
            try:
                _revisar(hablar)
            except Exception:
                pass
            time.sleep(INTERVALO)

    threading.Thread(target=_bucle, daemon=True).start()
