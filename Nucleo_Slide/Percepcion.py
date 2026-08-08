# PERCEPCIÓN: los SENTIDOS locales de AIDEN sobre el PC de Marco, en un solo lugar.
#
# El salto de feeling: antes la "foto del PC" (ventana activa, apps, portapapeles) solo la veía la
# Conciencia cada tantos minutos. Ahora el CEREBRO la recibe en CADA turno de conversación: cuando
# Marco dice "cierra eso", "¿qué opinas de esto?", "lo que estoy viendo", AIDEN YA SABE a qué se
# refiere — sin herramientas, sin preguntar. Es darle acceso permanente a la PC como sensación.
#
# Barato a propósito: solo win32gui/pyperclip/psutil locales (cero LLM, cero red) y con caché de
# unos segundos para no enumerar ventanas en cada frase.

import re
import threading
import time

_lock = threading.Lock()
_cache = {"t": 0.0, "texto": ""}
_TTL = 5.0   # segundos de vigencia de la foto


def ventana_activa():
    try:
        import win32gui
        return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or "(escritorio)"
    except Exception:
        return "(desconocida)"


def apps_abiertas(maximo=10):
    titulos = []
    try:
        import win32gui

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t and t.strip():
                    titulos.append(t.strip())

        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
    vistos, salida = set(), []
    for t in titulos:
        if t not in vistos:
            vistos.add(t)
            salida.append(t)
    return salida[:maximo]


def _portapapeles():
    try:
        import pyperclip
        clip = (pyperclip.paste() or "").strip().replace("\n", " ")
        return clip[:100]
    except Exception:
        return ""


def _energia():
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat is not None:
            return f"batería {int(bat.percent)}%" + ("" if bat.power_plugged else " SIN cargador")
    except Exception:
        pass
    return ""


# Lo que Marco dice cuando lo que le importa es lo que tiene copiado.
_APUNTA_AL_CLIP = ("esto", "eso", "lo que copie", "lo que copié", "portapapeles", "copiado",
                   "traduce", "traduc", "resume esto", "que significa", "qué significa",
                   "explicame esto", "explícame esto", "corrige")


def clip_completo(limite=1500):
    """El portapapeles ENTERO, no los 100 caracteres del resumen."""
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()[:limite]
    except Exception:
        return ""


# ── ¿ESTÁ HABLANDO DE LO QUE TIENE DELANTE? ──────────────────────────────────
#
# "¿por qué no compila?" no lleva ningún "esto" ni "eso" — no hay pronombre que agarrar — y aun así
# se refiere clarísimamente a lo que Marco tiene en pantalla. La regla que ya existía en el system
# prompt se apoyaba en los demostrativos, así que esta clase de frase se le escapaba y AIDEN podía
# contestar "¿qué error?" en vez de mirar.
#
# Lo que se hace con la detección importa tanto como la detección. Se puede EJECUTAR `analizar`
# sola, o AVISAR al modelo de que probablemente toque mirar. Se eligió avisar, y no por timidez:
# ejecutarla equivocándose cuesta una captura de pantalla y una llamada a Vision que Marco no pidió
# — dinero, un par de segundos, y una foto de su pantalla por una corazonada. Avisando, un fallo
# cuesta una frase que el modelo ignora. Misma detección, sin nada que perder cuando se equivoca.
_DEMOSTRATIVOS = ("esto", "eso", "esta", "este", "aqui", "aquí", "ahi", "ahí", "asi", "así")
# "arréglalo", "termínalo", "explícamelo": el pronombre va PEGADO al verbo y no hay objeto.
_CLITICOS = re.compile(r"\b\w{3,}(lo|la|melo|mela)\b")
# Hablar del ESTADO de algo que solo se puede ver: no hace falta demostrativo.
_ESTADO_VISIBLE = ("compila", "falla", "error", "esta mal", "está mal", "esta bien", "está bien",
                   "no funciona", "no anda", "no sirve", "se rompio", "se rompió")
# Si el verbo YA tiene su herramienta, el demostrativo no significa "mira": "cierra eso" es
# control_ventana, no visión.
_CON_TOOL_PROPIA = ("cierra", "cerra", "sube", "baja", "quita", "pon ", "abre", "guarda", "manda",
                    "envia", "envía", "copia", "apaga", "reinicia", "silencia", "borra", "mueve",
                    "busca", "reproduce", "programa")
# "este mes", "esta semana": el demostrativo va con tiempo, no señala la pantalla.
_TIEMPO = ("mes", "ano", "año", "semana", "dia", "día", "rato", "momento", "vez", "tarde",
           "manana", "mañana", "noche", "hora")
_MAX_PALABRAS = 6      # más que esto y la frase ya dice de qué habla


def apunta_a_la_pantalla(consulta=""):
    """True si la frase se refiere a algo VISIBLE sin decir qué es."""
    t = " " + str(consulta or "").lower().strip() + " "
    if any(v in t for v in _CON_TOOL_PROPIA):
        return False
    if len(t.split()) > _MAX_PALABRAS:
        return False
    for d in _DEMOSTRATIVOS:
        i = t.find(f" {d} ")
        if i < 0:
            continue
        siguiente = t[i + len(d) + 2:].split()
        if siguiente and siguiente[0] in _TIEMPO:
            continue
        return True
    if _CLITICOS.search(t):
        return True
    return any(e in t for e in _ESTADO_VISIBLE)


def contexto_del_turno(consulta=""):
    """Lo que conviene añadir al prompt SABIENDO ya lo que pidió Marco.

    La percepción normal recorta el portapapeles a 100 caracteres — bien, porque va en TODOS los
    turnos y casi ninguno trata de eso. Pero cuando Marco dice "traduce esto", esos 100 caracteres
    no le alcanzan al modelo, así que pide `leer_portapapeles`... y eso es una ronda entera de ida
    y vuelta con el modelo. Adelantarlo cuando su frase apunta al portapapeles se ahorra el viaje
    completo, que es de segundos, no de milisegundos."""
    t = str(consulta or "").lower()
    trozos = []

    # 1) ¿Habla de lo que TIENE DELANTE sin decir qué es?
    #
    # Aquí hay DOS formas de enterarse y una es mucho mejor que la otra. Si AIDEN acaba de ejecutar
    # algo que falló, tiene el stderr EXACTO en memoria: texto literal, gratis, sin ambigüedad.
    # Mirar la pantalla para leer ese mismo error sería sacarle una foto a un papel que ya tiene en
    # la mano — cuesta una captura, una llamada a Vision, un par de segundos, y encima puede leerlo
    # mal. Así que el texto GANA siempre que exista y sea reciente; la visión queda para cuando no
    # hay texto, que es la mayoría de las veces (un error del IDE, algo que Marco abrió él).
    if apunta_a_la_pantalla(consulta):
        delta = None
        try:
            from Nucleo_Slide.Ultimo_Error import reciente
            delta = reciente()
        except Exception:
            delta = None
        if delta:
            texto, de, edad = delta
            trozos.append(
                f"EL ÚLTIMO ERROR (lo tienes literal, de {de}, hace {int(edad)}s). Marco pregunta "
                "algo vago y casi seguro habla de esto. Respóndele con este texto: NO hace falta "
                f"analizar la pantalla ni pedirle que lo copie.\n{texto}\n"
                "Si al leerlo ves que no era de esto que hablaba, entonces sí mira la pantalla."
            )
        else:
            trozos.append(
                "AVISO: la frase de Marco no dice a QUÉ se refiere, y lo normal es que sea algo "
                "que tiene EN PANTALLA. Tu primera acción debe ser analizar(fuente='pantalla') "
                "para verlo — no le preguntes a qué se refiere. Si al mirarlo resulta que no era "
                "eso, sigue con lo que sí encaje."
            )

    # 2) ¿Habla de lo que tiene COPIADO? (el resumen de siempre solo lleva 100 caracteres)
    if any(p in t for p in _APUNTA_AL_CLIP):
        clip = clip_completo()
        if len(clip) > 100:
            trozos.append("PORTAPAPELES COMPLETO (Marco parece estar hablando de esto; ya lo "
                          "tienes, NO llames a leer_portapapeles):\n" + clip)
    return "\n\n".join(trozos)


def percepcion_compacta():
    """La vista de AIDEN sobre el PC AHORA, compacta para el prompt (con caché de unos segundos)."""
    ahora = time.time()
    with _lock:
        if ahora - _cache["t"] < _TTL:
            return _cache["texto"]
    lineas = [f"Ventana activa (lo que Marco tiene al frente): {ventana_activa()}"]
    apps = apps_abiertas(8)
    if apps:
        lineas.append("Abierto en su PC: " + " | ".join(apps))
    clip = _portapapeles()
    if clip:
        lineas.append(f"Portapapeles (lo último que copió): {clip}")
    e = _energia()
    if e:
        lineas.append(f"Energía: {e}")
    texto = "\n".join(lineas)
    with _lock:
        _cache.update(t=ahora, texto=texto)
    return texto
