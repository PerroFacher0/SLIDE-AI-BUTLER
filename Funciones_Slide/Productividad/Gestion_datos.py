import json
import os 
import webbrowser
import pyautogui
import time
import importlib
from Nucleo_Slide import Auto_Programacion


# RUTA ABSOLUTA, y una sola para todo el proyecto. Antes cada módulo abría "tareas.json" a secas,
# que se resuelve contra el DIRECTORIO DE TRABAJO, no contra el proyecto. Mientras AIDEN se lance
# desde su carpeta funciona; en cuanto arranca desde un acceso directo, desde el inicio automático
# o desde el Programador de tareas (que suele situarse en system32), deja de encontrar el archivo
# y los recordatorios y mensajes agendados se pierden SIN avisar. Cuatro módulos distintos tenían
# la misma cadena suelta; ahora todos importan esta.
RUTA_TAREAS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tareas.json"
)


def leer_tareas():
    """Las tareas pendientes. Lista vacía si el archivo aún no existe o está corrupto."""
    try:
        with open(RUTA_TAREAS, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except Exception:
        return []


def escribir_tareas(tareas):
    # ensure_ascii=False: el archivo lo puede abrir Marco y ver "señor", no "señor".
    with open(RUTA_TAREAS, "w", encoding="utf-8") as f:
        json.dump(tareas, f, indent=4, ensure_ascii=False)


def guardar_en_json(accion,target,info,hora):
    tareas = leer_tareas()

    nueva_tarea = {
        "accion": accion,
        "target": target,
        "info": info,
        "hora": hora,
        "estado": "pendiente"
    }
    tareas.append(nueva_tarea)
    escribir_tareas(tareas)





