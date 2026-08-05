# LA MIRA: el HUD que muestra DÓNDE va a hacer clic AIDEN, ANTES de moverse.
#
# Por qué existe: cuando AIDEN toma el mouse, el cursor salta y hace clic en menos de un segundo.
# Si se equivocó de botón, Marco se entera cuando ya pasó. La mira dibuja un círculo sobre el
# objetivo y espera un instante ANTES de tocar nada — da tiempo a ver la intención y a frenarla con
# Ctrl+Alt+P. Es lo mismo que hace el HUD de un caza: primero marca el blanco, después dispara.
#
# También lleva una píldora de ESTADO (escuchando / pensando / ejecutando) para que se sepa en qué
# anda AIDEN sin tener que mirar la consola.
#
# Es PySide6 (tkinter está prohibido) y click-through: no roba el mouse ni tapa nada. Aislado: si Qt
# no está corriendo (Main.py sin interfaz, o un test), todo esto se vuelve un no-op silencioso en vez
# de reventar la acción. Se dibuja sobre el ESCRITORIO VIRTUAL completo, así funciona en el segundo
# monitor igual que en el principal.

import threading
import time

_cola = []                 # marcas de punto pendientes de dibujar (las llena cualquier hilo)
_cajas = []                # recuadros etiquetados ("señálame dónde está el botón X")
_mensajes = []             # carteles flotantes
_lock = threading.RLock()
_estado_txt = ""
_ventana = None            # el widget, solo existe si Qt está vivo
_activa = False

MS_ANTES = 550             # cuánto se ve la mira antes de que el cursor se mueva
_TTL = 1.6                 # s que dura una marca de punto


def fijar_estado(texto):
    """Cambia la píldora de estado (escuchando / pensando / ejecutando). Vacío = ocultarla."""
    global _estado_txt
    _estado_txt = str(texto or "").strip()


def marcar_caja(x1, y1, x2, y2, etiqueta="", segundos=4.0):
    """Dibuja un recuadro sobre una zona de la pantalla. Para SEÑALAR sin tocar nada: 'dónde está
    el botón de exportar'. A diferencia de marcar(), no mueve el cursor ni hace clic."""
    if not _activa:
        return False
    with _lock:
        _cajas.append({"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                       "etiqueta": str(etiqueta or "")[:60], "hasta": time.time() + segundos})
    return True


def mensaje(texto, segundos=5.0, titulo=""):
    """Cartel flotante en pantalla. Para lo que conviene VER y no solo oír: un recordatorio, un
    dato que hay que copiar a mano, el resultado de algo que corrió en segundo plano.
    Admite varias líneas (separadas por saltos) y un título opcional."""
    if not _activa:
        return False
    with _lock:
        _mensajes.append({"texto": str(texto or "")[:900],
                          "titulo": str(titulo or "")[:60],
                          "hasta": time.time() + segundos})
    return True


_MAX_FILAS_TARJETA = 8


def presentar_tarjeta(titulo, lineas, segundos=8.0):
    """Muestra datos ESTRUCTURADOS como un cartel legible.

    Existe para que ninguna herramienta tenga que decidir cómo se ve un cartel. Quien llama trae el
    dato ya formateado —él sabe si son pesos, si lleva signo, cuántos decimales—; la Mira decide
    solo la presentación: el fondo, la tipografía, el espaciado y dónde cae en pantalla. Si cada
    tool armara su propio cartel, en tres semanas habría cinco estilos distintos.

      titulo   -> encabezado corto ('Tu portafolio')
      lineas   -> lista de textos YA formateados (['NVDA  $128.50  +3.2%', ...])
      segundos -> cuánto dura. Lo decide QUIEN LLAMA, que es el único que sabe si son dos datos de
                  un vistazo o una lista que hay que leer con calma.

    Se degrada igual que mensaje(): sin Qt no hace nada, ni bloquea ni lanza."""
    filas = [str(l).strip() for l in (lineas or []) if str(l).strip()]
    if not filas:
        return mensaje(str(titulo or ""), segundos) if titulo else False
    # Una tarjeta con veinte filas tapa la pantalla y no se lee: se corta y se dice cuántas faltan,
    # que es más honesto que recortar en silencio.
    sobran = len(filas) - _MAX_FILAS_TARJETA
    if sobran > 0:
        filas = filas[:_MAX_FILAS_TARJETA] + [f"(+{sobran} más)"]
    return mensaje("\n".join(filas), segundos, titulo=str(titulo or ""))


def limpiar():
    """Borra de inmediato todo lo dibujado."""
    with _lock:
        _cola.clear(); _cajas.clear(); _mensajes.clear()
    return True


# ── FLASH DE ESCANEO ─────────────────────────────────────────────────────────
# Cuando AIDEN captura la pantalla para mirarla, hoy no se nota nada. Un barrido de luz muy breve
# lo vuelve visible: Marco sabe que le acaban de mirar la pantalla y CUÁNDO. Importa porque una
# captura es lo más parecido a que alguien se asome por encima del hombro.
_flash = {"hasta": 0.0, "duracion": 0.30}


def flash_escaneo(duracion_ms=300):
    """Un barrido de plata sobre todos los monitores. Dispara y vuelve: no bloquea la captura."""
    if not _activa:
        return False
    with _lock:
        _flash["duracion"] = max(0.08, duracion_ms / 1000.0)
        _flash["hasta"] = time.time() + _flash["duracion"]
    return True


# ── CINTA DE PASOS ───────────────────────────────────────────────────────────
# Un turno puede encadenar varias herramientas. Sin nada que lo muestre, un turno de cuatro pasos y
# uno colgado se ven exactamente igual: silencio. La cinta dice cuántos son y por cuál va.
#
# Con UNA sola herramienta no se dibuja: no hay progreso que enseñar, solo estorbo.
_pasos = {"nombres": [], "actual": -1, "saltados": set()}


def actualizar_pasos(pasos, actual_idx=0):
    nombres = [str(p)[:18] for p in (pasos or [])]
    with _lock:
        _pasos["nombres"] = nombres if len(nombres) > 1 else []
        _pasos["actual"] = actual_idx
    return bool(_activa and len(nombres) > 1)


def marcar_paso(idx):
    with _lock:
        _pasos["actual"] = idx


def limpiar_pasos():
    with _lock:
        _pasos["nombres"], _pasos["actual"] = [], -1
        _pasos["saltados"].clear()


def paso_saltado(idx):
    """True si Marco pidió saltarse ESE paso (Ctrl+Alt+1..9 mientras corre la tanda).

    La 'X' clicable que se pensó al principio no es posible aquí: la Mira es click-through a
    propósito — nunca intercepta el ratón, para no quitarle a Marco un clic en lo que esté
    haciendo. Volverla clicable rompería esa garantía en TODA la superficie, por un botón. El
    teclado consigue lo mismo sin tocar el ratón, y encaja con el Ctrl+Alt+P que ya existe."""
    with _lock:
        return idx in _pasos["saltados"]


def _vigilar_saltos():
    """Sondea Ctrl+Alt+1..9 mientras hay una tanda en curso. Mismo enfoque que Cancelacion."""
    import ctypes
    while True:
        time.sleep(0.06)
        with _lock:
            if not _pasos["nombres"]:
                return
            total = len(_pasos["nombres"])
        try:
            u = ctypes.windll.user32
            if not (u.GetAsyncKeyState(0x11) & 0x8000 and u.GetAsyncKeyState(0x12) & 0x8000):
                continue
            for i in range(min(9, total)):
                if u.GetAsyncKeyState(0x31 + i) & 0x8000:      # '1'..'9'
                    with _lock:
                        _pasos["saltados"].add(i)
        except Exception:
            return


# ── ANCLA DE VIGILANCIA ──────────────────────────────────────────────────────
# Cuando AIDEN se queda esperando algo de una ventana concreta, cuatro escuadras en sus esquinas
# lo dicen sin ocupar sitio. Van MUY tenues a propósito: es un estado de fondo, no debe competir
# con el panel que sí pide atención en ese momento.
_vigiladas = {}          # hwnd -> (x1, y1, x2, y2)
_INTENSIDAD_VIGILA = 0.45


def marcar_vigilancia(hwnd, activo=True):
    if not _activa or not hwnd:
        return False
    with _lock:
        if not activo:
            _vigiladas.pop(hwnd, None)
            return True
        _vigiladas[hwnd] = None       # el rectángulo lo refresca el reloj, para que siga a la ventana
    return True


def marcar(x, y, etiqueta="", esperar=True):
    """Marca el punto (x, y) en pantalla. Si 'esperar', duerme MS_ANTES para que se alcance a ver.
    Devuelve al toque si Qt no está corriendo — nunca bloquea una acción por culpa del HUD."""
    if not _activa:
        return False
    with _lock:
        _cola.append({"x": int(x), "y": int(y), "etiqueta": str(etiqueta or "")[:40],
                      "hasta": time.time() + _TTL})
    if esperar:
        time.sleep(MS_ANTES / 1000.0)
    return True


def _construir():
    from Interfaz import _Estilo as _E          # la paleta y las primitivas, compartidas
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import (QPainter, QPen, QColor, QFont, QGuiApplication,
                               QLinearGradient)

    class _Mira(QWidget):
        def __init__(self):
            super().__init__(None)
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            # Cubre TODOS los monitores: la unión de todas las pantallas, no solo la principal.
            union = None
            for p in QGuiApplication.screens():
                g = p.geometry()
                union = g if union is None else union.united(g)
            if union is not None:
                self.setGeometry(union)
            self._origen = (self.geometry().x(), self.geometry().y())
            self._reloj = QTimer(self)
            self._reloj.timeout.connect(self._latir)
            self._reloj.start(40)
            self.show()

        def _latir(self):
            ahora = time.time()
            with _lock:
                _cola[:] = [m for m in _cola if m["hasta"] > ahora]
                _cajas[:] = [c for c in _cajas if c["hasta"] > ahora]
                _mensajes[:] = [m for m in _mensajes if m["hasta"] > ahora]
                vigiladas = list(_vigiladas)
            # Se relee el rectángulo de cada ventana vigilada para que las escuadras la SIGAN si
            # Marco la mueve. Si la ventana desapareció, se deja de vigilar sola.
            if vigiladas:
                try:
                    import win32gui
                    for h in vigiladas:
                        try:
                            r = win32gui.GetWindowRect(h)
                            with _lock:
                                if h in _vigiladas:
                                    _vigiladas[h] = r
                        except Exception:
                            with _lock:
                                _vigiladas.pop(h, None)
                except Exception:
                    pass
            self.update()

        def paintEvent(self, _e):
            ahora = time.time()
            with _lock:
                marcas, cajas, carteles = list(_cola), list(_cajas), list(_mensajes)
                pasos = list(_pasos["nombres"])
                paso_actual, saltados = _pasos["actual"], set(_pasos["saltados"])
                vigiladas = [r for r in _vigiladas.values() if r]
                flash_queda = max(0.0, _flash["hasta"] - ahora) / _flash["duracion"]
            if not any((marcas, cajas, carteles, pasos, vigiladas, _estado_txt)) and flash_queda <= 0:
                return
            ox, oy = self._origen
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)

            # ── Escuadras de vigilancia: solo las 4 esquinas, no el rectángulo entero. Un marco
            # completo alrededor de una ventana que Marco está usando sería una jaula; cuatro
            # esquinas dicen lo mismo y dejan respirar lo de dentro.
            for r in vigiladas:
                x1, y1, x2, y2 = r[0] - ox, r[1] - oy, r[2] - ox, r[3] - oy
                brazo = max(10, min(26, (x2 - x1) // 12))
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(_E.color(_E.ACENTO, int(255 * _INTENSIDAD_VIGILA * 0.55)), 1.6))
                for ex, ey, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1),
                                       (x1, y2, 1, -1), (x2, y2, -1, -1)):
                    p.drawLine(ex, ey, ex + brazo * dx, ey)
                    p.drawLine(ex, ey, ex, ey + brazo * dy)

            # ── Flash de escaneo: un barrido que cruza TODOS los monitores de una pasada.
            if flash_queda > 0:
                y = int(self.height() * (1.0 - flash_queda))
                grad = QLinearGradient(0, y - 40, 0, y + 40)
                grad.setColorAt(0.0, _E.color(_E.ACENTO, 0))
                grad.setColorAt(0.5, _E.color(_E.ACENTO_BRILLO, int(70 * flash_queda)))
                grad.setColorAt(1.0, _E.color(_E.ACENTO, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(grad)
                p.drawRect(0, y - 40, self.width(), 80)

            for c in cajas:
                x1, y1 = c["x1"] - ox, c["y1"] - oy
                w, h = max(2, c["x2"] - c["x1"]), max(2, c["y2"] - c["y1"])
                # El recuadro señalador NO se rellena: taparía justo lo que se está señalando.
                _E.borde_resplandor(p, _E.panel_chamferado((x1 - 3, y1 - 3, w + 6, h + 6), corte=6))
                if c["etiqueta"]:
                    p.setFont(_E.fuente(9))
                    ancho = p.fontMetrics().horizontalAdvance(c["etiqueta"]) + 20
                    # La etiqueta va encima salvo que no quepa; entonces baja.
                    ey = y1 - 28 if y1 > 32 else y1 + h + 8
                    ruta = _E.panel_chamferado((x1 - 3, ey, ancho, 23), corte=5)
                    _E.rellenar_panel(p, ruta)
                    _E.borde_resplandor(p, ruta, intensidad=0.75)
                    p.setPen(_E.color(_E.TEXTO))
                    p.drawText(x1 + 6, ey + 16, c["etiqueta"])

            for m in marcas:
                queda = max(0.0, m["hasta"] - time.time()) / _TTL
                x, y = m["x"] - ox, m["y"] - oy
                # El anillo se cierra sobre el blanco: grande y tenue -> pequeño y nítido.
                radio = int(12 + 34 * queda)
                alfa = int(90 + 145 * queda)
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(_E.color(_E.ACENTO, alfa), 2))
                p.drawEllipse(x - radio, y - radio, radio * 2, radio * 2)
                p.setPen(QPen(_E.color(_E.ACENTO_BRILLO, alfa), 1))
                p.drawLine(x - 9, y, x + 9, y)
                p.drawLine(x, y - 9, x, y + 9)
                if m["etiqueta"]:
                    p.setFont(_E.fuente(9))
                    p.setPen(_E.color(_E.ACENTO_BRILLO, min(235, alfa + 40)))
                    p.drawText(x + radio + 8, y + 4, m["etiqueta"])

            # Carteles flotantes: apilados arriba al centro, donde no estorban al trabajo.
            # MULTILÍNEA: drawText sobre un punto no interpreta los saltos de línea — dibuja todo
            # seguido. Se parte el texto y se pinta línea a línea, midiendo la más ancha para que
            # la caja quede a medida. Así el mismo cartel de siempre sirve para una frase suelta o
            # para una tarjeta con título y varias filas, sin un segundo overlay.
            arriba = 34
            for c in carteles:
                lineas = str(c["texto"]).split("\n") or [""]
                titulo = c.get("titulo") or ""
                f_tit = _E.fuente(11, negrita=True)
                f_txt = _E.fuente(11)

                p.setFont(f_tit)
                ancho = p.fontMetrics().horizontalAdvance(titulo) if titulo else 0
                p.setFont(f_txt)
                fm = p.fontMetrics()
                for l in lineas:
                    ancho = max(ancho, fm.horizontalAdvance(l))
                ancho = min(self.width() - 80, ancho + 40)
                alto_linea = fm.height() + 3
                alto = 20 + (26 if titulo else 0) + len(lineas) * alto_linea
                cx = (self.width() - ancho) // 2

                ruta = _E.panel_chamferado((cx, arriba, ancho, alto))
                _E.rellenar_panel(p, ruta)
                _E.borde_resplandor(p, ruta)
                # La línea de escaneo recorre el cartel mientras dura: un panel quieto parece una
                # captura pegada en la pantalla; moviéndose se lee como algo vivo.
                _E.linea_escaneo(p, (cx, arriba, ancho, alto), (time.time() * 0.35) % 1.0)

                y = arriba + 12
                if titulo:
                    p.setFont(f_tit)
                    p.setPen(_E.color(_E.ACENTO_BRILLO))
                    y += fm.ascent()
                    # El título SÍ va en mayúsculas: es una etiqueta corta, no contenido.
                    p.drawText(cx + 18, y, _E.etiqueta(titulo))
                    p.setPen(QPen(_E.color(_E.ACENTO, 70), 1))
                    p.drawLine(cx + 18, y + 7, cx + ancho - 18, y + 7)
                    y += 16
                p.setFont(f_txt)
                p.setPen(_E.color(_E.TEXTO, 245))
                for l in lineas:
                    y += fm.ascent()
                    # El contenido va TAL CUAL: son datos que ya formateó una herramienta.
                    p.drawText(cx + 18, y, l)
                    y += alto_linea - fm.ascent()
                arriba += alto + 10
                arriba += 48

            # ── Cinta de pasos: una fila de mini-paneles, uno por herramienta de la tanda.
            # El que corre AHORA lleva el resplandor entero; los hechos quedan tenues; los que
            # faltan, solo contorno. De un vistazo se sabe cuántos son y por dónde va.
            if pasos:
                p.setFont(_E.fuente(8))
                fm = p.fontMetrics()
                anchos = [fm.horizontalAdvance(_E.etiqueta(n)) + 22 for n in pasos]
                total = sum(anchos) + 8 * (len(pasos) - 1)
                cx = (self.width() - total) // 2
                cy = self.height() - 96
                for i, (nombre, ancho) in enumerate(zip(pasos, anchos)):
                    ruta = _E.panel_chamferado((cx, cy, ancho, 22), corte=5)
                    _E.rellenar_panel(p, ruta)
                    if i in saltados:
                        # Saltado por Marco: se marca con el rojo reservado, no se disfraza de hecho.
                        _E.borde_resplandor(p, ruta, acento=_E.BAJA, intensidad=0.55)
                        tinta = _E.color(_E.BAJA, 200)
                    elif i == paso_actual:
                        _E.borde_resplandor(p, ruta, intensidad=1.0)
                        tinta = _E.color(_E.ACENTO_BRILLO, 245)
                    elif i < paso_actual:
                        _E.borde_resplandor(p, ruta, intensidad=0.30)
                        tinta = _E.color(_E.TEXTO_TENUE, 190)
                    else:
                        p.setBrush(Qt.NoBrush)
                        p.setPen(QPen(_E.color(_E.ACENTO, 55), 1.0))
                        p.drawPath(ruta)
                        tinta = _E.color(_E.TEXTO_TENUE, 150)
                    p.setPen(tinta)
                    p.drawText(cx + 11, cy + 15, _E.etiqueta(nombre))
                    if i < len(pasos) - 1:      # el hilo que une un paso con el siguiente
                        p.setPen(QPen(_E.color(_E.ACENTO, 60), 1.0))
                        p.drawLine(cx + ancho, cy + 11, cx + ancho + 8, cy + 11)
                    cx += ancho + 8

            if _estado_txt:
                f = _E.fuente(9)
                f.setLetterSpacing(QFont.PercentageSpacing, 112)
                p.setFont(f)
                texto = _E.etiqueta(_estado_txt)      # 'ESCUCHANDO': etiqueta corta, va en mayúsculas
                ancho = p.fontMetrics().horizontalAdvance(texto) + 30
                caja_x, caja_y = self.width() - ancho - 26, self.height() - 54
                ruta = _E.panel_chamferado((caja_x, caja_y, ancho, 27), corte=7)
                _E.rellenar_panel(p, ruta)
                _E.borde_resplandor(p, ruta, intensidad=0.6)
                p.setPen(_E.color(_E.ACENTO_BRILLO, 235))
                p.drawText(caja_x + 15, caja_y + 19, texto)
            p.end()

    return _Mira()


def iniciar():
    """Enciende la mira. HAY QUE LLAMARLA DESDE EL HILO DE Qt (lo hace Main_AlwaysOn tras crear la
    QApplication). Si Qt no está disponible, no pasa nada: marcar() queda en no-op."""
    global _ventana, _activa
    if _activa:
        return True
    try:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        _ventana = _construir()
        _activa = True
        print("[Mira] HUD de intención activo.")
        return True
    except Exception as e:
        print(f"[Mira] no pude encender el HUD: {e}")
        return False
