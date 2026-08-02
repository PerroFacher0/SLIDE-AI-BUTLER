# PUENTE DE HARDWARE PERIFÉRICO: lo que está ENCHUFADO a la PC, no dentro de ella.
#
# Tres huecos que se sentían tontos teniendo un mayordomo con acceso de administrador:
#   1. "Pasa el sonido a los audífonos" -> había que ir al icono del volumen a mano.
#   2. "¿Cuánta batería le queda al mouse?" -> no había forma de saberlo.
#   3. El brillo solo funcionaba en la pantalla del portátil: `WmiMonitorBrightnessMethods` NO toca
#      los monitores externos. Para esos hay que hablar DDC/CI, que es el protocolo por el que el
#      monitor obedece por el propio cable de video.
#
# Sobre cambiar el dispositivo de audio: Windows no expone una API pública para ello. La vía real es
# IPolicyConfig, una interfaz COM interna que es justo lo que usan por dentro nircmd y
# AudioDeviceCmdlets. Se usa directamente por comtypes (que ya es dependencia del proyecto, vía
# uiautomation) para no obligar a instalar nada; si esa vía falla, se intenta AudioDeviceCmdlets, y
# si tampoco está, se abre el panel de sonido y se dice con todas las letras qué pasó.

import re
import subprocess


def _ps(comando, timeout=20):
    """Corre PowerShell y devuelve su salida limpia ('' si algo falla)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
                           capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _norm(t):
    # str(): 'nivel' puede llegar como número (75) o como texto ('subir'); el modelo manda
    # cualquiera de los dos y un int no tiene .strip().
    return str(t if t is not None else "").strip().lower().translate(
        str.maketrans("áéíóúü", "aeiouu"))


# ── Salidas de audio ──────────────────────────────────────────────────────────
def _listar_salidas():
    """[(nombre, id_mmdevice)] de las salidas de audio activas."""
    salida = _ps(
        "Get-PnpDevice -Class AudioEndpoint -Status OK -ErrorAction SilentlyContinue | "
        "ForEach-Object { $_.FriendlyName + '||' + $_.InstanceId }"
    )
    disp = []
    for linea in salida.splitlines():
        if "||" not in linea:
            continue
        nombre, instancia = linea.split("||", 1)
        # SWD\MMDEVAPI\{0.0.0.00000000}.{guid}  ->  {0.0.0.00000000}.{guid}
        # El dígito del medio dice el sentido: 0 = SALIDA (parlantes/audífonos), 1 = ENTRADA
        # (micrófonos). Solo interesan las salidas: "pasa el sonido a X" no debe ofrecer un
        # micrófono, y fijarlo como salida por defecto no tendría ningún sentido.
        m = re.search(r"(\{0\.0\.0\.00000000\}\.\{[0-9a-fA-F-]+\})", instancia)
        if m:
            disp.append((nombre.strip(), m.group(1)))
    return disp


def _fijar_por_comtypes(id_dispositivo):
    """Cambia la salida por defecto vía IPolicyConfig (sin instalar nada)."""
    try:
        import ctypes
        from ctypes.wintypes import LPCWSTR
        from comtypes import GUID, COMMETHOD, HRESULT, IUnknown, CoCreateInstance

        class IPolicyConfig(IUnknown):
            _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
            # Las 10 primeras ranuras solo se declaran para que SetDefaultEndpoint caiga en su
            # posición correcta de la tabla virtual; no se llaman nunca.
            _methods_ = [
                COMMETHOD([], HRESULT, "GetMixFormat"),
                COMMETHOD([], HRESULT, "GetDeviceFormat"),
                COMMETHOD([], HRESULT, "ResetDeviceFormat"),
                COMMETHOD([], HRESULT, "SetDeviceFormat"),
                COMMETHOD([], HRESULT, "GetProcessingPeriod"),
                COMMETHOD([], HRESULT, "SetProcessingPeriod"),
                COMMETHOD([], HRESULT, "GetShareMode"),
                COMMETHOD([], HRESULT, "SetShareMode"),
                COMMETHOD([], HRESULT, "GetPropertyValue"),
                COMMETHOD([], HRESULT, "SetPropertyValue"),
                COMMETHOD([], HRESULT, "SetDefaultEndpoint",
                          (["in"], LPCWSTR, "wszDeviceId"), (["in"], ctypes.c_int, "eRole")),
                COMMETHOD([], HRESULT, "SetEndpointVisibility"),
            ]

        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        cfg = CoCreateInstance(GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}"),
                               interface=IPolicyConfig)
        # Los tres roles: multimedia, consola y comunicaciones (si no, las llamadas siguen igual).
        for rol in (0, 1, 2):
            cfg.SetDefaultEndpoint(id_dispositivo, rol)
        return True
    except Exception:
        return False


def _fijar_por_modulo(nombre):
    """Respaldo: el módulo AudioDeviceCmdlets, si Marco lo tiene instalado."""
    salida = _ps(
        "if (Get-Module -ListAvailable -Name AudioDeviceCmdlets) {"
        " Import-Module AudioDeviceCmdlets;"
        f" $d = Get-AudioDevice -List | Where-Object {{ $_.Name -like '*{nombre}*' }} |"
        "  Select-Object -First 1;"
        " if ($d) { Set-AudioDevice -ID $d.ID; 'OK' } else { 'NODEV' }"
        "} else { 'NOMOD' }", timeout=30)
    return "OK" in salida


def audio(accion="listar", dispositivo=""):
    """HERRAMIENTA: controla POR DÓNDE suena el PC (parlantes, audífonos Bluetooth, monitor).
      accion = listar | cambiar
      dispositivo = parte del nombre de la salida (ej. 'sony', 'audifonos', 'parlantes')."""
    a = _norm(accion)
    disponibles = _listar_salidas()

    if a.startswith("list") or not dispositivo:
        if not disponibles:
            return "No pude leer las salidas de audio, señor."
        return "Salidas de audio disponibles, señor: " + "; ".join(n for n, _ in disponibles)

    buscado = _norm(dispositivo)
    elegido = next((par for par in disponibles if buscado in _norm(par[0])), None)
    if elegido is None:
        if not disponibles:
            return "No pude leer las salidas de audio, señor."
        return (f"No encontré una salida que se llame «{dispositivo}», señor. Tengo: "
                + "; ".join(n for n, _ in disponibles))

    nombre, ident = elegido
    if _fijar_por_comtypes(ident):
        return f"Sonido en {nombre}, señor."
    if _fijar_por_modulo(nombre):
        return f"Sonido en {nombre}, señor."
    _ps("Start-Process ms-settings:sound")
    return (f"No pude cambiarlo solo, señor: le abrí la configuración de sonido para que elija "
            f"{nombre} a mano. Si quiere que lo haga yo la próxima vez, instale el módulo con: "
            "Install-Module -Name AudioDeviceCmdlets -Scope CurrentUser")


# ── Batería de mouse / teclado / audífonos ───────────────────────────────────
def bateria_perifericos():
    """HERRAMIENTA: batería del mouse, teclado, audífonos y demás periféricos inalámbricos."""
    salida = _ps(
        "$k='{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2';"
        "Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | ForEach-Object {"
        " $p = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $k -ErrorAction SilentlyContinue;"
        " if ($p -and $p.Data -ne $null) { $_.FriendlyName + '||' + $p.Data } }", timeout=45)
    lecturas = []
    for linea in salida.splitlines():
        if "||" in linea:
            nombre, nivel = linea.split("||", 1)
            nombre, nivel = nombre.strip(), nivel.strip()
            if nombre and nivel.isdigit():
                lecturas.append((nombre, int(nivel)))
    if not lecturas:
        return ("Ninguno de sus periféricos reporta batería, señor. Solo los inalámbricos modernos "
                "(Bluetooth LE) la publican; los de dongle propio suelen no hacerlo.")
    partes = [f"{n}: {p}%" for n, p in sorted(lecturas, key=lambda x: x[1])]
    aviso = ""
    bajos = [n for n, p in lecturas if p <= 20]
    if bajos:
        aviso = f" Ojo con {', '.join(bajos)}, va bajo."
    return "Batería de periféricos, señor: " + "; ".join(partes) + aviso


# ── Brillo REAL, también en monitores externos (DDC/CI) ──────────────────────
def volumen_de_app(app, nivel):
    """Sube o baja el volumen de UNA aplicación, sin tocar el del resto.

    Windows lleva un mezclador por aplicación, pero no lo expone por teclado: control_volumen mueve
    el volumen MAESTRO, así que "bájale a Spotify" bajaba todo, incluida la propia voz de AIDEN.
    Esto habla con las sesiones de audio directamente."""
    try:
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        from comtypes import CoInitialize
    except Exception:
        return ("No tengo el control del mezclador de Windows, señor. Se activa con: "
                "pip install pycaw")
    buscado = _norm(app).removesuffix(".exe")
    if not buscado:
        return "¿A qué aplicación le cambio el volumen, señor?"
    try:
        n = max(0, min(100, int(float(nivel))))
    except (TypeError, ValueError):
        return "Dígame un número de 0 a 100, señor."

    try:
        CoInitialize()
    except Exception:
        pass
    try:
        sesiones = AudioUtilities.GetAllSessions()
    except Exception as e:
        return f"No pude leer el mezclador de Windows, señor: {e}"

    tocadas, sonando = [], []
    for s in sesiones:
        if not s.Process:
            continue
        try:
            nombre = s.Process.name()
        except Exception:
            continue
        sonando.append(nombre)
        if buscado in _norm(nombre).removesuffix(".exe"):
            try:
                s._ctl.QueryInterface(ISimpleAudioVolume).SetMasterVolume(n / 100.0, None)
                tocadas.append(nombre)
            except Exception:
                continue
    if tocadas:
        return f"{'Bajé' if n < 50 else 'Puse'} el volumen de {tocadas[0]} al {n}%, señor."
    if sonando:
        return (f"No encontré a «{app}» sonando ahora mismo, señor. Están sonando: "
                + ", ".join(sorted(set(sonando))[:6]))
    return "Ahora mismo no hay ninguna aplicación reproduciendo audio, señor."


def perifericos(accion="bateria", objetivo="", nivel=None):
    """HERRAMIENTA ÚNICA del hardware conectado.
      accion='brillo'  -> brillo de CUALQUIER monitor (nivel: 0-100, 'subir' o 'bajar')
      accion='audio'   -> por dónde suena el PC (objetivo vacío = listar salidas)
      accion='volumen_app' -> volumen de UNA app (objetivo=nombre, nivel=0-100)
      accion='bateria' -> batería de mouse/teclado/audífonos inalámbricos

    El brillo llegó a tener TRES caminos: 'ajustar_brillo' (relativo, monitor principal),
    'brillo_exacto' (WMI, que solo mueve el panel del portátil y ni se entera de un monitor
    externo) y esta. Tres formas de hacer lo mismo obligan al modelo a adivinar cuál, y una de
    ellas simplemente no funcionaba en la pantalla grande. Ahora es este único camino, que habla
    DDC/CI y por tanto sirve igual para el portátil y para los externos."""
    a = _norm(accion)
    # Antes que 'audio': "volumen_app" contiene... nada de audio, pero sí conviene mirarlo primero
    # por si el modelo escribe "audio_app" o "volumen de app".
    if "volumen" in a or "_app" in a or "mezclador" in a:
        return volumen_de_app(objetivo, nivel)
    if a.startswith("audio") or "sonid" in a or "altavo" in a or "audifon" in a:
        return audio("cambiar" if objetivo else "listar", objetivo)
    if a.startswith("bril") or "monitor" in a or "pantalla" in a or "luz" in a:
        return monitores(nivel, objetivo)
    return bateria_perifericos()


def monitores(nivel=None, cual=""):
    """HERRAMIENTA: brillo de CADA monitor, incluidos los externos por DDC/CI (el protocolo por el
    que el monitor obedece por el cable de video). Sin 'nivel', reporta cómo están.
      nivel = 0-100 para fijarlo; cual = parte del nombre del monitor (vacío = todos)."""
    try:
        import screen_brightness_control as sbc
    except Exception:
        return ("No tengo el control de brillo por cable instalado, señor. Se activa con: "
                "pip install screen-brightness-control")

    try:
        pantallas = sbc.list_monitors()
    except Exception as e:
        return f"No pude enumerar sus monitores, señor: {e}"
    if not pantallas:
        return "No detecté monitores que acepten control de brillo, señor."

    objetivo = _norm(cual)
    elegidas = [p for p in pantallas if objetivo in _norm(p)] if objetivo else pantallas
    if not elegidas:
        return (f"No encontré un monitor «{cual}», señor. Tengo: " + ", ".join(pantallas))

    def _leer(p):
        try:
            v = sbc.get_brightness(display=p)
            return int(v[0] if isinstance(v, list) else v)
        except Exception:
            return None

    if nivel is None or str(nivel).strip() == "":
        lecturas = [f"{p}: {v}%" if (v := _leer(p)) is not None else f"{p}: no reporta"
                    for p in elegidas]
        return "Brillo de sus monitores, señor: " + "; ".join(lecturas)

    # 'nivel' acepta un número o un empujón relativo ("sube el brillo" no trae número).
    texto = _norm(nivel)
    relativo = 0
    if texto in ("subir", "sube", "mas", "arriba", "aumenta"):
        relativo = +20
    elif texto in ("bajar", "baja", "menos", "abajo", "reduce"):
        relativo = -20

    if relativo:
        actual = next((v for p in elegidas if (v := _leer(p)) is not None), None)
        if actual is None:
            return "Sus monitores no me dicen en cuánto está el brillo, señor; dígame un número."
        n = max(0, min(100, actual + relativo))
    else:
        try:
            n = max(0, min(100, int(float(nivel))))
        except (TypeError, ValueError):
            return "Dígame un número de 0 a 100 (o 'subir'/'bajar') para el brillo, señor."

    hechos, fallidos = [], []
    for p in elegidas:
        try:
            sbc.set_brightness(n, display=p)
            hechos.append(p)
        except Exception:
            fallidos.append(p)
    if not hechos:
        return f"No pude cambiarle el brillo a {', '.join(fallidos)}, señor (no acepta DDC/CI)."
    cola = f" ({', '.join(fallidos)} no obedece)" if fallidos else ""
    return f"Brillo al {n}% en {', '.join(hechos)}, señor.{cola}"
