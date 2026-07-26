# Control VISIBLE de la pantalla: AIDEN se mete con la PC y lo VES.
#   - clic: PRIMERO busca un botón/elemento por su nombre (UI Automation, rápido, sin LLM). Si
#     no lo encuentra (juegos, apps de lienzo, botones sin nombre accesible), cae a VISIÓN: mira
#     la pantalla, ubica el objetivo por su descripción y calcula el punto exacto. Así cubre
#     CUALQUIER cosa visible, no solo lo que Windows sabe nombrar — el respaldo por visión tarda
#     un poco más (una consulta al modelo), pero nada se queda fuera de alcance.
#   - arrastrar: localiza origen y destino (por nombre o visión) y hace drag real del mouse.
#   - ordenar: acomoda tus ventanas en mosaico (las ves reorganizarse).
#   - enfocar: trae una app al frente.
# Una sola herramienta `interactuar_pc(accion, objetivo)` (estilo anti-bloat del proyecto).

import re

import win32gui

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


# ── Localización por VISIÓN — respaldo universal (cuando no hay nombre) ──────
def _capturar_pantalla():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return img, img.size
    except Exception:
        return None, None


def _localizar_en_pantalla(descripcion):
    """Mira la pantalla ACTUAL y devuelve (x, y) en píxeles reales de pantalla para 'descripcion',
    o None si no lo ve. Es el respaldo cuando la estructura de accesibilidad no tiene ese nombre
    (juegos, lienzos, iconos sin texto...). Cuesta una consulta al modelo (no es instantáneo).
    Usa el formato "box_2d" que Gemini tiene ENTRENADO para detección espacial — pedirle 'dame las
    coordenadas X,Y' a secas es MUCHO menos fiable (probado: fallaba incluso con objetivos obvios;
    con este formato oficial acierta)."""
    img, size = _capturar_pantalla()
    if img is None:
        return None
    try:
        import io
        import base64
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None
    try:
        from openai import OpenAI
        from secretos import OPENROUTER_API_KEY
        cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        prompt = (
            "Detect exactly this on the screen: '" + str(descripcion) + "'. Output ONLY a JSON list "
            'with one entry: {"box_2d": [ymin,xmin,ymax,xmax], "label": "..."}, coordinates '
            "normalized 0-1000. If it is not visible, output exactly: []"
        )
        r = cliente.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            max_tokens=150, temperature=0,
        )
        salida = (r.choices[0].message.content or "").strip()
    except Exception:
        return None
    m = re.search(r"\[\s*\{.*?\}\s*\]", salida, re.DOTALL)
    if not m:
        return None
    try:
        import json
        datos = json.loads(m.group(0))
        if not datos:
            return None
        ymin, xmin, ymax, xmax = datos[0]["box_2d"]
    except Exception:
        return None
    w, h = size
    cx = (xmin + xmax) / 2 / 1000 * w
    cy = (ymin + ymax) / 2 / 1000 * h
    x = max(0, min(w - 1, round(cx)))
    y = max(0, min(h - 1, round(cy)))
    return (x, y)


def _ubicar(objetivo):
    """Nombre primero (rápido); si no aparece, VISIÓN (cubre cualquier cosa visible).
    Devuelve (x, y, metodo, nombre_mostrado) o (None, None, None, None)."""
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
        pyautogui.moveTo(x, y, duration=0.5)   # movimiento VISIBLE del cursor
        if tipo == "doble":
            pyautogui.doubleClick()
        elif tipo == "derecho":
            pyautogui.rightClick()
        else:
            pyautogui.click()
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


def _ordenar_ventanas():
    try:
        import win32api
        ancho = win32api.GetSystemMetrics(0)
        alto = win32api.GetSystemMetrics(1) - 48          # deja la barra de tareas
    except Exception:
        ancho, alto = 1920, 1032
    vts = _ventanas_ordenables()
    if not vts:
        return "No hay ventanas que ordenar, señor."
    n = len(vts)
    # 1 -> full; 2 -> lado a lado; 3-4 -> cuadrícula 2x2.
    if n == 1:
        celdas = [(0, 0, ancho, alto)]
    elif n == 2:
        celdas = [(0, 0, ancho // 2, alto), (ancho // 2, 0, ancho // 2, alto)]
    else:
        cw, ch = ancho // 2, alto // 2
        celdas = [(0, 0, cw, ch), (cw, 0, cw, ch), (0, ch, cw, ch), (cw, ch, cw, ch)]
    for hwnd, (x, y, w, h) in zip(vts, celdas):
        try:
            win32gui.ShowWindow(hwnd, 9)                  # SW_RESTORE
            win32gui.MoveWindow(hwnd, x, y, w, h, True)   # se ve reacomodarse
        except Exception:
            pass
    return f"Listo, señor. Ordené {min(n, len(celdas))} ventanas en mosaico."


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
        return f"Al frente, señor: {win32gui.GetWindowText(hwnd)}."
    except Exception as e:
        return f"No pude traerla al frente, señor: {e}"


def _escribir(texto):
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    texto = str(texto or "")
    if not texto:
        return "¿Qué quiere que escriba, señor?"
    try:
        pyautogui.typewrite(texto, interval=0.02)   # escritura VISIBLE donde esté el cursor
        return f"Escrito, señor: {texto[:60]}"
    except Exception as e:
        return f"No pude escribir, señor: {e}"


def _scroll(objetivo):
    if pyautogui is None:
        return "No tengo control de scroll, señor."
    o = _norm(objetivo)
    cantidad = -600 if ("abajo" in o or "baja" in o or "down" in o) else 600
    try:
        pyautogui.scroll(cantidad)
        return "Listo, señor."
    except Exception as e:
        return f"No pude hacer scroll, señor: {e}"


def _cerrar_pestana():
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    try:
        pyautogui.hotkey("ctrl", "w")
        return "Cerré la pestaña, señor."
    except Exception as e:
        return f"No pude cerrar la pestaña, señor: {e}"


def _seleccionar_todo():
    if pyautogui is None:
        return "No tengo control de teclado, señor."
    try:
        pyautogui.hotkey("ctrl", "a")
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
        return f"Listo, señor. Pulsé {' + '.join(teclas)}."
    except Exception as e:
        return f"No pude ejecutar el atajo, señor: {e}"


def controlar_pantalla(accion, objetivo=""):
    """Control VISIBLE de la PC (mouse/teclado sobre lo que hay en pantalla). accion:
    'clic' / 'doble_clic' / 'clic_derecho' (busca el objetivo por nombre; si no lo encuentra, lo
    ubica VIENDO la pantalla — cubre CUALQUIER cosa visible, no solo lo que tiene nombre accesible),
    'arrastrar' (objetivo='X hasta Y'), 'ordenar' (mosaico de ventanas), 'enfocar' (trae una app al
    frente), 'escribir' (teclea texto), 'scroll' (arriba/abajo), 'cerrar_pestana' (Ctrl+W),
    'seleccionar' (Ctrl+A), 'atajo' (combo de teclas)."""
    a = _norm(accion)
    if "doble" in a:
        return _clic_en(objetivo, "doble")
    if "derech" in a or "secundario" in a or "right" in a:
        return _clic_en(objetivo, "derecho")
    if "arrastr" in a or "drag" in a:
        return _arrastrar(objetivo)
    if "clic" in a or "click" in a or "presion" in a or "pulsa el boton" in a:
        return _clic_en(objetivo, "clic")
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
    return ("No reconozco esa acción, señor (clic, doble_clic, clic_derecho, arrastrar, ordenar, "
            "enfocar, escribir, scroll, cerrar_pestana, seleccionar, atajo).")
