import os 
import webbrowser
import pyautogui
import time
import importlib
from Nucleo_Slide import Auto_Programacion
import ast
import threading
import queue

from secretos import CONTACTOS as contactos   # los telefonos viven en secretos.py (fuera de git)

# ── ENCONTRAR AL CONTACTO ────────────────────────────────────────────────────
# Antes se exigía que el nombre coincidiera EXACTO con la clave de CONTACTOS. Marco habla, no
# teclea: dice "Tito" y está guardado "TITO ANDRES", dice "Maria" y está guardado "MARÍA". Cada una
# de esas fallaba en seco, y encima sin decir qué contactos sí existían.
#
# Se resuelve por niveles, del más seguro al más laxo, parando en el primero que dé algo. La regla
# que NO se negocia: si hay más de un candidato, NO se manda nada — se pregunta. Mandarle un
# mensaje a la persona equivocada no se puede deshacer.

_CASI_IGUAL = 0.85   # parecido a partir del cual se da por buena una transcripción torcida


def _sin_tildes(texto):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or ""))
                   if unicodedata.category(c) != "Mn").strip().upper()


def _buscar_contacto(nombre_buscado):
    """Devuelve ('OK', {nombre_real, numero}) | ('AMBIGUO', [nombres]) | ('NO_ENCONTRADO', None)."""
    buscado = _sin_tildes(nombre_buscado)
    if not buscado:
        return "NO_ENCONTRADO", None

    # normalizado -> [claves reales]. Se guarda lista porque dos claves distintas pueden
    # normalizar igual ("MARÍA" y "MARIA") y no se puede elegir por ellas a ciegas.
    indice = {}
    for clave in contactos:
        indice.setdefault(_sin_tildes(clave), []).append(clave)

    def _resolver(claves):
        reales = [r for c in claves for r in indice[c]]
        if len(reales) == 1:
            return "OK", {"nombre_real": reales[0], "numero": contactos[reales[0]]}
        return "AMBIGUO", sorted(reales)

    # (b) exacto ya normalizado: el camino feliz, ahora tolerante a tildes y mayúsculas.
    if buscado in indice:
        return _resolver([buscado])

    # (c) por PALABRA COMPLETA. Deliberadamente NO se usa subcadena: "ANA" está dentro de "ANABEL",
    # y con subcadena AIDEN creería que acertó y le escribiría a Anabel sin preguntar. Por palabra
    # completa, "Ana" no encuentra a "ANABEL" — y eso es lo correcto: mejor preguntar que acertarle
    # a la persona equivocada.
    tokens = [c for c in indice if buscado in c.split()]
    if tokens:
        return _resolver(tokens)

    # (d) último recurso: parecido tipográfico, por si Whisper transcribió algo torcido.
    # Un parecido NO es una coincidencia, es una SUPOSICIÓN, y aquí suponer manda un mensaje que no
    # se puede recoger. Por eso se separa por confianza: "Josua" contra "JOSHUA" se parecen un 91%
    # (es claramente la misma palabra mal oída) y se acepta; "Ana" contra "ANABEL" se parecen un 67%
    # (comparten el principio y ya) y ahí se PREGUNTA, porque puede ser otra persona.
    import difflib
    parecidos = difflib.get_close_matches(buscado, list(indice), n=3, cutoff=0.6)
    if not parecidos:
        return "NO_ENCONTRADO", None
    seguros = [c for c in parecidos
               if difflib.SequenceMatcher(None, buscado, c).ratio() >= _CASI_IGUAL]
    if len(seguros) == 1:
        return _resolver(seguros)
    return "AMBIGUO", sorted(r for c in parecidos for r in indice[c])


def _fallo_contacto(estado, opciones, nombre, verbo):
    """El mensaje para cuando NO se puede actuar. Devuelve None si sí se puede."""
    if estado == "NO_ENCONTRADO":
        conocidos = ", ".join(sorted(contactos)[:8])
        cola = f" Tengo registrados a: {conocidos}." if conocidos else ""
        return f"No tengo registrado a «{nombre}», señor.{cola}"
    if estado == "AMBIGUO":
        # Con UN solo candidato "varios contactos parecidos" suena a error; es una confirmación,
        # no una lista. Marco esto lo OYE, así que tiene que sonar a persona.
        if len(opciones) == 1:
            return f"No tengo a «{nombre}» exacto, señor. ¿Quiere decir {opciones[0]}?"
        return (f"Tengo varios contactos parecidos a «{nombre}», señor: "
                f"{', '.join(opciones)}. ¿A cuál le {verbo}?")
    return None


def Enviar_mensaje_Whatsapp(nombre_contacto, mensaje):
    try:
        estado, res = _buscar_contacto(nombre_contacto)
        problema = _fallo_contacto(estado, res, nombre_contacto, "escribo")
        if problema:
            return problema

        # quote() y no replace(" ","%20"): antes solo se escapaban los ESPACIOS, así que un
        # mensaje con "&" se cortaba ahí mismo (en una URL el & separa parámetros) y los acentos
        # o los "?" llegaban rotos. Justo los mensajes en español que más manda AIDEN.
        import urllib.parse
        texto = urllib.parse.quote(str(mensaje or ""))
        os.startfile(f"whatsapp://send?phone={res['numero']}&text={texto}")
        time.sleep(4)
    except Exception as e:
        return f"No pude abrir WhatsApp para escribirle a {nombre_contacto}, señor: {e}"

    # El Enter se manda a lo que sea que tenga el foco. Si WhatsApp tardó más de la cuenta en
    # abrir, ese Enter cae en otra ventana y el mensaje se queda escrito sin enviar. Se separa
    # para poder decirlo con claridad en vez de dar por hecho que salió.
    try:
        pyautogui.press("enter")
    except Exception:
        return (f"Abrí WhatsApp con el mensaje para {res['nombre_real']}, señor, pero no pude "
                "confirmar el envío. Reviselo, por favor.")
    return f"Mensaje enviado a {res['nombre_real']}, señor"


def colgar():
    try:
        pyautogui.moveTo(1000, 600)
        pyautogui.click()
        pyautogui.press("tab", presses=7, interval=0.1)
        pyautogui.press("enter")
        return "Llamada finalizada, señor"
    except Exception as e:
        return f"No pude colgar la llamada, señor: {e}"


def llamada_whatsapp(nombre_contacto):
    try:
        estado, res = _buscar_contacto(nombre_contacto)
        problema = _fallo_contacto(estado, res, nombre_contacto, "llamo")
        if problema:
            return problema

        os.startfile(f"whatsapp://send?phone={res['numero']}")
        time.sleep(3)
    except Exception as e:
        return f"No pude abrir WhatsApp para llamar a {nombre_contacto}, señor: {e}"

    try:
        pyautogui.press("tab", presses=10, interval=0.1)
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.moveTo(1550, 160)
        pyautogui.click()
    except Exception:
        return (f"Abrí el chat de {res['nombre_real']}, señor, pero no pude iniciar la llamada. "
                "Pulse usted el botón de llamar.")
    return f"Llamando a {res['nombre_real']}, señor"
# ── ¿DÓNDE ESTÁ CLAUDE CODE? ─────────────────────────────────────────────────
#
# Antes se miraba en el PATH y en ~/.local/bin/claude.exe. En esta PC no hay ninguno de los dos, y
# la habilidad de auto-programarse llevaba muerta sin que nadie lo notara: devolvía "no lo
# encuentro" y ahí acababa.
#
# El motivo es que Claude Code se puede tener de tres formas y solo una deja el comando en el PATH:
# el instalador nativo, npm global, y la EXTENSIÓN DE VS CODE — que trae su propio binario dentro y
# no instala nada fuera. Marco lo tiene de la tercera.
#
# La ruta de la extensión lleva el NÚMERO DE VERSIÓN dentro
# (…/anthropic.claude-code-2.1.223-win32-x64/…), así que clavarla la rompería en la siguiente
# actualización. Se busca por patrón y se coge la versión más alta — que es lo que este proyecto ya
# aprendió con AIDEN.bat, donde una ruta escrita a mano llevaba meses apuntando a otra PC.
_CARPETAS_VSCODE = (".vscode", ".vscode-insiders", ".vscode-server", ".cursor", ".windsurf")
# Tope al rastreo. Lo señaló el auditor de resiliencia: esto lo dispara Marco POR VOZ, y recorrer
# una carpeta del disco es leer algo de fuera. En una instalación normal hay una o dos versiones;
# el tope solo existe para que una carpeta de extensiones absurda no deje el turno de voz mirando
# archivos. Con más de esto, algo raro pasa y da igual cuál se elija.
_MAX_CANDIDATOS = 40


def _version_de(carpeta):
    """(2, 1, 223) a partir de 'anthropic.claude-code-2.1.223-win32-x64'. Ordenar por texto pondría
    la 2.1.9 por encima de la 2.1.223."""
    import re
    m = re.search(r"claude-code-(\d+(?:\.\d+)*)", os.path.basename(carpeta))
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def _buscar_claude():
    """La ruta del CLI, o None. Se prueban las tres formas de tenerlo instalado.

    Los imports van dentro, como en el resto del archivo: `shutil` se importa dentro de
    Auto_Modificacion, así que a nivel de módulo no existe."""
    import glob
    import shutil

    en_path = shutil.which("claude")
    if en_path:
        return en_path

    nativo = os.path.join(os.path.expanduser("~"), ".local", "bin", "claude.exe")
    if os.path.exists(nativo):
        return nativo

    casa = os.path.expanduser("~")
    candidatos = []
    for carpeta in _CARPETAS_VSCODE:
        patron = os.path.join(casa, carpeta, "extensions", "anthropic.claude-code-*",
                              "resources", "native-binary", "claude*")
        for ruta in glob.glob(patron)[:_MAX_CANDIDATOS]:
            if os.path.isfile(ruta) and os.access(ruta, os.X_OK):
                candidatos.append(ruta)
        if len(candidatos) >= _MAX_CANDIDATOS:
            break
    if not candidatos:
        return None
    # La más nueva: por versión, y si empatan, la instalada más tarde.
    candidatos.sort(key=lambda r: (_version_de(os.path.dirname(os.path.dirname(os.path.dirname(r)))),
                                   os.path.getmtime(r)))
    return candidatos[-1]


def Auto_Modificacion(nombre_habilidad, instruccion):
    # Hace que AIDEN APRENDA una habilidad nueva para SI MISMO usando Claude Code: le pide
    # escribir la funcion en Nucleo_Slide/Auto_Programacion.py y la recarga en vivo. Corre en
    # SEGUNDO PLANO (es lento) y avisa por voz al terminar. (Antes el LLM escribia el codigo a
    # mano; ahora lo escribe Claude Code, mucho mas confiable.) Para un PROYECTO/app aparte:
    # crear_proyecto.
    import shutil
    import subprocess

    nombre_habilidad = str(nombre_habilidad or "").strip()
    instruccion = str(instruccion or "").strip()
    if not nombre_habilidad or not instruccion:
        return "Necesito el nombre de la habilidad y que debe hacer, senor."

    claude = _buscar_claude()
    if not claude:
        return ("No encuentro Claude Code, senor; no puedo programar la habilidad. "
                "Se instala con: npm install -g @anthropic-ai/claude-code")

    ruta_archivo = os.path.abspath(Auto_Programacion.__file__)
    repo = os.path.dirname(os.path.dirname(ruta_archivo))   # raiz del repo

    def _trabajo():
        from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
        try:
            prompt = (
                "Eres el programador de AIDEN. AGREGA UNA sola funcion de Python llamada exactamente "
                "'" + nombre_habilidad + "' al FINAL del archivo Nucleo_Slide/Auto_Programacion.py. "
                "Debe hacer: " + instruccion + ". REGLAS ESTRICTAS: no modifiques NINGUN otro archivo "
                "ni el codigo existente; SOLO agrega la funcion nueva al final de ese archivo; "
                "autocontenida y funcional (imports dentro de la funcion si hace falta); que DEVUELVA "
                "un texto de resultado; no la ejecutes. "
                "ADEMAS, al final de tu respuesta escribe una linea que empiece con 'PRUEBA:' "
                "seguida de UNA sola linea de Python que llame a la funcion con datos de ejemplo y "
                "compruebe el resultado con assert. Ejemplo: "
                "PRUEBA: assert '19' in " + nombre_habilidad + "(100)   "
                "Que sea una comprobacion REAL de que hace lo pedido, no 'assert True'. "
                "Si la funcion no devuelve algo comprobable, escribe: PRUEBA: (ninguna). "
                "Responde corto."
            )
            salida_cc = subprocess.run(
                [claude, "-p", prompt, "--permission-mode", "bypassPermissions"],
                cwd=repo, capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace",
            )
            # La linea 'PRUEBA:' que Claude Code deja al final es la comprobacion de que la
            # funcion HACE lo pedido, no solo de que compila.
            prueba = ""
            for linea in (salida_cc.stdout or "").splitlines():
                if linea.strip().upper().startswith("PRUEBA:"):
                    prueba = linea.split(":", 1)[1].strip()
                    break
            if prueba.lower().startswith("(ninguna"):
                prueba = ""
            # TRES puertas antes de recargar esto DENTRO del proceso de AIDEN: que compile,
            # que el codigo no se salga de lo pedido, y que al ejecutarlo haga lo que dice.
            # Antes solo estaba la primera, que no distingue "correcto" de "bien escrito".
            from Nucleo_Slide.Validador_Habilidades import validar
            ok, motivo = validar(ruta_archivo, nombre_habilidad, instruccion, prueba)
            if not ok:
                # El motivo CONCRETO, no un "no funciono": es lo que le permite a Marco decidir si
                # lo pide de otra forma o lo mira el mismo.
                hablado_del_asistente(
                    "Senor, no active la habilidad " + nombre_habilidad + ": " + motivo + "."
                )
                return
            importlib.reload(Auto_Programacion)
            # La prueba se GUARDA. Hasta ahora se usaba una vez y se tiraba, así que una habilidad
            # quedaba validada para siempre por una comprobacion del dia que nacio: si algo de lo
            # que usa cambiaba despues, nadie se enteraba. Guardada, el mantenimiento en reposo
            # puede volver a correrla cuando la PC esta sin usar.
            try:
                from Nucleo_Slide.Reposo import registrar_habilidad
                registrar_habilidad(nombre_habilidad, instruccion, prueba)
            except Exception:
                pass
            hablado_del_asistente("Senor, habilidad adquirida y probada: " + nombre_habilidad + ".")
        except subprocess.TimeoutExpired:
            hablado_del_asistente("Senor, programar " + nombre_habilidad + " tardo demasiado y lo detuve.")
        except Exception as e:
            hablado_del_asistente("Senor, no pude programar " + nombre_habilidad + ": " + str(e))

    threading.Thread(target=_trabajo, daemon=True).start()
    return ("Programando la habilidad '" + nombre_habilidad + "' con Claude Code, senor. "
            "Le aviso en cuanto la tenga lista.")




def enviar_mensaje(canal, destino, mensaje, asunto=""):
    """HERRAMIENTA única para escribirle a alguien, por el canal que sea.
      canal = 'whatsapp' | 'discord' | 'correo'
      destino = a quién (contacto, usuario/canal de Discord, o dirección de email)
      mensaje = qué decirle;  asunto = solo para correo (redáctalo tú si Marco no lo dio).

    Antes había tres herramientas casi idénticas — WhatsApp, Discord y correo — que compartían
    hasta el 23% del vocabulario de sus descripciones ("mándale a X diciendo..."). La intención de
    Marco es siempre la misma, ESCRIBIRLE A ALGUIEN; lo único que cambia es por dónde sale. Eso es
    un parámetro. Tres herramientas casi iguales solo le dan al modelo tres formas de equivocarse."""
    c = str(canal or "").strip().lower()
    destino = str(destino or "").strip()
    mensaje = str(mensaje or "").strip()
    if not destino:
        return "¿A quién le escribo, señor?"
    if not mensaje:
        return "¿Qué le digo, señor?"

    if "discord" in c:
        from Funciones_Slide.Comunicacion.Discord import Enviar_mensaje_Discord
        return Enviar_mensaje_Discord(destino, mensaje)
    if "correo" in c or "mail" in c or "email" in c:
        from Funciones_Slide.Info.Agenda import enviar_correo
        return enviar_correo(destino, asunto or "(sin asunto)", mensaje)
    if "whats" in c or "wpp" in c or not c:
        return Enviar_mensaje_Whatsapp(destino, mensaje)
    return (f"No sé enviar por «{canal}», señor. Puedo por WhatsApp, Discord o correo.")
