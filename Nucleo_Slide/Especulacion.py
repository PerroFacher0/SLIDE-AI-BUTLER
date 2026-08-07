# EMPEZAR ANTES DE QUE HAGA FALTA.
#
# Un turno de AIDEN es en serie: se le manda el prompt al modelo, se espera su respuesta, se
# ejecutan las herramientas que pidió, se le devuelve el resultado, se espera otra vez. Mientras el
# modelo piensa —que es lo más lento de todo— la PC no hace nada, aunque muchas veces ya se puede
# adivinar qué va a pedir.
#
# Esto arranca esas herramientas ANTES, en paralelo con la llamada al modelo. Si acierta, el
# resultado ya está esperando y ese paso sale gratis. Si falla, se tira y no ha pasado nada.
#
# ── LA REGLA QUE MANDA SOBRE TODO LO DEMÁS ───────────────────────────────────
# Una herramienta especulada que NO se usa tiene que ser indistinguible de que nunca corrió. Cero
# efectos, cero rastro, cero mención. Por eso aquí solo entran LECTURAS PURAS.
#
# ── POR QUÉ NO SE REUSA _TOOLS_PARALELAS ─────────────────────────────────────
# Era la candidata obvia: ya existe y ya dice "estas se pueden correr a la vez". Pero paralelizable
# NO es lo mismo que sin efectos, y comprobarlo una por una lo dejó claro: `notas` está en esa
# lista y con accion='guardar' ESCRIBE una nota. Especularla habría creado notas que Marco nunca
# pidió. Reusar esa lista por parecerse habría sido el mismo error de siempre, con otro disfraz.
#
# Así que la lista de aquí es explícita, corta y verificada función por función. Y para que no se
# quede desactualizada al añadir herramientas, `Pruebas/` comprueba con AST que ninguna de estas
# escriba archivos, toque la red de escritura ni llame a nada de la lista de riesgo.

import threading
import time

TTL = 25.0          # s que vive un resultado especulado; pasado eso, el mundo pudo cambiar

# LECTURAS PURAS. Cada una comprobada a mano: consultan y devuelven texto, no escriben nada.
# Deliberadamente NO están:
#   notas   -> escribe si le llega accion='guardar'
#   buscar  -> es lectura, pero gasta cuota de API en una CORAZONADA; especular no puede costar
#              dinero real de Marco por adivinar
SEGURAS = frozenset({
    "leer_portapapeles",
    "clima",
    "estado_sistema",
    "ver_apps_abiertas",
    "acciones",
    "mis_gastos",
    "noticias_del_dia",
    "resumen_actividad",
    "calculadora",
    "convertir_moneda",
    # OJO con esta: hay DOS funciones llamadas `recordar` en el proyecto. Memoria.recordar ESCRIBE
    # en la memoria permanente; Memoria_RAG.recordar BUSCA en las conversaciones. La herramienta
    # es la segunda (la de escribir se expone como `memoria`), comprobado en tools_map. Se deja
    # dicho porque el nombre invita a equivocarse justo del lado peligroso.
    "recordar",
})

# Lo que Marco dice -> lo que seguramente hará falta. Se mira SU FRASE, que es la única señal de
# verdad que hay antes de que el modelo decida nada.
_PISTAS = (
    (("portapapeles", "copie", "copié", "copiado", "esto que copi"), "leer_portapapeles", {}),
    (("clima", "tiempo hace", "va a llover", "temperatura", "pronostico", "pronóstico"), "clima", {}),
    (("cuanta bateria", "cuánta batería", "cuanta ram", "cuánta ram", "espacio en disco",
      "como esta el pc", "cómo está el pc", "temperatura del pc"), "estado_sistema", {}),
    (("que tengo abierto", "qué tengo abierto", "que apps", "qué apps",
      "que programas", "qué programas"), "ver_apps_abiertas", {}),
    (("mis acciones", "la bolsa", "portafolio", "como van mis", "cómo van mis"), "acciones", {}),
    (("cuanto he gastado", "cuánto he gastado", "mis gastos", "en que gaste", "en qué gasté"),
     "mis_gastos", {}),
    (("noticias", "que paso en el mundo", "qué pasó en el mundo"), "noticias_del_dia", {}),
)

# Entre rondas: después de esta herramienta, es probable que venga esta otra. Corta a propósito.
DESPUES_DE = {
    "buscar": ("recordar", None),          # se busca algo y se comprueba si ya se había hablado de ello
}

_lock = threading.RLock()
_pendientes = {}        # clave -> {"hilo", "resultado", "en", "usado"}
_stats = {"lanzadas": 0, "aciertos": 0, "fallos": 0}


def _clave(nombre, args):
    """Misma herramienta y mismos argumentos = mismo resultado. Los argumentos se normalizan
    (orden, espacios, mayúsculas) para que 'NVDA' y ' nvda ' no cuenten como cosas distintas."""
    if isinstance(args, str):
        try:
            import json
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    partes = sorted(f"{k}={str(v).strip().lower()}" for k, v in args.items() if v not in (None, ""))
    return f"{nombre}|{','.join(partes)}"


def es_segura(nombre):
    """La comprobación es doble a propósito: la lista de aquí, Y que no esté en la lista de riesgo
    de la verificación de voz. Si algún día alguien mueve una herramienta de sitio, tiene que
    fallar por los dos lados a la vez para colarse."""
    if nombre not in SEGURAS:
        return False
    try:
        from Nucleo_Slide.Verificacion_Voz import TOOLS_DE_RIESGO
        if nombre in TOOLS_DE_RIESGO:
            return False
    except Exception:
        pass
    return True


def lanzar(nombre, args=None):
    """Arranca una herramienta a cuenta y riesgo. Devuelve True si de verdad se lanzó."""
    if not es_segura(nombre):
        return False
    args = args or {}
    clave = _clave(nombre, args)
    with _lock:
        vivo = _pendientes.get(clave)
        if vivo and (time.time() - vivo["en"]) < TTL:
            return False                    # ya está en marcha o ya está lista
        _pendientes[clave] = {"hilo": None, "resultado": None, "en": time.time(), "usado": False}
        _stats["lanzadas"] += 1

    def _correr():
        r = None
        try:
            from Nucleo_Slide.configuracion_del_agente import tools_map
            fn = tools_map.get(nombre)
            if fn is not None:
                r = str(fn(**args))
        except Exception:
            r = None                        # una especulación que falla NO es un error de nadie
        with _lock:
            if clave in _pendientes:
                _pendientes[clave]["resultado"] = r

    h = threading.Thread(target=_correr, daemon=True, name=f"espec_{nombre}")
    with _lock:
        _pendientes[clave]["hilo"] = h
    h.start()
    return True


def cobrar(nombre, args=None, espera=0.0):
    """¿Había una especulación para esto? Devuelve el resultado o None.

    `espera` permite darle un momento a una que aún está corriendo: si el modelo pidió justo lo que
    se estaba adelantando, esperar 200 ms a que termine sigue siendo mejor que empezarla de cero."""
    clave = _clave(nombre, args)
    with _lock:
        p = _pendientes.get(clave)
        if not p or p["usado"] or (time.time() - p["en"]) > TTL:
            return None
    h = p.get("hilo")
    if h is not None and h.is_alive() and espera > 0:
        h.join(timeout=espera)
    with _lock:
        p = _pendientes.get(clave)
        if not p or p["usado"] or p["resultado"] is None:
            return None
        p["usado"] = True
        _stats["aciertos"] += 1
        return p["resultado"]


def olvidar():
    """Fin del turno: lo especulado y no cobrado se tira. No se registra, no se cuenta, no se
    menciona — para el resto de AIDEN es como si nunca hubiera existido."""
    with _lock:
        sin_usar = sum(1 for p in _pendientes.values() if not p["usado"])
        _stats["fallos"] += sin_usar
        _pendientes.clear()
    return sin_usar


def desde_lo_que_dijo(frase):
    """Lo que se puede adelantar sabiendo solo las palabras de Marco. Devuelve lo lanzado."""
    t = str(frase or "").lower()
    lanzadas = []
    for pistas, tool, args in _PISTAS:
        if any(p in t for p in pistas):
            if lanzar(tool, args):
                lanzadas.append(tool)
            break                           # una sola corazonada por turno: no es una escopeta
    return lanzadas


def desde_la_ronda_anterior(nombres_usados, texto_usuario=""):
    """Lo que se puede adelantar sabiendo qué herramientas acaban de correr."""
    lanzadas = []
    for n in nombres_usados:
        siguiente = DESPUES_DE.get(n)
        if not siguiente:
            continue
        tool, args = siguiente
        if args is None:
            args = {"consulta": str(texto_usuario or "")[:120]} if tool == "recordar" else {}
        if lanzar(tool, args):
            lanzadas.append(tool)
    return lanzadas


def estadisticas():
    with _lock:
        d = dict(_stats)
    total = d["aciertos"] + d["fallos"]
    d["tasa"] = (d["aciertos"] / total) if total else 0.0
    return d
