# PERFIL DE MARCO (Parte 3 del núcleo Jarvis): AIDEN no solo guarda datos sueltos, sino que APRENDE
# quién es Marco — sus temas recurrentes, rutinas, proyectos y forma de hablar — destilándolo de la
# memoria episódica. El perfil COMPONE con el tiempo y se inyecta en cada decisión, para que AIDEN
# "te conozca" y anticipe. Es lo que separa un asistente de un Jarvis.
#
# Dos capas:
#   1. BARATA (siempre): frecuencia de palabras clave -> los temas que más te importan.
#   2. INTELIGENTE (de vez en cuando): el LLM destila un perfil conciso a partir de los episodios +
#      el perfil anterior. Se auto-regula (cada INTERVALO horas o cada MIN_NUEVOS episodios).
#
# Módulo casi-hoja: stdlib + Memoria_Episodica (hoja). El cliente del LLM se importa PEREZOSO.

import json
import os
import threading
import time
from collections import Counter

from Nucleo_Slide.Memoria_Episodica import _cargar as _cargar_episodios

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "perfil_marco.json"
)
_lock = threading.RLock()

# ── Parámetros ajustables ─────────────────────────────────────────────────────
INTERVALO = 6 * 3600     # como máximo, re-destila con LLM cada 6h
MIN_NUEVOS = 12          # o cuando haya 12 episodios nuevos desde la última vez
CHEQUEO = 30 * 60        # el hilo revisa cada 30 min (y auto-decide si toca destilar)
MIN_APARICIONES = 3      # un tema cuenta si aparece al menos 3 veces

_perfil = {"texto": "", "temas": [], "actualizado": 0, "n_episodios": 0}


def _cargar():
    global _perfil
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                g = json.load(f)
            if isinstance(g, dict):
                _perfil.update(g)
    except Exception:
        pass


def _guardar():
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(_perfil, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


_cargar()


def perfil_texto():
    # Lo que AIDEN ha aprendido de Marco, para inyectar en el prompt.
    with _lock:
        t = (_perfil.get("texto") or "").strip()
        temas = _perfil.get("temas") or []
    partes = []
    if t:
        partes.append(t)
    if temas:
        partes.append("Temas que más le interesan (por frecuencia): " + ", ".join(temas))
    return "\n".join(partes).strip()


def _solo_vinetas(texto):
    # Quita preámbulos/cierres: deja desde la primera viñeta. Si no hay viñetas, devuelve igual.
    lineas = (texto or "").splitlines()
    while lineas and not lineas[0].lstrip().startswith(("-", "*", "•", "·")):
        lineas.pop(0)
    limpio = "\n".join(lineas).strip()
    return limpio or (texto or "").strip()


def _temas_frecuentes(episodios, n=8):
    c = Counter()
    for ep in episodios[-200:]:
        for k in ep.get("claves", []):
            c[k] += 1
    return [k for k, v in c.most_common(n) if v >= MIN_APARICIONES]


def actualizar_perfil(forzar=False):
    # Capa barata SIEMPRE; capa LLM solo si toca (auto-regulada).
    episodios = _cargar_episodios()
    n = len(episodios)
    ahora = time.time()

    temas = _temas_frecuentes(episodios)
    with _lock:
        _perfil["temas"] = temas

    if not forzar:
        nuevos = n - _perfil.get("n_episodios", 0)
        if nuevos < MIN_NUEVOS and (ahora - _perfil.get("actualizado", 0)) < INTERVALO:
            _guardar()
            return
    if n < 5:                      # muy pocos episodios para destilar algo útil
        _guardar()
        return

    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO as MODELO
        muestra = "\n".join(
            f'- [{e.get("fecha","")}] Marco: "{e.get("usuario","")[:120]}"'
            for e in episodios[-60:]
        )
        anterior = (_perfil.get("texto") or "").strip()
        prompt = (
            "Eres el sistema de aprendizaje de AIDEN, el asistente de Marco. A partir de estas "
            "conversaciones recientes (y el perfil anterior si lo hay), ACTUALIZA un PERFIL CONCISO "
            "de quién es Marco: sus intereses, rutinas, proyectos en curso, su forma de hablar y lo "
            "que le importa. Reglas: 5-8 viñetas cortas, en TERCERA persona, SOLO lo que se deduzca "
            "de los datos (NO inventes), fusiona lo nuevo con lo anterior sin perder lo válido. "
            "Responde SOLO con las viñetas (cada una empezando con '- '), SIN frase introductoria "
            "ni de cierre.\n\n"
            + (f"PERFIL ANTERIOR:\n{anterior}\n\n" if anterior else "")
            + f"CONVERSACIONES RECIENTES:\n{muestra}\n\nPERFIL ACTUALIZADO:"
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=400,
        )
        texto = _solo_vinetas((r.choices[0].message.content or "").strip())
        if texto:
            with _lock:
                _perfil["texto"] = texto
                _perfil["actualizado"] = ahora
                _perfil["n_episodios"] = n
            print("[perfil] perfil de Marco actualizado.")
    except Exception as e:
        print(f"[perfil] no pude actualizar el perfil: {e}")
    _guardar()


def iniciar_perfil():
    # Arranca el aprendizaje del perfil en segundo plano (auto-regulado).
    def _bucle():
        time.sleep(180)            # deja pasar el arranque
        while True:
            try:
                actualizar_perfil()
            except Exception:
                pass
            time.sleep(CHEQUEO)

    threading.Thread(target=_bucle, daemon=True).start()
