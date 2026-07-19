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
