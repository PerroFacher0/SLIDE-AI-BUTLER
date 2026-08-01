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

_cola = []                 # peticiones pendientes de dibujar (las llena cualquier hilo)
_lock = threading.RLock()
_estado_txt = ""
_ventana = None            # el widget, solo existe si Qt está vivo
_activa = False

MS_ANTES = 550             # cuánto se ve la mira antes de que el cursor se mueva
_TTL = 1.6                 # s que dura una marca en pantalla


def fijar_estado(texto):
    """Cambia la píldora de estado (escuchando / pensando / ejecutando). Vacío = ocultarla."""
    global _estado_txt
    _estado_txt = str(texto or "").strip()


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
            with _lock:
                vivos = [m for m in _cola if m["hasta"] > time.time()]
                _cola[:] = vivos
            self.update()

        def paintEvent(self, _e):
            with _lock:
                marcas = list(_cola)
            if not marcas and not _estado_txt:
                return
            ox, oy = self._origen
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)

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
