# VIGILANTE DE EVENTOS DEL SISTEMA: que AIDEN se entere de lo que PASA, no solo de lo que le dicen.
#
# Hasta ahora AIDEN sabía de notificaciones (Bitacora lee la base de Windows) y de lo que Marco
# copiaba, pero era ciego a dos cosas que ocurren todo el tiempo y siempre piden lo mismo:
#   - Metiste un USB o un disco externo  -> "¿lo abro, señor?"
#   - Terminó de bajar un archivo        -> "bajó el PDF; ¿lo abro?"
#
# Diseño ANTI-MOLESTIA, igual que los otros vigilantes:
#   1. Solo eventos INEQUÍVOCOS (una unidad nueva de verdad; un archivo que TERMINÓ de bajar).
#   2. Dedup: nada se anuncia dos veces.
#   3. Cooldown entre avisos.
#   4. Se PAUSA en modo gaming.
#   5. Solo AVISA; no abre nada sin permiso.
#
# El USB se detecta sondeando el mapa de unidades con kernel32 (un bitmask: es instantáneo y no
# cuesta nada). Se sondea en vez de escuchar WM_DEVICECHANGE porque ese mensaje exige una ventana
# nativa con su bucle propio, y aquí el hilo de ventanas es de Qt: montar una ventana oculta solo
# para esto sería más frágil que mirar un entero cada dos segundos.

#
# BUS DE EVENTOS Y ESPERA BLOQUEANTE: además de AVISAR, ahora AIDEN puede QUEDARSE ESPERANDO a que
# algo pase ("avísame en cuanto termine de compilar", "espera a que copie el enlace"). Eso convierte
# una pregunta que había que repetir en algo que se resuelve solo cuando ocurre.
#
# El cambio de ventana se detecta SONDEANDO GetForegroundWindow dos veces por segundo, no con
# SetWinEventHook. El hook es más elegante sobre el papel, pero exige un bucle de mensajes de
# Windows propio, y en este proceso el hilo de ventanas ya es de Qt: montar un segundo bucle de
# mensajes en paralelo es una fuente clásica de cuelgues. Dos llamadas por segundo a una función
# que solo devuelve un puntero cuestan una fracción de un 1% de CPU; la robustez vale más aquí.

import os
import threading
import time
from collections import deque

INTERVALO_USB = 2        # seg entre revisiones del mapa de unidades
INTERVALO_VENTANA = 0.5  # seg entre revisiones de la ventana en primer plano
_MAX_EVENTOS = 20        # historial reciente que se conserva

_eventos = deque(maxlen=_MAX_EVENTOS)   # [(t, tipo, proceso, titulo, detalle)]
_esperas = []                            # waiters activos: [{criterio, evento, encontrado}]
_lock_bus = threading.RLock()
COOLDOWN = 25            # seg mínimos entre dos avisos (no atosigar)
_ESTABLE = 1.5           # seg que el tamaño debe quedarse quieto para dar la descarga por terminada

_pausado = False
_ultimo_aviso = 0
_lock = threading.RLock()

# Archivos "en progreso" de los navegadores: no son descargas terminadas.
_TEMPORALES = (".crdownload", ".part", ".tmp", ".partial", ".download", ".opdownload")


def pausar_vigilante_eventos(pausar=True):
    # Silencia el vigilante (lo usa el modo gaming).
    global _pausado
    _pausado = bool(pausar)


# ── Bus de eventos ───────────────────────────────────────────────────────────
def publicar(tipo, proceso="", titulo="", detalle=""):
    """Registra un evento y despierta a quien lo estuviera esperando. Lo llama este módulo y
    también otros vigilantes (el del portapapeles), para no sondear dos veces lo mismo."""
    ev = (time.time(), tipo, str(proceso or ""), str(titulo or ""), str(detalle or "")[:300])
    with _lock_bus:
        _eventos.append(ev)
        for espera in list(_esperas):
            if espera["encontrado"] is None and _coincide(ev, espera["criterio"]):
                espera["encontrado"] = ev
                espera["evento"].set()
    return ev


def _coincide(ev, criterio):
    _t, tipo, proceso, titulo, detalle = ev
    quiere_tipo = criterio.get("tipo") or ""
    if quiere_tipo and quiere_tipo not in tipo:
        return False
    filtro = (criterio.get("filtro") or "").lower()
    if filtro and filtro not in f"{proceso} {titulo} {detalle}".lower():
        return False
    return True


def historial(cuantos=8):
    """Los últimos eventos significativos, del más reciente al más viejo."""
    with _lock_bus:
        return list(_eventos)[-cuantos:][::-1]


# ── Ventana en primer plano ──────────────────────────────────────────────────
def _foco_actual():
    try:
        import win32gui
        import win32process
        h = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(h) or ""
        proceso = ""
        try:
            import psutil
            _, pid = win32process.GetWindowThreadProcessId(h)
            proceso = psutil.Process(pid).name()
        except Exception:
            pass
        return proceso, titulo
    except Exception:
        return "", ""


# Ruido que no aporta nada como "evento" (el escritorio, el conmutador de ventanas).
_IGNORAR = ("dwm.exe", "searchhost.exe", "shellexperiencehost.exe", "textinputhost.exe", "")


def _bucle_ventanas():
    anterior = None
    while True:
        time.sleep(INTERVALO_VENTANA)
        try:
            proceso, titulo = _foco_actual()
            if not titulo or proceso.lower() in _IGNORAR:
                continue
            actual = (proceso, titulo)
            if actual != anterior:
                anterior = actual
                publicar("ventana_foco", proceso, titulo)
        except Exception:
            continue


# ── Espera bloqueante ────────────────────────────────────────────────────────
def _esperar_cierre_proceso(nombre, timeout):
    """Espera a que TERMINE un proceso (el caso '¿ya compiló?'). Si no está corriendo, se responde
    de inmediato en vez de esperar en vano un timeout entero."""
    try:
        import psutil
    except Exception:
        return "No puedo vigilar procesos, señor (falta psutil)."
    objetivo = nombre.lower().replace(".exe", "")

    def _vivos():
        pids = []
        for p in psutil.process_iter(["name"]):
            try:
                if objetivo in (p.info["name"] or "").lower():
                    pids.append(p.pid)
            except Exception:
                continue
        return pids

    if not _vivos():
        return f"«{nombre}» no está corriendo ahora mismo, señor; no hay nada que esperar."
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            from Nucleo_Slide import Cancelacion
            if Cancelacion.cancelado():
                return "Dejé de esperar, señor (me pidió parar)."
        except Exception:
            pass
        time.sleep(1.0)
        if not _vivos():
            publicar("proceso_cierra", nombre, "", "terminó")
            return f"Listo, señor: «{nombre}» terminó."
    return f"Pasaron {timeout} segundos y «{nombre}» sigue corriendo, señor."


def _ventana_por_titulo(texto):
    """hwnd de la primera ventana visible cuyo título contenga 'texto', o None."""
    try:
        import win32gui
    except Exception:
        return None
    objetivo, halladas = str(texto or "").lower(), []

    def _cb(h, _):
        try:
            if win32gui.IsWindowVisible(h):
                t = (win32gui.GetWindowText(h) or "").lower()
                if t and objetivo in t:
                    halladas.append(h)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return None
    return halladas[0] if halladas else None


def _marcar(hwnd, activo):
    """Enciende o apaga las escuadras del HUD. Adorno: si no hay HUD, no pasa nada."""
    if not hwnd:
        return
    try:
        from Interfaz import Mira
        Mira.marcar_vigilancia(hwnd, activo)
    except Exception:
        pass


def esperar_evento(tipo="ventana", filtro="", timeout_segundos=60):
    """HERRAMIENTA: se queda ESPERANDO a que algo pase en el PC y avisa en cuanto ocurre.
      tipo = ventana (cambia la app en primer plano) | portapapeles (Marco copia algo) |
             usb (conecta una unidad) | descarga (termina una descarga) |
             proceso_cierra (termina un programa: 'ya compiló', 'ya terminó de exportar')
      filtro = texto que debe aparecer (nombre de app, del proceso, del archivo). Vacío = cualquiera.
      timeout_segundos = cuánto esperar como máximo."""
    t = str(tipo or "ventana").strip().lower()
    filtro = str(filtro or "").strip()
    try:
        timeout = max(5, min(600, int(timeout_segundos)))
    except (TypeError, ValueError):
        timeout = 60

    if "proceso" in t or "cierr" in t or "termin" in t:
        if not filtro:
            return "¿Qué programa quiere que espere a que termine, señor?"
        return _esperar_cierre_proceso(filtro, timeout)

    mapa = {"ventana": "ventana_foco", "foco": "ventana_foco", "app": "ventana_foco",
            "portapapeles": "portapapeles", "copia": "portapapeles", "clipboard": "portapapeles",
            "usb": "usb", "unidad": "usb", "descarga": "descarga", "archivo": "descarga"}
    tipo_bus = mapa.get(t, t)

    espera = {"criterio": {"tipo": tipo_bus, "filtro": filtro},
              "evento": threading.Event(), "encontrado": None}
    with _lock_bus:
        _esperas.append(espera)
    # Escuadras en las esquinas de la ventana vigilada: "estoy con un ojo puesto aquí". Sin esto,
    # esperar y estar colgado se ven igual — es decir, no se ven.
    hwnd = _ventana_por_titulo(filtro) if (tipo_bus == "ventana_foco" and filtro) else None
    _marcar(hwnd, True)
    try:
        llego = espera["evento"].wait(timeout=timeout)
    finally:
        _marcar(hwnd, False)          # también si salta el timeout o Marco cancela
        with _lock_bus:
            if espera in _esperas:
                _esperas.remove(espera)

    if not llego or not espera["encontrado"]:
        detalle = f" «{filtro}»" if filtro else ""
        return f"Pasaron {timeout} segundos y no ocurrió{detalle}, señor."
    _t, _tp, proceso, titulo, detalle = espera["encontrado"]
    if tipo_bus == "portapapeles":
        return f"Marco acaba de copiar algo, señor: {detalle[:200]}"
    if tipo_bus == "usb":
        return f"Conectaron una unidad, señor: {titulo or detalle}"
    if tipo_bus == "descarga":
        return f"Terminó de descargarse, señor: {titulo or detalle}"
    # El nombre de la APP importa tanto como el del documento: "cambió a diseno.psd" no dice
    # cuál programa se abrió, que suele ser justo lo que Marco estaba esperando.
    app = proceso.replace(".exe", "") if proceso else ""
    if app and titulo:
        return f"Ya está, señor: cambió a {app} ({titulo[:60]})."
    return f"Ya está, señor: cambió a {titulo or app}."


def _puedo_hablar():
    global _ultimo_aviso
    with _lock:
        if _pausado or time.time() - _ultimo_aviso < COOLDOWN:
            return False
        _ultimo_aviso = time.time()
    return True


# ── USB / discos externos ─────────────────────────────────────────────────────
def _unidades_extraibles():
    """Letras de unidad extraíbles montadas AHORA (USB, discos externos, SD)."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        mapa = k32.GetLogicalDrives()
        fuera = set()
        for i in range(26):
            if not (mapa >> i) & 1:
                continue
            letra = f"{chr(65 + i)}:\\"
            tipo = k32.GetDriveTypeW(ctypes.c_wchar_p(letra))
            if tipo in (2, 6):        # DRIVE_REMOVABLE / DRIVE_RAMDISK-ish externos
                fuera.add(letra)
        return fuera
    except Exception:
        return set()


def _etiqueta(unidad):
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(unidad), buf, 260, None, None, None, None, 0)
        return (buf.value or "").strip()
    except Exception:
        return ""


def _cuanto_espacio(unidad):
    try:
        import shutil
        u = shutil.disk_usage(unidad)
        return f"{u.used / 1e9:.1f} de {u.total / 1e9:.1f} GB usados"
    except Exception:
        return ""


def _bucle_usb(hablar):
    conocidas = _unidades_extraibles()      # lo que ya estaba puesto al arrancar: no se anuncia
    while True:
        time.sleep(INTERVALO_USB)
        try:
            if _pausado:
                continue
            ahora = _unidades_extraibles()
            nuevas = ahora - conocidas
            quitadas = conocidas - ahora
            conocidas = ahora
            for u in sorted(nuevas):
                nombre = _etiqueta(u) or "sin nombre"
                # Se publica SIEMPRE (aunque el cooldown impida hablar): quien esté esperando
                # este evento debe enterarse igual.
                publicar("usb", "", f"{nombre} en {u[:2]}", u)
                if not _puedo_hablar():
                    continue
                espacio = _cuanto_espacio(u)
                detalle = f" ({espacio})" if espacio else ""
                hablar(f"Conectó una unidad externa, señor: {nombre} en {u[:2]}{detalle}. "
                       "¿Quiere que la abra?")
            for u in sorted(quitadas):
                if not _puedo_hablar():
                    break
                hablar(f"Retiraron la unidad {u[:2]}, señor.")
        except Exception:
            continue


# ── Descargas nuevas ──────────────────────────────────────────────────────────
def _carpeta_descargas():
    for ruta in (os.path.join(os.path.expanduser("~"), "Downloads"),
                 os.path.join(os.path.expanduser("~"), "Descargas")):
        if os.path.isdir(ruta):
            return ruta
    return None


def _esperar_a_que_termine(ruta):
    """Una descarga sigue creciendo. Se considera terminada cuando el tamaño deja de cambiar."""
    ultimo = -1
    for _ in range(40):                      # ~60 s como mucho
        try:
            actual = os.path.getsize(ruta)
        except OSError:
            return False                      # se lo llevaron (era un temporal renombrado)
        if actual == ultimo and actual > 0:
            return True
        ultimo = actual
        time.sleep(_ESTABLE)
    return True


def _bucle_descargas(hablar):
    carpeta = _carpeta_descargas()
    if not carpeta:
        return
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except Exception:
        return

    anunciados = set()

    class _Oido(FileSystemEventHandler):
        def _considerar(self, ruta):
            if _pausado or os.path.isdir(ruta):
                return
            nombre = os.path.basename(ruta)
            if nombre.startswith("~") or nombre.lower().endswith(_TEMPORALES):
                return                        # todavía se está bajando
            with _lock:
                if ruta in anunciados:
                    return
                anunciados.add(ruta)
            # En su propio hilo: esperar aquí bloquearía al observador de watchdog.
            threading.Thread(target=self._avisar, args=(ruta, nombre), daemon=True).start()

        def _avisar(self, ruta, nombre):
            if not _esperar_a_que_termine(ruta) or not os.path.exists(ruta):
                return
            publicar("descarga", "", nombre, ruta)   # siempre, aunque el cooldown calle la voz
            if not _puedo_hablar():
                return
            try:
                mb = os.path.getsize(ruta) / 1e6
                peso = f" ({mb:.1f} MB)" if mb >= 0.1 else ""
            except OSError:
                peso = ""
            hablar(f"Terminó de descargarse {nombre}{peso}, señor. ¿Lo abro?")

        def on_created(self, e):
            self._considerar(e.src_path)

        def on_moved(self, e):
            # Chrome baja a .crdownload y RENOMBRA al terminar: ese rename es el final real.
            self._considerar(e.dest_path)

    obs = Observer()
    obs.schedule(_Oido(), carpeta, recursive=False)
    obs.start()
    print(f"[Eventos] vigilando descargas en {carpeta}")
    while True:
        time.sleep(3600)


def iniciar_vigilante_eventos(hablar):
    """Arranca la vigilancia de USB y de descargas en hilos de fondo."""
    threading.Thread(target=_bucle_usb, args=(hablar,), daemon=True).start()
    threading.Thread(target=_bucle_descargas, args=(hablar,), daemon=True).start()
    threading.Thread(target=_bucle_ventanas, daemon=True).start()
    print("[Eventos] vigilante de USB, descargas y ventanas activo.")
    return True
