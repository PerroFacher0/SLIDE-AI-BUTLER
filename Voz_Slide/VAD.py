import torch
from collections import deque
import numpy as np
from Voz_Slide.Transcriptor import escuchador_de_usuario, es_alucinacion, _texto_confiable
from faster_whisper import WhisperModel
import pyaudio
from Voz_Slide.Herramientas_del_asistente import buscar_microfono
import time
from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente

palabras = ["DESPIERTA","SLIDE","SLIGHT","OYE","ACTIVATE","PAPA ESTA EN CASA","TE NECESITO","PAPA ESTA EN CAZA","AIDEN","EIDEN","AYDEN","HEY DEN"]

microfono =  buscar_microfono()
print(microfono)

modelo, herramientas = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', source="github")


segundos = 25
tiempo_despierto = 0


(tiempo_de_habla,_,_,_,_) = herramientas
asistente_despierto = False

memoria_de_audio = deque(maxlen=100)

#Whisper  pero rapido y pyaudio

modelo_rapido = WhisperModel("medium",device="cpu",compute_type="int8")

Formato=pyaudio.paInt16
Muestreo=16000
Chunk=512

pyaudio_=pyaudio.PyAudio()
_info = pyaudio_.get_device_info_by_index(microfono)
Canales = min(int(_info["maxInputChannels"]), 2)
if Canales < 1:
    Canales = 1

stream = pyaudio_.open(format=Formato,channels=Canales,rate=Muestreo,input=True,frames_per_buffer=Chunk,input_device_index=microfono)

print("termino la configuracion")

def quitar_tildes_simple(texto):
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return texto.translate(reemplazos)

def Reconocimiento_de_habla():

    if stream.is_stopped():
       stream.start_stream()



    global tiempo_despierto
    global asistente_despierto
    while True:
      while stream.get_read_available() > Chunk:
        data = stream.read(Chunk,exception_on_overflow=False)

      tiempo_inicial = time.time()
      data = stream.read(Chunk,exception_on_overflow=False)
     

      chunk_numpy = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
      if Canales > 1:
          chunk_numpy = chunk_numpy.reshape(-1, Canales).mean(axis=1)
      torch_datos = torch.from_numpy(chunk_numpy)# aqui a torch, q es un lenguaje que las IAS entienden

      # inference_mode: este forward corre ~31 veces por SEGUNDO, siempre, mientras AIDEN espera la
      # palabra clave. Sin esto torch va montando el andamiaje de autograd (grafo y contadores de
      # versión) en cada pasada para un gradiente que nadie va a calcular jamás. Es gratis quitarlo.
      with torch.inference_mode():
          probabilidad = modelo(torch_datos,16000).item()
      Tiempo_total = tiempo_inicial - tiempo_despierto

      if probabilidad > 0.6:
        memoria_de_audio.append(chunk_numpy)
      else:
        if len(memoria_de_audio) > 10:
            print("fin frase")
            frase_completa = np.concatenate(list(memoria_de_audio))
            


            segmentos,_ = modelo_rapido.transcribe(frase_completa,language="es",beam_size=5,vad_filter=True,condition_on_previous_text=False,no_speech_threshold=0.6,log_prob_threshold=-1.0)
            texto = _texto_confiable(segmentos)#_texto_confiable descarta los segmentos que el modelo marca como poco fiables (alucinaciones)
            texto = texto.upper()
            texto_limpio = quitar_tildes_simple(texto)
            print(texto_limpio)

            memoria_de_audio.clear()

            # Si lo "oido" es una alucinacion de Whisper (silencio/ruido), ignorar y seguir escuchando.
            if es_alucinacion(texto_limpio):
                print("🛇 Alucinacion descartada (wake word/conversacion)")
                continue

            if asistente_despierto == True and Tiempo_total < segundos:
                tiempo_despierto = time.time()
                stream.stop_stream()
               
                return True, texto_limpio
            elif any(i in texto_limpio for i in palabras):
                tiempo_despierto = time.time()
                asistente_despierto=True
                stream.stop_stream()
                # UNA SOLA RESPIRACIÓN: si con la palabra clave vino un COMANDO ("aiden, abre
                # spotify"), no digas "a su servicio" — AIDEN va a responder/ejecutar YA.
                _solo_wake = True
                try:
                    from Nucleo_Slide.Peticiones import extraer_comando_tras_wake
                    _solo_wake = extraer_comando_tras_wake(texto_limpio) == ""
                except Exception:
                    pass
                if _solo_wake:
                    hablado_del_asistente("A su servicio señor")
                return True, texto_limpio

                

            



            