# CONTROL TOTAL: la "llave maestra" de AIDEN sobre la PC de Marco.
#
# El salto Jarvis real: en vez de una herramienta por cada cosa, UNA sola que ejecuta PowerShell
# que AIDEN mismo compone. Con esto puede hacer LITERALMENTE cualquier cosa que Windows permita:
# mover/renombrar/buscar archivos, matar procesos, cambiar ajustes, red, energía, registro, abrir
# lo que sea con lo que sea, encadenar acciones... sin que haya que programarle una tool nueva cada
# vez. Es darle a AIDEN las manos que Jarvis tenía sobre la mansión de Tony.
#
# SEGURIDAD (red anti-catástrofe, no censura): se BLOQUEAN solo comandos irreversibles y
# destructivos de sistema (formatear discos, borrar Windows, wipe, deshabilitar el arranque...).
# Todo lo demás — que es reversible o normal — se ejecuta. Marco es el dueño y administrador.
#
# COMANDOS QUE PREGUNTAN: antes se corría con -NonInteractive, así que cualquier cosa que pidiera
# confirmación ([Y/n], "¿Desea continuar?", un instalador) se quedaba colgada hasta agotar el
# timeout completo sin que nadie pudiera responderle. Ahora el proceso se lanza con stdin abierto y
# se le contesta solo. Se detecta que está esperando de DOS formas, porque no todos avisan igual
# (medido, no supuesto):
#   1. La pregunta SE VE en la salida (típico de CLIs nativos: npm, pip, git). Se contesta al toque.
#   2. La pregunta NO SE VE. `Read-Host` de PowerShell escribe su prompt en la CONSOLA, no en la
#      salida redirigida: por el pipe no llega absolutamente nada. La firma de que está bloqueado
#      es entonces "proceso vivo + salida callada", y ahí se le manda la respuesta a ciegas — que
#      es justo lo que lo destraba. Si en realidad solo estaba calculando, esa línea se queda sin
#      leer y no molesta a nadie.
#   Límite honesto: esto habla por la ENTRADA ESTÁNDAR. Cubre PowerShell (Read-Host, -Confirm) y la
#   enorme mayoría de CLIs. Un programa que lea el búfer de consola directamente en vez de stdin
#   (algunos instaladores gráficos) seguiría sin oírnos: eso necesitaría un ConPTY real.
#
# PARAR A MEDIO CAMINO: el comando se ejecuta dentro de una operación cancelable, así que Marco
# puede abortarlo con Ctrl+Alt+P (o pidiéndoselo a AIDEN por Telegram) sin esperar el timeout.

import os
import re
import subprocess
import threading

from Nucleo_Slide import Cancelacion

# Patrones CATASTRÓFICOS (irreversibles / rompen el SO). Si aparecen, no se ejecuta.
_PROHIBIDO = (
    r"format\s+[a-z]:",                 # formatear una unidad
    r"format-volume",
    r"diskpart",                         # particionado a bajo nivel
    r"clear-disk",
    r"cipher\s+/w",                      # sobrescritura/wipe
    r"remove-item.*(windows|system32)",  # borrar el SO
    r"rd\s+/s.*(windows|system32)",
    r"rmdir\s+/s.*(windows|system32)",
    r"del\s+/[fsq].*(windows|system32)",
    r"bcdedit",                          # tocar el gestor de arranque
    r"vssadmin\s+delete",                # borrar copias de sombra (típico de ransomware)
    r"wevtutil\s+cl",                    # borrar TODOS los logs de eventos
    r"cipher\s+/k",
    r"reg\s+delete\s+hk.._machine\\\\(system|software\\\\microsoft\\\\windows nt)",
)

# La salida termina en una PREGUNTA esperando que alguien teclee algo.
# Se miran solo los últimos caracteres, y solo si NO acaban en salto de línea (un prompt deja el
# cursor en la misma línea; una línea de log normal termina con \n).
_PREGUNTAS = (
    r"\[y/n\]",                      # [Y/n] / [y/N]
    r"\[s/n\]",                      # español
    r"\(y/n\)",
    r"\(s/n\)",
    r"\[y\].*\[n\]",                 # PowerShell -Confirm: [Y] Yes [A] Yes to All [N] No ...
    r"\[s\].*\[n\]",
    r"y/n\s*[:?]?\s*$",
    r"s/n\s*[:?]?\s*$",
    r"\?\s*$",                       # cualquier cosa que acabe en '?'
    r":\s*$",                        # Read-Host deja "Texto: "
    r"press any key",
    r"presione (una|cualquier) tecla",
    r"desea continuar",
    r"are you sure",
    r"do you want to",
    r"continuar\?",
    r"\(default is",
)

_MAX_RESPUESTAS = 12   # tope de preguntas VISIBLES contestadas: si pide más, algo va en bucle
_MAX_A_CIEGAS = 8      # tope de respuestas mandadas sin ver la pregunta (Read-Host y compañía)
_SILENCIO = 1.5        # s callado y vivo = probablemente esperando que le contesten
_ESPERA_ENTRE = 1.5    # s mínimos entre dos respuestas a ciegas


def _es_catastrofico(comando):
    c = " ".join(str(comando or "").lower().split())
    return any(re.search(p, c) for p in _PROHIBIDO)


def _parece_pregunta(cola):
    """True si el final de la salida es un prompt esperando respuesta."""
    if not cola or cola.endswith("\n"):
        return False                          # línea cerrada = log normal, no pregunta
    t = cola.lower().strip()
    if not t:
        return False
    return any(re.search(p, t) for p in _PREGUNTAS)


def _guardar_delta(comando, descripcion, error, fallo):
    """Deja el error a mano por si Marco pregunta después.

    Vive aquí y no en cada return porque los DOS caminos de ejecución —la sesión caliente y el
    proceso suelto— acaban en la misma forma, y dos copias de esto acabarían divergiendo.

    Se guarda el COMANDO junto al error: sin él, un «no such file» a secas no le dice nada al
    modelo dos minutos después. Y nunca tumba una ejecución: si esto falla, el comando ya corrió."""
    try:
        if not fallo or not str(error or "").strip():
            return False
        from Nucleo_Slide.Ultimo_Error import recordar
        que = (descripcion or comando or "")[:120]
        return recordar(f"Al ejecutar «{que}»:\n{error}", "ejecutar_en_pc")
    except Exception:
        return False


def _matar_arbol(proc):
    # Mata el proceso Y sus hijos: PowerShell suele lanzar sub-procesos que sobreviven al padre.
    try:
        import psutil
        p = psutil.Process(proc.pid)
        for hijo in p.children(recursive=True):
            try:
                hijo.kill()
            except Exception:
                pass
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _term(fn, *a):
    """Puente a la terminal fantasma. Es un ADORNO: si el HUD no está, no pasa nada y el comando
    corre igual. Nunca puede tumbar una ejecución por no haber pantalla."""
    try:
        from Interfaz import TerminalFantasma
        return getattr(TerminalFantasma, fn)(*a)
    except Exception:
        return None


def _lector(flujo, acumulador, lock):
    # Lee de a un carácter para poder detectar prompts que NO terminan en salto de línea
    # (readline() se quedaría bloqueado esperando un \n que nunca llega).
    try:
        while True:
            c = flujo.read(1)
            if not c:
                return
            with lock:
                acumulador.append(c)
    except Exception:
        return


# ── SESIÓN CALIENTE ──────────────────────────────────────────────────────────
# Arrancar PowerShell cuesta CARO: medido en esta máquina, 1.7-2.6 segundos por llamada. Como cada
# comando abría uno nuevo, esos dos segundos se pagaban íntegros antes de empezar a hacer nada.
#
# Se mantiene UNA sesión ya arrancada y esperando, y los comandos se le mandan por la entrada
# estándar seguidos de una MARCA que delata cuándo terminó cada uno. Medido: 132 ms frente a 1.532.
#
# Lo que se hizo para no perder nada de lo que ya funcionaba:
#   · Las preguntas se siguen contestando por el mismo canal (comprobado: Read-Host se bloquea
#     esperando y responde igual que antes).
#   · El estado SÍ se filtra entre comandos en una sesión compartida — variables, carpeta actual —,
#     así que antes de cada comando se limpian las variables y se vuelve a la carpeta del proyecto.
#   · Cancelar o agotar el tiempo MATA la sesión entera y arranca otra: no hay forma de matar solo
#     un comando dentro de una sesión, y dejar viva una sesión con algo colgado sería peor.
#   · Si la sesión no arranca o se muere a mitad, se cae al camino de siempre (un proceso por
#     comando), que sigue intacto ahí abajo. Más lento, pero jamás deja a Marco sin respuesta.

_MARCA = "__AIDEN_FIN_5f3a__"
_sesion = None            # (proc, buf_out, buf_err, lock)
_lock_sesion = threading.RLock()
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _matar_sesion():
    global _sesion
    with _lock_sesion:
        if _sesion is None:
            return
        proc = _sesion[0]
        _sesion = None
    _matar_arbol(proc)


def _abrir_sesion():
    """Arranca una sesión y espera a que esté LISTA de verdad (no basta con que exista)."""
    try:
        proc = subprocess.Popen(
            # El guión final: lee de la entrada estándar y NO reimprime cada orden (el modo
            # interactivo a secas devuelve el prompt "PS C:\...>" mezclado con la salida).
            ["powershell", "-NoProfile", "-NoLogo", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    except Exception:
        return None
    buf_out, buf_err, lock = [], [], threading.Lock()
    threading.Thread(target=_lector, args=(proc.stdout, buf_out, lock), daemon=True).start()
    threading.Thread(target=_lector, args=(proc.stderr, buf_err, lock), daemon=True).start()

    # Handshake: hasta que no conteste la marca, no está lista.
    import time as _t
    try:
        proc.stdin.write(f"Write-Output '{_MARCA}'\n")
        proc.stdin.flush()
    except Exception:
        _matar_arbol(proc)
        return None
    limite = _t.monotonic() + 20
    while _t.monotonic() < limite:
        with lock:
            if _MARCA in "".join(buf_out):
                buf_out.clear()
                return (proc, buf_out, buf_err, lock)
        if proc.poll() is not None:
            return None
        _t.sleep(0.05)
    _matar_arbol(proc)
    return None


def _asegurar_sesion():
    global _sesion
    with _lock_sesion:
        if _sesion is not None and _sesion[0].poll() is None:
            return _sesion
        _sesion = None
    nueva = _abrir_sesion()
    with _lock_sesion:
        _sesion = nueva
    return nueva


def precalentar():
    """Deja una sesión lista ANTES de que Marco pida nada, para que el primer comando del día no
    pague el arranque. Lo llama Main al terminar de cargar; si falla, no pasa nada."""
    threading.Thread(target=_asegurar_sesion, daemon=True).start()


def _en_sesion(comando, descripcion, pendientes, por_defecto, timeout):
    """Ejecuta en la sesión YA arrancada. Devuelve el texto final, o None si la sesión no está
    disponible (entonces quien llama se va por el camino en frío)."""
    import time as _t

    sesion = _asegurar_sesion()
    if sesion is None:
        return None
    proc, buf_out, buf_err, lock = sesion

    with lock:
        buf_out.clear()
        buf_err.clear()
    # TODO EN UNA SOLA LÍNEA, y el comando en base64. Es lo que hace que esto funcione:
    #   · Si la marca del final viajara en su PROPIA línea, un Read-Host del comando se la
    #     tragaría creyendo que es la respuesta que espera. Entonces la marca no aparecería nunca,
    #     el turno se quedaría colgado y la respuesta acabaría ejecutándose como si fuera otro
    #     comando. (Pasó exactamente eso: "CONTESTASTE: Write-Output ...".)
    #   · El comando puede traer saltos de línea (un bucle, un here-string), que partirían la
    #     línea igual. Codificado en base64 es un bloque opaco: entra entero de una vez.
    # Con todo en una línea, lo único que queda pendiente en la entrada son las RESPUESTAS — que
    # es justo lo que Read-Host debe leer.
    #
    # El preámbulo aísla: en una sesión compartida las variables y la carpeta actual sobreviven
    # de un comando al siguiente, así que se limpian para que cada uno salga de cero.
    import base64
    b64 = base64.b64encode(comando.encode("utf-16-le")).decode("ascii")
    envoltorio = (
        "Remove-Variable * -Scope Global -Force -ErrorAction SilentlyContinue; "
        f"Set-Location -LiteralPath '{_carpeta_actual()}'; $Error.Clear(); "
        # Se pone a cero ANTES: en una sesión caliente $LASTEXITCODE sobrevive de un comando al
        # siguiente, y sin esto un fallo viejo se le atribuiría al comando nuevo.
        "$global:LASTEXITCODE=0; "
        f"Invoke-Expression ([Text.Encoding]::Unicode.GetString("
        f"[Convert]::FromBase64String('{b64}'))); "
        # La marca se lleva de paso el nº de errores, la carpeta donde quedó el comando y el código
        # de salida, así no hace falta un segundo delimitador ni ensuciar la salida que ve Marco.
        #
        # El código de salida hace falta además del contador de errores porque miden cosas
        # distintas: $Error.Count cuenta errores DE POWERSHELL, y no se entera de que `python` o
        # `pip` devolvieron 1. Sin él, un traceback de Python se veía en la salida pero constaba
        # como comando correcto.
        f"Write-Output \"{_MARCA}$($Error.Count)|$((Get-Location).Path)|$LASTEXITCODE\"\n"
    )
    try:
        proc.stdin.write(envoltorio)
        proc.stdin.flush()
    except Exception:
        _matar_sesion()
        return None

    inicio = _t.monotonic()
    contestadas = a_ciegas = 0
    ultimo_largo, quieto_desde, ultima_respuesta = 0, inicio, 0.0
    corte = None
    _term("mostrar", descripcion or comando[:52])

    def _responder():
        envio = pendientes.pop(0) if pendientes else por_defecto
        try:
            proc.stdin.write(envio + "\n")
            proc.stdin.flush()
            return True
        except Exception:
            return False

    with Cancelacion.operacion(descripcion or "un comando en el PC"):
        while True:
            with lock:
                texto = "".join(buf_out)
                largo = len(buf_out)
            if _MARCA in texto:
                break
            if proc.poll() is not None:          # la sesión se murió a mitad
                _matar_sesion()
                return None
            if Cancelacion.cancelado():
                corte = "cancelado"
                break
            if _t.monotonic() - inicio > timeout:
                corte = "timeout"
                break

            ahora = _t.monotonic()
            if largo != ultimo_largo:
                # A la terminal se le pasa SOLO lo nuevo, no el buffer entero: se reusa lo que el
                # bucle ya sabía (cuánto creció) en vez de releer nada.
                _term("actualizar", "".join(buf_out[ultimo_largo:largo]))
                ultimo_largo, quieto_desde = largo, ahora
            silencio = ahora - quieto_desde
            cola = texto[-400:]

            if silencio > 0.4 and _parece_pregunta(cola):
                if contestadas >= _MAX_RESPUESTAS:
                    corte = "bucle"
                    break
                if _responder():
                    contestadas += 1
                    with lock:
                        buf_out.append("\n")
                    quieto_desde = ultima_respuesta = _t.monotonic()
            elif (silencio > _SILENCIO and a_ciegas < _MAX_A_CIEGAS
                  and ahora - ultima_respuesta > _ESPERA_ENTRE):
                if _responder():
                    a_ciegas += 1
                    ultima_respuesta = _t.monotonic()

            _t.sleep(0.05)

    with lock:
        bruto = "".join(buf_out)
        error = "".join(buf_err).strip()

    # Cortar o agotar el tiempo obliga a MATAR la sesión: dentro de una sesión compartida no hay
    # forma de matar un solo comando, y dejarla viva con algo colgado envenenaría el siguiente.
    if corte in ("cancelado", "timeout", "bucle"):
        _term("cerrar", False)      # cortado: la ventana se queda, que es cuando hay algo que leer
        salida_parcial = bruto.split(_MARCA)[0].strip()
        _matar_sesion()
        precalentar()                            # deja otra lista para la próxima
        if corte == "cancelado":
            extra = f" Lo que alcanzó a hacer: {salida_parcial[:300]}" if salida_parcial else ""
            return f"Detenido, señor ({Cancelacion.motivo()}).{extra}"
        if corte == "timeout":
            return (f"El comando tardó demasiado y lo corté, señor (más de {timeout} segundos). "
                    "Si esperaba que tardara, pídamelo de nuevo con más tiempo.")
        return ("Corté el comando, señor: seguía preguntándome lo mismo una y otra vez "
                f"({_MAX_RESPUESTAS} veces). Reviselo a mano.")

    antes, _, despues = bruto.partition(_MARCA)
    salida = antes.strip()
    cabecera = despues.strip().split("\n")[0]
    # "3|C:\ruta|1" — la carpeta sigue en el mismo sitio que siempre; el código de salida se añadió
    # al final para no mover nada. Con menos partes (una sesión vieja), se degrada sin romperse.
    partes = cabecera.split("|")
    n_txt = partes[0] if partes else "0"
    carpeta = partes[1] if len(partes) > 1 else ""
    cod_txt = partes[2] if len(partes) > 2 else ""
    try:
        n_errores = int(n_txt.strip() or 0)
    except ValueError:
        n_errores = 0
    try:
        codigo = int(cod_txt.strip() or 0)
    except ValueError:
        codigo = 0
    _recordar_carpeta(carpeta.strip())

    _term("cerrar", not (n_errores and error))
    _registrar(descripcion, comando)
    nota = _nota_preguntas(contestadas)
    # Fallo = error de PowerShell O código de salida distinto de cero. Lo segundo es lo que
    # detecta que `python`, `pip` o `git` reventaron; sin ello el traceback aparecía en la
    # respuesta pero no se guardaba.
    _guardar_delta(comando, descripcion, error, n_errores or codigo)
    if n_errores and error:
        return f"El comando terminó con error, señor{nota}: {error[:400]}{_nota_permisos(error)}"
    if not salida and not error:
        return f"Hecho, señor{nota}. (Sin salida que reportar.)"
    resultado = salida or error
    return resultado[:1500] + (" (...recortado)" if len(resultado) > 1500 else "") + nota


# ── CARPETA DE TRABAJO QUE SE RECUERDA ───────────────────────────────────────
# "Entra en la carpeta del proyecto" y luego "corre el script": la segunda orden tiene que saber
# dónde dejó la primera. Se recuerda SOLO la carpeta, no el resto del estado — las variables se
# siguen limpiando entre comandos. Es el punto medio deliberado: lo que Marco espera que se
# recuerde (dónde está) se recuerda; lo que causaría efectos raros a distancia (variables sueltas
# de un comando anterior) no.
_carpeta = None


def _carpeta_actual():
    return _carpeta if (_carpeta and os.path.isdir(_carpeta)) else os.path.normpath(_RAIZ)


def _misma_carpeta(a, b):
    """En Windows las rutas NO distinguen mayúsculas, y PowerShell devuelve la unidad en mayúscula
    mientras que Python la calcula en minúscula: 'C:\\...' y 'c:\\...' son el mismo sitio."""
    try:
        return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))
    except Exception:
        return False


def _recordar_carpeta(ruta):
    global _carpeta
    if ruta and os.path.isdir(ruta):
        _carpeta = os.path.normpath(ruta)


def carpeta_de_trabajo():
    """Dónde quedó AIDEN tras el último comando (para que lo pueda decir si se le pregunta)."""
    return _carpeta_actual()


# ── ¿SE ABRIÓ UNA VENTANA? ───────────────────────────────────────────────────
# Un "start spotify" no devuelve nada por la salida estándar, así que AIDEN respondía "Hecho,
# señor. (Sin salida que reportar.)" sin saber qué había abierto — y sin poder decirle luego a
# controlar_pantalla sobre qué ventana actuar. Se comparan las ventanas de antes y las de después.
# Solo se espera a que aparezca si el comando PARECE que lanza algo: para un 'ipconfig' no se
# retrasa nada en absoluto.
_LANZADORES = re.compile(
    r"\b(start|start-process|invoke-item|explorer|notepad|code|spotify|chrome|msedge|firefox)\b"
    r"|\.exe\b|\.lnk\b", re.I)


def _titulos_visibles():
    try:
        import win32gui
    except Exception:
        return set()
    titulos = set()

    def _cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd):
                t = (win32gui.GetWindowText(hwnd) or "").strip()
                if t:
                    titulos.add(t)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return set()
    return titulos


def _ventana_nueva(antes, comando, espera_max=1.5):
    if not antes:
        return None
    if not _LANZADORES.search(comando or ""):
        nuevas = _titulos_visibles() - antes        # sin esperar nada
        return next(iter(nuevas), None) if nuevas else None
    import time as _t
    limite = _t.monotonic() + espera_max
    while _t.monotonic() < limite:
        nuevas = _titulos_visibles() - antes
        if nuevas:
            return sorted(nuevas, key=len)[-1]      # el título más descriptivo
        _t.sleep(0.15)
    return None


def _cola_ventana(antes, comando, resultado):
    """Añade al final ' (Se abrió la ventana: «X»)' si el comando levantó algo. No se anuncia si
    la cosa se cortó a medias: en ese caso el mensaje ya dice lo que hay que decir."""
    if any(resultado.startswith(p) for p in ("Detenido", "El comando tardó", "Corté", "Me niego")):
        return ""
    try:
        nueva = _ventana_nueva(antes, comando)
    except Exception:
        return ""
    return f" (Se abrió la ventana: «{nueva[:60]}»)" if nueva else ""


def _registrar(descripcion, comando):
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Ejecuté en el PC: {descripcion or comando[:60]}", "control_total")
    except Exception:
        pass


# Un fallo por FALTA DE PERMISOS se veía como un error cualquiera de PowerShell, así que AIDEN lo
# repetía tal cual ("Access is denied") y ahí moría la conversación. Es un caso con salida concreta
# —elevarse— y por tanto merece decirse con esas palabras.
_SIN_PERMISOS = re.compile(
    r"acceso denegado|access is denied|requires elevation|requiere elevaci|unauthorizedaccess|"
    r"no est[aá] autorizado|permissiondenied|se necesitan privilegios|administrator privileges",
    re.I)


def _nota_permisos(texto):
    if not _SIN_PERMISOS.search(texto or ""):
        return ""
    try:
        from Funciones_Slide.Sistema.Elevacion import soy_admin
        if soy_admin():
            # Ya se corre elevado: entonces no es cuestión de permisos de administrador, y decir
            # "deme permisos" sería mandar a Marco por un camino que no lleva a ninguna parte.
            return (" (Ya voy como administrador, señor, así que esto no es cosa de elevarme: el "
                    "archivo o el servicio está protegido o en uso por otro programa.)")
    except Exception:
        pass
    return (" — Eso falló por falta de permisos de administrador, señor. Dígame que me eleve y lo "
            "reintento; le saldrá un diálogo de Windows que tendrá que aceptar usted.")


def _nota_preguntas(contestadas):
    if not contestadas:
        return ""
    return f" (le contesté {contestadas} pregunta{'s' if contestadas != 1 else ''})"


def ejecutar_en_pc(comando, descripcion="", respuestas="", timeout=45):
    """HERRAMIENTA MAESTRA: ejecuta un comando de PowerShell en la PC de Marco y devuelve el
    resultado. Con esto AIDEN puede hacer CUALQUIER cosa en Windows (archivos, procesos, ajustes,
    red, energía, apps...) sin necesidad de una herramienta específica.
      comando     = el PowerShell a correr.
      descripcion = qué logra, en una frase (para el registro).
      respuestas  = qué contestar si el comando pregunta, en orden y separadas por '|'
                    (ej. "S|Y|"). Si se acaban, se sigue respondiendo con la última.
      timeout     = segundos máximos (por defecto 45; súbelo para instalaciones largas)."""
    comando = str(comando or "").strip()
    if not comando:
        return "No me diste un comando que ejecutar, señor."
    if _es_catastrofico(comando):
        return ("Me niego a ejecutar eso, señor: es una operación destructiva e irreversible "
                "(formatear/borrar sistema). Si de verdad lo necesita, hágalo usted a mano.")

    # Cola de respuestas para las preguntas. Por defecto "S" (sí): es lo que Marco quiere el 99%
    # de las veces cuando pidió la acción — el freno de verdad es la lista negra de arriba.
    pendientes = [r.strip() for r in str(respuestas or "").split("|")] if respuestas else []
    por_defecto = pendientes[-1] if pendientes else "S"

    ventanas_antes = _titulos_visibles()

    # Primero la sesión caliente (~130 ms). Si no está disponible o se cae, el camino de siempre.
    try:
        rapido = _en_sesion(comando, descripcion, list(pendientes), por_defecto, timeout)
        if rapido is not None:
            return rapido + _cola_ventana(ventanas_antes, comando, rapido)
    except Exception:
        _matar_sesion()

    try:
        # -NoProfile: arranque limpio y rápido. SIN -NonInteractive: queremos poder contestarle.
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", comando],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    except Exception as e:
        return f"No pude ejecutar el comando, señor: {e}"

    buf_out, buf_err, lock = [], [], threading.Lock()
    threading.Thread(target=_lector, args=(proc.stdout, buf_out, lock), daemon=True).start()
    threading.Thread(target=_lector, args=(proc.stderr, buf_err, lock), daemon=True).start()

    import time as _t
    inicio = _t.monotonic()
    contestadas = a_ciegas = 0
    ultimo_largo, quieto_desde, ultima_respuesta = 0, inicio, 0.0
    corte = None

    def _responder():
        # Manda la siguiente respuesta por la entrada estándar.
        envio = pendientes.pop(0) if pendientes else por_defecto
        try:
            proc.stdin.write(envio + "\n")
            proc.stdin.flush()
            return True
        except Exception:
            return False

    with Cancelacion.operacion(descripcion or "un comando en el PC"):
        while proc.poll() is None:
            if Cancelacion.cancelado():
                _matar_arbol(proc)
                corte = "cancelado"
                break
            if _t.monotonic() - inicio > timeout:
                _matar_arbol(proc)
                corte = "timeout"
                break

            with lock:
                cola = "".join(buf_out[-400:])
                largo = len(buf_out)

            ahora = _t.monotonic()
            if largo != ultimo_largo:                    # sigue escribiendo: aún no pregunta nada
                ultimo_largo, quieto_desde = largo, ahora
            silencio = ahora - quieto_desde

            # (1) La pregunta SE VE en la salida. Se espera un pelín a que termine de escribirla.
            if silencio > 0.4 and _parece_pregunta(cola):
                if contestadas >= _MAX_RESPUESTAS:
                    _matar_arbol(proc)
                    corte = "bucle"
                    break
                if _responder():
                    contestadas += 1
                    with lock:
                        buf_out.append("\n")   # cierra la línea: no re-detectar la misma pregunta
                    quieto_desde = ultima_respuesta = _t.monotonic()

            # (2) NO se ve nada y sigue vivo: la firma de un Read-Host esperando. Se contesta a
            #     ciegas, que es lo único que lo destraba (su prompt jamás llega por el pipe).
            elif (silencio > _SILENCIO and a_ciegas < _MAX_A_CIEGAS
                  and ahora - ultima_respuesta > _ESPERA_ENTRE):
                if _responder():
                    a_ciegas += 1
                    ultima_respuesta = _t.monotonic()

            _t.sleep(0.1)

    try:
        proc.stdin.close()
    except Exception:
        pass
    _t.sleep(0.2)                             # deja que los lectores vacíen lo último
    with lock:
        salida = "".join(buf_out).strip()
        error = "".join(buf_err).strip()

    if corte == "cancelado":
        parcial = f" Lo que alcanzó a hacer: {salida[:300]}" if salida else ""
        return f"Detenido, señor ({Cancelacion.motivo()}).{parcial}"
    if corte == "timeout":
        return (f"El comando tardó demasiado y lo corté, señor (más de {timeout} segundos). "
                "Si esperaba que tardara, pídamelo de nuevo con más tiempo.")
    if corte == "bucle":
        return ("Corté el comando, señor: seguía preguntándome lo mismo una y otra vez "
                f"({_MAX_RESPUESTAS} veces). Reviselo a mano.")

    # Registro en la conciencia compartida (queda en el hilo de eventos).
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Ejecuté en el PC: {descripcion or comando[:60]}", "control_total")
    except Exception:
        pass

    nota = f" (le contesté {contestadas} pregunta{'s' if contestadas != 1 else ''})" if contestadas else ""
    _guardar_delta(comando, descripcion, error, proc.returncode)
    if proc.returncode != 0 and error:
        return f"El comando terminó con error, señor{nota}: {error[:400]}"
    if not salida and not error:
        return f"Hecho, señor{nota}. (Sin salida que reportar.)"
    resultado = salida or error
    # Recorta salidas enormes (un 'dir' de miles de archivos): AIDEN resume lo esencial.
    return resultado[:1500] + (" (...recortado)" if len(resultado) > 1500 else "") + nota
