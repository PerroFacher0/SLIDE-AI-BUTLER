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

import os
import threading
import time

INTERVALO_USB = 2        # seg entre revisiones del mapa de unidades
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
                if not _puedo_hablar():
                    break
                nombre = _etiqueta(u) or "sin nombre"
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
    print("[Eventos] vigilante de USB y descargas activo.")
    return True
