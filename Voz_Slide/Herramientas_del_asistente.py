import re
import threading
import queue
import time
import torch
import numpy as np
from kokoro import KPipeline as pipe
import sounddevice as sound

SAMPLE_RATE_KOKORO = 24000
SAMPLE_RATE_OUT    = 44100

_lock_audio = threading.Lock()   # serializa la voz: nunca dos audios sonando a la vez

# Cronometro de latencia: empieza cuando el usuario termina de hablar y se detiene
# en el primer sonido que produce Kokoro (la latencia real percibida).
_metrica = {"t_peticion": None}
def marcar_fin_peticion():
    _metrica["t_peticion"] = time.perf_counter()

# Callback opcional: la interfaz lo registra para recibir la amplitud (0–1)
# del audio de Kokoro en tiempo real y animar la esfera con la voz.
_voz_callback = None
def set_voz_callback(fn):
    global _voz_callback
    _voz_callback = fn

def _resample(audio):
    n = int(len(audio) * SAMPLE_RATE_OUT / SAMPLE_RATE_KOKORO)
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)

def _buscar_salida():
    prueba = (np.sin(2 * np.pi * 440 * np.arange(100) / SAMPLE_RATE_OUT) * 0.01).astype(np.float32)
    for i, d in enumerate(sound.query_devices()):
        if d['max_output_channels'] < 1:
            continue
        try:
            sound.play(prueba, SAMPLE_RATE_OUT, device=i, blocking=True)
            print(f"Salida de audio: [{i}] {d['name'][:40]}")
            return i
        except:
            continue
    return None

_DEVICE_OUT = _buscar_salida()

def buscar_microfono():
    import pyaudio
    p = pyaudio.PyAudio()
    prioridad = ["hd audio", "high definition", "realtek"]
    fallback  = ["microfono", "microphone"]
    excluir   = ["wo mic", "wave", "web camera", "webcam", "asignador", "controlador"]

    def _abre(i, info):
        try:
            ch = min(int(info["maxInputChannels"]), 2)
            s = p.open(format=pyaudio.paInt16, channels=ch, rate=16000,
                       input=True, frames_per_buffer=512, input_device_index=i)
            s.stop_stream(); s.close()
            return True
        except:
            return False

    encontrado = None
    for grupo in [prioridad, fallback]:
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] < 1:
                continue
            nombre = info["name"].lower()
            if any(e in nombre for e in excluir):
                continue
            if any(k in nombre for k in grupo) and _abre(i, info):
                encontrado = i
                break
        if encontrado is not None:
            break

    p.terminate()
    if encontrado is not None:
        print(f"Microfono: [{encontrado}]")
    else:
        print("No se encontro microfono")
    return encontrado


#ESTE ES EL MOTOR CON LAS REGLAS DE COMO SE PRONUNCIAN LAS COSAS COMO LETRAS Y COMO DEBEN SONAR

torch.backends.cudnn.enabled = False
pipeline = pipe(lang_code='es', repo_id='hexgrad/Kokoro-82M', device='cuda')
voz1 = pipeline.load_voice('em_santa')
voz3 = pipeline.load_voice('jf_alpha')
voz_mezclada = (voz1 * 0.45) + (voz3 * 0.55)


def _asegurar_kokoro():
    # Recarga Kokoro (voz) si fue descargado (p. ej. en modo gaming).
    global pipeline, voz1, voz3, voz_mezclada
    if pipeline is None:
        print("Recargando Kokoro (voz)...")
        torch.backends.cudnn.enabled = False
        pipeline = pipe(lang_code='es', repo_id='hexgrad/Kokoro-82M', device='cuda')
        voz1 = pipeline.load_voice('em_santa')
        voz3 = pipeline.load_voice('jf_alpha')
        voz_mezclada = (voz1 * 0.45) + (voz3 * 0.55)


def descargar_kokoro():
    # Libera Kokoro de la GPU para soltar VRAM (modo gaming).
    global pipeline, voz1, voz3, voz_mezclada
    pipeline = None
    voz1 = None
    voz3 = None
    voz_mezclada = None
    try:
        import gc
        gc.collect()
        torch.cuda.empty_cache()
    except Exception:
        pass


def recargar_kokoro():
    # Vuelve a dejar Kokoro listo en la GPU.
    _asegurar_kokoro()


def _prosodia(hora=None):
    # VOZ VIVA: de noche AIDEN habla un punto más calmado y suave (velocidad, volumen).
    # Jarvis no suena igual a las 3 de la tarde que a las 2 de la mañana.
    h = time.localtime().tm_hour if hora is None else hora
    if h >= 22 or h < 7:
        return 0.95, 0.8
    return 1.0, 1.0


def _generar_audio(frase, cola):
    _asegurar_kokoro()
    velocidad, volumen = _prosodia()
    audios = [audio * volumen for _, _, audio in pipeline(frase, voice=voz_mezclada, speed=velocidad)]
    cola.put(audios)


# ── BARGE-IN: interrumpir a AIDEN hablando ────────────────────────────────────
_MIC_BARGE = None   # indice de microfono cacheado (se busca una sola vez)

def _escuchar_interrupcion(evento_interrumpir, parar):
    """Hilo vigia: escucha el microfono MIENTRAS AIDEN habla. Si detecta voz
    sostenida del usuario, activa 'evento_interrumpir' para cortar el audio.
    'parar' lo usamos para apagar este hilo cuando AIDEN termina de hablar."""
    global _MIC_BARGE
    import pyaudio
    if _MIC_BARGE is None:
        _MIC_BARGE = buscar_microfono()
    if _MIC_BARGE is None:
        return                      # sin microfono no hay barge-in

    UMBRAL    = 0.045   # que tan fuerte debe sonar para contar como voz
    SOSTENIDO = 7       # chunks seguidos por encima del umbral (~220ms) = hablaste
    CHUNK     = 512     # muestras por lectura (~32ms a 16kHz)

    p = pyaudio.PyAudio()
    try:
        info = p.get_device_info_by_index(_MIC_BARGE)
        ch = min(int(info["maxInputChannels"]), 2)
        stream = p.open(format=pyaudio.paInt16, channels=ch, rate=16000,
                        input=True, frames_per_buffer=CHUNK,
                        input_device_index=_MIC_BARGE)
    except Exception:
        p.terminate()
        return

    seguidos = 0
    while not parar.is_set():
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
        except Exception:
            break
        muestras = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            muestras = muestras.reshape(-1, ch).mean(axis=1)
        volumen = float(np.abs(muestras).mean())
        if volumen > UMBRAL:
            seguidos += 1
            if seguidos >= SOSTENIDO:
                evento_interrumpir.set()   # ¡el usuario esta hablando!
                break
        else:
            seguidos = 0

    try:
        stream.stop_stream(); stream.close()
    except Exception:
        pass
    p.terminate()


def _reproducir_con_nivel(snd, rate, evento=None):
    # Reproduce el audio y, en paralelo, empuja su amplitud (RMS) a la esfera.
    # Si 'evento' se activa (el usuario interrumpio), corta el audio y devuelve True.
    if evento is not None and evento.is_set():
        return True                          # ya nos interrumpieron, ni empezamos
    sound.play(snd, rate, device=_DEVICE_OUT)
    if _metrica["t_peticion"] is not None:
        print(f"⏱  Respuesta hasta la primera voz: {time.perf_counter() - _metrica['t_peticion']:.2f} s")
        _metrica["t_peticion"] = None
    dur  = len(snd) / rate
    win  = max(1, int(rate * 0.03))           # ventana de 30ms para el RMS
    peak = max(1e-4, float(np.abs(snd).max()))  # normaliza por el pico de la frase
    t0   = time.time()
    while True:
        # ¿el usuario empezo a hablar? -> callar de golpe
        if evento is not None and evento.is_set():
            sound.stop()
            return True
        elapsed = time.time() - t0
        if elapsed >= dur:
            break
        if _voz_callback is not None:
            idx = int(elapsed * rate)
            seg = snd[idx:idx + win]
            if seg.size:
                rms = float(np.sqrt(np.mean(seg * seg)))
                nivel = min(1.0, (rms / peak) * 1.8)
                try:
                    _voz_callback(nivel)
                except Exception:
                    pass
        time.sleep(0.03)
    if _voz_callback is not None:
        try:
            _voz_callback(0.0)
        except Exception:
            pass
    sound.wait()
    return False


def hablado_del_asistente(texto_final):
    texto_final = re.sub(r'[*`#_~]', '', texto_final)   # quita Markdown para que Kokoro no lo lea
    frases = [f.strip() for f in re.split(r'(?<=[.!?])\s+', texto_final.strip()) if f.strip()]
    if not frases:
        return False

    with _lock_audio:
        barge = _voz_callback is not None
        evento_interrumpir = threading.Event()
        parar_listener     = threading.Event()
        listener = None
        if barge:
            listener = threading.Thread(
                target=_escuchar_interrupcion,
                args=(evento_interrumpir, parar_listener),
                daemon=True)
            listener.start()

        cola = queue.Queue()
        hilo = threading.Thread(target=_generar_audio, args=(frases[0], cola))
        hilo.start()

        interrumpido = False
        for i, _ in enumerate(frases):
            hilo.join()
            audios = cola.get()

            if i + 1 < len(frases):
                hilo = threading.Thread(target=_generar_audio, args=(frases[i + 1], cola))
                hilo.start()

            for audio in audios:
                if _reproducir_con_nivel(_resample(audio), SAMPLE_RATE_OUT, evento_interrumpir):
                    interrumpido = True
                    break
            if interrumpido:
                break

        parar_listener.set()
        if listener is not None:
            listener.join(timeout=0.5)
        if interrumpido:
            print("[BARGE-IN] AIDEN fue interrumpido por el usuario")
        return interrumpido


def _indice_dispositivo(nombre):
    # Devuelve el indice del dispositivo de salida cuyo nombre contenga 'nombre'.
    # Si no se encuentra (o nombre es None), usa la salida normal.
    if not nombre:
        return _DEVICE_OUT
    try:
        for i, d in enumerate(sound.query_devices()):
            if d["max_output_channels"] > 0 and nombre.lower() in d["name"].lower():
                return i
    except Exception:
        pass
    return _DEVICE_OUT


def hablar_en_dispositivo(texto, nombre_dispositivo=None):
    # Genera la voz de Kokoro y la reproduce en un dispositivo de salida ESPECIFICO
    # (ej. el cable de audio virtual, para meter la voz dentro de una llamada).
    texto = re.sub(r'[*`#_~]', '', texto)
    frases = [f.strip() for f in re.split(r'(?<=[.!?])\s+', texto.strip()) if f.strip()]
    if not frases:
        return
    device = _indice_dispositivo(nombre_dispositivo)
    _asegurar_kokoro()
    with _lock_audio:
        for frase in frases:
            audios = [a for _, _, a in pipeline(frase, voice=voz_mezclada, speed=1)]
            for audio in audios:
                sound.play(_resample(audio), SAMPLE_RATE_OUT, device=device)
                sound.wait()