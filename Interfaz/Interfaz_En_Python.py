import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal, QThread
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QTimer, QEventLoop


from Voz_Slide.Herramientas_del_asistente import set_voz_callback
from Voz_Slide.Transcriptor import set_mic_callback

_funcion_texto_externa = None
_funcion_voz_externa = None

class ChatWorker(QThread):
    def __init__(self, mensaje, ventana):
        super().__init__()
        self.mensaje = mensaje
        self.ventana = ventana

    def run(self):
        if _funcion_texto_externa:
            _funcion_texto_externa(self.mensaje, self.ventana)
        else:
            self.ventana.enviar_texto_a_html("SYS >> ERROR: Sin función de texto.", "#ff0033")

class VoiceWorker(QThread):
    def __init__(self, ventana):
        super().__init__()
        self.ventana = ventana

    def run(self):
        if _funcion_voz_externa:
            _funcion_voz_externa(self.ventana)
        else:
            self.ventana.enviar_texto_a_html("SYS >> ERROR: Sin función de voz.", "#ff0033")
            self.ventana.cambiar_estado_html('inactivo')

class BackendBridge(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.chat_worker = None
        self.voice_worker = None

    @Slot()
    def activar_slide(self):
        self.main_window.cambiar_estado_html('activo')
        self.main_window.enviar_texto_a_html("SYS >> Iniciando escucha...", "#ffcc00")
        if self.voice_worker is None or not self.voice_worker.isRunning():
            self.voice_worker = VoiceWorker(self.main_window)
            self.voice_worker.start()

    @Slot(str)
    def recibir_comando(self, comando):
        self.main_window.enviar_texto_a_html(f"SYS >> Recibido: {comando}", "#ffcc00")
        if self.chat_worker is None or not self.chat_worker.isRunning():
            self.chat_worker = ChatWorker(comando, self.main_window)
            self.chat_worker.start()

class SlideHUD(QMainWindow):
    senal_texto = Signal(str, str)
    senal_estado = Signal(str)
    senal_voz = Signal(float)
    # Canal PROPIO para la entrada. Compartirlo con senal_voz haria que 'AIDEN habla'
    # y 'AIDEN me oye' se vieran igual, que es justo lo que hay que distinguir.
    senal_mic = Signal(float)
    pedir_mostrar = Signal()   # always-on: pedir mostrar la ventana desde otro hilo
    pedir_ocultar = Signal()   # always-on: ocultar la ventana ya (comando "ocultate")
    pedir_fijar = Signal(bool) # always-on: fijar/soltar la ventana (comando "quedate")

    def __init__(self):
        super().__init__()
        #self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(850, 800)

        # 🔥 RUTAS SEGURAS BASADAS EN EL ARCHIVO MAIN.PY 🔥
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # 🔥 REPRODUCTOR DE AUDIO 🔥
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0) 
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        
        # Ruta del audio corregida
        ruta_audio = os.path.join(base_dir, "startup.mp3")
        if os.path.exists(ruta_audio):
            self.player.setSource(QUrl.fromLocalFile(ruta_audio))
            self.player.play()
        # --------------------------------------------------

        self.browser = QWebEngineView(self)
        self.setCentralWidget(self.browser)
        self.browser.page().setBackgroundColor(Qt.transparent)
        self.browser.setAttribute(Qt.WA_TranslucentBackground)
        self.browser.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)

        self.channel = QWebChannel()
        self.backend = BackendBridge(self)
        self.channel.registerObject('backend', self.backend)
        self.browser.page().setWebChannel(self.channel)

        # Ruta del HTML corregida
        ruta_html = os.path.join(base_dir, "index.html")
        self.browser.load(QUrl.fromLocalFile(ruta_html))

        self.drag_bar = QWidget(self)
        self.drag_bar.setGeometry(0, 0, 850, 80)
        self.drag_bar.setStyleSheet("background: transparent;")
        self.drag_bar.mousePressEvent = self.iniciar_arrastre_nativo
        self.drag_bar.mouseMoveEvent = self.mover_arrastre_nativo
        self.drag_pos = None

        self.senal_texto.connect(self._ejecutar_js_texto)
        self.senal_estado.connect(self._ejecutar_js_estado)
        self.senal_voz.connect(self._ejecutar_js_voz)
        self.senal_mic.connect(self._ejecutar_js_mic)
        # La esfera imitará la amplitud real del audio de Kokoro
        set_voz_callback(self.enviar_nivel_voz)
        set_mic_callback(self.enviar_nivel_mic)

        # ── Always-on ────────────────────────────────────────────────────────
        # modo_persistente: si es True, cerrar la ventana NO la destruye (la oculta)
        # y avisa por al_ocultar, para que el cerebro vuelva a REPOSO. Por defecto
        # False => Main.py se comporta igual que siempre (cerrar = destruir).
        self.modo_persistente = False
        self.al_ocultar = None
        self._ms_inactividad = 120000   # 120s de inactividad antes de auto-ocultarse (always-on)
        self._fijada = False            # si True, la ventana NO se auto-oculta (comando 'quedate')
        self.pedir_mostrar.connect(self._mostrar_persistente)
        self.pedir_ocultar.connect(self._ocultar_persistente)
        self.pedir_fijar.connect(self._fijar_persistente)

        self.temporizador = QTimer(self)

        self.temporizador.timeout.connect(self.cerrar_interfaz_por_completo)

        self.temporizador.start(2147483647)

    def iniciar_arrastre_nativo(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mover_arrastre_nativo(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def enviar_texto_a_html(self, texto, color="#ffcc00"):
        try:
            self.senal_texto.emit(texto, color)
        except RuntimeError:
            # Si la ventana ya se destruyó, atrapamos el error en silencio
            pass

    def cambiar_estado_html(self, estado):
        try:
            self.senal_estado.emit(estado)
        except RuntimeError:
            # Si la ventana ya se destruyó, atrapamos el error en silencio
            pass

    def _ejecutar_js_texto(self, texto, color):
        self.browser.page().runJavaScript(f"appendLog('{texto}', '{color}');")
        self.mostrar_interfaz(True)
        self._reiniciar_timer()

    def _ejecutar_js_estado(self, estado):
        self.browser.page().runJavaScript(f"setEstado('{estado}');")
        self._reiniciar_timer()

    def enviar_nivel_voz(self, nivel):
        try:
            self.senal_voz.emit(float(nivel))
        except RuntimeError:
            pass

    def _ejecutar_js_voz(self, nivel):
        self.browser.page().runJavaScript(f"setVoiceLevel({nivel});")
        self._reiniciar_timer()   # mientras AIDEN habla, no se cierra la ventana

    def enviar_nivel_mic(self, nivel):
        # Lo llama el hilo de captura de voz; la señal cruza al hilo de Qt sola.
        try:
            self.senal_mic.emit(float(nivel))
        except RuntimeError:
            pass

    def _ejecutar_js_mic(self, nivel):
        self.browser.page().runJavaScript(f"setMicLevel({nivel});")
        self._reiniciar_timer()   # mientras MARCO habla, tampoco se cierra la ventana
    def mostrar_interfaz(self, mostrar: bool):
        comando_js = "toggleInterfaz(true);" if mostrar else "toggleInterfaz(false);"
        self.browser.page().runJavaScript(comando_js)
    def cerrar_interfaz_por_completo(self):

        self.temporizador.stop()   # 1)Apagado de reloj, soluciona el bug de autodestruccion
        self.close()               # 2)Funcion cerrar ventana

    def _mostrar_persistente(self):
        # Always-on: muestra la ventana desde el hilo principal y reinicia el timer
        # de inactividad (60s). Se llama por la señal pedir_mostrar (thread-safe).
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            self.mostrar_interfaz(True)
        except Exception:
            pass
        self._reiniciar_timer()

    def _reiniciar_timer(self):
        # Reinicia el contador de inactividad, salvo que la ventana este FIJADA ('quedate').
        if not getattr(self, '_fijada', False):
            self.temporizador.start(getattr(self, '_ms_inactividad', 120000))

    def _ocultar_persistente(self):
        # Comando 'ocultate/descansa': oculta la ventana YA y vuelve a REPOSO.
        self._fijada = False
        self.cerrar_interfaz_por_completo()

    def _fijar_persistente(self, fijar):
        # Comando 'quedate': True deja la ventana fija (no se auto-oculta); False la suelta.
        self._fijada = bool(fijar)
        if self._fijada:
            self.temporizador.stop()
        else:
            self.temporizador.start(getattr(self, '_ms_inactividad', 120000))

    def closeEvent(self, event):
        # En modo always-on (persistente), cerrar NO destruye la ventana: la oculta
        # y avisa (al_ocultar) para que el cerebro vuelva a REPOSO. En modo normal
        # (Main.py) se comporta como siempre (deja que la ventana se cierre/destruya).
        if getattr(self, 'modo_persistente', False):
            event.ignore()
            self.temporizador.stop()
            self.hide()
            try:
                self.mostrar_interfaz(False)
            except Exception:
                pass
            if self.al_ocultar:
                try:
                    self.al_ocultar()
                except Exception:
                    pass
        else:
            super().closeEvent(event)

   

def ejecutar_slide(funcion_texto=None, funcion_voz=None):
    global _funcion_texto_externa, _funcion_voz_externa
    _funcion_texto_externa = funcion_texto
    _funcion_voz_externa = funcion_voz


    app = QApplication.instance()
    if not app:
     QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
     app = QApplication(sys.argv)
     app.setQuitOnLastWindowClosed(False)


    ventana = SlideHUD()
    ventana.setAttribute(Qt.WA_DeleteOnClose)
    ventana.show()
    loop = QEventLoop()
    ventana.destroyed.connect(loop.quit)
    loop.exec()
    