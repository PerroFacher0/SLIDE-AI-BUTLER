# MOTOR DE AUTONOMÍA HÍBRIDA — capa cognitiva que decide POR DEBAJO del LLM principal si una orden
# se resuelve más rápido/seguro con SCRIPTS DE SISTEMA (Gestor_Archivos/ejecutar_en_pc: invisible,
# instantáneo, sin depender de qué se vea en pantalla) o si de verdad necesita la vía VISUAL
# (controlar_pantalla/navegar_web: cuando hay que interactuar con una interfaz gráfica concreta,
# como un instalador o un formulario web).
#
# NO es una puerta rígida: para el caso obvio (archivos/carpetas/rutas) resuelve al toque sin
# gastar un solo token de LLM — el mismo espíritu "reflejo instantáneo" que Peticiones.py ya usa
# para atajos de voz. Para lo ambiguo, devuelve "ambiguo" y deja que el LLM principal decida con
# su propio criterio (tiene ambas herramientas en su esquema); esto NUNCA le quita esa libertad.
#
# El PILAR 3 (self-healing) vive aquí también: ejecutar_con_resguardo() intenta la vía que el
# enrutador sugirió y, si es la visual y FALLA (vision no encontró el elemento), reintenta sola
# por la vía de sistema antes de darle a Marco un error — igual que un humano probaría "a mano"
# si el clic no funcionó.

import re

# Señales de que la orden es un asunto de SISTEMA DE ARCHIVOS: se puede resolver sin ver nada en
# pantalla (buscar/mover/copiar/leer metadatos), más rápido y más seguro por scripts.
_PATRON_SISTEMA = re.compile(
    r"\b(archivo|archivos|carpeta|carpetas|mover|mueve|copiar|copia|renombrar|"
    r"appdata|documentos|descargas|escritorio|mods?\b|instalador|"
    r"\.exe|\.msi|\.zip|\.rar|\.txt|\.docx?|\.pdf|\.mp3|\.mp4|\.jpg|\.png|"
    r"disco duro|todo el disco|c:\\|d:\\|ruta)\b",
    re.I,
)
# Señales de que la orden necesita de verdad la vía VISUAL: interactuar con algo que solo existe
# EN PANTALLA (un botón concreto de una app, un formulario web, un elemento sin API accesible).
_PATRON_VISUAL = re.compile(
    r"\b(haz clic|hazle clic|haz doble clic|clic derecho|arrastra|arrastrar|"
    r"en la pantalla|en pantalla|en el navegador|en la p[aá]gina|scrollea|scroll|"
    r"esa ventana|la ventana que|lo que tengo abierto|lo que veo en)\b",
    re.I,
)


def enrutar_tarea(orden):
    """Clasifica 'orden' en 'sistema' | 'visual' | 'ambiguo'. Heurística SIN LLM (instantánea);
    'ambiguo' significa "no está claro, que decida el LLM principal con su propio criterio" — esto
    NUNCA es una decisión final, solo un sesgo rápido para el caso obvio."""
    o = str(orden or "")
    hay_sistema = bool(_PATRON_SISTEMA.search(o))
    hay_visual = bool(_PATRON_VISUAL.search(o))
    if hay_sistema and not hay_visual:
        return "sistema"
    if hay_visual and not hay_sistema:
        return "visual"
    return "ambiguo"   # ambas señales, o ninguna: que decida el LLM principal


_PATRON_FALLO_VISUAL = re.compile(
    r"no encontr[eé].*(pantalla|p[aá]gina)|no pude hacer clic|no pude arrastrarlo", re.I,
)


def _parece_fallo_visual(resultado):
    return bool(_PATRON_FALLO_VISUAL.search(str(resultado or "")))


def ejecutar_con_resguardo(accion_visual, accion_sistema, descripcion=""):
    """PILAR 3 — SELF-HEALING: ejecuta 'accion_visual' (función sin argumentos, ya con sus
    parámetros aplicados) que representa la vía visual elegida por el enrutador. Si el resultado
    tiene cara de fallo de visión (patrón conocido: "no encontré X en pantalla"), reintenta
    AUTOMÁTICAMENTE con 'accion_sistema' (función sin argumentos) antes de devolver un error a
    Marco. Si 'accion_sistema' es None, no hay a dónde caer y se devuelve el fallo visual tal cual.
    Nunca deja pasar una excepción cruda: cualquier error se convierte en un mensaje claro."""
    try:
        resultado_visual = accion_visual()
    except Exception as e:
        resultado_visual = f"no encontré nada en pantalla (excepción de visión: {e})"
    if not _parece_fallo_visual(resultado_visual):
        return resultado_visual
    if accion_sistema is None:
        return resultado_visual
    try:
        resultado_sistema = accion_sistema()
    except Exception as e:
        return (f"La vía visual falló{(' para ' + descripcion) if descripcion else ''} y el "
                f"respaldo de sistema también dio error, señor: {e}")
    prefijo = "La vía visual no encontró el elemento, así que lo resolví por sistema: "
    return prefijo + str(resultado_sistema)
