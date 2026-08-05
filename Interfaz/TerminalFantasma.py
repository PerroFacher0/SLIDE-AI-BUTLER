# TERMINAL FANTASMA: ver lo que un comando largo va escupiendo, mientras lo escupe.
#
# `ejecutar_en_pc` ya lee stdout y stderr en vivo, carácter a carácter — pero eso se queda dentro y
# Marco no ve nada hasta que el comando termina. Para una instalación de tres minutos, eso son tres
# minutos de silencio en los que no se distingue "trabajando" de "colgado".
#
# SOLO APARECE SI DE VERDAD TARDA. Un comando típico se resuelve en ~105 ms con la sesión caliente;
# un panel que se abriera y se desvaneciera para eso sería un parpadeo constante, y en dos días
# Marco dejaría de mirarlo. Se espera a que el comando lleve un tiempo corriendo (_UMBRAL) y solo
# entonces se muestra: si nunca llega, no se ve nunca.
#
# Solo MUESTRA. No es un canal de entrada: contestar a lo que el comando pregunte sigue siendo cosa
# del parámetro 'respuestas'. Si esta ventana aceptara escritura, habría dos caminos para lo mismo
# y uno acabaría desincronizado del otro.
#
# Mismo trato que la Mira: se construye en el hilo de Qt, no roba foco, y si Qt no está todo esto
# es un no-op silencioso.

import threading
import time

from Interfaz import _Estilo as _E

_UMBRAL = 1.5          # segundos que debe llevar corriendo antes de asomarse
_MAX_LINEAS = 14
_FUNDIDO = 2.0         # cuánto tarda en desvanecerse cuando termina bien

_estado = {
    "activo": False, "titulo": "", "lineas": [], "desde": 0.0,
    "cerrado_en": 0.0, "exito": True, "visible": False,
}
_lock = threading.RLock()
_ventana = None
_encendida = False


def mostrar(descripcion=""):
    """Marca que ARRANCÓ un comando. Todavía no dibuja nada: espera a ver si tarda."""
    if not _encendida:
        return False
    with _lock:
        _estado.update({"activo": True, "titulo": str(descripcion or "comando")[:52],
                        "lineas": [], "desde": time.time(), "cerrado_en": 0.0,
                        "exito": True, "visible": False})
    return True


def actualizar(texto_nuevo):
    """Añade lo último que salió. Se llama con FRAGMENTOS, no con el buffer entero cada vez."""
    if not _encendida:
        return False
    fragmento = str(texto_nuevo or "")
    if not fragmento.strip():
        return False
    with _lock:
        if not _estado["activo"]:
            return False
        for linea in fragmento.replace("\r", "").split("\n"):
            if linea.strip():
                _estado["lineas"].append(linea[:110])
        del _estado["lineas"][:-_MAX_LINEAS]      # solo la cola: es una ventana, no un registro
        if not _estado["visible"] and time.time() - _estado["desde"] >= _UMBRAL:
            _estado["visible"] = True             # ya tardó lo suficiente: ahora sí se asoma
    return True


def cerrar(exito=True):
    """Termina. Si salió bien se desvanece; si falló se queda, que es cuando hay algo que leer."""
    if not _encendida:
        return False
    with _lock:
        if not _estado["activo"]:
            return False
        _estado.update({"activo": False, "exito": bool(exito), "cerrado_en": time.time()})
        if not exito:
            _estado["visible"] = True             # un fallo SÍ se enseña, aunque haya sido rápido
    return True


def _caduco(ahora):
    """True si ya no hay que dibujar nada."""
    with _lock:
        if not _estado["visible"]:
            return True
        if _estado["activo"]:
            return False
        if not _estado["exito"]:
            return False                          # el error se queda hasta el siguiente comando
        return ahora - _estado["cerrado_en"] > _FUNDIDO


def _construir():
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPainter, QGuiApplication

    ANCHO, ALTO = 520, 250

    class _Terminal(QWidget):
        def __init__(self):
            super().__init__(None)
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                | Qt.WindowTransparentForInput | Qt.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            g = QGuiApplication.primaryScreen().availableGeometry()
            # Abajo a la IZQUIERDA: el overlay vive abajo a la derecha, no deben pisarse.
            self.setGeometry(g.x() + 24, g.y() + g.height() - ALTO - 24, ANCHO, ALTO)
            self._reloj = QTimer(self)
            self._reloj.timeout.connect(self._latir)
            self._reloj.start(90)          # la consola no necesita 25 fps
            self.hide()

        def _latir(self):
            visible = not _caduco(time.time())
            if visible != self.isVisible():
                self.setVisible(visible)
            if visible:
                self.update()

        def paintEvent(self, _e):
            with _lock:
                titulo, lineas = _estado["titulo"], list(_estado["lineas"])
                corriendo, exito = _estado["activo"], _estado["exito"]
                cerrado_en = _estado["cerrado_en"]
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)

            # Al terminar bien, todo el panel se apaga poco a poco en vez de desaparecer de golpe.
            opacidad = 1.0
            if not corriendo and exito and cerrado_en:
                opacidad = max(0.0, 1.0 - (time.time() - cerrado_en) / _FUNDIDO)
            p.setOpacity(opacidad)

            ruta = _E.panel_chamferado((1, 1, self.width() - 2, self.height() - 2), corte=11)
            _E.rellenar_panel(p, ruta)
            # Mientras corre, el borde va tenue (está trabajando, no reclama nada). Al acabar bien
            # sube un instante; si falló, se pinta con el rojo reservado a los errores.
            if corriendo:
                _E.borde_resplandor(p, ruta, intensidad=0.55)
                _E.linea_escaneo(p, (1, 1, self.width() - 2, self.height() - 2),
                                 (time.time() * 0.5) % 1.0)
            elif exito:
                _E.borde_resplandor(p, ruta, intensidad=1.0)
            else:
                _E.borde_resplandor(p, ruta, acento=_E.BAJA, intensidad=1.0)

            p.setFont(_E.fuente(9, negrita=True))
            p.setPen(_E.color(_E.BAJA if not exito else _E.ACENTO_BRILLO))
            p.drawText(18, 26, _E.etiqueta(titulo))

            p.setFont(_E.fuente(9))
            fm = p.fontMetrics()
            y = 46
            for linea in lineas[-_MAX_LINEAS:]:
                y += fm.height()
                if y > self.height() - 12:
                    break
                p.setPen(_E.color(_E.TEXTO, 225))
                p.drawText(18, y, linea)
            p.end()

    return _Terminal()


def iniciar():
    """Se llama DESDE EL HILO DE Qt (lo hace Main_AlwaysOn). Sin Qt, todo queda en no-op."""
    global _ventana, _encendida
    if _encendida:
        return True
    try:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:
            return False
        _ventana = _construir()
        _encendida = True
        print("[TerminalFantasma] lista (solo aparece en comandos largos).")
        return True
    except Exception as e:
        print(f"[TerminalFantasma] omitida: {e}")
        return False
