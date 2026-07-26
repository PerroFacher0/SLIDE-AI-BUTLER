import json
import os
from datetime import datetime

# El archivo donde viven los recuerdos (en la raiz del proyecto).
_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memoria.json"
)

_MAX_RECUERDOS = 200   # tope para que no crezca sin control


def _cargar():
    # Lee los recuerdos y los NORMALIZA a dicts {texto, fecha, categoria}.
    # Compatible hacia atras: si el json viejo tenia strings, los convierte.
    if not os.path.exists(_RUTA):
        return []
    try:
        with open(_RUTA, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    normalizados = []
    for d in datos:
        if isinstance(d, str):
            texto = d.strip()
            if texto:
                normalizados.append({"texto": texto, "fecha": "", "categoria": "general"})
        elif isinstance(d, dict) and d.get("texto"):
            normalizados.append({
                "texto": str(d["texto"]).strip(),
                "fecha": d.get("fecha", ""),
                "categoria": (d.get("categoria") or "general"),
            })
    return normalizados


def _guardar(datos):
    with open(_RUTA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)


def recordar(dato, categoria="general"):
    # Herramienta del LLM: guarda un dato nuevo en la memoria permanente,
    # con fecha y una categoria opcional (ej. 'gustos', 'estudios', 'fechas').
    datos = _cargar()
    dato = str(dato).strip()
    if not dato:
        return "No había nada que recordar, señor."

    # deduplicacion: evita guardar lo mismo o algo ya contenido
    d_low = dato.lower()
    for d in datos:
        existente = d["texto"].lower()
        if d_low == existente or d_low in existente or existente in d_low:
            return "Eso ya lo tenía presente, señor."

    datos.append({
        "texto": dato,
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "categoria": str(categoria or "general").strip().lower(),
    })
    datos = datos[-_MAX_RECUERDOS:]
    _guardar(datos)
    return f"Anotado, señor. Lo recordaré: {dato}"


def olvidar(dato):
    # Herramienta del LLM: borra de la memoria los recuerdos que coincidan con 'dato'.
    datos = _cargar()
    dato = str(dato).strip().lower()
    if not dato:
        return "No me dijiste qué olvidar, señor."
    quedan = [d for d in datos if dato not in d["texto"].lower()]
    eliminados = len(datos) - len(quedan)
    if eliminados == 0:
        return "No tenía nada parecido guardado, señor."
    _guardar(quedan)
    return f"Listo, señor. Olvidé {eliminados} recuerdo(s) relacionado(s) con eso."


def memoria(accion="recordar", dato="", categoria="general"):
    """HERRAMIENTA unificada de memoria permanente. accion 'recordar' (por defecto) guarda un dato
    sobre Marco; accion 'olvidar' borra los que coincidan. Reemplaza recordar + olvidar sin perder nada."""
    a = str(accion or "").strip().lower()
    if a in ("olvidar", "borrar", "eliminar", "quitar"):
        return olvidar(dato)
    return recordar(dato, categoria)


def obtener_memoria_texto():
    # Devuelve los recuerdos listos para inyectar en el system prompt,
    # agrupados por categoria para que AIDEN los use mejor.
    datos = _cargar()
    if not datos:
        return "(aún no tienes datos guardados de Marco)"

    por_categoria = {}
    for d in datos:
        cat = d.get("categoria") or "general"
        por_categoria.setdefault(cat, []).append(d["texto"])

    lineas = []
    for cat in sorted(por_categoria):
        if cat != "general":
            lineas.append(f"[{cat}]")
        for texto in por_categoria[cat]:
            lineas.append(f"- {texto}")
    return "\n".join(lineas)
