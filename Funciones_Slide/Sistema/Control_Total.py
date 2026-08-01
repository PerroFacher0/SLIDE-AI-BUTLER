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
    if proc.returncode != 0 and error:
        return f"El comando terminó con error, señor{nota}: {error[:400]}"
    if not salida and not error:
        return f"Hecho, señor{nota}. (Sin salida que reportar.)"
    resultado = salida or error
    # Recorta salidas enormes (un 'dir' de miles de archivos): AIDEN resume lo esencial.
    return resultado[:1500] + (" (...recortado)" if len(resultado) > 1500 else "") + nota
