# "ME TOMÉ LA LIBERTAD DE…": Jarvis se ADELANTABA y preparaba lo que Tony iba a necesitar. AIDEN, al
# verte ABRIR una app de trabajo (Code/Word/Obsidian/…) teniendo metas activas, se ofrece a tener a
# mano TU CONTEXTO de la meta relevante (dónde quedaste), sin que lo pidas. Comportamiento de fondo.
#
# Anti-error (clave): NO fuerza una meta cualquiera. El LLM JUZGA si alguna meta encaja con lo que vas
# a hacer; si ninguna encaja con claridad, se CALLA (responde NADA). Vía Vocero + cooldown, y se calla
# en reunión/gaming/ausente.

import threading
import time

import win32gui

INTERVALO = 20
COOLDOWN = 90 * 60      # como mucho, una preparación cada 1.5h (subido: más presente)

_APPS_TRABAJO = (
    "code", "word", "excel", "powerpoint", "onenote", "obsidian", "notion", "docs",
    "overleaf", "pycharm", "jupyter", "spyder", "sheets", "slides", "figma", "photoshop",
)

_pausado = False
_ultimo_titulo = None   # None = aún no observamos; "" no aplica
_ultima_prep = 0


def pausar_preparacion(pausar=True):
    global _pausado
    _pausado = bool(pausar)


def _norm(t):
    return str(t or "").lower().translate(str.maketrans("áéíóúü", "aeiouu"))


def _ventana_titulo():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or ""
    except Exception:
        return ""


def _es_app_trabajo(titulo):
    t = _norm(titulo)
    return any(k in t for k in _APPS_TRABAJO)


def _preparar(app, metas):
    try:
        from Nucleo_Slide.Cerebro import client, MODELO
        metas_txt = "\n".join(
            f"- {m.get('texto','')} (avances: "
            + ("; ".join(a.get("nota", "") for a in (m.get("avances") or [])[-2:]) or "ninguno") + ")"
            for m in metas[:4]
        )
        prompt = (
            "Eres AIDEN, como Jarvis que se ADELANTA ('me tomé la libertad de...'). Marco acaba de abrir "
            f"«{app[:60]}» para ponerse a trabajar. Sus metas activas:\n{metas_txt}\n\n"
            "Si ALGUNA meta es CLARAMENTE relevante a lo que va a hacer, ofrécele en UNA frase corta "
            "tener a mano su contexto o recordarle dónde quedó, con estilo de mayordomo que se adelantó "
            "('Señor, me tomé la libertad de repasar…'). Si NINGUNA encaja con claridad, responde "
            "EXACTAMENTE: NADA."
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.5, max_tokens=90,
        )
        t = (r.choices[0].message.content or "").strip()
        return "" if t.upper().startswith("NADA") else t
    except Exception:
        return ""


def _revisar(hablar):
    global _ultimo_titulo, _ultima_prep
    if _pausado:
        return
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener, metas_activas
        est = obtener()
    except Exception:
        return
    if est.get("en_reunion") or est.get("modo") == "gaming" or not est.get("marco_presente", True):
        return

    t = _ventana_titulo()
    if _ultimo_titulo is None:        # primera observación: registra, no dispares aún
        _ultimo_titulo = t
        return
    if t == _ultimo_titulo:           # solo actúa cuando CAMBIAS a una ventana nueva
        return
    _ultimo_titulo = t

    if not _es_app_trabajo(t):
        return
    if (time.time() - _ultima_prep) < COOLDOWN:
        return
    metas = metas_activas()
    if not metas:
        return

    frase = _preparar(t, metas)
    if not frase:
        return
    try:
        from Nucleo_Slide.Vocero import emitir
        if emitir(hablar, frase, "preparacion"):
            _ultima_prep = time.time()
    except Exception:
        pass


def iniciar_preparacion(hablar):
    def _bucle():
        time.sleep(150)
        while True:
            try:
                _revisar(hablar)
            except Exception:
                pass
            time.sleep(INTERVALO)

    threading.Thread(target=_bucle, daemon=True).start()
