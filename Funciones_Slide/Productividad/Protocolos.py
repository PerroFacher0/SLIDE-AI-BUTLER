# PROTOCOLOS: rutinas que se disparan con UNA frase.
#
# Dos clases:
#   - FIJOS (cine, noche, concentración, normal): acciones directas de sistema, sin LLM.
#   - PERSONALIZADOS ("Prepárame el Mark VII"): Marco se los ENSEÑA por voz ("crea un protocolo
#     'modo estudio': cierra YouTube, abre Notion y pon lo-fi") y quedan guardados PARA SIEMPRE en
#     protocolos.json. Al activarlos, el resultado le ordena al cerebro ejecutar los pasos AHORA con
#     sus herramientas (el bucle multi-tool del cerebro hace la orquesta; aquí no se llama al LLM).

import json
import os
import threading
from datetime import datetime

from Funciones_Slide.Sistema.Modos import _notificaciones_windows
from Funciones_Slide.Productividad.Alertas_Mercado import pausar_alertas
from Funciones_Slide.Sistema.Control_PC import ajustar_brillo
from Funciones_Slide.Sistema.Funciones_Sistema import subir_volumen, silenciar

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "protocolos.json"
)
_lock = threading.RLock()
_MAX_PROTOCOLOS = 20

_TILDES = str.maketrans("áéíóúüñ", "aeiouun")


def _clave(nombre):
    # nombre normalizado (sin tildes, minúsculas) para buscar sin fricción por voz
    return str(nombre or "").strip().lower().translate(_TILDES)


def _cargar():
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def _guardar(datos):
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def protocolo(accion="activar", nombre="", pasos=""):
    """HERRAMIENTA única de protocolos (escenas que cambian varias cosas a la vez).
      accion='activar' -> dispara uno: 'cine', 'buenas noches', 'concentración', 'normal', o
                          cualquiera que Marco haya enseñado.
      accion='crear'   -> Marco ENSEÑA una rutina nueva ('crea un protocolo modo estudio: cierra
                          YouTube, abre Notion y pon lo-fi'). Queda guardada para siempre.
      accion='borrar'  -> la elimina.    accion='listar' -> dice cuáles hay.

    Antes eran dos herramientas, 'activar_protocolo' y 'crear_protocolo'. La herramienta 'macro' —
    que hace exactamente lo mismo con otra clase de rutina — ya vivía en UNA sola con acciones
    guardar/ejecutar/listar/borrar. Esto solo pone los protocolos en el mismo molde."""
    a = str(accion or "activar").strip().lower()
    if a.startswith("crear") or a.startswith("enseñ") or a.startswith("ensen") or a.startswith("aprend"):
        return crear_protocolo(nombre, pasos)
    if a.startswith("borr") or a.startswith("elimin"):
        return crear_protocolo(nombre, eliminar=True)
    if a.startswith("list"):
        return _listar()
    return activar_protocolo(nombre)


def crear_protocolo(nombre, pasos="", eliminar=False):
    """HERRAMIENTA: Marco te ENSEÑA una rutina con nombre ('crea un protocolo modo estudio: ...').
    Se guarda para siempre; luego la activa diciendo el nombre. eliminar=True la borra."""
    n = _clave(nombre)
    if not n:
        return "Necesito un nombre para el protocolo, señor."
    with _lock:
        datos = _cargar()
        if eliminar:
            if n in datos:
                del datos[n]
                _guardar(datos)
                return f"Protocolo '{nombre}' eliminado, señor. Como si nunca hubiera existido."
            return f"No tengo un protocolo llamado '{nombre}', señor."
        pasos = str(pasos or "").strip()
        if not pasos:
            return "Dígame los pasos del protocolo, señor (qué debo hacer, en orden)."
        if len(datos) >= _MAX_PROTOCOLOS and n not in datos:
            return f"Ya tengo {_MAX_PROTOCOLOS} protocolos, señor. Elimine alguno antes de crear otro."
        nuevo = n not in datos
        datos[n] = {"pasos": pasos[:500], "creado": datetime.now().strftime("%d/%m/%Y")}
        _guardar(datos)
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Protocolo {'creado' if nuevo else 'actualizado'}: {n}", "protocolos")
    except Exception:
        pass
    if nuevo:
        return (f"Protocolo '{nombre}' aprendido, señor. Cuando diga '{nombre}', ejecutaré: {pasos}. "
                "Como el Mark 7, pero sin la armadura.")
    return f"Protocolo '{nombre}' actualizado, señor."


def _listar():
    datos = _cargar()
    fijos = "cine, buenas noches, concentración, normal"
    if not datos:
        return (f"Tengo los protocolos de fábrica: {fijos}. Y puede enseñarme los suyos: "
                "'crea un protocolo <nombre>' y me dice los pasos.")
    propios = "; ".join(f"'{k}' ({v.get('pasos', '')[:60]}...)" if len(v.get('pasos', '')) > 60
                        else f"'{k}' ({v.get('pasos', '')})" for k, v in datos.items())
    return f"Protocolos de fábrica: {fijos}. Los suyos: {propios}."


def activar_protocolo(nombre):
    n = _clave(nombre)

    if any(k in n for k in ("lista", "listar", "cuales", "que protocolos", "mis protocolos")):
        return _listar()

    # PERSONALIZADOS primero: lo que Marco enseñó manda sobre lo de fábrica.
    datos = _cargar()
    encontrado = datos.get(n)
    if encontrado is None:
        # tolerancia: "activa modo estudio" vs guardado "modo estudio" (subcadena en ambos sentidos)
        for k, v in datos.items():
            if k and (k in n or n in k):
                encontrado = v
                n = k
                break
    if encontrado is not None:
        try:
            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
            registrar_evento(f"Protocolo activado: {n}", "protocolos")
        except Exception:
            pass
        # El cerebro recibe esto como resultado y ORQUESTA los pasos con sus herramientas.
        return (f"PROTOCOLO PERSONALIZADO '{n}' ACTIVADO. EJECUTA AHORA, en orden y con tus "
                f"herramientas, estos pasos que Marco te enseñó; al final confirma en UNA frase "
                f"corta con tu estilo: {encontrado.get('pasos', '')}")

    if "cine" in n or "pelicula" in n:
        _notificaciones_windows(False)
        pausar_alertas(True)
        ajustar_brillo("bajar")
        try:
            subir_volumen(0.2)
        except Exception:
            pass
        return ("Protocolo cine activado, señor. Bajé el brillo, subí el volumen y silencié las "
                "interrupciones. Que disfrute.")

    if "noche" in n or "dormir" in n:
        _notificaciones_windows(False)
        pausar_alertas(True)
        try:
            silenciar()
        except Exception:
            pass
        return "Buenas noches, señor. Silencié todo y dejé el equipo en calma. Que descanse."

    if "concentr" in n or "estudio" in n or "enfoque" in n or "trabajo" in n:
        _notificaciones_windows(False)
        pausar_alertas(True)
        return ("Protocolo de concentración activado, señor. Sin notificaciones ni interrupciones. "
                "A darle con todo.")

    if "normal" in n or "desactivar" in n or "fin" in n or "terminar" in n:
        _notificaciones_windows(True)
        pausar_alertas(False)
        return "Protocolos desactivados, señor. Todo vuelve a la normalidad."

    return ("No conozco ese protocolo, señor. " + _listar())
