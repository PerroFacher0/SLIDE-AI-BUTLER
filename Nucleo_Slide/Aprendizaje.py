# APRENDIZAJE DE CORRECCIONES: AIDEN se vuelve más TUYO con el uso. Cuando Marco lo corrige o expresa
# una preferencia ("no, prefiero X", "deja de hacer Y", "la próxima hazlo así"), AIDEN EXTRAE una regla
# duradera y la respeta PARA SIEMPRE (se inyecta en su prompt). Es adaptación real — la dimensión más
# débil de una IA que solo "resume lo que vio".
#
# Diseño para NO abrumar: es PASIVO (no corre ningún loop de fondo). Solo se activa tras un turno donde
# Marco parece corregir (heurística barata), y la extracción con LLM va en un HILO aparte -> cero
# latencia para Marco. Casi-hoja: stdlib + imports perezosos del LLM.

import json
import os
import threading

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "preferencias.json"
)
_lock = threading.RLock()
_MAX = 30   # tope de preferencias que recuerda

_TILDES = str.maketrans("áéíóúü", "aeiouu")


def _norm(t):
    return str(t or "").translate(_TILDES).lower()


# Señales de que Marco está CORRIGIENDO o fijando una preferencia (no una orden puntual).
_SENALES = (
    "prefiero", "no me gusta", "no me gustan", "no quiero que", "la proxima", "de ahora en adelante",
    "te dije que", "ya te dije", "deja de", "no hagas", "no vuelvas a", "en vez de", "mejor ",
    "me molesta", "odio cuando", "no digas", "no uses", "hazlo asi", "quiero que siempre",
    "siempre que", "recuerda que prefiero", "no tan", "mas corto", "menos ", "no seas tan",
)


def _es_posible_correccion(consulta):
    c = _norm(consulta)
    if len(c) < 4:
        return False
    return any(s in c for s in _SENALES)


def _cargar():
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        pass
    return []


def _guardar(datos):
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(datos[-_MAX:], f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def preferencias_texto():
    # Lo aprendido de Marco, para inyectar en el prompt.
    prefs = _cargar()
    if not prefs:
        return ""
    return ("PREFERENCIAS QUE MARCO TE HA ENSEÑADO CORRIGIÉNDOTE (respétalas SIEMPRE, sin que te las "
            "recuerde):\n" + "\n".join(f"- {p}" for p in prefs))


def _extraer_y_guardar(consulta):
    try:
        from Nucleo_Slide.Cerebro import client, MODELO
        prompt = (
            "Marco (tu usuario) acaba de decirte esto, que parece una CORRECCIÓN o PREFERENCIA sobre "
            "cómo debes comportarte. Extrae UNA regla/preferencia DURADERA y GENERAL que debas recordar "
            "siempre, redactada en imperativo corto (ej. 'Da respuestas más cortas', 'No uses emojis', "
            "'Trátalo de tú, no de señor'). Si es solo una orden PUNTUAL (no una preferencia general), "
            "responde EXACTAMENTE: NADA.\n\nLO QUE DIJO MARCO: " + str(consulta)
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=60,
        )
        regla = (r.choices[0].message.content or "").strip().strip('"').strip()
        if not regla or regla.upper().startswith("NADA") or len(regla) < 4:
            return
        with _lock:
            prefs = _cargar()
            rn = _norm(regla)
            # dedup: no repetir una preferencia muy parecida
            if any(rn in _norm(p) or _norm(p) in rn for p in prefs):
                # si ya existe una parecida, reemplázala por la nueva (más fresca)
                prefs = [p for p in prefs if not (rn in _norm(p) or _norm(p) in rn)]
            prefs.append(regla)
            _guardar(prefs)
        print(f"[aprendizaje] nueva preferencia aprendida: {regla}")
    except Exception as e:
        print(f"[aprendizaje] no pude extraer preferencia: {e}")


def aprender_de(consulta):
    """Tras un turno, si Marco pareció corregir, aprende su preferencia EN SEGUNDO PLANO (cero latencia).
    Llamar como registrar_episodio, sin bloquear la respuesta."""
    try:
        if _es_posible_correccion(consulta):
            threading.Thread(target=_extraer_y_guardar, args=(str(consulta),), daemon=True).start()
    except Exception:
        pass
