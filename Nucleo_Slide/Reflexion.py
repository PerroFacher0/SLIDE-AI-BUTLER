# REFLEXIÓN: el entendimiento que EVOLUCIONA sobre la situación actual de Marco.
#
# Es la capa más profunda de "te conoce". No son datos estables (eso es Perfil_Marco) ni tu estado de
# este instante (eso es Sintonia). Es la LECTURA CONTEMPLADA de tu MOMENTO: cómo has estado de ánimo
# estos días, en qué andas metido, dónde pareces atascado o en racha, y qué te vendría bien. AIDEN la
# genera en ratos tranquilos (auto-regulada) y la inyecta en CADA decisión, para que se sienta que de
# verdad PIENSA EN TI y entiende por lo que pasas — no que solo reacciona.
#
# Capas de comprensión de Marco, juntas:
#   Sintonia  -> cómo está AHORA MISMO (este turno)        [momentáneo]
#   Perfil    -> QUIÉN es (intereses, rutinas, estable)     [identidad]
#   Reflexion -> CÓMO está en su arco actual (su momento)   [situación, evoluciona]   <-- esto
#
# Casi-hoja: stdlib + Memoria_Episodica (hoja). LLM/estado se importan PEREZOSOS (sin ciclos).

import json
import os
import threading
import time

from Nucleo_Slide.Memoria_Episodica import _cargar as _cargar_episodios

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reflexion.json"
)
_lock = threading.RLock()

# ── Parámetros ajustables ─────────────────────────────────────────────────────
INTERVALO = 4 * 3600     # como máx, vuelve a reflexionar cada 4h
MIN_NUEVOS = 8           # o cuando haya 8 conversaciones nuevas
CHEQUEO = 30 * 60        # el hilo revisa cada 30 min (auto-decide si toca)

_reflexion = {"texto": "", "actualizado": 0, "n_episodios": 0}


def _cargar():
    global _reflexion
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                g = json.load(f)
            if isinstance(g, dict):
                _reflexion.update(g)
    except Exception:
        pass


def _guardar():
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(_reflexion, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


_cargar()


def reflexion_texto():
    # La lectura actual de Marco, para inyectar en el prompt.
    with _lock:
        return (_reflexion.get("texto") or "").strip()


def reflexionar(forzar=False):
    eps = _cargar_episodios() or []
    n = len(eps)
    ahora = time.time()
    if not forzar:
        nuevos = n - _reflexion.get("n_episodios", 0)
        if nuevos < MIN_NUEVOS and (ahora - _reflexion.get("actualizado", 0)) < INTERVALO:
            return
    if n < 6:                       # muy pocas conversaciones para una lectura útil
        return
    try:
        from Nucleo_Slide.Estado_Del_Mundo import metas_activas
        metas = "; ".join(m.get("texto", "") for m in metas_activas())
    except Exception:
        metas = ""
    muestra = "\n".join(
        f'[{e.get("fecha","")} {e.get("hora","")}] Marco: "{e.get("usuario","")[:110]}"'
        for e in eps[-40:]
    )
    anterior = (_reflexion.get("texto") or "").strip()
    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO as MODELO
        prompt = (
            "Eres la parte REFLEXIVA de AIDEN, que piensa en Marco como un amigo cercano que lo conoce "
            "bien. A partir de sus conversaciones recientes (y tu reflexión anterior si la hay), escribe "
            "una REFLEXIÓN breve y honesta sobre su SITUACIÓN ACTUAL: cómo ha estado de ánimo estos días, "
            "en qué anda metido, dónde parece ATASCADO o EN RACHA, y qué le vendría bien. NO son datos "
            "sueltos: es tu LECTURA empática de su momento. 3-5 frases, en tercera persona, concreta; "
            "solo lo que se deduzca de los datos, sin inventar; integra lo nuevo con lo anterior.\n\n"
            + (f"REFLEXIÓN ANTERIOR:\n{anterior}\n\n" if anterior else "")
            + (f"METAS DE MARCO: {metas}\n" if metas else "")
            + f"CONVERSACIONES RECIENTES:\n{muestra}\n\nTU REFLEXIÓN ACTUAL:"
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.5, max_tokens=250,
        )
        texto = (r.choices[0].message.content or "").strip()
        if texto:
            with _lock:
                _reflexion["texto"] = texto
                _reflexion["actualizado"] = ahora
                _reflexion["n_episodios"] = n
            print("[reflexion] AIDEN reflexionó sobre el momento de Marco.")
    except Exception as e:
        print(f"[reflexion] no pude reflexionar: {e}")
    _guardar()


def iniciar_reflexion():
    # Arranca la reflexión de fondo (auto-regulada).
    def _bucle():
        time.sleep(240)
        while True:
            try:
                reflexionar()
            except Exception:
                pass
            time.sleep(CHEQUEO)

    threading.Thread(target=_bucle, daemon=True).start()
