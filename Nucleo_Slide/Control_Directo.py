# CONTROL DIRECTO: manejar TODA la PC por voz, casi instantáneo. Dos carriles:
#
#   1. ACCIONES INSTANTÁNEAS (cero LLM): las cosas mas comunes (bloquear, suspender, apagar, subir/
#      bajar volumen, silenciar, mostrar escritorio, captura, vaciar papelera, abrir explorador...)
#      se disparan al instante desde el atajo, sin pasar por el cerebro. Latencia ~0.
#
#   2. CARRIL RÁPIDO (LLM minimo): para ordenes ARBITRARIAS ("crea una carpeta Tesis en el escritorio",
#      "cierra Spotify", "renombra ese archivo") se usa un cerebro CHIQUITO: una sola llamada al modelo
#      ligero SIN el esquema de 58 herramientas (que pesa miles de tokens) y SIN todo el contexto ->
#      solo traduce la orden a UN comando de PowerShell y lo ejecuta. Mucho mas rapido que el cerebro
#      completo, y sigue pudiendo hacer literalmente cualquier cosa (con el mismo guard de seguridad).

import subprocess

_TILDES = str.maketrans("áéíóúüñ", "aeiouun")


def _p(t):
    return str(t or "").strip().lower().translate(_TILDES)


def _run_async(args):
    # Lanza y NO espera (para que la voz siga fluida).
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _sendkey(codigo, veces=1):
    # Manda una tecla multimedia (volumen/mute) via WScript.Shell. 175=subir 174=bajar 173=mute.
    cmd = f"$w=New-Object -ComObject WScript.Shell; 1..{veces}|%{{$w.SendKeys([char]{codigo})}}"
    return _run_async(["powershell", "-NoProfile", "-Command", cmd])


# ── 1. ACCIONES INSTANTÁNEAS ──────────────────────────────────────────────────
# Cada entrada: (conjunto de frases exactas normalizadas) -> id de accion.
_INSTANT = {
    "bloquear": ("bloquea", "bloquea la pc", "bloquea el equipo", "bloquear", "bloquea el computador",
                 "bloquea la pantalla"),
    "suspender": ("suspende", "suspende la pc", "suspende el equipo", "modo suspension", "suspender"),
    "apagar": ("apaga la pc", "apaga el computador", "apaga el equipo", "apaga el pc", "apagar el equipo",
               "apaga la computadora"),
    "cancelar_apagado": ("cancela el apagado", "cancela apagado", "no apagues", "aborta el apagado"),
    "reiniciar": ("reinicia la pc", "reinicia el computador", "reinicia el equipo", "reiniciar el equipo",
                  "reinicia la computadora"),
    "escritorio": ("muestra el escritorio", "minimiza todo", "minimiza las ventanas", "ver el escritorio"),
    "papelera": ("vacia la papelera", "vaciar la papelera", "limpia la papelera", "vacia la basura"),
    "explorador": ("abre el explorador", "abre archivos", "abre el explorador de archivos",
                   "abre mis archivos"),
    "captura": ("captura", "pantallazo", "toma una captura", "captura de pantalla", "haz una captura"),
    "mute": ("silencia", "mutea", "quita el sonido", "silencio", "silencia el equipo"),
    "unmute": ("activa el sonido", "quita el silencio", "vuelve el sonido", "reactiva el sonido"),
    "vol_up": ("sube el volumen", "mas volumen", "sube el sonido", "sube volumen", "sube el audio"),
    "vol_down": ("baja el volumen", "menos volumen", "baja el sonido", "baja volumen", "baja el audio"),
    "vol_max": ("volumen al maximo", "maximo volumen", "sube el volumen al maximo"),
    "brillo_up": ("sube el brillo", "mas brillo", "aumenta el brillo", "sube el brillo de la pantalla"),
    "brillo_down": ("baja el brillo", "menos brillo", "reduce el brillo", "baja el brillo de la pantalla"),
    "taskmgr": ("abre el administrador de tareas", "administrador de tareas", "abre el task manager"),
    "ajustes": ("abre la configuracion", "abre los ajustes", "abre ajustes", "abre configuracion"),
    "calc": ("abre la calculadora", "calculadora", "abre calculadora"),
    "notepad": ("abre el bloc de notas", "bloc de notas", "abre notepad", "abre el bloc"),
}


def clasificar_instantanea(p):
    # Pura: devuelve el id de accion si la frase coincide exacta, o None. (No ejecuta nada.)
    p = _p(p)
    for accion, frases in _INSTANT.items():
        if p in frases:
            return accion
    return None


def ejecutar_instantanea(accion):
    # Ejecuta la accion instantanea y devuelve una confirmacion corta.
    try:
        if accion == "bloquear":
            _run_async(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Bloqueando, señor."
        if accion == "suspender":
            _run_async(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return "Suspendiendo el equipo, señor."
        if accion == "apagar":
            _run_async(["shutdown", "/s", "/t", "25"])
            return "Apagando en 25 segundos, señor. Diga 'cancela el apagado' si se arrepiente."
        if accion == "cancelar_apagado":
            _run_async(["shutdown", "/a"])
            return "Apagado cancelado, señor."
        if accion == "reiniciar":
            _run_async(["shutdown", "/r", "/t", "25"])
            return "Reiniciando en 25 segundos, señor. Diga 'cancela el apagado' para abortar."
        if accion == "escritorio":
            _run_async(["powershell", "-NoProfile", "-Command",
                        "(New-Object -ComObject shell.application).MinimizeAll()"])
            return "Ahí tiene el escritorio, señor."
        if accion == "papelera":
            _run_async(["powershell", "-NoProfile", "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
            return "Papelera vaciada, señor."
        if accion == "explorador":
            _run_async(["explorer.exe"])
            return "Explorador abierto, señor."
        if accion == "captura":
            try:
                from Funciones_Slide.Sistema.Control_PC import tomar_captura
                return str(tomar_captura())
            except Exception:
                return "No pude tomar la captura, señor."
        if accion == "mute":
            _sendkey(173)
            return "Silenciado, señor."
        if accion == "unmute":
            _sendkey(173)   # 173 es toggle
            return "Sonido de vuelta, señor."
        if accion == "vol_up":
            _sendkey(175, 4)
            return "Subiendo el volumen, señor."
        if accion == "vol_down":
            _sendkey(174, 4)
            return "Bajando el volumen, señor."
        if accion == "vol_max":
            _sendkey(175, 50)
            return "Volumen al máximo, señor."
        if accion in ("brillo_up", "brillo_down"):
            try:
                from Funciones_Slide.Sistema.Control_PC import ajustar_brillo
                ajustar_brillo("subir" if accion == "brillo_up" else "bajar")
            except Exception:
                # respaldo directo por WMI si la herramienta no aplica
                signo = "+20" if accion == "brillo_up" else "-20"
                _run_async(["powershell", "-NoProfile", "-Command",
                            "$b=(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness)."
                            f"CurrentBrightness; $n=[Math]::Max(0,[Math]::Min(100,$b{signo})); "
                            "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods)."
                            "WmiSetBrightness(1,$n)"])
            return "Brillo arriba, señor." if accion == "brillo_up" else "Brillo abajo, señor."
        if accion == "taskmgr":
            _run_async(["taskmgr.exe"])
            return "Administrador de tareas abierto, señor."
        if accion == "ajustes":
            _run_async(["explorer.exe", "ms-settings:"])
            return "Ahí tiene la configuración, señor."
        if accion == "calc":
            _run_async(["calc.exe"])
            return "Calculadora lista, señor."
        if accion == "notepad":
            _run_async(["notepad.exe"])
            return "Bloc de notas abierto, señor."
    except Exception as e:
        return f"No pude, señor: {e}"
    return "No reconocí esa acción, señor."


# ── 1b. FUNCIONES DE WINDOWS (red / rendimiento / mantenimiento / info) ───────
# Frases exactas -> id de función de Windows_Admin. Cero LLM, valen siempre.
_ADMIN = {
    "arreglar_internet": ("arregla el internet", "arregla mi internet", "repara el internet",
                          "arregla la conexion", "se cayo el internet", "reinicia el internet"),
    "limpiar_dns": ("limpia el dns", "vacia el dns", "flush dns"),
    "mi_ip": ("cual es mi ip", "mi ip", "dame mi ip", "dime mi ip", "que ip tengo",
              "cual es mi direccion ip"),
    "clave_wifi": ("cual es la clave del wifi", "clave del wifi", "contrasena del wifi",
                   "cual es la contrasena del wifi", "dame la clave del wifi", "clave del internet"),
    "desconectar_wifi": ("desconecta el wifi", "apaga el wifi", "desactiva el wifi"),
    "reconectar_wifi": ("reconecta el wifi", "conecta el wifi", "prende el wifi", "activa el wifi"),
    "plan_alto": ("modo alto rendimiento", "maximo rendimiento", "modo rendimiento",
                  "plan de alto rendimiento", "modo gaming de energia", "energia al maximo"),
    "plan_equilibrado": ("modo equilibrado", "energia equilibrada", "plan equilibrado",
                         "modo de energia normal"),
    "despierto_on": ("mantente despierta", "no te duermas", "manten la pc despierta",
                     "no dejes que se duerma", "modo cafeina", "no dejes que se apague la pantalla"),
    "despierto_off": ("deja que se duerma", "desactiva la cafeina", "ya puedes dormir"),
    "hibernar": ("hiberna", "hiberna la pc", "modo hibernacion", "hibernar"),
    "limpiar_temporales": ("limpia los temporales", "libera espacio", "borra los temporales",
                           "limpia la basura del sistema", "limpia el pc", "limpia archivos basura"),
    "reiniciar_explorador": ("reinicia el explorador", "arregla la barra de tareas",
                             "reinicia la barra de tareas", "se colgo la barra de tareas"),
    "espacio_disco": ("cuanto espacio me queda", "cuanto disco me queda", "espacio en disco",
                      "cuanto espacio tengo", "cuanto me queda de disco"),
    "procesos_top": ("que esta usando la pc", "que consume mas", "que esta consumiendo",
                     "que usa mas memoria", "por que esta lenta la pc", "que tiene lenta la pc"),
    "modo_oscuro": ("modo oscuro", "pon el tema oscuro", "tema oscuro", "activa el modo oscuro"),
    "modo_claro": ("modo claro", "pon el tema claro", "tema claro", "activa el modo claro"),
    "mostrar_ocultos": ("muestra los archivos ocultos", "ver archivos ocultos", "muestra los ocultos"),
    "ocultar_ocultos": ("oculta los archivos ocultos", "esconde los archivos ocultos"),
    "cerrar_sesion": ("cierra sesion", "cierra mi sesion", "cerrar sesion"),
    "specs": ("cuales son mis specs", "specs de la pc", "info del pc", "que specs tengo",
              "caracteristicas del pc", "info de la pc"),
    "bateria": ("como esta la bateria", "cuanta bateria tengo", "nivel de bateria", "la bateria"),
    "encendido": ("cuanto llevo encendido", "cuanto lleva encendida la pc", "tiempo encendido",
                  "hace cuanto prendi la pc", "cuanto lleva prendida"),
}


def clasificar_admin(p):
    p = _p(p)
    for accion, frases in _ADMIN.items():
        if p in frases:
            return accion
    return None


def ejecutar_admin(accion):
    from Funciones_Slide.Sistema import Windows_Admin as W
    m = {
        "arreglar_internet": W.arreglar_internet, "limpiar_dns": W.limpiar_dns, "mi_ip": W.mi_ip,
        "clave_wifi": W.clave_wifi, "desconectar_wifi": W.desconectar_wifi,
        "reconectar_wifi": W.reconectar_wifi,
        "plan_alto": lambda: W.plan_energia("alto"), "plan_equilibrado": lambda: W.plan_energia("equilibrado"),
        "despierto_on": lambda: W.mantener_despierto(True), "despierto_off": lambda: W.mantener_despierto(False),
        "hibernar": W.hibernar, "limpiar_temporales": W.limpiar_temporales,
        "reiniciar_explorador": W.reiniciar_explorador, "espacio_disco": W.espacio_disco,
        "procesos_top": W.procesos_top, "modo_oscuro": lambda: W.modo_oscuro(True),
        "modo_claro": lambda: W.modo_oscuro(False), "mostrar_ocultos": lambda: W.mostrar_ocultos(True),
        "ocultar_ocultos": lambda: W.mostrar_ocultos(False), "cerrar_sesion": W.cerrar_sesion,
        "specs": W.specs_pc, "bateria": W.estado_bateria, "encendido": W.tiempo_encendido,
    }
    fn = m.get(accion)
    if not fn:
        return "No reconocí esa función, señor."
    try:
        return fn()
    except Exception as e:
        return f"No pude, señor: {e}"


# ── 2. CARRIL RÁPIDO (traduce voz -> PowerShell, cerebro mínimo) ───────────────
def control_directo(instruccion):
    """Traduce la orden de voz a UN comando de PowerShell con una llamada MINIMA (modelo ligero, sin
    esquema de herramientas ni contexto) y lo ejecuta. Rapido y de proposito general."""
    instruccion = str(instruccion or "").strip()
    if not instruccion:
        return "Dígame qué hago, señor."
    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO
    except Exception:
        return "No tengo el cerebro disponible ahora, señor."
    prompt = (
        "Eres el traductor de comandos de AIDEN. Convierte esta orden hablada de Marco en UN comando "
        "de PowerShell para Windows 11 que la cumpla. Responde EXCLUSIVAMENTE el comando, en una sola "
        "linea, sin explicacion, sin markdown, sin comillas de bloque. Si la orden NO es una accion "
        "ejecutable en el PC (es una pregunta o charla), responde solo: NADA\n\nOrden: " + instruccion
    )
    try:
        r = client.chat.completions.create(
            model=MODELO_LIGERO, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=140,
        )
        cmd = (r.choices[0].message.content or "").strip().strip("`").strip()
        if cmd.lower().startswith("powershell"):
            cmd = cmd.split(None, 1)[-1].strip()
        cmd = cmd.splitlines()[0].strip() if cmd else ""
    except Exception as e:
        return f"No pude interpretar la orden, señor: {e}"
    if not cmd or cmd.upper().startswith("NADA"):
        return "Eso no me sonó a una acción del PC, señor. ¿Lo repite de otra forma?"
    from Funciones_Slide.Sistema.Control_Total import ejecutar_en_pc
    res = str(ejecutar_en_pc(cmd, descripcion=f"control por voz: {instruccion[:50]}"))
    # Fluidez: si fue una ACCIÓN (sin salida útil), confirma en una palabra; si devolvió un DATO, lo da.
    if res.startswith("Hecho, señor") or not res.strip():
        import random
        return random.choice(("Hecho.", "Listo, señor.", "Ya está.", "Hecho, señor.", "Cumplido."))
    if res.startswith(("Me niego", "El comando terminó con error", "No pude")):
        return res[:300]
    return res[:400]
