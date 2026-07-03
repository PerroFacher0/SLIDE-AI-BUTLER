# COMPAÑÍA: la re-entrada RELACIONAL de AIDEN. Un compañero no te saluda en frío — RETOMA el hilo de
# lo que estaban haciendo. Aquí viven los momentos en que AIDEN "vuelve a ti":
#   - saludo_de_reanudacion(): al arrancar, un saludo cálido que continúa vuestra historia
#     (última conversación + metas activas + cuánto tiempo pasó). [Idea #2]
#   - lo_que_retuve(desde_ts): al VOLVER al PC, UNA cosa notable que pasó mientras no estabas
#     (llamada, error, algo que la conciencia/Vocero calló). Se siente como "estuve pendiente". [Idea #3]
#   - despedida_del_dia(): al irte a dormir, un cierre cálido que reconoce tu día. Contraparte de la
#     reanudación; cierra el arco apertura<->cierre. [Idea #5]
#
# Imports PEREZOSOS del LLM/estado para no crear ciclos. Fallbacks robustos: si algo falla, saluda
# normal — JAMÁS rompe el arranque de AIDEN.

import time

from Nucleo_Slide.Memoria_Episodica import _cargar as _cargar_episodios

_FALLBACK = "Bienvenido de vuelta, señor. ¿En qué andamos hoy?"


def _gap_humano(ts):
    # Traduce el tiempo desde la última interacción a algo natural.
    if not ts:
        return ""
    seg = time.time() - ts
    if seg < 2 * 3600:
        return "hace un rato"
    if seg < 8 * 3600:
        return "hace unas horas"
    if seg < 40 * 3600:
        return "desde ayer"
    return f"hace {int(seg // 86400)} días"


def saludo_de_reanudacion():
    """Un saludo de bienvenida que RETOMA el hilo (última charla + metas + tiempo). Nunca crashea."""
    try:
        eps = _cargar_episodios() or []
        from Nucleo_Slide.Estado_Del_Mundo import metas_activas, obtener
        metas = [m.get("texto", "") for m in metas_activas()][:2]
        ult = (obtener() or {}).get("ultima_interaccion", 0)

        if not eps and not metas:
            return _FALLBACK   # primera vez / sin historia: saludo simple

        ultimos = eps[-2:]
        contexto = "\n".join(
            f'Marco: "{e.get("usuario","")[:100]}" -> tú: "{e.get("aiden","")[:80]}"'
            for e in ultimos
        )
        gap = _gap_humano(ult)

        from Nucleo_Slide.Cerebro import client, MODELO
        prompt = (
            "Eres AIDEN saludando a Marco (trátalo de 'señor') cuando vuelve, como un compañero "
            "cercano que RETOMA EL HILO, no como un saludo en frío.\n"
            + (f"Última vez que hablaron: {gap}.\n" if gap else "")
            + (f"Lo último que hicieron:\n{contexto}\n" if contexto else "")
            + (f"Metas activas de Marco: {'; '.join(metas)}.\n" if metas else "")
            + "Dale UN saludo cálido y BREVE (1-2 frases) que retome lo de antes con naturalidad e "
            "invite a seguir. Como un amigo que continúa la conversación; NO listes datos, NO suenes "
            "a robot, NO seas meloso de más."
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=120,
        )
        t = (r.choices[0].message.content or "").strip()
        return t or _FALLBACK
    except Exception:
        return _FALLBACK


# Orígenes "notables" para traer al volver, en orden de prioridad.
def _prioridad(ev):
    origen = ev.get("origen", "")
    texto = (ev.get("texto", "") or "").lower()
    if origen == "llamadas":
        return 0                       # alguien te llamó: lo más importante
    if origen == "pantalla":
        return 1                       # una app se rompió / un error
    if "callado para no molestar" in texto:
        return 2                       # algo que AIDEN pensó pero calló por respeto
    if origen == "conciencia":
        return 2
    if origen == "reunion":
        return 3
    return 9                           # el resto (voz, presencia, modos...) NO se trae


def lo_que_retuve(desde_ts=0):
    """UNA cosa notable que pasó desde 'desde_ts' (mientras Marco no estaba), o "" si nada amerita.
    Se siente como 'estuve pendiente mientras no estabas'."""
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        evs = (obtener() or {}).get("eventos", []) or []
    except Exception:
        return ""
    candidatos = [e for e in evs if e.get("t", 0) >= desde_ts and _prioridad(e) < 9]
    if not candidatos:
        return ""
    candidatos.sort(key=lambda e: (_prioridad(e), -e.get("t", 0)))   # más importante y más reciente
    txt = candidatos[0].get("texto", "").replace("(callado para no molestar) ", "").strip()
    if not txt:
        return ""
    return "Por cierto, señor, mientras no estaba: " + txt


def apertura_rica():
    """El MOMENTO de bienvenida: al abrir AIDEN, UN saludo que canaliza TODO el núcleo de golpe —
    retoma el hilo (memoria) + lo notable que pasó mientras no estabas + tu momento (reflexión) +
    un enganche con tu meta. Para que el valor se SIENTA al abrir la app, sin pedir nada. Nunca crashea."""
    try:
        eps = _cargar_episodios() or []
        from Nucleo_Slide.Estado_Del_Mundo import metas_activas, obtener
        est = obtener() or {}
        metas = [m.get("texto", "") for m in metas_activas()][:2]
        ult = est.get("ultima_interaccion", 0)
        if not eps and not metas:
            return _FALLBACK

        ultimos = eps[-2:]
        contexto = "\n".join(
            f'Marco: "{e.get("usuario","")[:90]}" -> tú: "{e.get("aiden","")[:60]}"' for e in ultimos
        )
        # Notable que pasó mientras no estabas (del hilo de conciencia, desde la última interacción).
        notables = []
        for e in (est.get("eventos") or [])[-6:]:
            o = e.get("origen", "")
            if o in ("llamadas", "pantalla") or "callado para no molestar" in (e.get("texto", "").lower()):
                notables.append(e.get("texto", "").replace("(callado para no molestar) ", ""))
        pendiente = notables[-1] if notables else ""
        try:
            from Nucleo_Slide.Reflexion import reflexion_texto
            refl = (reflexion_texto() or "")[:220]
        except Exception:
            refl = ""
        gap = _gap_humano(ult)

        from Nucleo_Slide.Cerebro import client, MODELO
        prompt = (
            "Eres AIDEN recibiendo a Marco (trátalo de 'señor') cuando abre la app, como Jarvis "
            "recibiendo a Tony al taller: cálido, con chispa, que demuestra que lo CONOCE y estuvo "
            "PENDIENTE. Con este contexto, dale UN saludo natural de 2-4 frases que: retome el hilo de "
            "lo último, mencione lo notable que pasó mientras no estaba (si lo hay), muestre que "
            "entiende su momento, y lo enganche con su meta o le pregunte por dónde seguir. NO listes "
            "datos, NO suenes a robot, que fluya como un amigo.\n"
            + (f"Última vez que hablaron: {gap}.\n" if gap else "")
            + (f"Lo último que hicieron:\n{contexto}\n" if contexto else "")
            + (f"Mientras no estaba pasó: {pendiente}\n" if pendiente else "")
            + (f"Metas activas: {'; '.join(metas)}\n" if metas else "")
            + (f"Tu lectura de su momento: {refl}\n" if refl else "")
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=200,
        )
        return (r.choices[0].message.content or "").strip() or _FALLBACK
    except Exception:
        return _FALLBACK


def despedida_del_dia():
    """Cierre cálido del día (contraparte de la reanudación): reconoce lo de hoy y desea descanso."""
    _simple = "Buenas noches, señor. Que descanse; mañana seguimos."
    try:
        from datetime import datetime
        hoy = datetime.now().strftime("%d/%m/%Y")
        eps = _cargar_episodios() or []
        de_hoy = [e for e in eps if e.get("fecha", "") == hoy]
        from Nucleo_Slide.Estado_Del_Mundo import metas_activas
        metas = [m.get("texto", "") for m in metas_activas()][:2]
        if not de_hoy and not metas:
            return "Buenas noches, señor. Que descanse."
        resumen = "; ".join(e.get("usuario", "")[:60] for e in de_hoy[-4:]) or "un día tranquilo"

        from Nucleo_Slide.Cerebro import client, MODELO
        prompt = (
            "Eres AIDEN despidiendo a Marco (trátalo de 'señor') que se va a dormir, como un compañero "
            "cercano. Hoy, en resumen, hablaron/trabajaron en: " + resumen + ". "
            + (f"Sus metas activas: {'; '.join(metas)}. " if metas else "")
            + "Despídete cálido y BREVE (1-2 frases): reconoce algo concreto de su día y deséale buenas "
            "noches o descanso. Natural, sin listar, sin sonar a robot ni meloso de más."
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=100,
        )
        return (r.choices[0].message.content or "").strip() or _simple
    except Exception:
        return _simple
