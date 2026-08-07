# NÚCLEO DE CONCIENCIA COMPARTIDA (estado del mundo).
#
# El salto hacia "Jarvis": una SOLA mente que TODAS las partes de AIDEN (cerebro de voz, cerebro
# remoto, conciencia ambiental, vigilantes, presencia) LEEN y ESCRIBEN. Convierte a AIDEN de varios
# scripts reactivos sueltos en un agente con CONTINUIDAD: sabe qué pasa AHORA, qué pasó hace un rato,
# en qué anda Marco, su estado, y qué METAS persigue. Es la base de la proactividad con propósito.
#
# Es un módulo HOJA: solo usa la stdlib, así CUALQUIER parte lo importa sin riesgo de import circular.
# Persiste en estado_del_mundo.json (GITIGNORED, privado). Thread-safe (RLock).

import json
import os
import threading
import time
from datetime import datetime

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estado_del_mundo.json"
)
_lock = threading.RLock()
MAX_EVENTOS = 40          # cuántos eventos recientes se conservan en el hilo de conciencia

_estado = {
    "foco_actual": "",        # app/ventana donde está Marco
    "marco_presente": True,   # ¿está frente al PC?
    "en_reunion": False,
    "modo": "normal",         # normal | gaming | manos_libres | ...
    "ultima_interaccion": 0,  # timestamp del último intercambio (voz/texto)
    "eventos": [],            # hilo de conciencia: [{t, hora, texto, origen}]
    "metas": [],              # objetivos que AIDEN persigue (Parte 2): [{texto, creada, estado}]
}


def _cargar():
    global _estado
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                guardado = json.load(f)
            if isinstance(guardado, dict):
                _estado.update(guardado)
    except Exception:
        pass


def _guardar():
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(_estado, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


_cargar()


# ── Escritura (cualquier parte de AIDEN) ──────────────────────────────────────
def actualizar(**campos):
    # Actualiza campos del estado: actualizar(foco_actual="Word", en_reunion=True, ...)
    with _lock:
        _estado.update(campos)
        _guardar()


# ── ¿ESTO LO PIDIÓ MARCO, O LO DECIDIÓ AIDEN? ────────────────────────────────
#
# `origen` dice de QUÉ MÓDULO salió el evento, no por qué. Y no sirve para separar las dos cosas:
# "control_total" aparece igual cuando Marco dice "cierra Chrome" que cuando la conciencia ambiental
# decide ejecutar algo sola — es literalmente la misma línea de código. Lo mismo con "protocolos",
# "navegador_web" o "redactor".
#
# La tentación es etiquetar los ~35 sitios que registran eventos. Sería la segunda lista del mismo
# concepto, y este proyecto ya sabe cómo acaba eso (_PROHIBIDAS).
#
# Lo que sí es un solo sitio: el TURNO de Marco. O AIDEN está atendiendo algo que él pidió, o no lo
# está. Se marca ese turno en un hilo-local y todo lo que se registre dentro hereda la respuesta,
# por hondo que esté. Fuera del turno —los hilos de fondo, sin excepción— es decisión propia.
#
# El defecto es "por mi cuenta" A PROPÓSITO: si mañana aparece un vigía nuevo y nadie se acuerda de
# marcarlo, sus eventos salen en la bitácora de autonomía. Equivocarse hacia "te lo cuento" es el
# lado correcto en el que fallar cuando lo que está en juego es la confianza.
_hilo = threading.local()


def atendiendo_a_marco():
    return bool(getattr(_hilo, "atendiendo", False))


def fijar_atendiendo(valor):
    """Devuelve el valor anterior, para poder restaurarlo (turnos anidados)."""
    previo = atendiendo_a_marco()
    _hilo.atendiendo = bool(valor)
    return previo


class turno_de_marco:
    """with turno_de_marco(): ...  — todo lo de dentro es «Marco lo pidió»."""

    def __enter__(self):
        self._previo = fijar_atendiendo(True)
        return self

    def __exit__(self, *exc):
        fijar_atendiendo(self._previo)
        return False


def registrar_evento(texto, origen="sistema"):
    # Añade al HILO de conciencia lo que acaba de pasar (lo ve toda la mente).
    texto = str(texto or "").strip()
    if not texto:
        return
    solo = not atendiendo_a_marco()
    with _lock:
        ev = _estado.get("eventos", [])
        if ev and ev[-1].get("texto") == texto:   # dedup consecutivo
            return
        ev.append({
            "t": time.time(), "hora": datetime.now().strftime("%H:%M"),
            "texto": texto[:200], "origen": origen, "solo": solo,
        })
        _estado["eventos"] = ev[-MAX_EVENTOS:]
        _guardar()


def eventos_autonomos(horas=16, maximo=12):
    """Lo que AIDEN hizo POR SU CUENTA. Los eventos de antes de este cambio no traen la marca:
    se omiten en vez de adivinarles una, que sería inventarse historia."""
    corte = time.time() - max(1, float(horas)) * 3600
    fuera = []
    with _lock:
        for e in _estado.get("eventos", []):
            if e.get("solo") is True and e.get("t", 0) >= corte:
                fuera.append(e)
    return fuera[-maximo:]


def marcar_interaccion():
    with _lock:
        _estado["ultima_interaccion"] = time.time()
        _guardar()


# ── Metas (base de la Parte 2: perseguir objetivos en el tiempo) ──────────────
def agregar_meta(texto):
    with _lock:
        _estado.setdefault("metas", []).append(
            {"texto": str(texto or "")[:200], "creada": time.time(), "estado": "abierta"}
        )
        _guardar()


def cerrar_meta(subcadena):
    sub = str(subcadena or "").lower()
    with _lock:
        for m in _estado.get("metas", []):
            if sub and sub in m.get("texto", "").lower():
                m["estado"] = "hecha"
        _guardar()


def metas_activas():
    with _lock:
        return [m for m in _estado.get("metas", []) if m.get("estado") != "hecha"]


def anotar_avance(subcadena, nota=""):
    # Registra un avance en la meta que coincida. Devuelve el texto de la meta o "".
    sub = str(subcadena or "").lower()
    with _lock:
        for m in _estado.get("metas", []):
            if m.get("estado") != "hecha" and sub and sub in m.get("texto", "").lower():
                m.setdefault("avances", []).append({"t": time.time(), "nota": str(nota or "")[:200]})
                m["avances"] = m["avances"][-10:]
                m["ultimo_seguimiento"] = time.time()
                _guardar()
                return m.get("texto", "")
        return ""


def meta_para_seguimiento(min_horas=22):
    # La meta activa MÁS olvidada (cuyo último seguimiento supere min_horas). None si ninguna toca.
    ahora = time.time()
    with _lock:
        cands = [m for m in _estado.get("metas", [])
                 if m.get("estado") != "hecha"
                 and ahora - m.get("ultimo_seguimiento", m.get("creada", 0)) >= min_horas * 3600]
        if not cands:
            return None
        cands.sort(key=lambda m: m.get("ultimo_seguimiento", m.get("creada", 0)))
        return json.loads(json.dumps(cands[0]))


def marcar_seguimiento(subcadena):
    sub = str(subcadena or "").lower()
    with _lock:
        for m in _estado.get("metas", []):
            if sub and sub in m.get("texto", "").lower():
                m["ultimo_seguimiento"] = time.time()
        _guardar()


# ── Lectura ───────────────────────────────────────────────────────────────────
def obtener():
    with _lock:
        return json.loads(json.dumps(_estado))   # copia profunda barata


def resumen_texto(n_eventos=8):
    # Texto compacto del estado + últimos eventos, para inyectar en prompts (toda la mente lo ve).
    with _lock:
        lineas = []
        if _estado.get("foco_actual"):
            lineas.append(f"Foco actual de Marco: {_estado['foco_actual']}")
        est = []
        if not _estado.get("marco_presente", True):
            est.append("ausente del PC")
        if _estado.get("en_reunion"):
            est.append("en una reunión")
        if _estado.get("modo") and _estado["modo"] != "normal":
            est.append(f"modo {_estado['modo']}")
        if est:
            lineas.append("Estado: " + ", ".join(est))
        metas = [m for m in _estado.get("metas", []) if m.get("estado") != "hecha"]
        if metas:
            lineas.append("Metas activas: " + " | ".join(m.get("texto", "") for m in metas[:5]))
        evs = _estado.get("eventos", [])[-n_eventos:]
        if evs:
            lineas.append("Lo que ha pasado recientemente:")
            for e in evs:
                lineas.append(f"  [{e.get('hora', '')}] {e.get('texto', '')}")
        return "\n".join(lineas).strip()
