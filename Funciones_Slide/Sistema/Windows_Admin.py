# WINDOWS ADMIN: las funciones de Windows que de verdad aligeran la vida, por voz.
#
# Cosas que uno normalmente hace hurgando en menús: arreglar el internet, liberar espacio, ver qué
# consume la PC, cambiar el plan de energía para jugar, reiniciar la barra de tareas colgada, saber
# la clave del wifi, mantener la PC despierta durante una descarga... Todo aquí, en una frase.
#
# Cada función devuelve un texto en español (accion hecha o el DATO pedido). Se apoyan en comandos
# nativos (powershell/netsh/powercfg/ipconfig) + psutil/ctypes; nada que instalar. Las que necesitan
# permisos de administrador lo intentan y, si Windows no deja, lo dicen con honestidad.

import ctypes
import subprocess
import threading
import time


def _ps(cmd, timeout=25):
    # Corre un comando de PowerShell y devuelve (salida, ok).
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (r.stdout or r.stderr or "").strip(), r.returncode == 0
    except Exception as e:
        return f"error: {e}", False


def _run(args):
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _cmd(args, timeout=20):
    # Lo que devuelve esto acaba, en varias funciones, dentro de la frase que AIDEN DICE. Un
    # "error: WinError 2" en mitad de una respuesta hablada no le dice nada a nadie; se traduce a
    # algo que se entienda al oírlo.
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (r.stdout or r.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return "el comando de Windows tardó demasiado y lo corté"
    except FileNotFoundError:
        return "esa utilidad de Windows no está disponible en este equipo"
    except Exception:
        return "Windows no me dejó ejecutar eso"


# ── RED / CONECTIVIDAD ────────────────────────────────────────────────────────
def arreglar_internet():
    # El "apaga y prende" del internet: renueva IP + limpia DNS. Cura la mayoría de caídas.
    _cmd(["ipconfig", "/release"], timeout=15)
    _cmd(["ipconfig", "/renew"], timeout=25)
    _cmd(["ipconfig", "/flushdns"], timeout=10)
    return "Listo, señor: renové la conexión y limpié el DNS. Debería andar de nuevo."


def limpiar_dns():
    _cmd(["ipconfig", "/flushdns"], timeout=10)
    return "DNS limpiado, señor."


def mi_ip():
    salida = _cmd(["powershell", "-NoProfile", "-Command",
                   "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "
                   "'127.*' -and $_.IPAddress -notlike '169.*'} | Select-Object -First 1 "
                   "-ExpandProperty IPAddress)"])
    ip = (salida.splitlines()[0].strip() if salida and "error" not in salida else "")
    return f"Su IP local es {ip}, señor." if ip else "No pude leer la IP, señor."


def clave_wifi():
    # Muestra la contraseña de la red WiFi a la que está conectado (de los perfiles guardados).
    info = _cmd(["netsh", "wlan", "show", "interfaces"])
    ssid = ""
    for ln in info.splitlines():
        s = ln.strip()
        if s.lower().startswith("ssid") and "bssid" not in s.lower():
            ssid = s.split(":", 1)[-1].strip()
            break
    if not ssid:
        return "No parece haber una red WiFi conectada, señor."
    perfil = _cmd(["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"])
    for ln in perfil.splitlines():
        s = ln.strip().lower()
        if "key content" in s or "contenido de la clave" in s:
            clave = ln.split(":", 1)[-1].strip()
            return f"La clave de '{ssid}' es: {clave}, señor."
    return f"Está en '{ssid}', pero no encontré la clave guardada, señor."


def desconectar_wifi():
    _cmd(["netsh", "wlan", "disconnect"], timeout=10)
    return "WiFi desconectado, señor."


def reconectar_wifi():
    perfiles = _cmd(["netsh", "wlan", "show", "profiles"])
    nombre = ""
    for ln in perfiles.splitlines():
        if ":" in ln and ("todos los usuarios" in ln.lower() or "all user" in ln.lower()):
            nombre = ln.split(":", 1)[-1].strip()
            break
    if not nombre:
        return "No tengo un perfil WiFi guardado para reconectar, señor."
    _cmd(["netsh", "wlan", "connect", f"name={nombre}"], timeout=12)
    return f"Reconectando a '{nombre}', señor."


# ── ENERGÍA / RENDIMIENTO ─────────────────────────────────────────────────────
def plan_energia(modo="alto"):
    # SCHEME_MIN = máximo rendimiento; SCHEME_BALANCED = equilibrado.
    if str(modo).lower().startswith(("alto", "max", "rend", "gam")):
        _cmd(["powercfg", "/setactive", "SCHEME_MIN"])
        return "Plan de energía en MÁXIMO RENDIMIENTO, señor. A todo gas."
    _cmd(["powercfg", "/setactive", "SCHEME_BALANCED"])
    return "Plan de energía EQUILIBRADO, señor."


_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM = 0x00000001
_ES_DISPLAY = 0x00000002
_despierto = {"on": False}


def _keeper():
    while _despierto["on"]:
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                _ES_CONTINUOUS | _ES_SYSTEM | _ES_DISPLAY)
        except Exception:
            pass
        time.sleep(50)
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)  # libera
    except Exception:
        pass


def mantener_despierto(activar=True):
    if activar:
        if _despierto["on"]:
            return "Ya la tengo despierta, señor."
        _despierto["on"] = True
        threading.Thread(target=_keeper, daemon=True).start()
        return "Mantendré la PC despierta, señor: nada de suspensión ni pantalla apagada."
    _despierto["on"] = False
    return "Dejo que la PC descanse cuando toque, señor."


def hibernar():
    if not _run(["shutdown", "/h"]):
        return "No pude hibernar, señor (quizá la hibernación está desactivada)."
    return "Hibernando, señor."


# ── MANTENIMIENTO ─────────────────────────────────────────────────────────────
def limpiar_temporales():
    cmd = ("$t=@($env:TEMP,'C:\\Windows\\Temp'); $n=0; foreach($d in $t){Get-ChildItem $d -Recurse "
           "-Force -ErrorAction SilentlyContinue | ForEach-Object { try{ Remove-Item $_.FullName "
           "-Recurse -Force -ErrorAction Stop; $n++ }catch{} }}; $n")
    salida, _ = _ps(cmd, timeout=60)
    n = salida.splitlines()[-1].strip() if salida else "?"
    return f"Temporales limpiados, señor: eliminé {n} elementos y liberé espacio."


def reiniciar_explorador():
    # Arregla la barra de tareas / el escritorio colgados. explorer.exe se reinicia solo.
    _run(["powershell", "-NoProfile", "-Command",
          "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue"])
    return "Reinicié el explorador, señor. La barra de tareas debería revivir."


def espacio_disco():
    salida, _ = _ps("$d=Get-PSDrive C; '{0} {1}' -f [math]::Round($d.Free/1GB,1),"
                    "[math]::Round(($d.Used+$d.Free)/1GB,1)")
    try:
        libre, total = salida.split()
        return f"Le quedan {libre} GB libres de {total} GB en el disco C, señor."
    except Exception:
        return "No pude leer el espacio en disco, señor."


def procesos_top():
    salida, _ = _ps("Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 5 "
                    "@{n='n';e={$_.ProcessName}},@{n='m';e={[math]::Round($_.WorkingSet/1MB)}} | "
                    "ForEach-Object { '{0} {1}MB' -f $_.n,$_.m }")
    if not salida or "error" in salida:
        return "No pude ver los procesos, señor."
    top = "; ".join(salida.splitlines()[:5])
    return f"Lo que más memoria consume ahora, señor: {top}."


def matar_proceso(nombre):
    """HERRAMIENTA: cierra a la fuerza un programa por nombre. 'cierra Chrome a la fuerza', 'mata X'."""
    nombre = str(nombre or "").strip().replace(".exe", "")
    if not nombre:
        return "¿Qué proceso cierro, señor?"
    salida, ok = _ps(f"$p=Get-Process -Name '{nombre}' -ErrorAction SilentlyContinue; if($p){{"
                     f"$p | Stop-Process -Force; 'ok'}}else{{'nada'}}")
    if "ok" in salida:
        return f"Cerré {nombre} a la fuerza, señor."
    return f"No encontré ningún proceso '{nombre}' abierto, señor."


# ── APARIENCIA / SESIÓN ───────────────────────────────────────────────────────
def modo_oscuro(activar=True):
    v = 0 if activar else 1
    _ps(f"$k='HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'; "
        f"Set-ItemProperty -Path $k -Name AppsUseLightTheme -Value {v}; "
        f"Set-ItemProperty -Path $k -Name SystemUsesLightTheme -Value {v}")
    return ("Modo oscuro activado, señor." if activar else "Modo claro activado, señor.")


def mostrar_ocultos(activar=True):
    v = 1 if activar else 2
    _ps(f"Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\"
        f"Advanced' -Name Hidden -Value {v}")
    _run(["powershell", "-NoProfile", "-Command",
          "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue"])
    return ("Muestro los archivos ocultos, señor." if activar
            else "Oculto de nuevo los archivos del sistema, señor.")


def cerrar_sesion():
    _run(["shutdown", "/l"])
    return "Cerrando su sesión, señor."


# ── INFO / CONSULTAS ──────────────────────────────────────────────────────────
def specs_pc():
    salida, _ = _ps(
        "$c=Get-CimInstance Win32_Processor; $r=[math]::Round((Get-CimInstance "
        "Win32_ComputerSystem).TotalPhysicalMemory/1GB); $g=(Get-CimInstance Win32_VideoController | "
        "Select-Object -First 1 -ExpandProperty Name); '{0}|{1}|{2}' -f $c.Name.Trim(),$r,$g")
    try:
        cpu, ram, gpu = salida.split("|")
        return f"Su equipo, señor: {cpu}, {ram} GB de RAM, gráfica {gpu}."
    except Exception:
        return "No pude leer las specs, señor."


def estado_bateria():
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is None:
            return "Este equipo no reporta batería, señor (o es de escritorio)."
        estado = "cargando" if b.power_plugged else "con batería"
        cola = ""
        if not b.power_plugged and b.secsleft and b.secsleft > 0:
            cola = f", le quedan unas {b.secsleft // 3600}h {b.secsleft % 3600 // 60}m"
        return f"Batería al {int(b.percent)}%, {estado}{cola}, señor."
    except Exception:
        return "No pude leer la batería, señor."


def tiempo_encendido():
    try:
        import psutil
        seg = int(time.time() - psutil.boot_time())
        h, m = seg // 3600, (seg % 3600) // 60
        return f"La PC lleva encendida {h} horas y {m} minutos, señor."
    except Exception:
        return "No pude calcular el tiempo encendido, señor."


# ── VOLUMEN / BRILLO EXACTOS ──────────────────────────────────────────────────
def brillo_exacto(nivel):
    """HERRAMIENTA: pone el brillo de la pantalla en un porcentaje exacto (0-100)."""
    try:
        n = max(0, min(100, int(float(nivel))))
    except (ValueError, TypeError):
        return "Dígame un número de 0 a 100 para el brillo, señor."
    _ps(f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods)."
        f"WmiSetBrightness(1,{n})")
    return f"Brillo al {n}%, señor."


def volumen_exacto(nivel):
    """HERRAMIENTA: pone el volumen del sistema en un porcentaje aproximado (0-100)."""
    try:
        n = max(0, min(100, int(float(nivel))))
    except (ValueError, TypeError):
        return "Dígame un número de 0 a 100 para el volumen, señor."
    # Sin librerías extra: baja a 0 y sube en pasos (~2% cada uno) hasta el objetivo.
    pasos = round(n / 2)
    cmd = ("$w=New-Object -ComObject WScript.Shell; 1..50|%{$w.SendKeys([char]174)}; "
           f"1..{pasos}|%{{$w.SendKeys([char]175)}}")
    _run(["powershell", "-NoProfile", "-Command", cmd])
    return f"Volumen al {n}%, señor."


# ── VENTANAS / ESCRITORIOS VIRTUALES (teclas del sistema, fiables sin foco) ────
_KEYUP = 0x0002
_VK = {"win": 0x5B, "ctrl": 0x11, "alt": 0x12, "shift": 0x10,
       "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "d": 0x44, "f4": 0x73, "tab": 0x09}


def _combo(*teclas):
    # Presiona una combinación (mantiene modificadores, pulsa la última, suelta al revés).
    vks = [_VK[t] for t in teclas]
    try:
        for v in vks:
            ctypes.windll.user32.keybd_event(v, 0, 0, 0)
        time.sleep(0.04)
        for v in reversed(vks):
            ctypes.windll.user32.keybd_event(v, 0, _KEYUP, 0)
        return True
    except Exception:
        return False


def escritorio_nav(accion="siguiente"):
    a = str(accion).lower()
    if "nuev" in a:
        _combo("win", "ctrl", "d"); return "Nuevo escritorio, señor."
    if "cierr" in a or "cerr" in a:
        _combo("win", "ctrl", "f4"); return "Escritorio cerrado, señor."
    if "anter" in a or "izq" in a:
        _combo("win", "ctrl", "left"); return "Escritorio anterior, señor."
    _combo("win", "ctrl", "right"); return "Siguiente escritorio, señor."


def acomodar_ventana(lado="izquierda"):
    l = str(lado).lower()
    if "max" in l or "arr" in l:
        _combo("win", "up"); return "Ventana maximizada, señor."
    if "der" in l:
        _combo("win", "right"); return "Ventana a la derecha, señor."
    _combo("win", "left"); return "Ventana a la izquierda, señor."


def captura_region():
    # Abre el recorte de región de Windows (Win+Shift+S) para seleccionar un área.
    _run(["explorer.exe", "ms-screenclip:"])
    return "Seleccione el área a recortar, señor."


# ── RED / DIAGNÓSTICO ─────────────────────────────────────────────────────────
def probar_internet():
    salida = _cmd(["ping", "-n", "4", "8.8.8.8"], timeout=15)
    import re
    perdida = re.search(r"\((\d+)%", salida)
    prom = re.findall(r"(\d+)ms", salida)
    if not prom and "error" not in salida:
        # a veces el promedio viene como "Media = Xms" al final
        prom = re.findall(r"=\s*(\d+)\s*ms", salida)
    if perdida and perdida.group(1) == "100":
        return "Sin respuesta de internet, señor: 100% de paquetes perdidos. Revise la conexión."
    if prom:
        media = round(sum(int(x) for x in prom) / len(prom))
        p = f", {perdida.group(1)}% de pérdida" if perdida and perdida.group(1) != "0" else ""
        calidad = "excelente" if media < 40 else "aceptable" if media < 120 else "lenta"
        return f"Internet {calidad}, señor: {media} ms de latencia{p}."
    return "No pude medir el internet, señor."


def ip_publica():
    try:
        import requests
        ip = requests.get("https://api.ipify.org", timeout=8).text.strip()
        return f"Su IP pública es {ip}, señor."
    except Exception:
        return "No pude consultar la IP pública, señor (¿sin internet?)."


def version_windows():
    salida, _ = _ps("$o=Get-CimInstance Win32_OperatingSystem; '{0}|{1}' -f $o.Caption.Trim(),"
                    "$o.Version")
    try:
        nombre, ver = salida.split("|")
        return f"{nombre} (versión {ver}), señor."
    except Exception:
        return "No pude leer la versión de Windows, señor."


def temperatura_gpu():
    salida = _cmd(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
                   "--format=csv,noheader,nounits"], timeout=10)
    try:
        temp, uso = [x.strip() for x in salida.splitlines()[0].split(",")]
        return f"La GPU está a {temp}°C, al {uso}% de uso, señor."
    except Exception:
        return "No pude leer la temperatura de la GPU, señor."


def archivos_grandes():
    cmd = ("Get-ChildItem $HOME\\Downloads,$HOME\\Desktop,$HOME\\Documents,$HOME\\Videos -Recurse "
           "-File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object "
           "-First 6 | ForEach-Object { '{0} {1}MB' -f $_.Name,[math]::Round($_.Length/1MB) }")
    salida, _ = _ps(cmd, timeout=40)
    if not salida or "error" in salida:
        return "No encontré archivos grandes, señor."
    return "Los archivos más pesados, señor: " + "; ".join(salida.splitlines()[:6]) + "."


# ── LAUNCHERS DE UTILIDADES ───────────────────────────────────────────────────
def abrir_utilidad(cual="panel"):
    c = str(cual).lower()
    if "dispositiv" in c:
        _run(["devmgmt.msc"]); return "Administrador de dispositivos abierto, señor."
    if "servici" in c:
        _run(["services.msc"]); return "Servicios abiertos, señor."
    if "sonido" in c or "audio" in c:
        _run(["explorer.exe", "ms-settings:sound"]); return "Configuración de sonido abierta, señor."
    if "red" in c:
        _run(["explorer.exe", "ms-settings:network"]); return "Configuración de red abierta, señor."
    if "disco" in c or "almacen" in c:
        _run(["explorer.exe", "ms-settings:storagesense"]); return "Almacenamiento abierto, señor."
    _run(["control.exe"]); return "Panel de control abierto, señor."


# ── PORTAPAPELES INTELIGENTE ──────────────────────────────────────────────────
def _clip():
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()
    except Exception:
        return ""


def leer_copiado():
    t = _clip()
    if not t:
        return "No hay nada copiado, señor."
    return t[:600]


def _llm_sobre_clip(instruccion, max_tokens=400):
    t = _clip()
    if not t:
        return "No hay nada copiado, señor."
    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO
        r = client.chat.completions.create(
            model=MODELO_LIGERO,
            messages=[{"role": "user", "content": instruccion + "\n\nTEXTO:\n" + t[:4000]}],
            temperature=0.2, max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip() or "No obtuve resultado, señor."
    except Exception as e:
        return f"No pude procesarlo, señor: {e}"


def traducir_copiado():
    return _llm_sobre_clip(
        "Traduce este texto al español (si ya está en español, tradúcelo al inglés). Responde SOLO "
        "la traducción, sin comentarios.")


def resumir_copiado():
    return _llm_sobre_clip(
        "Resume este texto en 2-3 frases claras, en español, para leérselo a Marco. Solo el resumen.")
