import os
import time
import ctypes
import threading
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


# ── DICTADO CONTINUO ─────────────────────────────────────────────────────────
# Hasta ahora escribir por voz era: Marco dice una frase -> ronda completa del LLM -> AIDEN escribe
# esa frase. Para un párrafo largo eso son diez rondas, diez esperas y diez oportunidades de que el
# modelo "mejore" lo dicho. Para REDACTAR hablando de corrido hace falta lo contrario: transcribir
# y pegar, frase a frase, SIN que el LLM toque nada en medio. Aquí la fidelidad importa más que la
# inteligencia — lo dictado es de Marco, no del modelo.
#
# Se corta diciendo una frase de cierre, o con el freno de siempre (Ctrl+Alt+P).
_FRASES_FIN = ("fin del dictado", "para de escribir", "deja de escribir", "termina el dictado",
               "fin de dictado", "para el dictado", "ya termine", "ya terminé", "listo aiden")
# Signos que se dicen en voz alta y no se escriben solos.
_PUNTUACION = {"punto y aparte": ".\n", "punto y seguido": ". ", "punto final": ".",
               "nueva linea": "\n", "nueva línea": "\n", "salto de linea": "\n",
               "salto de línea": "\n", "punto": ". ", "coma": ", ",
               "dos puntos": ": ", "punto y coma": "; ",
               "signo de interrogacion": "?", "signo de interrogación": "?",
               "abre parentesis": " (", "cierra parentesis": ") "}

_dictando = {"activo": False}


def _limpiar_frase(frase):
    """Convierte los signos DICHOS en signos escritos y deja la frase lista para pegar."""
    t = " " + str(frase or "").strip() + " "
    bajo = t.lower()
    # De más largo a más corto: "punto y aparte" antes que "punto", o se rompería en pedazos.
    for dicho in sorted(_PUNTUACION, key=len, reverse=True):
        idx = bajo.find(" " + dicho + " ")
        while idx != -1:
            t = t[:idx] + _PUNTUACION[dicho] + t[idx + len(dicho) + 2:]
            bajo = t.lower()
            idx = bajo.find(" " + dicho + " ")
    # strip(" \t") y NO strip(): un strip pelado se comía el salto de línea recién puesto, así que
    # un "punto y aparte" AL FINAL de la frase — que es justo como se cierra un párrafo dictando —
    # perdía el salto y el párrafo siguiente se pegaba al anterior.
    return t.strip(" \t")


def _bucle_dictado(hablar=None):
    from Nucleo_Slide import Cancelacion
    from Voz_Slide.Transcriptor import escuchador_de_usuario, es_alucinacion

    escritas = 0
    try:
        with Cancelacion.operacion("el dictado continuo"):
            while _dictando["activo"]:
                Cancelacion.revisar()
                frase = escuchador_de_usuario(timeout=30)
                if not frase or es_alucinacion(frase):
                    continue                       # silencio o ruido: se sigue escuchando
                if any(f in frase.lower() for f in _FRASES_FIN):
                    break
                texto = _limpiar_frase(frase)
                if not texto:
                    continue
                dictar(texto + " ")
                escritas += 1
    except Cancelacion.Cancelado:
        pass
    except Exception as e:
        print(f"[dictado] se corto: {e}")
    _dictando["activo"] = False
    fin = (f"Dictado cerrado, señor: {escritas} frase(s) escritas."
           if escritas else "Cerré el dictado sin escribir nada, señor.")
    if callable(hablar):
        try:
            hablar(fin)
        except Exception:
            pass
    return fin


def dictado_continuo(hablar=None):
    """Arranca el modo dictado: todo lo que Marco diga se escribe tal cual, hasta que diga que
    pare. No pasa por el LLM en ningún momento — lo dictado sale como se dijo."""
    if _dictando["activo"]:
        return "Ya estoy tomando dictado, señor. Dígame 'fin del dictado' cuando termine."
    _dictando["activo"] = True
    threading.Thread(target=_bucle_dictado, args=(hablar,), daemon=True).start()
    return ("Le tomo el dictado, señor: hable con calma y voy escribiendo. Diga 'punto', 'coma' o "
            "'nueva línea' para los signos, y 'fin del dictado' cuando termine.")


def detener_dictado():
    if not _dictando["activo"]:
        return "No estaba tomando dictado, señor."
    _dictando["activo"] = False
    return "Dictado detenido, señor."


def dictar(texto="", continuo=False):
    """Escribe donde esté el cursor. Con continuo=True entra en modo DICTADO: todo lo que Marco
    diga se va escribiendo tal cual hasta que diga 'fin del dictado'."""
    if continuo:
        return dictado_continuo()
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
