# AIDEN CONSTRUCTOR: AIDEN delega tareas REALES de programación a Claude Code (headless)
# y puede EJECUTAR el código resultante. Es la jugada "Jarvis construye cosas".
#
# Diseño:
#   - crear_proyecto(instruccion, nombre): lanza `claude -p` en una carpeta SANDBOX
#     (Proyectos_AIDEN/) en SEGUNDO PLANO (es lento) y avisa por voz al terminar.
#   - ejecutar_proyecto(nombre, archivo): corre el código generado (Python) y devuelve la salida.
#
# SEGURIDAD: los proyectos viven en Proyectos_AIDEN/ (sandbox, en el Escritorio). Se usa
# --permission-mode bypassPermissions para que Claude Code trabaje desatendido (Marco ya usa
# bypass); el riesgo es el mismo que él ya acepta. Mejor para ÓRDENES DE ALTO NIVEL.

import os
import re
import sys
import shutil
import subprocess
import threading

from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente

# Carpeta sandbox donde AIDEN crea y corre proyectos (visible, en el Escritorio).
BASE_PROYECTOS = os.path.join(os.path.expanduser("~"), "Desktop", "Proyectos_AIDEN")
TIMEOUT_CLAUDE = 1800     # 30 min máx para una tarea de Claude Code
TIMEOUT_EJECUCION = 60    # 60s máx al ejecutar el código generado

# Raíz del propio repo de AIDEN (para dictarle tareas a Claude Code SOBRE su propio código).
_REPO_AIDEN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_CLAUDE = shutil.which("claude") or os.path.join(
    os.path.expanduser("~"), ".local", "bin", "claude.exe"
)


def pedir_a_claude_code(instruccion):
    """HERRAMIENTA (dictado por voz -> Claude Code): Marco dicta una tarea de programación y AIDEN se
    la encarga a Claude Code EN EL PROPIO REPO de AIDEN, en segundo plano. Va avisando cada tanto que
    sigue trabajando (latido) y al terminar reporta por voz un resumen de lo que Claude hizo. OJO:
    puede MODIFICAR el código del proyecto; conviene revisar 'git diff' después."""
    instruccion = str(instruccion or "").strip()
    if not instruccion:
        return "¿Qué le encargo a Claude Code, señor?"
    if not _CLAUDE or not os.path.exists(_CLAUDE):
        return "No encuentro Claude Code en el sistema, señor; no puedo dictarle la tarea."

    def _trabajo():
        from Nucleo_Slide.Latido_Trabajo import latido
        lat = latido(hablado_del_asistente, cada=60).iniciar()   # avisa cada minuto que sigue en ello
        try:
            r = subprocess.run(
                [_CLAUDE, "-p", instruccion, "--permission-mode", "bypassPermissions"],
                cwd=_REPO_AIDEN, capture_output=True, text=True,
                timeout=TIMEOUT_CLAUDE, encoding="utf-8", errors="replace",
            )
            salida = (r.stdout or "").strip()
            resumen = salida[-600:] if salida else "Terminó, aunque no obtuve un resumen claro."
            lat.detener()
            hablado_del_asistente(
                f"Señor, Claude Code terminó su encargo. {resumen} Revise 'git diff' por si acaso."
            )
        except subprocess.TimeoutExpired:
            lat.detener()
            hablado_del_asistente("Señor, el encargo a Claude Code tardó demasiado y lo detuve.")
        except Exception as e:
            lat.detener()
            hablado_del_asistente(f"Señor, hubo un problema con el encargo a Claude Code: {e}")

    threading.Thread(target=_trabajo, daemon=True).start()
    return ("Se lo dicto a Claude Code, señor; trabaja en el proyecto y le voy avisando. "
            "Le reporto en cuanto termine.")


def _slug(texto):
    # Nombre de carpeta seguro a partir de un texto.
    s = re.sub(r"[^a-zA-Z0-9_ -]", "", str(texto or "")).strip().replace(" ", "_").lower()
    return s[:40] or "proyecto"


def _carpeta_proyecto(nombre):
    os.makedirs(BASE_PROYECTOS, exist_ok=True)
    carpeta = os.path.join(BASE_PROYECTOS, _slug(nombre))
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def crear_proyecto(instruccion, nombre=""):
    """Construye un proyecto de código delegando a Claude Code (headless), en sandbox y en
    SEGUNDO PLANO. Devuelve confirmación inmediata; avisa por voz al terminar."""
    instruccion = str(instruccion or "").strip()
    if not instruccion:
        return "¿Qué quiere que construya, señor?"
    if not _CLAUDE or not os.path.exists(_CLAUDE):
        return "No encuentro Claude Code en el sistema, señor; no puedo construir el proyecto."

    carpeta = _carpeta_proyecto(nombre or instruccion)
    nombre_carpeta = os.path.basename(carpeta)

    def _trabajo():
        try:
            prompt = (
                "Eres el ejecutor de código de AIDEN. Construye lo siguiente en ESTA carpeta, "
                "completo y funcional, con todos los archivos necesarios. Si es Python, deja un "
                "punto de entrada claro (main.py o app.py). Al final resume en 2-3 líneas qué "
                "creaste y cómo se ejecuta.\n\nTAREA: " + instruccion
            )
            r = subprocess.run(
                [_CLAUDE, "-p", prompt, "--permission-mode", "bypassPermissions"],
                cwd=carpeta, capture_output=True, text=True,
                timeout=TIMEOUT_CLAUDE, encoding="utf-8", errors="replace",
            )
            salida = (r.stdout or "").strip()
            resumen = salida[-600:] if salida else "Terminé, aunque no obtuve un resumen claro."
            hablado_del_asistente(
                f"Señor, terminé el proyecto '{nombre_carpeta}'. {resumen}"
            )
        except subprocess.TimeoutExpired:
            hablado_del_asistente(f"Señor, el proyecto '{nombre_carpeta}' tardó demasiado y lo detuve.")
        except Exception as e:
            hablado_del_asistente(f"Señor, hubo un problema construyendo '{nombre_carpeta}': {e}")

    threading.Thread(target=_trabajo, daemon=True).start()
    return (f"Manos a la obra, señor. Estoy construyendo '{nombre_carpeta}' con Claude Code. "
            "Le aviso en cuanto termine.")


def _resolver_carpeta(nombre):
    os.makedirs(BASE_PROYECTOS, exist_ok=True)
    if nombre:
        directo = os.path.join(BASE_PROYECTOS, _slug(nombre))
        if os.path.isdir(directo):
            return directo
        cands = [d for d in os.listdir(BASE_PROYECTOS)
                 if os.path.isdir(os.path.join(BASE_PROYECTOS, d)) and _slug(nombre) in d]
        if cands:
            return os.path.join(BASE_PROYECTOS, cands[0])
        return None
    # sin nombre: el proyecto más reciente
    subs = [os.path.join(BASE_PROYECTOS, d) for d in os.listdir(BASE_PROYECTOS)]
    subs = [d for d in subs if os.path.isdir(d)]
    return max(subs, key=os.path.getmtime) if subs else None


def ejecutar_proyecto(nombre="", archivo=""):
    """Ejecuta (corre) el código Python de un proyecto que AIDEN ya creó y devuelve su salida.
    Acotado al sandbox Proyectos_AIDEN/."""
    carpeta = _resolver_carpeta(nombre)
    if not carpeta:
        return ("No encuentro ese proyecto, señor."
                if nombre else "No tengo proyectos creados todavía, señor.")

    if archivo:
        objetivo = os.path.join(carpeta, archivo)
    else:
        objetivo = None
        for cand in ("main.py", "app.py", "run.py", "__main__.py"):
            if os.path.exists(os.path.join(carpeta, cand)):
                objetivo = os.path.join(carpeta, cand)
                break
        if objetivo is None:
            pys = [f for f in os.listdir(carpeta) if f.endswith(".py")]
            objetivo = os.path.join(carpeta, pys[0]) if pys else None

    if not objetivo or not os.path.exists(objetivo):
        return f"No encontré un archivo de Python para ejecutar en '{os.path.basename(carpeta)}', señor."

    try:
        r = subprocess.run(
            [sys.executable, objetivo], cwd=carpeta, capture_output=True, text=True,
            timeout=TIMEOUT_EJECUCION, encoding="utf-8", errors="replace",
        )
        salida = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode == 0:
            return f"Ejecuté '{os.path.basename(objetivo)}', señor. Salida:\n{salida or '(sin salida)'}"
        return f"'{os.path.basename(objetivo)}' terminó con error, señor:\n{err[-800:]}"
    except subprocess.TimeoutExpired:
        return "El programa tardó demasiado (¿bucle o espera entrada?); lo detuve, señor."
    except Exception as e:
        return f"No pude ejecutar el proyecto, señor: {e}"


def proyecto(accion="crear", instruccion="", nombre="", archivo="", verificar=False):
    """HERRAMIENTA unificada de proyectos construidos por Claude Code.
      accion='crear'    -> lo construye a partir de 'instruccion'.
      accion='ejecutar' -> corre el código de uno ya creado.
      verificar=True    -> además de construirlo, lo EJECUTA para comprobar que de verdad funciona
                           y se autocorrige si falla. Para encargos grandes que deben quedar
                           andando, no solo escritos.

    'verificar' era antes una herramienta entera aparte, 'ejecutar_mision', que se disputaba con
    esta cada "hazme un programa que...". Las dos construían con Claude Code; la única diferencia
    real era si después se comprobaba el resultado. Eso es una casilla, no otra herramienta."""
    a = str(accion or "").strip().lower()
    if a in ("ejecutar", "correr", "corre", "run", "abrir"):
        return ejecutar_proyecto(nombre, archivo)
    if verificar:
        from Funciones_Slide.Sistema.Misiones import ejecutar_mision
        return ejecutar_mision(instruccion, nombre)
    return crear_proyecto(instruccion, nombre)