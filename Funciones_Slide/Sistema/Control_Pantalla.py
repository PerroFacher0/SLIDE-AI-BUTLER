# Control VISIBLE de la pantalla: AIDEN se mete con la PC y lo VES.
#   - clic: PRIMERO busca un botón/elemento por su nombre (UI Automation, rápido, sin LLM). Si
#     no lo encuentra (juegos, apps de lienzo, botones sin nombre accesible), cae a VISIÓN: mira
#     la pantalla, ubica el objetivo por su descripción y calcula el punto exacto. Así cubre
#     CUALQUIER cosa visible, no solo lo que Windows sabe nombrar — el respaldo por visión tarda
#     un poco más (una consulta al modelo), pero nada se queda fuera de alcance.
#   - arrastrar: localiza origen y destino (por nombre o visión) y hace drag real del mouse.
#   - ajustar: MIRA-MUEVE-REMIRA. Para lo que no se acierta de un solo clic (un slider "hasta que
#     se vea bien"): arrastra un poco, vuelve a mirar la pantalla y corrige, hasta lograrlo.
#   - ordenar: acomoda tus ventanas en mosaico (las ves reorganizarse).
#   - enfocar: trae una app al frente.
# Una sola herramienta `interactuar_pc(accion, objetivo)` (estilo anti-bloat del proyecto).
#
# VARIAS PANTALLAS: todo esto trabaja sobre el ESCRITORIO VIRTUAL (la caja que engloba todos los
# monitores), no sobre el principal. Dos correcciones que antes rompían el clic en la 2ª pantalla:
#   1. Se declara el proceso "per-monitor DPI aware" ANTES de tocar nada. Sin esto Windows miente:
#      con la pantalla al 150% devuelve coordenadas escaladas y el cursor caía desplazado.
#   2. La captura toma TODOS los monitores (all_screens) y se guarda el ORIGEN del escritorio
#      virtual, que es NEGATIVO si hay un monitor a la izquierda del principal. Las coordenadas
#      normalizadas (0-1000) del modelo se convierten contra ese origen, no contra (0,0).

import re
import threading
import time

import win32gui

from Nucleo_Slide import Cancelacion

_lock_indices = threading.RLock()   # la lista de la capa de rayos X la leen el LLM y el HUD


# ── DPI: hay que declararlo ANTES de la primera captura o consulta de tamaño ──
def _hacerse_dpi_aware():
    import ctypes
    try:
        # PER_MONITOR_AWARE_V2 (-4): cada monitor con su propio factor de escala. Windows 10 1703+.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()        # respaldo antiguo (system-aware)
    except Exception:
        pass


_hacerse_dpi_aware()


def _escritorio_virtual():
    """(x, y, ancho, alto) de la caja que engloba TODOS los monitores. El origen puede ser
    negativo si hay una pantalla a la izquierda o encima de la principal."""
    try:
        import win32api
        return (win32api.GetSystemMetrics(76),    # SM_XVIRTUALSCREEN
                win32api.GetSystemMetrics(77),    # SM_YVIRTUALSCREEN
                win32api.GetSystemMetrics(78),    # SM_CXVIRTUALSCREEN
                win32api.GetSystemMetrics(79))    # SM_CYVIRTUALSCREEN
    except Exception:
        try:
            import win32api
            return (0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
        except Exception:
            return (0, 0, 1920, 1080)

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

try:
    import uiautomation as auto
except Exception:
    auto = None

# Tipos de control que tiene sentido "clicar".
_CLICABLES = ("ButtonControl", "HyperlinkControl", "MenuItemControl", "ListItemControl",
              "TabItemControl", "CheckBoxControl", "RadioButtonControl", "SplitButtonControl",
              "TreeItemControl", "TextControl")


def _co_init():
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass


def _norm(t):
    return (t or "").strip().lower().translate(str.maketrans("áéíóúü", "aeiouu"))


# ── Enganches opcionales (HUD y grabadora de macros) ─────────────────────────
# Los dos son ADORNOS: si fallan o no están, la acción se hace igual. Import perezoso para no
# crear un ciclo (Macros necesita a este módulo para reproducir los pasos).
def _mira(x, y, etiqueta):
    try:
        from Interfaz import Mira
        Mira.marcar(x, y, etiqueta)
    except Exception:
        pass


def _grabar(tipo, objetivo, metodo=None, x=None, y=None):
    try:
        from Funciones_Slide.Sistema import Macros
        Macros.registrar(tipo, objetivo, metodo, x, y)
    except Exception:
        pass


# ── Localización por NOMBRE (UI Automation) — rápido, sin LLM ────────────────
def _ubicar_por_nombre(objetivo_n):
    if auto is None:
        return None, None
    _co_init()
    try:
        ventana = auto.GetForegroundControl()
        if not ventana:
            return None, None
        for ctrl, _depth in auto.WalkControl(ventana, maxDepth=22):
            try:
                if ctrl.ControlTypeName in _CLICABLES and objetivo_n in _norm(ctrl.Name):
                    r = ctrl.BoundingRectangle
                    x = getattr(r, "xcenter", lambda: (r.left + r.right) // 2)()
                    y = getattr(r, "ycenter", lambda: (r.top + r.bottom) // 2)()
                    return (x, y), (ctrl.Name or None)
            except Exception:
                continue
    except Exception:
        pass
    return None, None


# ── CAPA DE RAYOS X: enumerar TODO lo clicable de la ventana en foco ─────────
#
# _ubicar_por_nombre recorre el árbol buscando UNO. Esto hace el mismo recorrido pero sin filtrar
# por nombre: devuelve todos, numerados. Dos cosas que da y antes no había:
#   — Marco puede decir "haz clic en el 4" en vez de describir el botón.
#   — Y VE lo que AIDEN está interpretando de la pantalla, en vez de que actúe en secreto.
_MAX_INDICES = 30        # más que esto satura la pantalla y el contexto del modelo
_VIDA_INDICES = 20.0     # s: pasado ese rato la lista ya no representa lo que hay en pantalla

_indices = {"lista": [], "en": 0.0}


def _listar_clicables(tope=_MAX_INDICES):
    """[(x, y, nombre, tipo)] de los elementos clicables de la ventana activa, en el orden en que
    aparecen en el árbol. Sin nombre no se descarta: un botón de icono no tiene texto y sigue
    siendo clicable — se le pone su tipo, que para elegir "el 4" da igual."""
    if auto is None:
        return []
    _co_init()
    fuera = []
    try:
        ventana = auto.GetForegroundControl()
        if not ventana:
            return []
        vistos = set()
        for ctrl, _d in auto.WalkControl(ventana, maxDepth=22):
            if len(fuera) >= tope:
                break
            try:
                if ctrl.ControlTypeName not in _CLICABLES:
                    continue
                r = ctrl.BoundingRectangle
                if r.right - r.left < 4 or r.bottom - r.top < 4:
                    continue                      # elementos de 0 px: existen en el árbol, no en pantalla
                x = getattr(r, "xcenter", lambda: (r.left + r.right) // 2)()
                y = getattr(r, "ycenter", lambda: (r.top + r.bottom) // 2)()
                if (x, y) in vistos:              # contenedores que ocupan lo mismo que su hijo
                    continue
                vistos.add((x, y))
                nombre = (ctrl.Name or "").strip()
                fuera.append((x, y, nombre, ctrl.ControlTypeName))
            except Exception:
                continue
    except Exception:
        pass
    return fuera


def _mostrar_elementos():
    elementos = _listar_clicables()
    if not elementos:
        return ("No encontré elementos enumerables en esta ventana, señor — algunas apps "
                "(juegos, lienzos de dibujo) no exponen sus controles. Ahí sígame describiendo "
                "qué quiere y lo busco viendo la pantalla.")
    with _lock_indices:
        _indices["lista"] = elementos
        _indices["en"] = time.time()
    try:
        from Interfaz import Mira
        Mira.mostrar_indices([(x, y) for x, y, _n, _t in elementos], _VIDA_INDICES)
    except Exception:
        pass
    lineas = []
    for i, (_x, _y, nombre, tipo) in enumerate(elementos, 1):
        lineas.append(f"{i}. {nombre or '(' + tipo.replace('Control', '').lower() + ')'}")
    return (f"{len(elementos)} elementos, señor. Dígame el número:\n" + "\n".join(lineas))


def _olvidar_indices():
    with _lock_indices:
        _indices["lista"], _indices["en"] = [], 0.0
    try:
        from Interfaz import Mira
        Mira.ocultar_indices()
    except Exception:
        pass


def _por_indice(objetivo):
    """Si Marco dijo un número y la lista sigue fresca, devuelve (x, y, nombre). Si no, None.

    La lista CADUCA a propósito: los números se dibujaron sobre la pantalla de hace un rato, y si
    la ventana cambió, "el 4" ya no es el mismo botón. Actuar sobre una lista vieja sería clicar a
    ciegas con toda la confianza."""
    txt = str(objetivo or "").strip().lstrip("#").rstrip(".")
    if not txt.isdigit():
        return None
    with _lock_indices:
        lista, en = list(_indices["lista"]), _indices["en"]
    if not lista or (time.time() - en) > _VIDA_INDICES:
        return None
    n = int(txt)
    if not (1 <= n <= len(lista)):
        return None
    x, y, nombre, tipo = lista[n - 1]
    return x, y, (nombre or f"el {n}")


# ── Localización por VISIÓN — respaldo universal (cuando no hay nombre) ──────
def _capturar_pantalla():
    """Captura TODOS los monitores. Devuelve (imagen, (ancho, alto), (origen_x, origen_y)) —
    el origen es la esquina del escritorio virtual, que se suma luego para obtener coordenadas
    de pantalla reales."""
    ox, oy, _vw, _vh = _escritorio_virtual()
    try:
        from PIL import ImageGrab
        try:
            img = ImageGrab.grab(all_screens=True)     # Pillow >= 6 en Windows
        except TypeError:
            img = ImageGrab.grab()                      # Pillow viejo: solo el principal
            ox = oy = 0
        # El barrido va DESPUÉS de capturar: se pinta en el overlay, que está EN la pantalla, así
        # que dispararlo antes lo metería dentro de la imagen que el modelo va a mirar.
        try:
            from Interfaz import Mira
            Mira.flash_escaneo()
        except Exception:
            pass
        return img, img.size, (ox, oy)
    except Exception:
        return None, None, (0, 0)


# Lado máximo de la imagen que se le manda al modelo. Con dos monitores la captura son 3840 px
# de ancho y ~1.7 MB en base64; a 1280 baja a ~66 KB (96% menos) y el viaje por red deja de ser
# el cuello de botella. NO se pierde precisión: las coordenadas que devuelve el modelo vienen
# normalizadas 0-1000, así que se reescalan solas contra el tamaño REAL — que es justo por lo que
# aquí se sigue devolviendo `size` original y no el de la imagen reducida. Además el propio Germini
# submuestrea la imagen por dentro, así que mandarle 3840 px era tirar ancho de banda para nada.
_LADO_MAX = 1280


def _consultar_vista(prompt, max_tokens=150):
    """Captura TODOS los monitores y le hace UNA pregunta al modelo sobre lo que se ve.
    Devuelve (texto, (ancho, alto), (origen_x, origen_y)) o (None, None, None).
    OJO: `size` es el tamaño REAL de la pantalla, no el de la imagen enviada."""
    img, size, origen = _capturar_pantalla()
    if img is None:
        return None, None, None
    try:
        import io
        import base64
        if max(img.size) > _LADO_MAX:
            img = img.copy()
            img.thumbnail((_LADO_MAX, _LADO_MAX))   # conserva la proporción
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None, None, None
    try:
        from openai import OpenAI
        from secretos import OPENROUTER_API_KEY
        # Con timeout: esto se llama en bucle dentro de _ajustar_visual, que es una operación
        # cancelable. Sin él, Ctrl+Alt+P no puede llegar mientras se espera a la red.
        cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY,
                         timeout=30.0, max_retries=1)
        r = cliente.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            max_tokens=max_tokens, temperature=0,
        )
        return (r.choices[0].message.content or "").strip(), size, origen
    except Exception:
        return None, None, None


def _a_pixeles(caja_norm, size, origen):
    """[ymin,xmin,ymax,xmax] normalizado 0-1000 -> (x1, y1, x2, y2) en pantalla real."""
    ymin, xmin, ymax, xmax = caja_norm
    w, h = size
    ox, oy = origen
    return (round(ox + xmin / 1000 * w), round(oy + ymin / 1000 * h),
            round(ox + xmax / 1000 * w), round(oy + ymax / 1000 * h))


def _detectar_caja(descripcion):
    """Mira la pantalla ACTUAL y devuelve la CAJA (x1, y1, x2, y2) en píxeles reales de pantalla
    donde está 'descripcion', o None si no la ve. Es el respaldo cuando la estructura de
    accesibilidad no tiene ese nombre (juegos, lienzos, iconos sin texto...). Cuesta una consulta
    al modelo (no es instantáneo).
    Usa el formato "box_2d" que Gemini tiene ENTRENADO para detección espacial — pedirle 'dame las
    coordenadas X,Y' a secas es MUCHO menos fiable (probado: fallaba incluso con objetivos obvios;
    con este formato oficial acierta)."""
    prompt = (
        "Detect exactly this on the screen: '" + str(descripcion) + "'. Output ONLY a JSON list "
        'with one entry: {"box_2d": [ymin,xmin,ymax,xmax], "label": "..."}, coordinates '
        "normalized 0-1000. If it is not visible, output exactly: []"
    )
    salida, size, origen = _consultar_vista(prompt)
    if salida is None:
        return None
    m = re.search(r"\[\s*\{.*?\}\s*\]", salida, re.DOTALL)
    if not m:
        return None
    try:
        import json
        datos = json.loads(m.group(0))
        if not datos:
            return None
        caja = datos[0]["box_2d"]
    except Exception:
        return None
    # Normalizadas (0-1000) -> píxeles de la CAPTURA -> + origen del escritorio virtual.
    # Ese origen es lo que hace que el clic caiga bien en un monitor a la izquierda (x negativa).
    return _a_pixeles(caja, size, origen)


def _localizar_en_pantalla(descripcion):
    """El CENTRO de lo que se ve, en coordenadas reales de pantalla, o None."""
    caja = _detectar_caja(descripcion)
    if caja is None:
        return None
    x1, y1, x2, y2 = caja
    ox, oy, vw, vh = _escritorio_virtual()
    x = max(ox, min(ox + vw - 1, round((x1 + x2) / 2)))
    y = max(oy, min(oy + vh - 1, round((y1 + y2) / 2)))
    return (x, y)


def _ubicar(objetivo):
    """Nombre primero (rápido); si no aparece, VISIÓN (cubre cualquier cosa visible).
    Devuelve (x, y, metodo, nombre_mostrado) o (None, None, None, None)."""
    # ATAJO: si Marco dijo un número y acaba de ver los índices en pantalla, ya está resuelto —
    # ni árbol de UI ni visión. Va primero porque es el único camino con coordenada exacta ya
    # conocida; los otros dos hay que buscarlos.
    directo = _por_indice(objetivo)
    if directo:
        return directo[0], directo[1], "indice", directo[2]

    objetivo_n = _norm(objetivo)
    xy, nombre = _ubicar_por_nombre(objetivo_n)
    if xy:
        return xy[0], xy[1], "estructura", (nombre or objetivo)
    xy = _localizar_en_pantalla(objetivo)
    if xy:
        return xy[0], xy[1], "vision", objetivo
    return None, None, None, None


def _clic_en(objetivo, tipo="clic"):
    if pyautogui is None:
        return "No tengo control de mouse disponible, señor."
    objetivo = str(objetivo or "").strip()
    if not objetivo:
        return "¿En qué quiere que haga clic, señor?"
    x, y, metodo, nombre = _ubicar(objetivo)
    if x is None:
        return f"No encontré «{objetivo}» en pantalla, señor (ni por nombre ni viéndola)."
    try:
        # Los índices se quitan ANTES del clic: en cuanto se pulsa algo la pantalla cambia, y unos
        # números flotando sobre la interfaz nueva señalarían sitios que ya no son los de antes.
        _olvidar_indices()
        _mira(x, y, nombre)                    # marca el blanco ANTES de moverse (se puede frenar)
        pyautogui.moveTo(x, y, duration=0.5)   # movimiento VISIBLE del cursor
        if tipo == "doble":
            pyautogui.doubleClick()
        elif tipo == "derecho":
            pyautogui.rightClick()
        else:
            pyautogui.click()
        _grabar({"doble": "doble_clic", "derecho": "clic_derecho"}.get(tipo, "clic"),
                objetivo, metodo, x, y)
        verbo = {"doble": "doble clic", "derecho": "clic derecho"}.get(tipo, "clic")
        cola = "" if metodo == "estructura" else " (lo ubiqué viendo la pantalla)"
        return f"Listo, señor. Hice {verbo} en «{nombre}».{cola}"
    except Exception as e:
        return f"No pude hacer el clic, señor: {e}"


def _arrastrar(descripcion):
    # "arrastra X hasta Y" / "arrastra X hacia Y" / "arrastra X a Y".
    texto = str(descripcion or "").strip()
    partes = re.split(r"\s+hasta\s+|\s+hacia\s+", texto, maxsplit=1)
    if len(partes) != 2:
        partes = re.split(r"\s+a\s+", texto, maxsplit=1)
    if len(partes) != 2:
        return "Dígame 'arrastra X hasta Y', señor."
    origen_txt, destino_txt = partes[0].strip(), partes[1].strip()
    if not origen_txt or not destino_txt:
        return "Necesito el origen y el destino del arrastre, señor."
    ox, oy, _m1, on = _ubicar(origen_txt)
    if ox is None:
        return f"No encontré «{origen_txt}» para arrastrar, señor."
    dx, dy, _m2, dn = _ubicar(destino_txt)
    if dx is None:
        return f"No encontré «{destino_txt}» como destino, señor."
    if pyautogui is None:
        return "No tengo control de mouse disponible, señor."
    try:
        pyautogui.moveTo(ox, oy, duration=0.4)
        pyautogui.mouseDown()
        pyautogui.moveTo(dx, dy, duration=0.6)
        pyautogui.mouseUp()
        return f"Arrastré «{on}» hasta «{dn}», señor."
    except Exception as e:
        try:
            pyautogui.mouseUp()   # por si quedó el botón presionado a medio arrastre
        except Exception:
            pass
        return f"No pude arrastrar, señor: {e}"


def _caja_por_nombre(objetivo_n):
    """Rectángulo de un elemento localizado por la estructura de accesibilidad, o None."""
    if auto is None:
        return None
    _co_init()
    try:
        ventana = auto.GetForegroundControl()
        if not ventana:
            return None
        for ctrl, _d in auto.WalkControl(ventana, maxDepth=22):
            try:
                if ctrl.ControlTypeName in _CLICABLES and objetivo_n in _norm(ctrl.Name):
                    r = ctrl.BoundingRectangle
                    return (r.left, r.top, r.right, r.bottom), (ctrl.Name or None)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _senalar(objetivo, segundos=5.0):
    """Dibuja un recuadro sobre algo de la pantalla SIN tocarlo. Para 'señálame dónde está X':
    responder con palabras dónde queda un botón es inútil; marcarlo se entiende de un vistazo."""
    objetivo = str(objetivo or "").strip()
    if not objetivo:
        return "¿Qué quiere que le señale, señor?"
    nombre = objetivo
    hallazgo = _caja_por_nombre(_norm(objetivo))
    if hallazgo:
        caja, nombre = hallazgo[0], (hallazgo[1] or objetivo)
    else:
        caja = _detectar_caja(objetivo)      # respaldo por visión
    if not caja:
        return f"No encontré «{objetivo}» en pantalla, señor (ni por nombre ni viéndola)."
    try:
        from Interfaz import Mira
        pintado = Mira.marcar_caja(caja[0], caja[1], caja[2], caja[3], nombre, segundos)
    except Exception:
        pintado = False
    cx, cy = (caja[0] + caja[2]) // 2, (caja[1] + caja[3]) // 2
    if pintado:
        return f"Ahí lo tiene, señor: se lo marqué en pantalla («{nombre}»)."
    return (f"«{nombre}» está en la posición {cx}, {cy} de la pantalla, señor. "
            "No pude dibujarle el recuadro porque la interfaz no está corriendo.")


_MAX_PASOS_AJUSTE = 5      # tope de iteraciones mirar-mover-remirar
_CERCA = 5                 # px: más cerca que esto del destino, se da por logrado


def _ajustar_visual(descripcion):
    """MIRAR-MOVER-REMIRAR: para lo que NO se acierta de un solo tirón.

    Un clic o un arrastre normal son "a ciegas": se mira una vez, se calcula un punto y se suelta.
    Eso falla con controles CONTINUOS (el slider del brillo, el volumen, un recorte, una barra de
    progreso) porque el punto exacto depende del resultado, no de la posición. Aquí AIDEN hace lo
    que haría Marco: mueve un poco, VUELVE A MIRAR, corrige, y repite hasta lograrlo o rendirse.

    Se usa como: ajustar('el slider de brillo hasta la mitad')."""
    texto = str(descripcion or "").strip()
    if not texto:
        return "¿Qué quiere que ajuste, señor? (ej. 'el brillo hasta la mitad')"
    if pyautogui is None:
        return "No tengo control de mouse disponible, señor."

    partes = re.split(r"\s+hasta\s+|\s+a\s+que\s+|\s+para\s+que\s+", texto, maxsplit=1)
    control_txt = partes[0].strip()
    meta_txt = partes[1].strip() if len(partes) == 2 else texto

    prompt = (
        "You are helping adjust a control on a Windows screen.\n"
        f"CONTROL to adjust: '{control_txt}'\n"
        f"GOAL: '{meta_txt}'\n"
        "Look at the screenshot and answer ONLY with one JSON object:\n"
        '{"listo": true|false, "control": [ymin,xmin,ymax,xmax], '
        '"destino": [ymin,xmin,ymax,xmax], "nota": "<short note in Spanish>"}\n'
        '- "listo": true if the GOAL is ALREADY satisfied in this screenshot.\n'
        '- "control": box of the draggable handle/knob/thumb as it is RIGHT NOW.\n'
        '- "destino": box of where that handle must END UP to satisfy the goal '
        '(repeat "control" if listo is true).\n'
        "- coordinates normalized 0-1000.\n"
        'If you cannot see the control, answer exactly: {"listo": false, "nota": "no visible"}'
    )

    import json
    import time
    ultima_nota = ""
    for paso in range(_MAX_PASOS_AJUSTE):
        Cancelacion.revisar()
        salida, size, origen = _consultar_vista(prompt, max_tokens=250)
        if salida is None:
            return "No pude ver la pantalla para ajustar, señor."
        m = re.search(r"\{.*\}", salida, re.DOTALL)
        if not m:
            return "No entendí lo que veo en pantalla, señor."
        try:
            d = json.loads(m.group(0))
        except Exception:
            return "No entendí lo que veo en pantalla, señor."

        ultima_nota = str(d.get("nota") or "").strip()
        if d.get("listo"):
            hechos = f" (me tomó {paso} ajuste{'s' if paso != 1 else ''})" if paso else ""
            return f"Listo, señor: {meta_txt}.{hechos}"
        if not d.get("control") or not d.get("destino"):
            return f"No encontré «{control_txt}» en pantalla, señor." + (
                f" ({ultima_nota})" if ultima_nota else "")

        try:
            cx1, cy1, cx2, cy2 = _a_pixeles(d["control"], size, origen)
            dx1, dy1, dx2, dy2 = _a_pixeles(d["destino"], size, origen)
        except Exception:
            return "Las coordenadas que vi no tenían sentido, señor."
        ox_, oy_ = (cx1 + cx2) // 2, (cy1 + cy2) // 2
        dx_, dy_ = (dx1 + dx2) // 2, (dy1 + dy2) // 2

        if abs(dx_ - ox_) <= _CERCA and abs(dy_ - oy_) <= _CERCA:
            return f"Listo, señor: {meta_txt}."      # ya está donde debe

        try:
            pyautogui.moveTo(ox_, oy_, duration=0.3)
            pyautogui.mouseDown()
            pyautogui.moveTo(dx_, dy_, duration=0.5)   # movimiento VISIBLE
            pyautogui.mouseUp()
        except Exception as e:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            return f"No pude mover el control, señor: {e}"
        time.sleep(0.45)     # deja que la pantalla refleje el cambio antes de volver a mirar

    cola = f" Lo último que vi: {ultima_nota}." if ultima_nota else ""
    return (f"Lo intenté {_MAX_PASOS_AJUSTE} veces y no logré «{meta_txt}», señor.{cola} "
            "Dígame el valor exacto y lo pongo directo.")


def _ventanas_ordenables():
    # Top-level visibles, con título, no minimizadas, que son ventanas de app (no herramientas).
    res = []

    def _cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return
            titulo = win32gui.GetWindowText(hwnd)
            if not titulo or not titulo.strip():
                return
            estilo = win32gui.GetWindowLong(hwnd, -20)   # GWL_EXSTYLE
            if estilo & 0x00000080:                      # WS_EX_TOOLWINDOW -> ignorar
                return
            res.append(hwnd)
        except Exception:
            pass

    win32gui.EnumWindows(_cb, None)
    return res[:4]   # ordenamos hasta 4 (mosaico cómodo)


def _area_trabajo():
    """Zona útil (sin barra de tareas) del monitor donde está la ventana activa. Con dos pantallas
    el mosaico se arma en LA QUE MARCO ESTÁ USANDO, no siempre en la principal."""
    try:
        import win32api
        hmon = win32api.MonitorFromWindow(win32gui.GetForegroundWindow(), 2)  # NEAREST
        izq, arr, der, aba = win32api.GetMonitorInfo(hmon)["Work"]
        return izq, arr, der - izq, aba - arr
    except Exception:
        try:
            import win32api
            return 0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1) - 48
        except Exception:
            return 0, 0, 1920, 1032


def _ordenar_ventanas():
    x0, y0, ancho, alto = _area_trabajo()
    vts = _ventanas_ordenables()
    if not vts:
        return "No hay ventanas que ordenar, señor."
    n = len(vts)
    # 1 -> full; 2 -> lado a lado; 3-4 -> cuadrícula 2x2. Todo relativo al origen del monitor.
    if n == 1:
        celdas = [(x0, y0, ancho, alto)]
    elif n == 2:
        celdas = [(x0, y0, ancho // 2, alto), (x0 + ancho // 2, y0, ancho // 2, alto)]
    else:
        cw, ch = ancho // 2, alto // 2
        celdas = [(x0, y0, cw, ch), (x0 + cw, y0, cw, ch),
                  (x0, y0 + ch, cw, ch), (x0 + cw, y0 + ch, cw, ch)]
    for hwnd, (x, y, w, h) in zip(vts, celdas):
        try:
            win32gui.ShowWindow(hwnd, 9)                  # SW_RESTORE
            win32gui.MoveWindow(hwnd, x, y, w, h, True)   # se ve reacomodarse
        except Exception:
            pass
    return f"Listo, señor. Ordené {min(n, len(celdas))} ventanas en mosaico."


# ── COLOCAR EN UN MONITOR CONCRETO ───────────────────────────────────────────
# _ordenar_ventanas ya arma el mosaico en el monitor donde Marco está. Esto es lo otro que hacía
# falta: decir DÓNDE. "Pon el navegador en el 2" no se podía expresar.
def _monitores():
    """[(indice, (x, y, ancho, alto) del área útil)] en orden de izquierda a derecha, que es como
    Marco los cuenta mirándolos — no en el orden arbitrario en que los enumera Windows."""
    try:
        import win32api
        fuera = []
        for h, _hdc, _r in win32api.EnumDisplayMonitors():
            izq, arr, der, aba = win32api.GetMonitorInfo(h)["Work"]
            fuera.append((izq, arr, der - izq, aba - arr))
        fuera.sort(key=lambda a: a[0])
        return list(enumerate(fuera, 1))
    except Exception:
        return []


def _colocar(descripcion):
    """'la ventana X en el monitor 2' / 'chrome en la pantalla 1' / 'en el monitor 2'."""
    texto = str(descripcion or "").strip()
    mons = _monitores()
    if not mons:
        return "No pude consultar los monitores, señor."

    m = re.search(r"(?:monitor|pantalla|display)\s*(\d+)", texto, re.I)
    if not m:
        m = re.search(r"\b(\d+)\s*$", texto)
    if not m:
        return (f"¿En cuál monitor, señor? Tiene {len(mons)}: dígame «en el monitor 1» o "
                "«en el monitor 2».")
    n = int(m.group(1))
    if not (1 <= n <= len(mons)):
        # Decirlo claro y no fallar en silencio: con un solo monitor, "ponlo en el 2" es un error
        # de Marco, no de AIDEN, y hay que devolvérselo entendible.
        return (f"Solo tiene {len(mons)} monitor{'es' if len(mons) > 1 else ''}, señor; "
                f"no existe el {n}.")
    x0, y0, ancho, alto = mons[n - 1][1]

    # A qué ventana: lo que quede del texto quitando la parte del monitor. Sin nombre, la activa.
    resto = _norm(texto[:m.start()].replace("en el", " ").replace("en la", " "))
    hwnd = None
    if resto:
        for h in _ventanas_ordenables():
            try:
                if resto in _norm(win32gui.GetWindowText(h)):
                    hwnd = h
                    break
            except Exception:
                continue
        if hwnd is None:
            return f"No encontré una ventana que se llame «{resto}», señor."
    else:
        hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return "No hay ninguna ventana activa que mover, señor."

    try:
        titulo = win32gui.GetWindowText(hwnd) or "la ventana"
        win32gui.ShowWindow(hwnd, 9)                                # SW_RESTORE
        # Ocupa el monitor entero menos un margen: pegarla al borde exacto se ve peor y estorba
        # con la barra de tareas si está en auto-ocultar.
        win32gui.MoveWindow(hwnd, x0, y0, ancho, alto, True)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        return f"No pude mover la ventana, señor: {e}"
    return f"Listo, señor: «{titulo[:40]}» al monitor {n}."


# ── AISLAR: atenuar TODO menos una ventana ───────────────────────────────────
def _aislar(objetivo=""):
    """Oscurece el escritorio entero salvo la ventana indicada (o la activa)."""
    objetivo_n = _norm(objetivo)
    hwnd = None
    if objetivo_n:
        for h in _ventanas_ordenables():
            try:
                if objetivo_n in _norm(win32gui.GetWindowText(h)):
                    hwnd = h
                    break
            except Exception:
                continue
        if hwnd is None:
            return f"No encontré «{objetivo}», señor."
    else:
        hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return "No hay ninguna ventana que aislar, señor."
    try:
        r = win32gui.GetWindowRect(hwnd)
        titulo = win32gui.GetWindowText(hwnd) or "esta ventana"
    except Exception as e:
        return f"No pude leer la ventana, señor: {e}"
    try:
        from Interfaz import Mira
        if not Mira.aislar(r):
            return "No tengo la interfaz visual disponible para aislar, señor."
    except Exception:
        return "No tengo la interfaz visual disponible para aislar, señor."
    return f"Listo, señor: solo «{titulo[:40]}». Diga «normal» cuando quiera el resto de vuelta."


def _sin_aislar():
    try:
        from Interfaz import Mira
        Mira.aislar(None)
    except Exception:
        pass
    return "Vista completa de vuelta, señor."


def _enfocar_app(objetivo):
    objetivo_n = _norm(objetivo)
    if not objetivo_n:
        return "¿Qué ventana quiere que traiga al frente, señor?"
    destino = []

    def _cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t and objetivo_n in _norm(t):
                    destino.append(hwnd)
        except Exception:
            pass

    win32gui.EnumWindows(_cb, None)
    if not destino:
        return f"No encontré una ventana de «{objetivo}», señor."
    try:
        hwnd = destino[0]
        win32gui.ShowWindow(hwnd, 9)            # SW_RESTORE
        win32gui.SetForegroundWindow(hwnd)
        _grabar("enfocar", objetivo)
        return f"Al frente, señor: {win32gui.GetWindowText(hwnd)}."
    except Exception as e:
        return f"No pude traerla al frente, señor: {e}"


def _escribir(texto):
    """Escribe donde esté el cursor. Va por el PORTAPAPELES, no tecleando letra a letra.

    `pyautogui.typewrite` no sabe teclear lo que no está en la distribución del teclado: las tildes,
    la ñ y los saltos de línea salían mal o directamente se perdían — y AIDEN escribe en español
    todo el rato. Pegar desde el portapapeles no tiene ese problema, es instantáneo por largo que
    sea el texto, y además se restaura lo que Marco tuviera copiado.

    La lógica no se duplica: `dictar` (Control_PC) ya la tenía resuelta, incluido el respaldo a
    tecleo si el portapapeles falla. Aquí se reusa en vez de escribir una segunda versión peor."""
    texto = str(texto or "")
    if not texto:
        return "¿Qué quiere que escriba, señor?"
    try:
        from Funciones_Slide.Sistema.Control_PC import dictar
        dictar(texto)
    except Exception:
        if pyautogui is None:
            return "No tengo control de teclado, señor."
        try:
            pyautogui.typewrite(texto, interval=0.02)
        except Exception as e:
            return f"No pude escribir, señor: {e}"
    _grabar("escribir", texto)
    return f"Escrito, señor: {texto[:60]}"


def _hover(objetivo):
    """Deja el cursor QUIETO encima de algo, sin hacer clic. Hay menús y tooltips que solo se
    despliegan al pasar el mouse por encima; sin esto había que clicar, que muchas veces hace otra
    cosa distinta (o abre lo que no era)."""
    if pyautogui is None:
        return "No tengo control de mouse disponible, señor."
    objetivo = str(objetivo or "").strip()
    if not objetivo:
        return "¿Sobre qué quiere que deje el cursor, señor?"
    x, y, metodo, nombre = _ubicar(objetivo)      # el MISMO localizador que usa el clic
    if x is None:
        return f"No encontré «{objetivo}» en pantalla, señor."
    try:
        _mira(x, y, nombre)
        pyautogui.moveTo(x, y, duration=0.3)
        cola = "" if metodo == "estructura" else " (lo ubiqué viendo la pantalla)"
        return f"Ahí tiene el cursor, señor: sobre «{nombre}».{cola}"
    except Exception as e:
        return f"No pude mover el cursor, señor: {e}"


def _scroll(objetivo):
    if pyautogui is None:
        return "No tengo control de scroll, señor."
    o = _norm(objetivo)
    cantidad = -600 if ("abajo" in o or "baja" in o or "down" in o) else 600
    try:
        pyautogui.scroll(cantidad)
        _grabar("scroll", objetivo)
        return "Listo, señor."
    except Exception as e:
        return f"No pude hacer scroll, señor: {e}"


def _cerrar_pestana():
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    try:
        pyautogui.hotkey("ctrl", "w")
        _grabar("cerrar_pestana", "")
        return "Cerré la pestaña, señor."
    except Exception as e:
        return f"No pude cerrar la pestaña, señor: {e}"


def _seleccionar_todo():
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    try:
        pyautogui.hotkey("ctrl", "a")
        _grabar("seleccionar", "")
        return "Seleccioné todo, señor."
    except Exception as e:
        return f"No pude seleccionar, señor: {e}"


def _atajo(combo):
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    teclas = [t.strip().lower() for t in re.split(r"[+\s]+", str(combo or "")) if t.strip()]
    if not teclas:
        return "¿Qué combinación de teclas, señor? (ej. control + s)"
    # normaliza nombres comunes en español
    mapa = {"ctrl": "ctrl", "control": "ctrl", "mayus": "shift", "mayús": "shift", "shift": "shift",
            "alt": "alt", "win": "win", "windows": "win", "tab": "tab", "esc": "esc", "enter": "enter",
            "intro": "enter", "supr": "delete", "borrar": "backspace", "espacio": "space"}
    teclas = [mapa.get(t, t) for t in teclas]
    try:
        pyautogui.hotkey(*teclas)
        _grabar("atajo", combo)
        return f"Listo, señor. Pulsé {' + '.join(teclas)}."
    except Exception as e:
        return f"No pude ejecutar el atajo, señor: {e}"


def _despachar(a, objetivo):
    # Va antes que "muestra"/"senal" porque _senalar también responde a "muestra" y se lo comería.
    if "elemento" in a or "rayos" in a or "enumera" in a or "numera" in a:
        return _mostrar_elementos()
    if "doble" in a:
        return _clic_en(objetivo, "doble")
    if "derech" in a or "secundario" in a or "right" in a:
        return _clic_en(objetivo, "derecho")
    if "hover" in a or "posar" in a or "encima" in a or "pasa el mouse" in a or "sobrevol" in a:
        return _hover(objetivo)
    if "senal" in a or "señal" in a or "muestra" in a or "indica" in a or "resalt" in a:
        return _senalar(objetivo)
    if "ajust" in a or "reglar" in a or "calibr" in a:
        return _ajustar_visual(objetivo)
    if "arrastr" in a or "drag" in a:
        return _arrastrar(objetivo)
    if "clic" in a or "click" in a or "presion" in a or "pulsa el boton" in a:
        return _clic_en(objetivo, "clic")
    # 'colocar' va ANTES que 'ordenar': "acomoda esto en el monitor 2" lleva las dos palabras, y
    # la que manda es la que trae un destino concreto.
    if "coloca" in a or "monitor" in a or "pantalla " in a or "mueve" in a or "pasa" in a:
        return _colocar(objetivo)
    if "aisla" in a or "aísla" in a or "solo esto" in a or "concentra" in a:
        return _aislar(objetivo)
    if a.startswith("normal") or "quita el aisl" in a or "vista completa" in a:
        return _sin_aislar()
    if "orden" in a or "mosaico" in a or "acomod" in a:
        return _ordenar_ventanas()
    if "enfoc" in a or "frente" in a or "cambia a" in a:
        return _enfocar_app(objetivo)
    if "escrib" in a or "teclea" in a or "redacta" in a:
        return _escribir(objetivo)
    if "scroll" in a or "desplaz" in a or "baja" in a or "sube" in a:
        return _scroll(objetivo)
    if "pestan" in a:
        return _cerrar_pestana()
    if "seleccion" in a:
        return _seleccionar_todo()
    if "atajo" in a or "combinacion" in a or "teclas" in a or "presiona" in a:
        return _atajo(objetivo)
    return ("No reconozco esa acción, señor (clic, doble_clic, clic_derecho, arrastrar, ajustar, "
            "ordenar, enfocar, escribir, scroll, cerrar_pestana, seleccionar, atajo).")


def controlar_pantalla(accion, objetivo=""):
    """Control VISIBLE de la PC (mouse/teclado sobre lo que hay en pantalla). accion:
    'clic' / 'doble_clic' / 'clic_derecho' (busca el objetivo por nombre; si no lo encuentra, lo
    ubica VIENDO la pantalla — cubre CUALQUIER cosa visible, no solo lo que tiene nombre accesible),
    'arrastrar' (objetivo='X hasta Y'), 'ajustar' (objetivo='el slider X hasta Y' — mira, mueve y
    REMIRA hasta lograrlo), 'ordenar' (mosaico de ventanas), 'enfocar' (trae una app al frente),
    'escribir' (teclea texto), 'scroll' (arriba/abajo), 'cerrar_pestana' (Ctrl+W), 'seleccionar'
    (Ctrl+A), 'atajo' (combo de teclas).
    Todo corre dentro de una operación cancelable: Marco puede parar con Ctrl+Alt+P."""
    a = _norm(accion)
    try:
        with Cancelacion.operacion(f"{a} en pantalla"):
            return _despachar(a, objetivo)
    except Cancelacion.Cancelado:
        try:
            pyautogui.mouseUp()      # no dejar el botón trabado si se cortó a medio arrastre
        except Exception:
            pass
        return f"Detenido, señor ({Cancelacion.motivo()})."
