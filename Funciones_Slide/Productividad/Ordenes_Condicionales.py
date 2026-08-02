# ÓRDENES CONDICIONALES: el "Remind me to..." de Jarvis, pero con disparadores.
#
# "En 20 minutos dime que saque la pizza" / "cuando abra Chrome recuérdame revisar el correo" /
# "a las 9 recuérdame llamar a mamá". AIDEN guarda el recado y VIGILA la condición; cuando se
# cumple, te lo dice (prioridad alta: un recado pedido no se silencia). Persisten en ordenes.json:
# sobreviven reinicios.
#
# Disparadores: 'tiempo' (minutos u hora HH:MM) y 'app' (cuando esa app pase a estar en foco,
# leído del Estado_Del_Mundo que ya mantienen los vigilantes). Chequeo barato cada 10s, sin LLM.

import json
import os
import threading
import time
from datetime import datetime

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ordenes.json"
)
_lock = threading.RLock()
_hablar = None
_MAX = 15

_TILDES = str.maketrans("áéíóúüñ", "aeiouun")


def _norm(t):
    return str(t or "").strip().lower().translate(_TILDES)


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


def programar_orden(tipo="", valor="", recado="", accion="crear"):
    """HERRAMIENTA: recados condicionales de Marco.
    tipo 'tiempo' (valor: minutos como '20' u hora como '21:30') o 'app' (valor: nombre de la app).
    accion: crear | listar | cancelar (cancelar: recado = subcadena del recado a borrar)."""
    a = _norm(accion) or "crear"

    if a in ("listar", "lista", "ver"):
        datos = [o for o in _cargar() if not o.get("hecha")]
        if not datos:
            return "No tengo recados pendientes, señor."
        lineas = []
        for o in datos:
            if o.get("tipo") == "tiempo":
                cuando = datetime.fromtimestamp(o.get("cuando", 0)).strftime("%H:%M")
                lineas.append(f"a las {cuando}: {o.get('recado', '')}")
            else:
                lineas.append(f"cuando abra {o.get('valor', '')}: {o.get('recado', '')}")
        return "Recados pendientes, señor: " + "; ".join(lineas) + "."

    if a in ("cancelar", "borrar", "eliminar", "quitar"):
        sub = _norm(recado or valor)
        if not sub:
            return "¿Cuál recado cancelo, señor?"
        with _lock:
            datos = _cargar()
            antes = len(datos)
            datos = [o for o in datos if sub not in _norm(o.get("recado", ""))]
            _guardar(datos)
        return ("Recado cancelado, señor." if len(datos) < antes
                else f"No encontré un recado que diga '{recado or valor}', señor.")

    # crear
    recado = str(recado or "").strip()
    if not recado:
        return "Dígame el recado, señor (qué debo recordarle)."
    t = _norm(tipo)
    orden = {"recado": recado[:200], "hecha": False, "creada": time.time()}
    if t == "app":
        app = _norm(valor)
        if not app:
            return "¿Con cuál aplicación disparo el recado, señor?"
        orden.update(tipo="app", valor=app)
        detalle = f"cuando abra {valor}"
    else:
        v = str(valor or "").strip()
        try:
            if ":" in v:   # hora "HH:MM" (si ya pasó hoy, será mañana)
                hh, mm = v.split(":")[:2]
                ahora = datetime.now()
                objetivo = ahora.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                cuando = objetivo.timestamp()
                if cuando <= time.time():
                    cuando += 24 * 3600
            else:          # minutos desde ahora
                cuando = time.time() + max(1, int(float(v))) * 60
        except (ValueError, TypeError):
            return f"No entendí el tiempo '{valor}', señor: dígame minutos (ej. 20) u hora (ej. 21:30)."
        orden.update(tipo="tiempo", cuando=cuando)
        detalle = f"a las {datetime.fromtimestamp(cuando).strftime('%H:%M')}"
    with _lock:
        datos = _cargar()
        datos.append(orden)
        _guardar(datos)
    return f"Anotado, señor: {detalle} le recuerdo '{recado}'. Cuente con ello."


def _revisar():
    ahora = time.time()
    foco = ""
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        foco = _norm(obtener().get("foco_actual", ""))
    except Exception:
        pass
    disparadas = []
    with _lock:
        datos = _cargar()
        for o in datos:
            if o.get("hecha"):
                continue
            if o.get("tipo") == "tiempo" and ahora >= o.get("cuando", 0):
                o["hecha"] = True
                disparadas.append(o)
            elif o.get("tipo") == "app" and o.get("valor") and o["valor"] in foco:
                o["hecha"] = True
                disparadas.append(o)
        if disparadas:
            _guardar(datos)
    for o in disparadas:
        try:
            from Nucleo_Slide.Vocero import emitir
            # prioridad alta: es un recado que MARCO pidió; no se silencia por presupuesto.
            emitir(_hablar, f"Señor, me pidió recordarle: {o.get('recado', '')}.",
                   origen="ordenes", prioridad="alta")
            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
            registrar_evento(f"Recado entregado: {o.get('recado', '')}", "ordenes")
        except Exception:
            pass


def iniciar_ordenes(hablar):
    # Vigila los recados pendientes (barato: comparaciones cada 10s, cero LLM).
    global _hablar
    _hablar = hablar

    def _bucle():
        while True:
            try:
                _revisar()
            except Exception:
                pass
            time.sleep(10)

    threading.Thread(target=_bucle, daemon=True).start()


# ── HERRAMIENTA ÚNICA: todo lo que pasa DESPUÉS ──────────────────────────────
# Antes esto estaba partido en dos que se pisaban: 'programar_orden' (recados con disparador) y
# 'guardar_en_json' (tareas con hora). "En 20 minutos recuérdame X" encajaba en LAS DOS, y el modelo
# tenía que adivinar. Lo que de verdad varía no es cuándo, sino QUÉ ocurre al cumplirse: si AIDEN
# solo tiene que DECIR algo, o si tiene que HACER algo (mandar un WhatsApp, llamar). Eso es el
# parámetro 'hacer'; el disparador es el mismo para ambos casos.

def _es_hora(v):
    import re
    # \d{1,2} en los MINUTOS a propósito: el modelo puede escribir "9:5" para las nueve y cinco.
    # Ser estricto aquí hacía que esa hora se rechazara como si no fuera una hora en absoluto.
    return bool(re.fullmatch(r"\d{1,2}:\d{1,2}", str(v or "").strip()))


def _a_hora_absoluta(cuando):
    """'20' (minutos desde ahora) -> 'HH:MM'. Si ya es una hora, la deja igual."""
    from datetime import datetime, timedelta
    v = str(cuando or "").strip()
    if _es_hora(v):
        h, m = v.split(":")
        return f"{int(h):02d}:{int(m):02d}"
    if v.isdigit():
        return (datetime.now() + timedelta(minutes=int(v))).strftime("%H:%M")
    return None


def programar(cuando="", recado="", hacer="recordar", contacto="", accion="crear"):
    """HERRAMIENTA: deja algo listo para MÁS TARDE.
      cuando   = minutos ('20'), una hora ('21:30'), o el nombre de una app ('chrome' = cuando la abra)
      recado   = qué decir (recordatorio) o qué mandar (si es un WhatsApp)
      hacer    = 'recordar' (por defecto, AIDEN lo dice) | 'whatsapp' | 'llamar' | 'colgar'
      contacto = a quién, solo para whatsapp/llamar
      accion   = crear (por defecto) | listar | cancelar"""
    a = _norm(accion) or "crear"
    h = _norm(hacer) or "recordar"

    if a in ("listar", "cancelar"):
        return programar_orden(accion=a, recado=recado)

    cuando = str(cuando or "").strip()
    if not cuando:
        return "¿Para cuándo lo dejo, señor?"

    # Solo DECIR algo -> recado condicional (admite disparador por tiempo y por app).
    if h.startswith("record") or h.startswith("avis") or h.startswith("dec"):
        if not recado:
            return "¿Qué le recuerdo, señor?"
        tipo = "tiempo" if (cuando.isdigit() or _es_hora(cuando)) else "app"
        return programar_orden(tipo=tipo, valor=cuando, recado=recado, accion="crear")

    # HACER algo (mandar/llamar) -> tarea con hora absoluta.
    hora = _a_hora_absoluta(cuando)
    if hora is None:
        return ("Para mandar un mensaje o llamar necesito una hora o unos minutos, señor, "
                "no una app como disparador.")
    mapa = {"whatsapp": "WHATSAPP", "wpp": "WHATSAPP", "mensaje": "WHATSAPP",
            "llamar": "LLAMAR", "llamada": "LLAMAR", "colgar": "COLGAR"}
    clave = next((v for k, v in mapa.items() if h.startswith(k)), None)
    if clave is None:
        return f"No sé qué es «{hacer}», señor (puedo recordar, whatsapp, llamar o colgar)."
    if clave in ("WHATSAPP", "LLAMAR") and not contacto:
        return "¿A quién, señor?"

    from Funciones_Slide.Productividad.Gestion_datos import guardar_en_json
    guardar_en_json(clave, contacto, recado, hora)
    if clave == "WHATSAPP":
        return f"Listo, señor: a las {hora} le mando el mensaje a {contacto}."
    if clave == "LLAMAR":
        return f"Listo, señor: a las {hora} llamo a {contacto}."
    return f"Listo, señor: a las {hora} cuelgo."
