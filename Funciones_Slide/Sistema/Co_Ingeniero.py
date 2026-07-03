# CO-INGENIERO: la dinámica del taller de Tony y Jarvis. AIDEN no espera a que le pidan ayuda — NOTA
# cuando Marco lleva rato ATASCADO peleando con lo mismo y se ofrece a echar una mano, como Jarvis
# diciendo "Señor, quizá si intentara…". Comportamiento de fondo.
#
# Anti-molestia (CLAVE para que no sea un pesado): solo dispara si hay EVIDENCIA de lucha —
#   (a) llevas mucho rato en la MISMA ventana, Y
#   (b) hay señal de struggle: un ERROR en pantalla reciente, o FRUSTRACIÓN en lo último que dijiste.
# Así, leer/ver algo un buen rato NO lo activa; pelear con un error SÍ. Pasa por el Vocero (presupuesto
# global + se calla en reunión/gaming/ausente) y tiene cooldown por episodio de atasco.

import threading
import time

import win32gui

# ── Parámetros ajustables ─────────────────────────────────────────────────────
INTERVALO = 30          # cada cuántos seg revisa la ventana activa
UMBRAL_ATASCO = 8 * 60   # seg en la MISMA ventana para considerar "atascado" (subido: ayuda antes)
COOLDOWN = 30 * 60       # no volver a ofrecer ayuda tan pronto

_pausado = False
_titulo = ""            # título de la ventana activa que venimos observando
_desde = 0              # desde cuándo está en esa ventana
_ofrecido_en = 0        # timestamp de la última oferta


def pausar_co_ingeniero(pausar=True):
    global _pausado
    _pausado = bool(pausar)


def _ventana_titulo():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or ""
    except Exception:
        return ""


def _hay_senal_de_lucha():
    # (a) ¿error en pantalla reciente? (lo registra el Vigilante_Pantalla en el hilo de conciencia)
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        ahora = time.time()
        for e in (obtener().get("eventos", []) or []):
            if e.get("origen") == "pantalla" and (ahora - e.get("t", 0)) < UMBRAL_ATASCO:
                return True
    except Exception:
        pass
    # (b) ¿frustración en lo último que dijo Marco?
    try:
        from Nucleo_Slide.Memoria_Episodica import _cargar
        from Nucleo_Slide.Sintonia import _FRUSTRACION, _norm
        eps = _cargar() or []
        if eps:
            ultimo = _norm(eps[-1].get("usuario", ""))
            if any(p in ultimo for p in _FRUSTRACION):
                return True
    except Exception:
        pass
    return False


def _generar_oferta(titulo):
    base = f"Señor, lo noto atascado con «{titulo[:40]}» hace un buen rato. ¿Le echo un ojo?"
    try:
        from Nucleo_Slide.Cerebro import client, MODELO
        from Nucleo_Slide.Reflexion import reflexion_texto
        refl = (reflexion_texto() or "")[:200]
        prompt = (
            "Eres AIDEN, como Jarvis en el taller con Tony. Notas que Marco (trátalo de 'señor') lleva "
            f"un buen rato ATASCADO peleando con «{titulo[:60]}». "
            + (f"Lo que sabes de su momento: {refl}. " if refl else "")
            + "Ofrécele ayuda en UNA frase corta, cálida y con tu chispa, como un co-ingeniero que se "
            "mete a echar una mano (invítalo a que le eches un ojo a la pantalla). Natural, sin robot."
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=80,
        )
        return (r.choices[0].message.content or "").strip() or base
    except Exception:
        return base


def _revisar(hablar):
    global _titulo, _desde, _ofrecido_en
    if _pausado:
        return
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        est = obtener()
    except Exception:
        est = {}
    if est.get("en_reunion") or est.get("modo") == "gaming" or not est.get("marco_presente", True):
        _titulo = ""                      # reinicia el conteo cuando no aplica
        return

    t = _ventana_titulo()
    if not t:
        return
    if t != _titulo:                      # cambió de ventana -> reinicia el cronómetro
        _titulo = t
        _desde = time.time()
        return

    ahora = time.time()
    if (ahora - _desde) < UMBRAL_ATASCO:
        return
    if (ahora - _ofrecido_en) < COOLDOWN:
        return
    if not _hay_senal_de_lucha():         # rato largo PERO sin evidencia de lucha -> no molestar
        return

    frase = _generar_oferta(t)
    try:
        from Nucleo_Slide.Vocero import emitir
        if emitir(hablar, frase, "coingeniero"):
            _ofrecido_en = ahora
            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
            registrar_evento(f"Co-ingeniero se ofreció a ayudar con «{t[:40]}».", "coingeniero")
    except Exception:
        pass


def iniciar_co_ingeniero(hablar):
    def _bucle():
        time.sleep(120)
        while True:
            try:
                _revisar(hablar)
            except Exception:
                pass
            time.sleep(INTERVALO)

    threading.Thread(target=_bucle, daemon=True).start()
