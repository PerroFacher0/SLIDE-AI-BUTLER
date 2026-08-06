# FRENO DURO — el respaldo para cuando el freno normal no puede llegar.
#
# Ctrl+Alt+P es COOPERATIVO: levanta una bandera y el código en curso tiene que mirarla. Funciona
# bien, y medirlo lo confirma: los 6 bloques cancelables del proyecto consultan la bandera dentro
# de sus bucles. El problema no está ahí.
#
# ── LOS DOS HUECOS QUE ESTE ARCHIVO SÍ TAPA ───────────────────────────────────
#
# 1. AIDEN COLGADO DENTRO DE UNA LLAMADA DE RED. El SDK de OpenAI trae 600 s de timeout de lectura
#    y 2 reintentos: hasta media hora sentado dentro de create() sin volver nunca al bucle que
#    miraría la bandera. Cancelar no sirve porque no hay quien mire. (El arreglo de fondo es poner
#    timeouts cortos, y se pusieron; esto es la red por debajo.)
#
# 2. NO HAY ATAJO NINGUNO CUANDO NO HAY OPERACIÓN EN CURSO. El vigía de Ctrl+Alt+P solo existe
#    mientras corre un `with operacion(...)`, y pedir_cancelar() devuelve False si no hay ninguna.
#    Si AIDEN se cuelga en cualquier otro sitio — el bucle principal del cerebro, el arranque, un
#    hilo de fondo — no hay ninguna tecla que hacer. Justo cuando más falta hace.
#
# Por eso este vigía corre SIEMPRE, no solo durante una operación. Exigirle "que haya algo en
# curso", como hace cancelar(), reproduciría exactamente el hueco 2 y lo dejaría inútil en el único
# caso para el que existe.
#
# ── QUE NO SE DISPARE POR ACCIDENTE ───────────────────────────────────────────
# La protección no es exigir una operación activa: es que hay que MANTENER las cuatro teclas
# pulsadas 1,2 s. Un roce no lo consigue, y la intención se nota.
#
# ── Y QUE NO SEA UN MARTILLO CUANDO NO HACE FALTA ─────────────────────────────
# Al dispararse NO mata de entrada. Va de menos a más:
#   1. Si hay una operación en curso, prueba primero el freno normal y espera 2 s. Si aquello
#      estaba vivo y solo era largo, se detiene solo y AIDEN sigue funcionando. Fin.
#   2. Si no cede (o no había operación: AIDEN colgado de verdad), mata el árbol de procesos hijos
#      — el PowerShell caliente, Playwright, lo que haya quedado agarrado.
#   3. Intenta el cierre limpio de Salir(), que es el que se despide por voz y quita el icono de la
#      bandeja, con 2,5 s de gracia.
#   4. Si a esas alturas el proceso sigue vivo, es que está colgado de verdad: os._exit().
#
# Solo se llega al paso 4 si los tres anteriores no bastaron. Que es la definición del caso.

import ctypes
import os
import subprocess
import threading
import time

# Ctrl + Alt + Shift + K. Cuatro teclas y una letra que no está en ningún atajo de Windows.
_VK_CONTROL, _VK_ALT, _VK_SHIFT, _VK_K = 0x11, 0x12, 0x10, 0x4B
_COMBO = (_VK_CONTROL, _VK_ALT, _VK_SHIFT, _VK_K)

MANTENER = 1.2         # s que hay que sostener la combinación: descarta el roce accidental
GRACIA_COOPERATIVA = 2.0    # s de margen para que el freno normal haga su trabajo
GRACIA_LIMPIA = 2.5         # s para que Salir() se despida antes del corte seco
_SONDEO = 0.06

_vigia = None
_disparado = threading.Event()


def _tecla(vk):
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def _combo_pulsado():
    return all(_tecla(v) for v in _COMBO)


class _ENTRADA_PROC(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong), ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_char * 260)]


def _hijos_sin_psutil():
    """Los PIDs descendientes preguntándole a Windows por ctypes.

    Existe por dos motivos, los dos aprendidos midiendo:

    1. Este es el ÚLTIMO recurso y no puede depender de que un import esté. La primera versión
       usaba solo psutil y, al no estar instalado, se tragaba el ImportError y devolvía 0 —
       idéntico a "no había hijos". Un freno que falla en silencio es peor que no tenerlo, porque
       parece que funcionó.
    2. El segundo intento preguntaba por PowerShell, y tardaba entre 2,5 y 5 segundos en arrancar
       en frío. Un freno de emergencia no puede pararse a lanzar un proceso: la foto de Toolhelp32
       es instantánea y no arranca nada."""
    TH32CS_SNAPPROCESS, INVALID = 0x2, ctypes.c_void_p(-1).value
    k32 = ctypes.windll.kernel32
    padres = {}
    try:
        foto = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if foto == INVALID:
            return []
        try:
            e = _ENTRADA_PROC()
            e.dwSize = ctypes.sizeof(_ENTRADA_PROC)
            if not k32.Process32First(foto, ctypes.byref(e)):
                return []
            while True:
                padres[e.th32ProcessID] = e.th32ParentProcessID
                if not k32.Process32Next(foto, ctypes.byref(e)):
                    break
        finally:
            k32.CloseHandle(foto)
    except Exception:
        return []

    # Hijos, nietos y demás: el equivalente al recursive=True de psutil.
    yo, descendientes, frontera = os.getpid(), [], [os.getpid()]
    while frontera:
        actual = frontera.pop()
        for pid, padre in padres.items():
            if padre == actual and pid != yo and pid not in descendientes:
                descendientes.append(pid)
                frontera.append(pid)
    return descendientes


def _matar_hijos():
    """El mismo patrón que _matar_arbol de Control_Total, pero desde el proceso de AIDEN hacia
    abajo: lo que cuelga suele ser un hijo agarrado, no AIDEN mismo.

    Devuelve (muertos, como). `como` distingue "no había nada que matar" de "no pude" — que es
    justo lo que la primera versión confundía."""
    try:
        import psutil
        yo = psutil.Process(os.getpid())
        muertos = 0
        for hijo in yo.children(recursive=True):
            try:
                hijo.kill()
                muertos += 1
            except Exception:
                pass
        return muertos, "psutil"
    except ImportError:
        pass
    except Exception:
        return 0, "fallo"

    # Sin psutil: la lista ya viene recursiva, así que basta con terminar cada uno. Se hace por
    # ctypes y no con taskkill porque taskkill es otro proceso más que lanzar, y aquí se está
    # justamente porque algo no responde.
    PROCESS_TERMINATE = 0x0001
    k32 = ctypes.windll.kernel32
    muertos = 0
    for pid in _hijos_sin_psutil():
        try:
            h = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h:
                if k32.TerminateProcess(h, 1):
                    muertos += 1
                k32.CloseHandle(h)
        except Exception:
            pass
    return muertos, "ctypes"


def _cierre_limpio():
    try:
        from Funciones_Slide.Sistema.Comandos_Asistente import Salir
        Salir(demora=0.5)
    except Exception:
        pass


def frenar(motivo="freno duro"):
    """Los cuatro pasos, de menos a más. Devuelve el texto de lo que hizo (para poder probarlo sin
    que mate el proceso de la prueba: el paso 4 se salta si _MATAR está en False)."""
    if _disparado.is_set():
        return "ya estaba frenando"
    _disparado.set()
    print(f"\n[FRENO DURO] {motivo}")

    # 1) Lo suave primero: si esto era una operación larga y sana, aquí se acaba.
    try:
        from Nucleo_Slide import Cancelacion
        if Cancelacion.operacion_en_curso() is not None:
            Cancelacion.pedir_cancelar("freno duro (Ctrl+Alt+Shift+K)")
            print(f"[FRENO DURO] freno normal pedido; {GRACIA_COOPERATIVA}s de margen...")
            fin = time.time() + GRACIA_COOPERATIVA
            while time.time() < fin:
                if Cancelacion.operacion_en_curso() is None:
                    print("[FRENO DURO] cedió con el freno normal. AIDEN sigue vivo.")
                    _disparado.clear()
                    return "cedio_normal"
                time.sleep(0.05)
    except Exception:
        pass

    # 2) No cedió: lo que cuelga es un hijo, o AIDEN mismo.
    muertos, como = _matar_hijos()
    print(f"[FRENO DURO] procesos hijos terminados: {muertos} (via {como})")

    # 3) Cierre limpio, en su propio hilo: si Salir() también se cuelga, no arrastra al paso 4.
    threading.Thread(target=_cierre_limpio, daemon=True).start()
    time.sleep(GRACIA_LIMPIA)

    # 4) Sigue vivo -> corte seco. Aquí ya no hay nada elegante que hacer.
    if _MATAR:
        print("[FRENO DURO] no cerró solo. Corte seco.")
        os._exit(1)
    return "corte_seco"


_MATAR = True          # las pruebas lo apagan para poder llegar al paso 4 sin morirse


def _vigilar():
    desde = None
    while True:
        try:
            if _combo_pulsado():
                if desde is None:
                    desde = time.time()
                elif time.time() - desde >= MANTENER:
                    frenar("Ctrl+Alt+Shift+K sostenido")
                    desde = None
            else:
                desde = None            # se soltó antes de tiempo: no cuenta
        except Exception:
            desde = None
        time.sleep(_SONDEO)


def iniciar():
    """Arranca el vigía permanente. Idempotente."""
    global _vigia
    if _vigia is not None and _vigia.is_alive():
        return False
    _vigia = threading.Thread(target=_vigilar, daemon=True, name="freno_duro")
    _vigia.start()
    return True
