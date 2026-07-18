import os as os
import speech_recognition as sr
import time
from Voz_Slide.Herramientas_del_asistente import buscar_microfono, marcar_fin_peticion
from faster_whisper import WhisperModel





instancia = sr.Recognizer()
# 1.5s de silencio para dar por terminada la frase (antes 2s: medio segundo de espera muerta
# en CADA turno antes de siquiera empezar a transcribir).
instancia.pause_threshold = 1.5
print("Cargando Modelo...")
# large-v3-turbo: calidad de large-v3 con velocidad de medium (~1.7 GB VRAM en int8_float16).
# Sube MUCHO el oído en español vs "small" (que era PEOR que el "medium" del wake-word del VAD).
_MODELO_VOZ = "large-v3-turbo"
model = WhisperModel(_MODELO_VOZ, device="cuda", compute_type="int8_float16")


def _asegurar_modelo():
    # Recarga el Whisper de voz si fue descargado (p. ej. en modo gaming).
    global model
    if model is None:
        print("Recargando Whisper (voz)...")
        model = WhisperModel(_MODELO_VOZ, device="cuda", compute_type="int8_float16")
    return model


def descargar_modelo_voz():
    # Libera el Whisper de la GPU para soltar VRAM (modo gaming).
    global model
    model = None
    try:
        import gc
        gc.collect()
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def recargar_modelo_voz():
    # Vuelve a dejar el Whisper listo en la GPU.
    _asegurar_modelo()


microfono_encontrado = buscar_microfono()
_calibrado = False


# --- Guardia anti-alucinaciones de Whisper ---------------------------------
# Cuando Whisper recibe SILENCIO o ruido (un suspiro, el ventilador, la calle, la tele baja)
# tiende a "inventar" frases que vio millones de veces en subtitulos de YouTube. DOS defensas:
#   (1) _texto_confiable: filtra por la CONFIANZA del propio modelo (la senal mas potente).
#   (2) es_alucinacion: lista negra de frases/tokens fantasma conocidos.
# Frases fantasma (subcadena: si aparece dentro del texto, es alucinacion).
_ALUCINACIONES = (
    "amara.org", "subtitulamos.tv", "subtitulado por", "subtitulos por",
    "subtitulos realizados por", "subtitulos hechos por", "subtitles by",
    "gracias por ver", "gracias por su atencion", "gracias por escuchar",
    "no olvides suscribirte", "suscribete al canal", "dale like",
    "like y suscribete", "comenta y suscribete", "nos vemos en el proximo",
    "nos vemos en la proxima", "hasta la proxima", "hasta el proximo video",
    "thanks for watching", "thank you for watching", "see you next time",
    "mooji.org", "editado por", "transcripcion por", "www.", ".com/",
    "musica de fondo",
)
# Tokens/frases que SOLO son alucinacion si vienen SOLOS (texto completo == esto).
# OJO: NO se incluyen "si"/"no"/"ok" porque son respuestas validas a una pregunta.
_ALUCINACIONES_EXACTAS = (
    "suscribete", "gracias", "muchas gracias", "subtitulos", "adios",
    "hasta luego", "you", "thank you", "thanks", "bye", "musica",
    "aplausos", "risas", "silencio",
)


def _norm(texto):
    # minusculas, sin tildes, sin signos al inicio/fin, espacios colapsados.
    t = (texto or "").strip().lower()
    t = t.translate(str.maketrans("áéíóúü", "aeiouu"))
    t = t.strip(" ¡!¿?.,;:-—\"'()[]")
    return " ".join(t.split())


# Palabras cortas (<=2 letras) que SI son validas (respuestas a una pregunta).
_VALIDAS_CORTAS = ("si", "no", "ya", "ok", "va")


def es_alucinacion(texto):
    """True si el texto transcrito es una alucinacion tipica de Whisper sobre silencio/ruido."""
    limpio = _norm(texto)
    if not limpio:
        return True
    if len(limpio) <= 2 and limpio not in _VALIDAS_CORTAS:   # ruido, no un comando
        return True
    if limpio in _ALUCINACIONES_EXACTAS:
        return True
    return any(frase in limpio for frase in _ALUCINACIONES)


def _texto_confiable(segmentos):
    """Une el texto de los segmentos descartando los que el MODELO marca como poco fiables
    (probable alucinacion): no detecto voz, confianza pesima, o texto muy repetitivo.
    Umbrales conservadores para no cortar voz real."""
    partes = []
    for s in segmentos:
        no_voz     = getattr(s, "no_speech_prob", 0.0)    # prob. de que NO haya voz
        confianza  = getattr(s, "avg_logprob", 0.0)       # mas negativo = menos seguro
        repeticion = getattr(s, "compression_ratio", 0.0) # alto = texto en bucle
        if no_voz > 0.6 and confianza < -0.5:   # silencio disfrazado
            continue
        if confianza < -1.0:                    # confianza pesima -> invento
            continue
        if repeticion > 2.4:                    # "gracias gracias gracias..."
            continue
        partes.append(s.text)
    return "".join(partes).strip()


def escuchador_de_usuario(timeout=15):
 global _calibrado
 try:

  with sr.Microphone(device_index=microfono_encontrado) as source:
    if not _calibrado:
        print("Calibrando microfono (solo la primera vez)...")
        instancia.adjust_for_ambient_noise(source, duration=0.5)
        _calibrado = True
    print("Escuchandote....")
    audio_capturar = instancia.listen(source, phrase_time_limit=50, timeout=timeout)
    marcar_fin_peticion()   # terminaste de hablar -> arranca el cronometro de respuesta
    print("Fin de la conversacion, procesando...")
  if audio_capturar is not None: 
   with open("archivo_temporal_voz.wav","wb") as x:
     x.write(audio_capturar.get_wav_data())
    
   _t0 = time.perf_counter()
   # vad_filter: el Silero interno de faster-whisper descarta el audio SIN voz antes de
   # transcribir -> mata casi todas las alucinaciones de silencio.
   # condition_on_previous_text=False: evita que arrastre/repita texto fantasma.
   segmentos,_ = _asegurar_modelo().transcribe(
       "archivo_temporal_voz.wav", language="es",
       vad_filter=True, condition_on_previous_text=False,
       no_speech_threshold=0.6, log_prob_threshold=-1.0,
   )
   texto = _texto_confiable(segmentos)
   print(f"⏱  Transcripcion (Whisper) : {time.perf_counter() - _t0:5.2f} s")
   if es_alucinacion(texto):
       print(f"🛇 Alucinacion descartada: {texto!r}")
       return None
   return texto
  else:
    print("No se capturo audio...")


 except sr.WaitTimeoutError:
   print("Paso mucho tiempo y no dijiste nada, volviendo a esperar...")
   return None

 except Exception as e:
    print(f"Error detectado: {e}") 


  
    
   


