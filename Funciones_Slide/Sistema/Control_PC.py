import os
import time
import ctypes
from datetime import datetime
import pyautogui

_CARPETA_CAPTURAS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Capturas"
)

_CARPETAS = {
    "descargas": os.path.join(os.path.expanduser("~"), "Downloads"),
    "documentos": os.path.join(os.path.expanduser("~"), "Documents"),
    "escritorio": os.path.join(os.path.expanduser("~"), "Desktop"),
    "imagenes": os.path.join(os.path.expanduser("~"), "Pictures"),
    "musica": os.path.join(os.path.expanduser("~"), "Music"),
    "videos": os.path.join(os.path.expanduser("~"), "Videos"),
}


def dictar(texto):
    # Escribe 'texto' en donde esté el cursor. Usa el portapapeles (Ctrl+V) para que
    # los acentos y caracteres especiales salgan bien, y luego restaura lo que había.
    texto = str(texto)
    if not texto.strip():
        return "No me dijiste qué escribir, señor."
    try:
        import pyperclip
        anterior = pyperclip.paste()
        pyperclip.copy(texto)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyperclip.copy(anterior)   # restaura el portapapeles original
    except Exception:
        pyautogui.typewrite(texto, interval=0.02)
    return "Escrito, señor."


def abrir_carpeta(nombre):
    nombre = str(nombre).strip().lower()
    ruta = _CARPETAS.get(nombre)
    if ruta and os.path.isdir(ruta):
        os.startfile(ruta)
        return f"Abriendo la carpeta {nombre}, señor."
    if os.path.exists(nombre):
        os.startfile(nombre)
        return f"Abriendo {nombre}, señor."
    return f"No encontré la carpeta {nombre}, señor."


def control_ventana(accion):
    accion = str(accion).strip().lower()
    if accion in ("minimizar",):
        pyautogui.hotkey("win", "down")
    elif accion in ("maximizar",):
        pyautogui.hotkey("win", "up")
    elif accion in ("cerrar", "cerrar ventana"):
        pyautogui.hotkey("alt", "f4")
    elif accion in ("cambiar", "cambiar ventana", "siguiente ventana"):
        pyautogui.hotkey("alt", "tab")
    elif accion in ("escritorio", "mostrar escritorio", "minimizar todo"):
        pyautogui.hotkey("win", "d")
    else:
        return "No entendí qué hacer con la ventana, señor."
    return "Hecho, señor."


def buscar_archivo(nombre):
    nombre = str(nombre).strip().lower()
    if not nombre:
        return "¿Qué archivo busco, señor?"
    raices = [v for v in _CARPETAS.values() if os.path.isdir(v)]
    encontrados = []
    escaneados = 0
    for raiz in raices:
        for dirpath, _dirs, files in os.walk(raiz):
            for f in files:
                escaneados += 1
                if nombre in f.lower():
                    encontrados.append(os.path.join(dirpath, f))
                    if len(encontrados) >= 8:
                        break
            if len(encontrados) >= 8 or escaneados > 60000:
                break
        if len(encontrados) >= 8 or escaneados > 60000:
            break
    if not encontrados:
        return f"No encontré ningún archivo con '{nombre}', señor."
    try:
        os.startfile(encontrados[0])   # abre el primero en su app por defecto
    except Exception:
        pass
    nombres = ", ".join(os.path.basename(e) for e in encontrados)
    return f"Encontré y abrí: {os.path.basename(encontrados[0])}. También vi: {nombres}."


def abrir_reciente(que="descarga"):
    # Abre el archivo MÁS RECIENTE de una carpeta: lo último que Marco descargó / su último documento
    # / su última captura. Lo que uno hace a diario ("abre lo que acabo de bajar").
    q = str(que or "descarga").strip().lower()
    if "document" in q or "word" in q or "pdf" in q or "trabajo" in q:
        carpeta, exts = _CARPETAS["documentos"], (".docx", ".doc", ".pdf", ".pptx", ".xlsx", ".txt")
        etiqueta = "documento"
    elif "captur" in q or "foto" in q or "imagen" in q or "screenshot" in q:
        carpeta, exts = _CARPETAS["imagenes"], (".png", ".jpg", ".jpeg", ".gif", ".webp")
        etiqueta = "captura"
    else:
        carpeta, exts = _CARPETAS["descargas"], None   # descargas: cualquier tipo
        etiqueta = "descarga"
    if not os.path.isdir(carpeta):
        return f"No encuentro la carpeta de {etiqueta}s, señor."
    candidatos = []
    for nombre in os.listdir(carpeta):
        ruta = os.path.join(carpeta, nombre)
        if not os.path.isfile(ruta):
            continue
        if nombre.endswith(".crdownload") or nombre.endswith(".tmp"):   # descarga a medias
            continue
        if exts and not nombre.lower().endswith(exts):
            continue
        candidatos.append(ruta)
    if not candidatos:
        return f"No veo ninguna {etiqueta} reciente, señor."
    reciente = max(candidatos, key=os.path.getmtime)
    try:
        os.startfile(reciente)
        return f"Abriendo su última {etiqueta}, señor: {os.path.basename(reciente)}."
    except Exception as e:
        return f"La encontré pero no pude abrirla, señor: {e}"


def grabar_pantalla():
    # Inicia/detiene la grabación de pantalla de Windows (Xbox Game Bar): Win+Alt+R (es un toggle).
    try:
        pyautogui.hotkey("win", "alt", "r")
        return ("Grabación de pantalla activada, señor (Win+Alt+R). Dígame 'para la grabación' para "
                "detenerla. Si no arrancó, active la Xbox Game Bar en Configuración.")
    except Exception as e:
        return f"No pude iniciar la grabación, señor: {e}"


def controlar_energia(accion, minutos=0):
    accion = str(accion).strip().lower()
    try:
        seg = int(float(minutos) * 60)
    except (ValueError, TypeError):
        seg = 0

    if accion in ("apagar", "apaga", "apagate", "apágate"):
        os.system(f"shutdown /s /t {seg}")
        return f"Apagaré el equipo en {int(seg/60)} minutos, señor." if seg else "Apagando el equipo, señor."
    if accion in ("reiniciar", "reinicia"):
        os.system(f"shutdown /r /t {seg}")
        return "Reiniciando el equipo, señor."
    if accion in ("cancelar", "cancela"):
        os.system("shutdown /a")
        return "Cancelé el apagado programado, señor."
    if accion in ("bloquear", "bloquea"):
        ctypes.windll.user32.LockWorkStation()
        return "Equipo bloqueado, señor."
    if accion in ("suspender", "suspende", "dormir"):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Suspendiendo el equipo, señor."
    return "No entendí la acción de energía, señor."


def tomar_captura():
    try:
        from PIL import ImageGrab
        if not os.path.isdir(_CARPETA_CAPTURAS):
            os.makedirs(_CARPETA_CAPTURAS)
        nombre = datetime.now().strftime("captura_%Y-%m-%d_%H-%M-%S.png")
        ImageGrab.grab().save(os.path.join(_CARPETA_CAPTURAS, nombre))
        return f"Captura guardada, señor: {nombre}"
    except Exception as e:
        return f"No pude tomar la captura, señor: {e}"


def ajustar_brillo(accion):
    try:
        import screen_brightness_control as sbc
        actual = sbc.get_brightness()
        actual = actual[0] if isinstance(actual, list) else actual
        a = str(accion).strip().lower()
        if a in ("subir", "sube", "mas", "más", "arriba"):
            nuevo = min(100, actual + 20)
        elif a in ("bajar", "baja", "menos", "abajo"):
            nuevo = max(0, actual - 20)
        elif a.isdigit():
            nuevo = max(0, min(100, int(a)))
        else:
            return "No entendí el ajuste de brillo, señor."
        sbc.set_brightness(nuevo)
        return f"Brillo al {nuevo}%, señor."
    except Exception as e:
        return f"No pude ajustar el brillo (tu monitor podría no permitirlo), señor: {e}"
