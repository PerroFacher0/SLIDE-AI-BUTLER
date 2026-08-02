# AUTO-SÍNTESIS DE MACROS: que resolver algo por VISIÓN una vez sirva para siempre.
#
# El problema: ubicar algo por visión cuesta una consulta a Gemini y ~2 segundos. Si Marco exporta
# el mismo reporte en el mismo programa viejo todos los viernes, AIDEN vuelve a mirar la pantalla,
# vuelve a razonar dónde está cada botón y vuelve a pagar — cada vez, como si fuera la primera.
#
# La idea: Control_Pantalla ya sabe, en cada acción que le sale bien, QUÉ hizo, SOBRE QUÉ y CÓMO lo
# ubicó. Eso se va guardando en un carrete. Cuando la secuencia funciona, Marco dice "guarda eso
# como 'exportar reporte'" y el carrete se compila en una macro reutilizable.
#
# Al reproducirla, cada paso se resuelve por el camino MÁS BARATO que siga siendo correcto:
#   - Lo que se ubicó por NOMBRE se vuelve a buscar por nombre: instantáneo, sin IA, y sigue
#     funcionando aunque la ventana haya cambiado de tamaño o de sitio.
#   - Lo que hubo que ubicar por VISIÓN se reintenta en su posición RELATIVA dentro de la ventana
#     (fracciones 0-1, no píxeles: sobrevive a que la ventana se mueva o se redimensione). Solo si
#     esa ventana ya no está, se vuelve a pagar la visión.
# Así la primera vez cuesta lo que cueste, y de ahí en adelante es gratis e inmediata.

import json
import os
import threading
import time

import win32gui

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "macros.json"
)
_MAX_CARRETE = 40      # pasos recordados hacia atrás (más que eso, ya no es una macro: es un día)
_PAUSA = 0.45          # s entre pasos al reproducir (que la app alcance a reaccionar)

_carrete = []          # lo que AIDEN acaba de hacer bien, en orden
_lock = threading.RLock()

# Acciones que tiene sentido rebobinar. 'ordenar'/'ajustar' dependen del momento, no se graban.
_GRABABLES = ("clic", "doble_clic", "clic_derecho", "escribir", "atajo", "scroll",
              "enfocar", "cerrar_pestana", "seleccionar")


def _ventana_activa():
    """(titulo, (izq, arr, ancho, alto)) de la ventana en primer plano."""
    try:
        h = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(h) or ""
        izq, arr, der, aba = win32gui.GetWindowRect(h)
        return titulo, (izq, arr, max(1, der - izq), max(1, aba - arr))
    except Exception:
        return "", (0, 0, 1, 1)


def _buscar_ventana(titulo):
    """hwnd de la primera ventana visible cuyo título contenga 'titulo', o None."""
    if not titulo:
        return None
    objetivo = titulo.strip().lower()
    encontrada = []

    def _cb(h, _):
        try:
            if win32gui.IsWindowVisible(h):
                t = (win32gui.GetWindowText(h) or "").lower()
                if t and (objetivo in t or t in objetivo):
                    encontrada.append(h)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return None
    return encontrada[0] if encontrada else None


def registrar(tipo, objetivo="", metodo=None, x=None, y=None):
    """Lo llama Control_Pantalla cada vez que una acción SALE BIEN. Guarda lo justo para poder
    repetirla: qué se hizo, sobre qué, cómo se ubicó y dónde cayó dentro de su ventana."""
    if tipo not in _GRABABLES:
        return
    titulo, (izq, arr, ancho, alto) = _ventana_activa()
    paso = {"tipo": tipo, "objetivo": str(objetivo or ""), "metodo": metodo or "",
            "ventana": titulo, "t": time.time()}
    if x is not None and y is not None:
        # Fracción dentro de la ventana: sobrevive a mover o redimensionar; los píxeles no.
        paso["rel"] = [round((x - izq) / ancho, 4), round((y - arr) / alto, 4)]
    with _lock:
        _carrete.append(paso)
        del _carrete[:-_MAX_CARRETE]


# ── Grabar lo que hace MARCO (no lo que hace AIDEN) ──────────────────────────
# El carrete de arriba guarda las acciones de AIDEN. Esto es lo complementario: Marco hace la
# secuencia con su propio mouse y teclado, y AIDEN la aprende mirando. Sirve para lo que AIDEN aún
# no sabe hacer solo, o para programas donde es más rápido enseñárselo que explicárselo.
#
# Lo grabado se guarda en coordenadas RELATIVAS a la ventana (igual que el resto del módulo), no en
# píxeles absolutos: una macro en píxeles se rompe en cuanto la ventana se abre corrida.
_grabacion = {"activa": False, "nombre": "", "pasos": [], "oyentes": [], "texto": ""}


def _cerrar_texto():
    """Junta las teclas sueltas acumuladas en un solo paso de escritura."""
    t = _grabacion["texto"]
    if t:
        _grabacion["pasos"].append({"tipo": "escribir", "objetivo": t, "ventana": ""})
        _grabacion["texto"] = ""


def _al_hacer_clic(x, y, boton, presionado):
    if not presionado or not _grabacion["activa"]:
        return
    _cerrar_texto()
    titulo, (izq, arr, ancho, alto) = _ventana_activa()
    tipo = "clic_derecho" if str(boton).endswith("right") else "clic"
    _grabacion["pasos"].append({
        "tipo": tipo, "objetivo": "", "metodo": "grabado", "ventana": titulo,
        "rel": [round((x - izq) / ancho, 4), round((y - arr) / alto, 4)],
    })


def _al_teclear(tecla):
    if not _grabacion["activa"]:
        return
    nombre = getattr(tecla, "name", None)
    if nombre == "esc":
        detener_grabacion_usuario()          # freno de mano: ESC corta la grabación
        return False
    caracter = getattr(tecla, "char", None)
    if caracter:
        _grabacion["texto"] += caracter
        return
    if nombre in ("space",):
        _grabacion["texto"] += " "
        return
    _cerrar_texto()
    if nombre in ("enter", "tab", "backspace", "delete", "up", "down", "left", "right"):
        _grabacion["pasos"].append({"tipo": "atajo", "objetivo": nombre, "ventana": ""})


def iniciar_grabacion_usuario(nombre):
    """Empieza a mirar el mouse y el teclado de Marco para aprender una secuencia."""
    if _grabacion["activa"]:
        return f"Ya estoy grabando «{_grabacion['nombre']}», señor. Dígame cuándo paro."
    try:
        from pynput import mouse, keyboard
    except Exception:
        return ("No puedo grabar sus acciones, señor: falta la librería. Se instala con: "
                "pip install pynput")
    _grabacion.update({"activa": True, "nombre": nombre, "pasos": [], "texto": "", "oyentes": []})
    try:
        om = mouse.Listener(on_click=_al_hacer_clic)
        ot = keyboard.Listener(on_press=_al_teclear)
        om.start(); ot.start()
        _grabacion["oyentes"] = [om, ot]
    except Exception as e:
        _grabacion["activa"] = False
        return f"No pude empezar a grabar, señor: {e}"
    return (f"Grabando «{nombre}», señor. Haga la secuencia con calma; cuando termine dígame que "
            "pare, o pulse ESC.")


def detener_grabacion_usuario():
    """Cierra la grabación y guarda lo aprendido."""
    if not _grabacion["activa"]:
        return "No estaba grabando nada, señor."
    _grabacion["activa"] = False
    _cerrar_texto()
    for o in _grabacion["oyentes"]:
        try:
            o.stop()
        except Exception:
            pass
    _grabacion["oyentes"] = []
    pasos, nombre = _grabacion["pasos"], _grabacion["nombre"]
    if not pasos:
        return f"No alcancé a ver ninguna acción, señor; no guardo «{nombre}» vacía."
    guardadas = _cargar()
    guardadas[nombre] = {"pasos": pasos, "creada": time.time(), "origen": "marco"}
    if not _guardar_archivo(guardadas):
        return "No pude guardar la macro en disco, señor."
    return (f"Aprendido, señor. «{nombre}» quedó con {len(pasos)} pasos: {_describir(pasos)}. "
            "Dígame 'ejecuta " + nombre + "' cuando la quiera.")


def _cargar():
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def _guardar_archivo(d):
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False


def _describir(pasos):
    partes = []
    for p in pasos:
        o = p.get("objetivo") or ""
        partes.append(f"{p['tipo']}{(' ' + o[:24]) if o else ''}")
    return " → ".join(partes)


# ── Reproducción ──────────────────────────────────────────────────────────────
def _esperar_condicion(p):
    """Espera a que algo ESTÉ LISTO antes de seguir, en vez de dormir un rato fijo y cruzar los
    dedos. Una pausa de 2 segundos funciona el día que la PC va suelta y falla el día que va
    cargada: el paso siguiente se ejecuta contra una ventana que aún no existe y la macro entera
    se descarrilla en silencio. Aquí se espera a la CONDICIÓN, con un tope.

    Devuelve (ok, mensaje)."""
    from Nucleo_Slide import Cancelacion
    from Funciones_Slide.Sistema import Control_Pantalla as CP

    que = str(p.get("esperar") or "").strip().lower()
    valor = str(p.get("objetivo") or "").strip()
    try:
        tope = max(1, min(120, int(p.get("timeout", 15))))
    except (TypeError, ValueError):
        tope = 15
    if not valor:
        return True, "espera sin objetivo (omitida)"

    limite = time.time() + tope
    while time.time() < limite:
        if Cancelacion.cancelado():
            return False, "cancelado por Marco"
        try:
            if que.startswith("proc"):
                import psutil
                objetivo_n = valor.lower().removesuffix(".exe")
                for pr in psutil.process_iter(["name"]):
                    if objetivo_n in (pr.info["name"] or "").lower().removesuffix(".exe"):
                        return True, f"apareció el proceso {valor}"
            elif que.startswith("vent"):
                if _buscar_ventana(valor) is not None:      # el mismo buscador del reproductor
                    return True, f"apareció la ventana «{valor}»"
            elif que.startswith("elem"):
                xy, _n = CP._ubicar_por_nombre(CP._norm(valor))   # sin gastar visión
                if xy:
                    return True, f"apareció «{valor}» en pantalla"
            else:
                return True, f"no sé esperar «{que}» (omitida)"
        except Exception:
            pass
        time.sleep(0.2)
    return False, f"esperé {tope} segundos a que apareciera «{valor}» y no apareció"


def _reproducir_paso(p):
    """Ejecuta un paso por el camino más barato que siga siendo correcto."""
    from Funciones_Slide.Sistema import Control_Pantalla as CP

    tipo, objetivo = p.get("tipo"), p.get("objetivo", "")

    # Teclado y scroll no dependen de dónde esté nada: se repiten tal cual.
    if tipo in ("escribir", "atajo", "tecla", "scroll", "cerrar_pestana", "seleccionar", "enfocar"):
        return CP._despachar("atajo" if tipo == "tecla" else tipo, objetivo)

    # Asegura que estemos en la ventana correcta antes de tocar nada.
    hwnd = _buscar_ventana(p.get("ventana", ""))
    if hwnd:
        try:
            win32gui.ShowWindow(hwnd, 9)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.25)
        except Exception:
            pass

    mapa = {"clic": "clic", "doble_clic": "doble", "clic_derecho": "derecho"}
    variante = mapa.get(tipo, "clic")

    # Lo que se ubicó por NOMBRE se vuelve a buscar por nombre: gratis y robusto.
    if p.get("metodo") == "estructura" and objetivo:
        return CP._clic_en(objetivo, variante)

    # Lo que costó VISIÓN: reintento en su posición relativa dentro de la ventana (gratis).
    rel = p.get("rel")
    if rel and hwnd and CP.pyautogui is not None:
        try:
            izq, arr, der, aba = win32gui.GetWindowRect(hwnd)
            x = round(izq + rel[0] * max(1, der - izq))
            y = round(arr + rel[1] * max(1, aba - arr))
            CP.pyautogui.moveTo(x, y, duration=0.3)
            if variante == "doble":
                CP.pyautogui.doubleClick()
            elif variante == "derecho":
                CP.pyautogui.rightClick()
            else:
                CP.pyautogui.click()
            return f"clic en la posición recordada de «{objetivo or 'el punto'}»"
        except Exception:
            pass

    # Última opción: volver a pagar la visión.
    if objetivo:
        return CP._clic_en(objetivo, variante)
    return "paso omitido (no supe repetirlo)"


def macro(accion, nombre="", pasos=0):
    """HERRAMIENTA: convierte en macro reutilizable lo que AIDEN acaba de hacer en pantalla, y la
    vuelve a ejecutar cuando Marco la pida por su nombre.
      accion = guardar | ejecutar | listar | borrar
      nombre = cómo se llama la macro
      pasos  = cuántas de las últimas acciones incluir al guardar (0 = todo el carrete)."""
    from Nucleo_Slide import Cancelacion

    a = str(accion or "").strip().lower()
    nombre = str(nombre or "").strip()
    guardadas = _cargar()

    if a.startswith("grab") or a.startswith("mira") or a.startswith("aprende_vien"):
        if not nombre:
            return "¿Con qué nombre grabo lo que va a hacer, señor?"
        return iniciar_grabacion_usuario(nombre)

    if a.startswith("deten") or a.startswith("para") or a.startswith("termina"):
        return detener_grabacion_usuario()

    if a.startswith("list"):
        if not guardadas:
            return "Aún no tengo macros guardadas, señor."
        return "Macros guardadas, señor: " + "; ".join(
            f"«{n}» ({len(d.get('pasos', []))} pasos)" for n, d in guardadas.items())

    if a.startswith("borr") or a.startswith("elimin"):
        if nombre not in guardadas:
            return f"No tengo ninguna macro llamada «{nombre}», señor."
        guardadas.pop(nombre)
        _guardar_archivo(guardadas)
        return f"Borré la macro «{nombre}», señor."

    if a.startswith("guard") or a.startswith("aprend"):
        if not nombre:
            return "¿Con qué nombre la guardo, señor?"
        with _lock:
            recientes = list(_carrete)
        if not recientes:
            return ("No tengo nada que guardar, señor: no he hecho ninguna acción en pantalla "
                    "todavía. Pídame la secuencia primero y luego le pongo nombre.")
        try:
            n = int(pasos)
        except (TypeError, ValueError):
            n = 0
        elegidos = recientes[-n:] if n > 0 else recientes
        guardadas[nombre] = {"pasos": elegidos, "creada": time.time()}
        if not _guardar_archivo(guardadas):
            return "No pude guardar la macro en disco, señor."
        return (f"Guardado, señor. La macro «{nombre}» tiene {len(elegidos)} pasos: "
                f"{_describir(elegidos)}. La próxima vez la hago de una, sin volver a analizarla.")

    if a.startswith("ejecut") or a.startswith("corr") or a.startswith("repet"):
        d = guardadas.get(nombre)
        if not d:
            if guardadas:
                return (f"No tengo una macro llamada «{nombre}», señor. Tengo: "
                        + ", ".join(f"«{n}»" for n in guardadas))
            return f"No tengo una macro llamada «{nombre}», señor, ni ninguna otra guardada."
        lista = d.get("pasos", [])
        if not lista:
            return f"La macro «{nombre}» está vacía, señor."
        hechos, fallos = 0, []
        try:
            with Cancelacion.operacion(f"la macro «{nombre}»"):
                for i, p in enumerate(lista, 1):
                    Cancelacion.revisar()
                    # Un paso de ESPERA que no se cumple ABORTA la macro. Seguir después de que
                    # algo no apareció es ejecutar a ciegas contra una pantalla que no es la que
                    # la macro esperaba: en el mejor caso no hace nada, en el peor clica encima
                    # de otra cosa.
                    if p.get("tipo") == "esperar" or p.get("esperar"):
                        ok, motivo = _esperar_condicion(p)
                        if not ok:
                            return (f"La macro «{nombre}» se detuvo en el paso {i}, señor: "
                                    f"{motivo}.")
                        hechos += 1
                        continue
                    r = _reproducir_paso(p)
                    if "No encontré" in r or "No pude" in r or "omitido" in r:
                        fallos.append(f"paso {i} ({p.get('tipo')} {p.get('objetivo', '')[:20]})")
                    else:
                        hechos += 1
                    time.sleep(_PAUSA)
        except Cancelacion.Cancelado:
            return f"Detuve la macro «{nombre}» en el paso {hechos + 1}, señor."
        if fallos:
            return (f"Ejecuté «{nombre}»: {hechos} de {len(lista)} pasos, señor. "
                    f"Se me atravesaron: {', '.join(fallos[:3])}.")
        return f"Listo, señor: ejecuté «{nombre}» completa ({hechos} pasos)."

    return "¿Qué hago con la macro, señor? (guardar, ejecutar, listar o borrar)"
