import winreg
import threading
import time
from Funciones_Slide.Productividad.Alertas_Mercado import pausar_alertas
from Funciones_Slide.Productividad.Anticipacion import pausar_anticipacion
from Funciones_Slide.Sistema.Presencia import pausar_presencia
from Funciones_Slide.Comunicacion.Vigilante_Llamadas import pausar_vigilante_llamadas
from Funciones_Slide.Sistema.Vigilante_Pantalla import pausar_vigilante_pantalla
from Funciones_Slide.Sistema.Vigilante_Portapapeles import pausar_vigilante_portapapeles
from Funciones_Slide.Sistema.Vigilante_Reunion import pausar_vigilante_reunion
from Nucleo_Slide.Conciencia_Ambiental import pausar_conciencia
from Funciones_Slide.Sistema.Vigilante_Eventos import pausar_vigilante_eventos
from Nucleo_Slide.Memoria_Visual import pausar_memoria_visual
from Voz_Slide.Transcriptor import descargar_modelo_voz, recargar_modelo_voz
from Voz_Slide.Herramientas_del_asistente import descargar_kokoro, recargar_kokoro, _lock_audio


def _notificaciones_windows(activadas):
    # Activa/desactiva las notificaciones (toasts) de Windows via registro.
    try:
        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications",
        )
        winreg.SetValueEx(key, "ToastEnabled", 0, winreg.REG_DWORD, 1 if activadas else 0)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _liberar_vram(liberar):
    # gaming ON -> descarga Whisper(voz) ya, y Kokoro DESPUÉS de la confirmación hablada
    #              (espera el candado de audio para no recargarlo al hablar).
    # gaming OFF -> recarga ambos. (La palabra clave NO se afecta: su Whisper está en CPU.)
    try:
        if liberar:
            descargar_modelo_voz()   # Whisper de voz: se suelta de una (no se usa para hablar)

            def _soltar_kokoro_tras_hablar():
                time.sleep(1.5)          # deja que arranque la confirmación hablada
                with _lock_audio:        # espera a que AIDEN termine de hablar
                    descargar_kokoro()

            threading.Thread(target=_soltar_kokoro_tras_hablar, daemon=True).start()
        else:
            recargar_modelo_voz()
            recargar_kokoro()
        return True
    except Exception as e:
        print(f"[modo_gaming] no pude tocar la VRAM: {e}")
        return False


def modo_gaming(activar):
    # 'activar' puede venir como texto; lo interpretamos.
    txt = str(activar).strip().lower()
    encender = txt not in ("off", "desactivar", "apagar", "no", "false", "0", "quitar")

    _notificaciones_windows(not encender)   # gaming ON  -> notificaciones OFF
    pausar_alertas(encender)                # gaming ON  -> alertas de mercado en pausa
    pausar_anticipacion(encender)           # gaming ON  -> anticipación proactiva en pausa
    pausar_presencia(encender)              # gaming ON  -> saludo por presencia en pausa
    pausar_vigilante_llamadas(encender)     # gaming ON  -> aviso de llamadas en pausa
    pausar_vigilante_pantalla(encender)     # gaming ON  -> centinela de pantalla en pausa
    pausar_vigilante_portapapeles(encender) # gaming ON  -> portapapeles inteligente en pausa
    pausar_vigilante_reunion(encender)      # gaming ON  -> detector de reuniones en pausa
    pausar_conciencia(encender)             # gaming ON  -> conciencia ambiental en pausa
    pausar_vigilante_eventos(encender)      # gaming ON  -> avisos de USB/descargas en pausa
    pausar_memoria_visual(encender)         # gaming ON  -> deja de mirar la pantalla
    try:                                    # avisa a la conciencia compartida el modo actual
        from Nucleo_Slide.Estado_Del_Mundo import actualizar, registrar_evento
        actualizar(modo="gaming" if encender else "normal")
        registrar_evento("Marco entró a modo gaming." if encender else "Marco salió de modo gaming.", "modos")
    except Exception:
        pass
    vram_ok = _liberar_vram(encender)       # gaming ON  -> libera VRAM (descarga modelos)

    if encender:
        extra = " Liberé la VRAM de la GPU descargando mis modelos de voz." if vram_ok else ""
        return ("Modo gaming activado, señor. Silencié las notificaciones de Windows y mis avisos." +
                extra + " A disfrutar.")
    extra = " Recargué mis modelos de voz." if vram_ok else ""
    return ("Modo gaming desactivado, señor. Notificaciones y avisos de vuelta a la normalidad." + extra)
