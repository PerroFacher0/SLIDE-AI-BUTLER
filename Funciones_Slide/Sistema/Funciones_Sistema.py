import time

import psutil
import requests
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


#funciones previas necesarias para las modificaciones

def obtener_control_audio():
    
    enumerador = AudioUtilities.GetDeviceEnumerator()

    dispositivo = enumerador.GetDefaultAudioEndpoint(0, 0)
    

    interfaz = dispositivo.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    
    return cast(interfaz, POINTER(IAudioEndpointVolume))

def modificar_volumen(delta):
    
    control = obtener_control_audio()
    
    volumen_actual = control.GetMasterVolumeLevelScalar()
    
    
    nuevo_volumen = max(0.0, min(1.0, volumen_actual + delta))
    
    
    control.SetMasterVolumeLevelScalar(nuevo_volumen, None)
    print(f"Volumen ajustado a: {int(nuevo_volumen * 100)}%")


# ── VOLUMEN ──────────────────────────────────────────────────────────────────
def subir_volumen(Cantidad):
    modificar_volumen(Cantidad)
    return "Volumen arriba, señor"

def bajar_volumen(Cantidad):
    modificar_volumen(-Cantidad)
    return "Volumen abajo, señor"

def poner_volumen(nivel):
    try:
        nivel = max(0, min(100, int(float(nivel))))
    except (ValueError, TypeError):
        return "Dame un número de 0 a 100, señor."
    control = obtener_control_audio()
    control.SetMasterVolumeLevelScalar(nivel / 100.0, None)
    return f"Volumen al {nivel}%, señor."

def silenciar():
    control = obtener_control_audio()
    control.SetMute(True,None)
    return "Sistema silenciado correctamente"

def desilenciar():
    control = obtener_control_audio()
    control.SetMute(False,None)
    return "Sonido desilenciado"

def control_volumen(accion, nivel=None):
    # Una sola herramienta para todo el volumen: subir, bajar, silenciar,
    # desilenciar o poner un nivel exacto (0-100).
    a = str(accion).strip().lower()
    if a in ("silenciar", "mutear", "mute"):
        return silenciar()
    if a in ("desilenciar", "activar", "unmute", "quitar silencio"):
        return desilenciar()
    if nivel is not None:
        return poner_volumen(nivel)
    if a.isdigit():
        return poner_volumen(a)
    if a in ("subir", "sube", "mas", "más", "arriba"):
        return subir_volumen(0.1)
    if a in ("bajar", "baja", "menos", "abajo"):
        return bajar_volumen(0.1)
    return "No entendí qué hacer con el volumen, señor."


# ── PROCESOS ─────────────────────────────────────────────────────────────────
def cerrar_aplicacion(nombre_app, forzar=False):
   """Cierra un programa por nombre. Con forzar=True no le pide permiso: lo mata (para lo que ya
   está colgado y no responde).

   Antes esto vivía partido en dos herramientas — 'cerrar_aplicacion' y 'matar_proceso' — que decían
   casi lo mismo y competían por la misma petición. Es la MISMA intención con distinta contundencia,
   así que ahora es un parámetro, no otra herramienta."""
   nombre = str(nombre_app or "").strip()
   if not nombre:
       return "¿Qué aplicación cierro, señor?"
   # Tolerante con el .exe: Marco dice "chrome", el proceso se llama "chrome.exe".
   buscado = nombre.lower().removesuffix(".exe")
   tocados = []

   for proceso in psutil.process_iter(['name']):
       try:
           actual = (proceso.info['name'] or "").lower().removesuffix(".exe")
           if actual == buscado:
               proceso.kill() if forzar else proceso.terminate()
               tocados.append(proceso.pid)
       except (psutil.NoSuchProcess, psutil.AccessDenied):
           continue   # ese proceso no se dejo, seguimos buscando el nuestro

   if not tocados:
       return f"No encontré {nombre} abierto, señor"
   if forzar:
       return f"Cerré {nombre} a la fuerza, señor"

   # COMPROBAR QUE DE VERDAD CERRÓ. terminate() solo PIDE a la aplicación que se cierre; si tiene
   # un documento sin guardar, Word o Excel abren un "¿Desea guardar los cambios?" y se quedan ahí
   # esperando una respuesta que nadie va a dar. Antes AIDEN decía "Cerré Word, señor" y Word
   # seguía abierto: peor que fallar, porque Marco se queda con una idea falsa de lo que pasó.
   time.sleep(1.2)
   vivos = [p for p in tocados if psutil.pid_exists(p)]
   if not vivos:
       return f"Cerré {nombre}, señor"
   return (f"{nombre} no se cerró del todo, señor: {len(vivos)} proceso(s) siguen abiertos, "
           "probablemente esperando a que alguien conteste si guarda los cambios. Dígame si lo "
           "fuerzo (y se pierde lo que no esté guardado) o prefiere revisarlo usted.")


def ver_apps_abiertas():
    # Usa los TITULOS de las ventanas abiertas (apps reales que ve el usuario),
    # no los procesos de fondo del sistema (que no le sirven a Marco).
    try:
        import pygetwindow as gw
        titulos = []
        for t in gw.getAllTitles():
            t = (t or "").strip()
            if t and t not in titulos:
                titulos.append(t)
        if not titulos:
            return "No detecté ventanas de aplicaciones abiertas, señor."
        return "Ventanas/aplicaciones abiertas: " + ", ".join(titulos[:20])
    except Exception as e:
        return f"No pude listar las aplicaciones, señor: {e}"


# ── CLIMA ─────────────────────────────────────────────────────────────────────
def obtener_clima(ciudad):
    try:

        url =  f"https://wttr.in/{ciudad}?format=3"
        respuesta = requests.get(url)

        if respuesta.status_code == 200:
            return f"El clima actual es: {respuesta.text.strip()}"
        else:
            return f"No se pudo obtener el clima"
    except Exception as e:
        return f"Ocurrio un error al conectar: {e}"


# ── BUSQUEDA EN INTERNET (DuckDuckGo, sin API key) ────────────────────────────
def buscar_en_internet(consulta):
    # Trae los mejores resultados de la web y los DEVUELVE como texto para que
    # el LLM los lea y responda con informacion real y actual.
    from ddgs import DDGS

    try:
        with DDGS() as buscador:
            resultados = list(buscador.text(consulta, max_results=4))

        if not resultados:
            return "No encontré nada en internet sobre eso, señor."

        partes = []
        for r in resultados:
            titulo = r.get("title", "")
            cuerpo = (r.get("body", "") or "")[:180]   # recortado para no saturar
            partes.append(f"- {titulo}: {cuerpo}")

        return "Esto encontré en internet:\n" + "\n".join(partes)
    except Exception as e:
        return f"No pude buscar en internet, señor: {e}"


def buscar(consulta, abrir=False):
    """Busca en internet. Por defecto LEE los resultados y los devuelve como texto para responder
    con datos reales; con abrir=True los deja EN PANTALLA, en el navegador, para que Marco mire.

    Antes eran dos herramientas ('buscar_en_internet' y 'Buscar_en_Google') que se disputaban cada
    "busca X": comparten el 23% del vocabulario de sus descripciones. Lo que de verdad cambia entre
    ellas no es qué buscan, sino DÓNDE acaba el resultado — así que eso es lo que ahora se pide."""
    consulta = str(consulta or "").strip()
    if not consulta:
        return "¿Qué quiere que busque, señor?"
    if abrir:
        import urllib.parse
        import webbrowser
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(consulta))
        return f"Le abrí la búsqueda de «{consulta}» en el navegador, señor."
    return buscar_en_internet(consulta)


# ── PORTAPAPELES ──────────────────────────────────────────────────────────────
def leer_portapapeles():
    # Devuelve lo que Marco tiene copiado, para que el LLM lo explique/traduzca/resuma.
    try:
        import pyperclip
        texto = pyperclip.paste()
        if not texto or not texto.strip():
            return "El portapapeles está vacío, señor."
        return "Contenido del portapapeles: " + texto.strip()[:1500]
    except Exception as e:
        return f"No pude leer el portapapeles, señor: {e}"


# ── CONTROL DE MUSICA / MEDIOS ────────────────────────────────────────────────
def control_musica(accion):
    import pyautogui
    teclas = {
        "play": "playpause", "pausa": "playpause", "pausar": "playpause",
        "reanudar": "playpause", "reproducir": "playpause",
        "siguiente": "nexttrack", "adelante": "nexttrack",
        "anterior": "prevtrack", "atras": "prevtrack",
        "parar": "stop", "detener": "stop",
    }
    t = teclas.get(str(accion).strip().lower())
    if not t:
        return "No entendí qué hacer con la música, señor."
    pyautogui.press(t)
    return "Hecho, señor."


# ── ESTADO DEL SISTEMA (bateria, CPU, RAM, red) ───────────────────────────────
def estado_sistema():
    # Reporte rapido del estado del PC: bateria, CPU, RAM e IP local.
    partes = []
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            estado = "cargando" if bat.power_plugged else "con batería"
            partes.append(f"Batería al {int(bat.percent)}% ({estado})")
    except Exception:
        pass
    try:
        partes.append(f"CPU al {psutil.cpu_percent(interval=0.5):.0f}%")
    except Exception:
        pass
    try:
        mem = psutil.virtual_memory()
        partes.append(f"RAM al {mem.percent:.0f}% ({mem.used/1e9:.1f} de {mem.total/1e9:.1f} GB)")
    except Exception:
        pass
    # GPU NVIDIA: uso, VRAM y temperatura (via nvidia-smi, sin librerias extra)
    try:
        import subprocess
        _g = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if _g:
            _linea = _g.splitlines()[0]
            _u, _mu, _mt, _t = [x.strip() for x in _linea.split(",")[:4]]
            partes.append(f"GPU al {_u}% ({_mu} de {_mt} MB de VRAM, {_t}°C)")
    except Exception:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        partes.append(f"IP local {s.getsockname()[0]}")
        s.close()
    except Exception:
        partes.append("sin conexión de red detectada")
    if not partes:
        return "No pude leer el estado del sistema, señor."
    return "Estado del equipo: " + ", ".join(partes) + "."


# ── PRONOSTICO DEL CLIMA EXTENDIDO (wttr.in, varios dias) ──────────────────────
def pronostico_clima(ciudad, dias=3):
    # Pronostico de hasta 3 dias (hoy + siguientes) con maxima, minima y estado.
    try:
        dias = max(1, min(3, int(dias)))
    except (ValueError, TypeError):
        dias = 3
    try:
        url = f"https://wttr.in/{ciudad}?format=j1&lang=es"
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            return f"No pude obtener el pronóstico de {ciudad}, señor."
        data = r.json()
        lineas = [f"Pronóstico para {ciudad}:"]
        nombres = ["hoy", "mañana", "pasado mañana"]
        for i, dia in enumerate(data.get("weather", [])[:dias]):
            maxt = dia.get("maxtempC")
            mint = dia.get("mintempC")
            desc = ""
            mediodia = dia.get("hourly", [])
            if len(mediodia) >= 5:
                lang = mediodia[4].get("lang_es")
                if lang:
                    desc = lang[0].get("value", "")
            etiqueta = nombres[i] if i < len(nombres) else dia.get("date", "")
            lineas.append(f"- {etiqueta}: máx {maxt}°C, mín {mint}°C{', ' + desc if desc else ''}")
        return "\n".join(lineas)
    except Exception as e:
        return f"No pude obtener el pronóstico, señor: {e}"


# ── CLIMA UNIFICADO (actual o pronostico) ──────────────────────────────────────
def clima(ciudad, cuando=None):
    # Una sola herramienta para el clima: actual o pronostico de varios dias.
    # Si 'cuando' menciona el futuro -> pronostico; si no -> clima de ahora.
    c = str(cuando or "").strip().lower()
    futuro = any(p in c for p in (
        "pronos", "mañana", "manana", "futuro", "semana",
        "proximos", "próximos", "dias", "días", "siguiente", "despues", "después",
    ))
    if futuro:
        return pronostico_clima(ciudad)
    return obtener_clima(ciudad)



