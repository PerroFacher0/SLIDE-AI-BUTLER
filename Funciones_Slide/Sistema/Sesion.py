# RETOMEMOS: AIDEN recuerda tu espacio de trabajo y lo restaura.
#
# Puro Jarvis: te sientas, dices "retomemos" y el taller ya esta servido — reabre las apps que
# tenias (VS Code, el navegador, el PDF...). Guarda cada pocos minutos las apps de ventana visible;
# al restaurar, relanza las que no esten abiertas. No restaura el documento exacto (eso depende de
# cada app), pero deja el entorno puesto.

import json
import os
import threading
import time

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sesion.json"
)
_lock = threading.RLock()

# Procesos de sistema/ruido que NO cuentan como "espacio de trabajo".
_IGNORAR = {
    "explorer.exe", "python.exe", "pythonw.exe", "searchhost.exe", "textinputhost.exe",
    "applicationframehost.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "systemsettings.exe", "dwm.exe", "sihost.exe", "ctfmon.exe", "aiden.exe",
}


def _apps_visibles():
    # Nombres de ejecutable de las apps con ventana VISIBLE con titulo (lo que Marco tiene abierto).
    procesos = set()
    try:
        import win32gui
        import win32process
        import psutil

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            if not (win32gui.GetWindowText(hwnd) or "").strip():
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                nombre = psutil.Process(pid).name()
                if nombre and nombre.lower() not in _IGNORAR:
                    procesos.add(nombre)
            except Exception:
                pass

        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
    return sorted(procesos)


def guardar_sesion():
    apps = _apps_visibles()
    if not apps:
        return
    with _lock:
        try:
            with open(_RUTA, "w", encoding="utf-8") as f:
                json.dump({"t": time.time(), "apps": apps}, f, ensure_ascii=False, indent=1)
        except Exception:
            pass


def _cargar():
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def restaurar_sesion(accion="restaurar"):
    """HERRAMIENTA: reabre el espacio de trabajo que Marco tenia ('retomemos', 'restaura mi sesion').
    accion 'guardar' fuerza guardar el estado actual; 'restaurar' (def) reabre lo guardado."""
    if str(accion).lower().startswith("guard"):
        guardar_sesion()
        d = _cargar()
        return (f"Sesion guardada, señor: {len(d.get('apps', []))} aplicaciones anotadas."
                if d.get("apps") else "No vi aplicaciones de trabajo que guardar, señor.")
    d = _cargar()
    apps = d.get("apps", [])
    if not apps:
        return "Aun no tengo una sesion suya guardada, señor. En cuanto trabaje un rato, la recordare."
    # Las que ya estan abiertas no se relanzan.
    abiertas = set(a.lower() for a in _apps_visibles())
    faltan = [a for a in apps if a.lower() not in abiertas]
    if not faltan:
        return "Su espacio de trabajo ya esta como lo dejo, señor. Todo en su sitio."
    relanzadas = []
    try:
        import subprocess
        for exe in faltan[:8]:
            try:
                subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Start-Process '{exe}'"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                relanzadas.append(exe.replace(".exe", ""))
            except Exception:
                continue
    except Exception:
        pass
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Restaure la sesion: {', '.join(relanzadas)}", "sesion")
    except Exception:
        pass
    if not relanzadas:
        return "Intente reabrir su espacio pero Windows no dejo, señor."
    return f"Retomando donde lo dejo, señor: reabri {', '.join(relanzadas)}."


def iniciar_sesion_autoguardado():
    # Guarda el espacio de trabajo cada 5 min (para poder retomarlo mañana).
    def _bucle():
        time.sleep(90)
        while True:
            try:
                guardar_sesion()
            except Exception:
                pass
            time.sleep(300)

    threading.Thread(target=_bucle, daemon=True).start()
