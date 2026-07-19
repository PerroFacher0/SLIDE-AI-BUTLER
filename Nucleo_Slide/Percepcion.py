# PERCEPCIÓN: los SENTIDOS locales de AIDEN sobre el PC de Marco, en un solo lugar.
#
# El salto de feeling: antes la "foto del PC" (ventana activa, apps, portapapeles) solo la veía la
# Conciencia cada tantos minutos. Ahora el CEREBRO la recibe en CADA turno de conversación: cuando
# Marco dice "cierra eso", "¿qué opinas de esto?", "lo que estoy viendo", AIDEN YA SABE a qué se
# refiere — sin herramientas, sin preguntar. Es darle acceso permanente a la PC como sensación.
#
# Barato a propósito: solo win32gui/pyperclip/psutil locales (cero LLM, cero red) y con caché de
# unos segundos para no enumerar ventanas en cada frase.

import threading
import time

_lock = threading.Lock()
_cache = {"t": 0.0, "texto": ""}
_TTL = 5.0   # segundos de vigencia de la foto


def ventana_activa():
    try:
        import win32gui
        return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or "(escritorio)"
    except Exception:
        return "(desconocida)"


def apps_abiertas(maximo=10):
    titulos = []
    try:
        import win32gui

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t and t.strip():
                    titulos.append(t.strip())

        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
    vistos, salida = set(), []
    for t in titulos:
        if t not in vistos:
            vistos.add(t)
            salida.append(t)
    return salida[:maximo]


def _portapapeles():
    try:
        import pyperclip
        clip = (pyperclip.paste() or "").strip().replace("\n", " ")
        return clip[:100]
    except Exception:
        return ""


def _energia():
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat is not None:
            return f"batería {int(bat.percent)}%" + ("" if bat.power_plugged else " SIN cargador")
    except Exception:
        pass
    return ""


def percepcion_compacta():
    """La vista de AIDEN sobre el PC AHORA, compacta para el prompt (con caché de unos segundos)."""
    ahora = time.time()
    with _lock:
        if ahora - _cache["t"] < _TTL:
            return _cache["texto"]
    lineas = [f"Ventana activa (lo que Marco tiene al frente): {ventana_activa()}"]
    apps = apps_abiertas(8)
    if apps:
        lineas.append("Abierto en su PC: " + " | ".join(apps))
    clip = _portapapeles()
    if clip:
        lineas.append(f"Portapapeles (lo último que copió): {clip}")
    e = _energia()
    if e:
        lineas.append(f"Energía: {e}")
    texto = "\n".join(lineas)
    with _lock:
        _cache.update(t=ahora, texto=texto)
    return texto
