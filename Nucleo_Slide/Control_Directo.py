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
    "vol_up": ("sube el volumen", "mas volumen", "sube el sonido", "sube volumen"),
    "vol_down": ("baja el volumen", "menos volumen", "baja el sonido", "baja volumen"),
    "vol_max": ("volumen al maximo", "maximo volumen", "sube el volumen al maximo"),
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
    except Exception as e:
        return f"No pude, señor: {e}"
    return "No reconocí esa acción, señor."


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
    if res.startswith("Hecho, señor") or not res.strip():
        return "Hecho, señor."
    return res[:400]
