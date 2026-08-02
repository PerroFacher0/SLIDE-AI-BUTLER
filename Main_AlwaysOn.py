# ─────────────────────────────────────────────────────────────────────────────
# AIDEN — versión ALWAYS-ON (siempre encendido)
#
# Diferencia con Main.py: AIDEN hace login UNA sola vez y luego vive en un bucle
# infinito que NUNCA termina, alternando:
#   - REPOSO: escucha la palabra clave (barato; Whisper/Kokoro/LLM en reposo).
#   - ACTIVO: abre la esfera y conversa; al cerrar la ventana, vuelve a REPOSO.
# Si la palabra clave no se detecta, sigue esperando (no se apaga).
#
# Es un archivo APARTE: Main.py queda intacto. Para probarlo: F5 sobre este archivo.
# Si te convence, cambia el lanzador (AIDEN.bat) para que corra Main_AlwaysOn.py.
# ─────────────────────────────────────────────────────────────────────────────

# ── INSTANCIA ÚNICA ───────────────────────────────────────────────────────────
# Si AIDEN ya está corriendo, esta copia se cierra de inmediato (antes de cargar
# modelos) para no duplicar el asistente ni gastar el doble de memoria.
import sys as _sys
import socket as _socket
_instancia_lock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
try:
    _instancia_lock.bind(("127.0.0.1", 50607))
except OSError:
    print("AIDEN ya está corriendo; cierro esta instancia para no duplicar.")
    _sys.exit(0)

from Nucleo_Slide.Cerebro import iniciar_centinela
from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
from Funciones_Slide.Productividad.Tareas_Hilos_Comandos import iniciar_hilos
from Funciones_Slide.Sistema.Comandos_Asistente import Reconocimiento_Facial
from Voz_Slide.VAD import Reconocimiento_de_habla
from Interfaz.Interfaz_En_Python import SlideHUD
import Interfaz.Interfaz_En_Python as interfaz
import sys
import os
import threading
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt
from Funciones_Slide.Productividad.Rutina import briefing
from Funciones_Slide.Productividad.Alertas_Mercado import iniciar_alertas
from Funciones_Slide.Productividad.Descanso import iniciar_guardian_descanso
from Funciones_Slide.Info.Bitacora import contar_actividad
from Funciones_Slide.Comunicacion.Telegram_Control import iniciar_telegram
from Funciones_Slide.Productividad.Anticipacion import iniciar_anticipacion
from Funciones_Slide.Sistema.Presencia import iniciar_presencia
from Funciones_Slide.Comunicacion.Vigilante_Llamadas import iniciar_vigilante_llamadas
from Funciones_Slide.Sistema.Vigilante_Pantalla import iniciar_vigilante_pantalla
from Funciones_Slide.Sistema.Vigilante_Portapapeles import iniciar_vigilante_portapapeles
from Funciones_Slide.Sistema.Vigilante_Eventos import iniciar_vigilante_eventos
from Nucleo_Slide.Memoria_Visual import iniciar_memoria_visual
from Funciones_Slide.Sistema.Control_Total import precalentar as precalentar_ps
from Funciones_Slide.Sistema.Vigilante_Reunion import iniciar_vigilante_reunion
from Nucleo_Slide.Conciencia_Ambiental import iniciar_conciencia_ambiental
from Nucleo_Slide.Perfil_Marco import iniciar_perfil
from Funciones_Slide.Productividad.Seguimiento_Metas import iniciar_seguimiento_metas
from Nucleo_Slide.Compania import apertura_rica
from Nucleo_Slide.Reflexion import iniciar_reflexion
from Nucleo_Slide.Memoria_RAG import iniciar_rag
from Funciones_Slide.Sistema.Co_Ingeniero import iniciar_co_ingeniero
from Funciones_Slide.Sistema.Preparacion import iniciar_preparacion
from Funciones_Slide.Info.Finanzas_Gastos import iniciar_vigilante_gastos
from Funciones_Slide.Productividad.Ordenes_Condicionales import iniciar_ordenes
from Nucleo_Slide.Monologo import iniciar_monologo
from Funciones_Slide.Sistema.Sesion import iniciar_sesion_autoguardado
from Funciones_Slide.Sistema.Mayordomo_Archivos import iniciar_mayordomo_archivos
from Funciones_Slide.Info.Agenda import resumen_dia
from Funciones_Slide.Info.Bitacora import resumen_priorizado
# El enrutador de peticiones (atajos + LLM + manos libres) vive en UN solo módulo compartido
# con Main.py: cada arreglo aplica a los dos a la vez (antes estaba duplicado y divergía).
from Nucleo_Slide.Peticiones import Procesar_Peticion, Voz
iniciar_hilos()


# ── ARRANQUE (always-on con inversión de Qt) ─────────────────────────────────
# Arquitectura:
#   - HILO PRINCIPAL = Qt: app + ventana (persistente, oculta) + icono en bandeja,
#     corriendo SIEMPRE con app.exec(). Eso da el "vive de fondo" y el tray reactivo.
#   - HILO DE FONDO  = cerebro de REPOSO: escucha la palabra clave (micrófono) y,
#     al detectarla, pide MOSTRAR la ventana (por señal). La conversación dentro de
#     la ventana sigue igual que siempre (clic en la esfera -> Voz; escribir -> texto).
#   - La ventana se oculta sola tras 60s de inactividad (timer) -> vuelve a REPOSO.
# DECISIÓN DE SEGURIDAD: el login FACIAL (cámara) se hace en el HILO PRINCIPAL (como
# Main.py, que ya funciona). Solo la escucha de palabra clave (mic) va al hilo de fondo,
# para evitar el bug conocido de abrir la cámara en un hilo secundario.

# Control remoto por Telegram: arranca primero (control desde el celular aunque no estés).
iniciar_telegram()

hablado_del_asistente("Iniciando sistema de seguridad...")
print("Iniciando sistema de seguridad...")

# LOGIN: una sola vez, en el hilo principal (cámara).
verificacion = Reconocimiento_Facial()

if verificacion != "Bienvenido Marco":
    hablado_del_asistente("Acceso denegado")
    print("Acceso denegado")
    sys.exit(0)

# Login OK: briefing + arranque de hilos de fondo (todo una sola vez).
hablado_del_asistente(apertura_rica())   # apertura que canaliza TODO el núcleo (memoria+pendiente+meta+momento)
hablado_del_asistente(briefing())
# TU DÍA REAL: agenda de hoy + correos sin leer (si Marco configuró correo/calendario en secretos).
_dia = resumen_dia()
if _dia:
    hablado_del_asistente(_dia)
# NOTIFICACIONES PRIORIZADAS: en vez de "llegaron 23", AIDEN dice solo lo que importa.
_prior = resumen_priorizado()
if _prior:
    hablado_del_asistente(_prior)
iniciar_alertas(hablado_del_asistente)
iniciar_guardian_descanso(hablado_del_asistente)
iniciar_anticipacion(hablado_del_asistente)   # anticipación proactiva (clima, trasnochadas)
iniciar_presencia(hablado_del_asistente)      # te saluda al llegar al PC (ve tu cara)
iniciar_vigilante_llamadas(hablado_del_asistente)  # te avisa de llamadas entrantes al PC
iniciar_vigilante_pantalla(hablado_del_asistente)  # te avisa si una app se congela / hay un error
iniciar_vigilante_portapapeles(hablado_del_asistente)  # reacciona a lo que copias (error/YouTube)
iniciar_vigilante_eventos(hablado_del_asistente)   # USB conectado / descarga terminada
iniciar_memoria_visual()                           # pasado visual de la pantalla (APAGADA por defecto)
# Deja una sesion de PowerShell ya arrancada: el primer comando del dia no paga los ~2s
# de arranque. Si falla, ejecutar_en_pc sigue funcionando por el camino de siempre.
precalentar_ps()
iniciar_vigilante_reunion(hablado_del_asistente)   # modo reunión: silencia distracciones en llamadas
iniciar_conciencia_ambiental()                     # mira el estado del PC y decide solo qué hacer
iniciar_perfil()                                   # aprende quién es Marco con el tiempo
iniciar_seguimiento_metas(hablado_del_asistente)   # PERSIGUE tus metas (te acompaña 1 vez/día)
iniciar_reflexion()                                # contempla y entiende el momento de Marco
iniciar_rag()                                      # memoria semántica (búsqueda por significado)
iniciar_co_ingeniero(hablado_del_asistente)        # te ofrece ayuda al verte atascado (taller)
iniciar_preparacion(hablado_del_asistente)         # "me tomé la libertad de..." prepara tu contexto
iniciar_vigilante_gastos()                         # captura tus gastos de las notis de Nequi/Nu (auto)
iniciar_centinela()                                # detecta SyntaxError al guardar tu código (estaba muerto)
iniciar_ordenes(hablado_del_asistente)             # recados condicionales ("en 20 min...", "cuando abra X...")
iniciar_monologo()                                 # mini consciencia: pensamiento interno vivo (se ve en el overlay)
iniciar_sesion_autoguardado()                      # recuerda tu espacio de trabajo (para "retomemos")
iniciar_mayordomo_archivos(hablado_del_asistente)  # ordena capturas/instaladores 1 vez al día (habito suyo)

# ── Qt en el hilo principal ───────────────────────────────────────────────────
# Las funciones que usa la ventana para conversar (event-driven, sin cambios):
interfaz._funcion_texto_externa = Procesar_Peticion
interfaz._funcion_voz_externa = Voz

app = QApplication.instance()
if not app:
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)   # no se cierra al ocultar la ventana

ventana = SlideHUD()
ventana.modo_persistente = True                 # cerrar = ocultar (no destruir)
_evento_oculto = threading.Event()
ventana.al_ocultar = _evento_oculto.set         # avisa al cerebro cuando se oculta
# La ventana arranca OCULTA: AIDEN vive en la bandeja hasta la palabra clave.

# ── Icono en la bandeja del sistema ──────────────────────────────────────────
_ruta_ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AIDEN.ico")
tray = QSystemTrayIcon()
if os.path.exists(_ruta_ico):
    tray.setIcon(QIcon(_ruta_ico))
tray.setToolTip("AIDEN — asistente activo")
_menu = QMenu()
_act_mostrar = QAction("Mostrar AIDEN")
_act_mostrar.triggered.connect(lambda *_: ventana.pedir_mostrar.emit())
_act_salir = QAction("Salir")
_act_salir.triggered.connect(lambda *_: app.quit())
_menu.addAction(_act_mostrar)
_menu.addAction(_act_salir)
tray.setContextMenu(_menu)
# Clic en el icono de la bandeja -> muestra AIDEN (cualquier tipo de clic).
tray.activated.connect(lambda *_: ventana.pedir_mostrar.emit())
tray.show()
try:
    tray.showMessage("AIDEN", "En línea, señor. Diga la palabra clave cuando me necesite.")
except Exception:
    pass

# ── Cerebro de REPOSO en hilo de fondo (solo micrófono) ──────────────────────
def bucle_reposo():
    from Nucleo_Slide.Peticiones import extraer_comando_tras_wake
    while True:
        Activado, Texto = Reconocimiento_de_habla()    # REPOSO: escucha la palabra clave
        if not Activado:
            continue                                    # no detectada -> sigue esperando (no se apaga)
        # ACTIVO: pide mostrar la ventana (en el hilo principal).
        _evento_oculto.clear()
        ventana.pedir_mostrar.emit()
        # UNA SOLA RESPIRACIÓN: si con la palabra clave vino el comando ("aiden, ¿qué hora
        # es?"), se responde YA — antes el comando se DESCARTABA y tocaba repetirlo.
        try:
            comando = extraer_comando_tras_wake(Texto or "")
            if comando:
                ventana.enviar_texto_a_html(f"USER (Voz) >> {comando}", "#ffffff")
                print(f"USER (Voz, con la palabra clave): {comando}")
                Procesar_Peticion(comando, ventana)
        except Exception as e:
            print(f"[reposo] error procesando el comando del despertar: {e}")
        _evento_oculto.wait()                           # la ventana se oculta tras 60s o al cerrarla
        # vuelve arriba a REPOSO

threading.Thread(target=bucle_reposo, daemon=True).start()

# OVERLAY DE PRESENCIA: hace VISIBLE el núcleo (foco, estado, metas, eventos, reflexión) en una
# esquina, siempre encima y click-through. Aislado: si falla, no afecta nada.
try:
    from Interfaz.Overlay import crear_overlay
    _overlay = crear_overlay()
except Exception as _e:
    _overlay = None
    print(f"[overlay] omitido: {_e}")

# LA MIRA: marca en pantalla DÓNDE va a hacer clic AIDEN antes de moverse (da tiempo a verlo y a
# frenarlo con Ctrl+Alt+P). Va aquí porque necesita el hilo de Qt. Aislada: si falla, no afecta nada.
try:
    from Interfaz.Mira import iniciar as _iniciar_mira
    _iniciar_mira()
except Exception as _e:
    print(f"[mira] omitida: {_e}")

# Qt corre para siempre aquí (esto es lo "always-on"); se sale solo con "Salir" del tray.
sys.exit(app.exec())