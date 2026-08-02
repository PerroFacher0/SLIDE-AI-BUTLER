import os
import json
from datetime import datetime
from Funciones_Slide.Sistema.Funciones_Sistema import obtener_clima


def briefing():
    ahora = datetime.now()
    if ahora.hour < 12:
        saludo = "Buenos dias"
    elif ahora.hour < 19:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"
    hora = ahora.strftime("%H:%M")
    clima = obtener_clima("Bogota")
    pendientes = 0
    try:
        from Funciones_Slide.Productividad.Gestion_datos import leer_tareas
        pendientes = sum(1 for t in leer_tareas() if t.get("estado") == "pendiente")
    except Exception:
        pendientes = 0
    return f"{saludo} Marco. Son las {hora}. {clima}. Tiene {pendientes} recordatorios pendientes."
