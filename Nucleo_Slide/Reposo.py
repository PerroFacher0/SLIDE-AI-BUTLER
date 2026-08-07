# MANTENIMIENTO CUANDO MARCO NO ESTÁ.
#
# Todo lo que corre de fondo en AIDEN va por reloj: cada 20 minutos, cada 25 segundos. Ninguno mira
# si Marco está delante. Eso está bien para lo que tiene que ocurrir sí o sí, y mal para el trabajo
# que conviene hacer pero no urge: acaba haciéndose justo cuando él está usando la PC, o no
# haciéndose nunca.
#
# Esto es el disparador que faltaba: no un reloj, sino la AUSENCIA de Marco.
#
# ── LO QUE HACE, Y POR QUÉ CADA COSA ─────────────────────────────────────────
# Nada inventado. Las tres tareas son mantenimiento que YA debería pasar y hoy no tiene momento:
#
#   1. PURGAR LA MEMORIA VISUAL. Memoria_Visual borra lo más viejo de 24 h en cada ronda... pero
#      solo mientras está ACTIVA, y nace apagada. Si Marco la enciende un rato y la apaga, lo que
#      grabó se queda en el disco para siempre. La purga existía; le faltaba correr también cuando
#      nadie está mirando.
#
#   2. REPROBAR LAS HABILIDADES AUTO-PROGRAMADAS. Su prueba de comportamiento (D19) se ejecutaba
#      una vez, el día que nacieron, y se tiraba. Una habilidad quedaba validada para siempre por
#      una comprobación de hace tres meses. Ahora la prueba se guarda y aquí se vuelve a correr.
#
#   3. BARRER LOS TEMPORALES PROPIOS. Los guiones de prueba del validador quedan en el temporal si
#      el proceso muere entre escribirlos y borrarlos. Nadie los limpia.
#
# ── LA REGLA QUE MANDA SOBRE TODAS ───────────────────────────────────────────
# En cuanto Marco toca el ratón, esto desaparece. No al final de la tarea en curso: en el siguiente
# punto de control. Un mantenimiento que le roba CPU justo cuando vuelve es peor que no hacerlo,
# porque lo que él nota es que su PC va lenta al sentarse.
#
# Por eso las tareas van de barata a cara, y ninguna deja nada a medias: la purga es un DELETE
# transaccional, el barrido borra archivo por archivo, y la reprueba corre en otro proceso.

import ctypes
import json
import os
import threading
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_HABILIDADES = os.path.join(_RAIZ, "habilidades_probadas.json")

INACTIVO_MIN = 15        # minutos sin tocar nada antes de considerar que la PC está libre
_SONDEO = 60             # cada cuánto se mira si Marco sigue fuera
_CADA = 6 * 3600         # y cada cuánto, como mucho, se repite la ronda de mantenimiento

_pausado = False
_lock = threading.RLock()
_ultima_ronda = 0.0


class _INFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]


def inactivo_seg():
    """Segundos desde el último movimiento de ratón o tecla. 0 si no se puede saber — y ese 0 es
    deliberado: si no hay forma de saber si Marco está, se asume que SÍ está y no se hace nada."""
    try:
        info = _INFO()
        info.cbSize = ctypes.sizeof(_INFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        return max(0.0, (ctypes.windll.kernel32.GetTickCount64() - info.dwTime) / 1000.0)
    except Exception:
        return 0.0


def pausar_reposo(pausar=True):
    global _pausado
    with _lock:
        _pausado = bool(pausar)
    return True


def _sigue_libre():
    """El punto de control. Se llama ANTES de cada tarea y dentro de las largas."""
    if _pausado:
        return False
    if inactivo_seg() < INACTIVO_MIN * 60:
        return False                       # volvió: se acabó
    try:
        from Nucleo_Slide import Cancelacion
        if Cancelacion.operacion_en_curso() is not None:
            return False                   # AIDEN está haciendo algo pedido; eso manda
    except Exception:
        pass
    return True


# ── 1) La purga que solo corría con la memoria visual encendida ──────────────
def purgar_memoria_visual():
    """Devuelve cuántas filas viejas se borraron."""
    try:
        from Nucleo_Slide import Memoria_Visual as MV
        if not os.path.exists(MV._BD):
            return 0
        import sqlite3
        limite = time.time() - MV.RETENCION_H * 3600
        con = sqlite3.connect(MV._BD, timeout=10)
        try:
            # Un solo DELETE con su commit: si se corta a la mitad, SQLite deshace la transacción
            # entera. No hay estado intermedio que pueda quedar corrupto.
            cur = con.execute("DELETE FROM pantallazos WHERE CAST(t AS REAL) < ?", (limite,))
            con.commit()
            return cur.rowcount or 0
        finally:
            con.close()
    except Exception:
        return 0


# ── 2) Las habilidades, reprobadas con la prueba que ahora sí se guarda ──────
def _leer_habilidades():
    try:
        with open(RUTA_HABILIDADES, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def registrar_habilidad(nombre, instruccion, prueba):
    """Lo llama Auto_Modificacion al activar una habilidad nueva."""
    if not nombre or not str(prueba or "").strip():
        return False                      # sin prueba no hay nada que reprobar después
    with _lock:
        d = _leer_habilidades()
        d[str(nombre)] = {"instruccion": str(instruccion or ""), "prueba": str(prueba),
                          "creada": time.time()}
        try:
            with open(RUTA_HABILIDADES, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
        except Exception:
            return False
    return True


def reprobar_habilidades(comprobar=None):
    """Vuelve a correr la prueba de cada habilidad. Devuelve [(nombre, motivo)] de las que fallan.

    `comprobar` es el punto de control: se consulta ENTRE habilidad y habilidad, no solo al
    principio, porque cada una lanza un subproceso y son lo más caro de la ronda."""
    fallidas = []
    d = _leer_habilidades()
    if not d:
        return fallidas
    try:
        from Nucleo_Slide.Validador_Habilidades import probar_comportamiento
        from Nucleo_Slide import Auto_Programacion
        ruta = os.path.abspath(Auto_Programacion.__file__)
    except Exception:
        return fallidas
    for nombre, info in list(d.items()):
        if comprobar is not None and not comprobar():
            break                          # Marco volvió: se deja para la próxima
        try:
            ok, motivo = probar_comportamiento(ruta, nombre, info.get("prueba", ""))
            if not ok:
                fallidas.append((nombre, motivo))
        except Exception:
            continue
    return fallidas


# ── 3) Los guiones de prueba que quedan huérfanos en el temporal ─────────────
def barrer_temporales(dias=1):
    import glob
    import tempfile
    borrados = 0
    limite = time.time() - dias * 86400
    for patron in ("_aiden_prueba_*.py",):
        for p in glob.glob(os.path.join(tempfile.gettempdir(), patron)):
            try:
                if os.path.getmtime(p) < limite:
                    os.remove(p)           # de uno en uno: cortar aquí no deja nada a medias
                    borrados += 1
            except OSError:
                continue
    return borrados


def ronda(comprobar=None):
    """Una ronda completa, de lo barato a lo caro. Devuelve un resumen para el registro."""
    comprobar = comprobar or _sigue_libre
    hecho = {}
    if not comprobar():
        return hecho
    hecho["temporales"] = barrer_temporales()
    if not comprobar():
        return hecho
    hecho["memoria_visual"] = purgar_memoria_visual()
    if not comprobar():
        return hecho
    fallidas = reprobar_habilidades(comprobar)
    hecho["habilidades_fallidas"] = fallidas

    # Solo se avisa de lo que le CAMBIA algo a Marco. "Borré 3 temporales" es ruido; "la habilidad
    # que te escribiste ya no hace lo que decía" no lo es.
    if fallidas:
        try:
            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
            nombres = ", ".join(n for n, _m in fallidas)
            registrar_evento(f"Habilidades que ya no pasan su propia prueba: {nombres}.",
                             "mantenimiento")
        except Exception:
            pass
    return hecho


def _bucle():
    global _ultima_ronda
    time.sleep(120)                        # que arranque AIDEN entero antes de nada
    while True:
        time.sleep(_SONDEO)
        try:
            if not _sigue_libre():
                continue
            if time.time() - _ultima_ronda < _CADA:
                continue
            _ultima_ronda = time.time()
            r = ronda()
            if any(r.values()):
                print(f"[reposo] mantenimiento: {r}")
        except Exception:
            continue


def iniciar_reposo():
    threading.Thread(target=_bucle, daemon=True, name="reposo").start()
    return True
