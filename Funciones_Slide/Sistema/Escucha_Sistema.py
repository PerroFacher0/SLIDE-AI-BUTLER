# CANAL DE AUDIO DEL SISTEMA: AIDEN puede "escuchar" lo que SUENA en la PC (un video, una
# llamada, un aviso de Windows) -- no el micrófono, sino la salida de audio real, vía captura
# WASAPI loopback (pyaudiowpatch; reemplaza al viejo "Stereo Mix" que ya casi ningún driver trae).
#
# A PROPÓSITO esto es una herramienta BAJO DEMANDA, no un vigilante que transcribe todo el tiempo
# en silencio: el audio del sistema puede incluir videollamadas o contenido privado, así que AIDEN
# solo escucha cuando Marco (o el propio agente, a raíz de algo que Marco pidió) lo pregunta
# explícitamente -- como preguntarle a otra persona "oye, ¿qué está sonando ahí?".
#
# Reutiliza el MISMO modelo Whisper que ya está cargado para la voz (Voz_Slide.Transcriptor): cero
# VRAM extra, cero tiempo de carga adicional.

import os
import threading
import time
import wave

_lock = threading.Lock()
_RUTA_TEMPORAL = "audio_sistema_temporal.wav"


def _dispositivo_loopback(pa):
    return pa.get_default_wasapi_loopback()


def _capturar(segundos):
    import pyaudiowpatch as pyaudio
    pa = pyaudio.PyAudio()
    try:
        dev = _dispositivo_loopback(pa)
        canales = dev["maxInputChannels"]
        rate = int(dev["defaultSampleRate"])
        frames = []

        def _callback(in_data, frame_count, time_info, status):
            frames.append(in_data)
            return (in_data, pyaudio.paContinue)

        stream = pa.open(
            format=pyaudio.paInt16, channels=canales, rate=rate,
            frames_per_buffer=1024, input=True, input_device_index=dev["index"],
            stream_callback=_callback,
        )
        stream.start_stream()
        time.sleep(max(0.2, float(segundos or 1)))
        stream.stop_stream()
        stream.close()
        return b"".join(frames), canales, rate
    finally:
        pa.terminate()


def nivel_audio_sistema():
    """HERRAMIENTA: dice si hay algo sonando AHORA MISMO en la PC (nivel de volumen instantáneo),
    sin transcribir nada -- rápido y barato, sin IA."""
    import numpy as np
    with _lock:
        try:
            datos, _canales, _rate = _capturar(0.6)
        except Exception as e:
            return f"No pude revisar el audio del sistema, señor: {e}"
    if not datos:
        return "No detecto el dispositivo de audio del sistema, señor."
    muestras = np.frombuffer(datos, dtype=np.int16)
    rms = float(np.sqrt(np.mean(muestras.astype(np.float64) ** 2))) if muestras.size else 0.0
    # Umbrales calibrados con mediciones reales (RMS ambiente sin nada sonando ~800-900 en esta
    # PC: el "silencio" digital nunca es exactamente cero). Aproximado, no milimétrico.
    if rms < 700:
        return "Silencio, señor: no hay nada sonando en la PC ahora mismo."
    if rms < 1800:
        return "Hay algo sonando bajito en la PC ahora mismo, señor."
    return "Sí, hay audio sonando en la PC ahora mismo, señor."


def que_esta_sonando(segundos=6):
    """HERRAMIENTA: graba lo que SUENA en la PC (un video, una llamada, un aviso del sistema --
    NO el micrófono) y lo transcribe, para saber qué se está diciendo o reproduciendo. Úsala
    cuando Marco pregunte 'qué está sonando', 'qué dice ese video' o 'sonó algo ahorita'."""
    segundos = max(2, min(30, float(segundos or 6)))
    with _lock:
        try:
            datos, canales, rate = _capturar(segundos)
        except Exception as e:
            return f"No pude grabar el audio del sistema, señor: {e}"
        if not datos:
            return "No conseguí capturar audio del sistema, señor."
        try:
            with wave.open(_RUTA_TEMPORAL, "wb") as wf:
                wf.setnchannels(canales)
                wf.setsampwidth(2)   # paInt16 -> 2 bytes por muestra
                wf.setframerate(rate)
                wf.writeframes(datos)
            from Voz_Slide.Transcriptor import _asegurar_modelo, _texto_confiable, es_alucinacion
            segmentos, _info = _asegurar_modelo().transcribe(
                _RUTA_TEMPORAL, language="es", vad_filter=True,
                condition_on_previous_text=False,
                no_speech_threshold=0.6, log_prob_threshold=-1.0,
            )
            texto = _texto_confiable(segmentos)
        except Exception as e:
            return f"Grabé el audio pero no pude transcribirlo, señor: {e}"
        finally:
            try:
                os.remove(_RUTA_TEMPORAL)
            except Exception:
                pass
    if not texto or es_alucinacion(texto):
        return "Grabé, pero no distinguí ninguna voz o diálogo claro (puede ser solo música o silencio), señor."
    return f"Esto es lo que suena en la PC, señor: «{texto}»"
