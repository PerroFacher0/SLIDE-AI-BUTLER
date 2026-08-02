# PERMISOS DE ADMINISTRADOR: la salida práctica al muro del UAC.
#
# El muro: cuando Windows va a hacer algo que necesita permiso de administrador, saca su diálogo
# "¿Permitir que esta aplicación haga cambios?" en el SECURE DESKTOP — un escritorio aparte que el
# kernel aísla justamente para que ningún programa pueda pulsarlo. Ni ejecutar_en_pc ni
# controlar_pantalla llegan ahí, y no es un fallo de implementación: es el punto entero de esa
# pantalla. Automatizarla significaría que cualquier cosa que comprometiera a AIDEN se daría
# permisos de administrador sola.
#
# La salida: no pelear con ese diálogo, sino no llegar a él. Si AIDEN YA corre elevado, lo que
# habría pedido permiso simplemente no lo pide. Hay dos formas, de menos a más cómoda:
#
#   1. RELANZAR COMO ADMIN: se cierra y se vuelve a abrir pidiendo permiso. Sale UN diálogo, que
#      Marco acepta con la mano. De ahí en adelante, cero. Sirve para ahora mismo.
#   2. TAREA PROGRAMADA con privilegios máximos: Windows lo arranca ya elevado al iniciar sesión,
#      SIN diálogo ninguno. Es la buena para el día a día. Se instala una vez (esa instalación sí
#      pide permiso) y queda.
#
# Correr elevado tiene un precio real y conviene decirlo: todo lo que AIDEN ejecute tendrá permisos
# de administrador, incluido lo que le pida el LLM. La red de seguridad sigue siendo la lista negra
# de Control_Total y el freno de Cancelacion; por eso 'ejecutar_en_pc' no deja de revisar lo que
# corre por estar elevado.

import os
import subprocess
import sys

_NOMBRE_TAREA = "AIDEN_Arranque_Elevado"


def soy_admin():
    """True si este proceso YA corre con permisos de administrador."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _lanzador():
    """El archivo con el que arranca AIDEN (Main_AlwaysOn.py si existe, si no Main.py)."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for nombre in ("Main_AlwaysOn.py", "Main.py"):
        ruta = os.path.join(raiz, nombre)
        if os.path.exists(ruta):
            return raiz, ruta
    return raiz, os.path.join(raiz, "Main.py")


def relanzar_como_admin():
    """Cierra AIDEN y lo vuelve a abrir elevado. Sale UN diálogo de UAC, que Marco acepta."""
    if soy_admin():
        return "Ya estoy corriendo como administrador, señor."
    raiz, guion = _lanzador()
    try:
        import ctypes
        # ShellExecuteW con el verbo "runas" es la forma soportada de pedir elevación. Devuelve
        # >32 si el usuario aceptó; si lo canceló, no se toca nada y AIDEN sigue como estaba.
        r = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{guion}"', raiz, 1)
        if int(r) <= 32:
            return ("No me dio permiso de administrador, señor (o lo canceló). Sigo como estaba; "
                    "todo lo que no necesite permisos funciona igual.")
    except Exception as e:
        return f"No pude pedir la elevación, señor: {e}"

    # La copia elevada ya arranca; esta se retira para no quedar duplicada. Se le da un respiro
    # para que la nueva coja el candado de instancia única.
    def _retirarse():
        import time
        time.sleep(4)
        os._exit(0)

    import threading
    threading.Thread(target=_retirarse, daemon=True).start()
    return "Reabriendo como administrador, señor. Deme un momento."


def instalar_arranque_elevado():
    """Deja a AIDEN arrancando ya elevado al iniciar sesión, SIN diálogo de UAC nunca más.

    Se usa el Programador de tareas porque una tarea con 'privilegios máximos' es la única forma
    soportada de arrancar algo elevado sin que Windows pregunte. Crear la tarea SÍ pide permiso una
    vez (es lo correcto: si no lo pidiera, cualquier programa podría auto-elevarse en silencio)."""
    if not soy_admin():
        return ("Para dejarlo configurado necesito estar como administrador, señor. Primero "
                "dígame que me eleve, y luego repita esta orden.")
    raiz, guion = _lanzador()
    # /RL HIGHEST = privilegios máximos; /SC ONLOGON = al iniciar sesión; /F = reemplaza si existe.
    cmd = ["schtasks", "/create", "/TN", _NOMBRE_TAREA, "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
           "/TR", f'"{sys.executable}" "{guion}"']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return f"No pude crear la tarea de arranque, señor: {e}"
    if r.returncode != 0:
        return f"Windows no aceptó la tarea, señor: {(r.stderr or r.stdout)[:250]}"
    return ("Listo, señor: de ahora en adelante arranco solo al iniciar sesión y ya con permisos "
            "de administrador, sin que Windows le pregunte nada. Si algún día quiere revertirlo, "
            "dígame que quite el arranque automático.")


def quitar_arranque_elevado():
    try:
        r = subprocess.run(["schtasks", "/delete", "/TN", _NOMBRE_TAREA, "/F"],
                           capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return f"No pude quitar la tarea, señor: {e}"
    if r.returncode != 0:
        return "No había ningún arranque automático configurado, señor."
    return "Quitado, señor: ya no arranco solo al iniciar sesión."


def _hay_tarea():
    try:
        r = subprocess.run(["schtasks", "/query", "/TN", _NOMBRE_TAREA],
                           capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
        return r.returncode == 0
    except Exception:
        return False


def permisos(accion="estado"):
    """HERRAMIENTA: los permisos con los que corre AIDEN.
      accion='estado'   -> dice si va como administrador y si arranca elevado solo
      accion='elevar'   -> se reabre como administrador (sale UN diálogo de Windows)
      accion='arranque' -> deja el arranque elevado automático (sin más diálogos)
      accion='quitar_arranque' -> lo revierte"""
    a = str(accion or "estado").strip().lower()
    if a.startswith("elev") or a.startswith("admin") or a.startswith("sube"):
        return relanzar_como_admin()
    if a.startswith("arranq") or a.startswith("instal") or a.startswith("siempre"):
        return instalar_arranque_elevado()
    if a.startswith("quitar") or a.startswith("desinstal") or a.startswith("revert"):
        return quitar_arranque_elevado()

    admin = soy_admin()
    tarea = _hay_tarea()
    partes = ["Corro como ADMINISTRADOR" if admin else "Corro con permisos normales"]
    partes.append("y arranco elevado solo al iniciar sesión" if tarea
                  else "y no tengo arranque automático configurado")
    cola = ""
    if not admin:
        cola = (" Si necesita que haga algo que Windows proteja, dígame que me eleve: le saldrá un "
                "diálogo de permiso, lo acepta, y a partir de ahí no vuelve a preguntarle.")
    return ", ".join(partes) + ", señor." + cola
