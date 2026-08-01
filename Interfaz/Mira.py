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


def mensaje(texto, segundos=5.0):
    """Cartel flotante en pantalla. Para lo que conviene VER y no solo oír: un recordatorio, un
    dato que hay que copiar a mano, el resultado de algo que corrió en segundo plano."""
    if not _activa:
        return False
    with _lock:
        _mensajes.append({"texto": str(texto or "")[:220], "hasta": time.time() + segundos})
    return True


def limpiar():
    """Borra de inmediato todo lo dibujado."""
    with _lock:
        _cola.clear(); _cajas.clear(); _mensajes.clear()
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
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPainter, QPen, QColor, QFont, QGuiApplication

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
            self.update()

        def paintEvent(self, _e):
            with _lock:
                marcas, cajas, carteles = list(_cola), list(_cajas), list(_mensajes)
            if not marcas and not cajas and not carteles and not _estado_txt:
                return
            ox, oy = self._origen
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)

            for c in cajas:
                x1, y1 = c["x1"] - ox, c["y1"] - oy
                w, h = max(2, c["x2"] - c["x1"]), max(2, c["y2"] - c["y1"])
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, 230), 2))
                p.drawRoundedRect(x1 - 3, y1 - 3, w + 6, h + 6, 4, 4)
                if c["etiqueta"]:
                    f = QFont(); f.setPointSize(9); p.setFont(f)
                    ancho = p.fontMetrics().horizontalAdvance(c["etiqueta"]) + 16
                    # La etiqueta va encima salvo que no quepa; entonces baja.
                    ey = y1 - 26 if y1 > 30 else y1 + h + 6
                    p.setPen(Qt.NoPen)
                    p.setBrush(QColor(16, 16, 18, 214))
                    p.drawRoundedRect(x1 - 3, ey, ancho, 22, 5, 5)
                    p.setPen(QColor(240, 240, 240, 240))
                    p.drawText(x1 + 5, ey + 15, c["etiqueta"])

            for m in marcas:
                queda = max(0.0, m["hasta"] - time.time()) / _TTL
                x, y = m["x"] - ox, m["y"] - oy
                # El anillo se cierra sobre el blanco: grande y tenue -> pequeño y nítido.
                radio = int(12 + 34 * queda)
                alfa = int(90 + 145 * queda)
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(235, 235, 235, alfa), 2))
                p.drawEllipse(x - radio, y - radio, radio * 2, radio * 2)
                p.setPen(QPen(QColor(255, 255, 255, alfa), 1))
                p.drawLine(x - 9, y, x + 9, y)
                p.drawLine(x, y - 9, x, y + 9)
                if m["etiqueta"]:
                    f = QFont(); f.setPointSize(9); p.setFont(f)
                    p.setPen(QColor(255, 255, 255, min(235, alfa + 40)))
                    p.drawText(x + radio + 8, y + 4, m["etiqueta"])

            # Carteles flotantes: apilados arriba al centro, donde no estorban al trabajo.
            arriba = 34
            for c in carteles:
                f = QFont(); f.setPointSize(11); p.setFont(f)
                ancho = min(self.width() - 80, p.fontMetrics().horizontalAdvance(c["texto"]) + 34)
                cx = (self.width() - ancho) // 2
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(14, 14, 16, 226))
                p.drawRoundedRect(cx, arriba, ancho, 40, 9, 9)
                p.setPen(QColor(238, 238, 238, 245))
                p.drawText(cx + 17, arriba + 26, c["texto"])
                arriba += 48

            if _estado_txt:
                f = QFont(); f.setPointSize(9); f.setLetterSpacing(QFont.PercentageSpacing, 108)
                p.setFont(f)
                ancho = p.fontMetrics().horizontalAdvance(_estado_txt) + 26
                caja_x, caja_y = self.width() - ancho - 26, self.height() - 54
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(16, 16, 18, 168))
                p.drawRoundedRect(caja_x, caja_y, ancho, 26, 13, 13)
                p.setPen(QColor(224, 224, 224, 232))
                p.drawText(caja_x + 13, caja_y + 18, _estado_txt)
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
