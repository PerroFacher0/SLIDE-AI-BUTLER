import cv2
import webbrowser
import os
import subprocess
import pyautogui
import face_recognition
import face_recognition_models
import time 
import urllib.parse
import sys
from Funciones_Slide.Productividad.Gestion_datos import guardar_en_json
import json





Cara = cv2.imread(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Imagenes", "Marco.jpg"))

def abrir_camara():
 captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
 cv2.namedWindow("Camara_IA",cv2.WND_PROP_FULLSCREEN)
 cv2.setWindowProperty("Camara_IA",cv2.WND_PROP_FULLSCREEN,cv2.WND_PROP_FULLSCREEN)

 while True:
    
    resultado, imagen = captura.read()
    if not resultado:
        break
    
    resultado = cv2.imshow("Camara_IA",imagen)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

 captura.release()
 cv2.destroyAllWindows()
 return "Cámara cerrada, señor"

def Reconocimiento_Facial():

    Localizacion_cara = face_recognition.face_locations(Cara)[0]
    Vectores_referencia = face_recognition.face_encodings(Cara, known_face_locations=[Localizacion_cara])[0]
    captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    tiempo_inicio = time.time()
    segundos_maximos = 20
    cv2.namedWindow("Camara_IA", cv2.WND_PROP_FULLSCREEN) 
    cv2.setWindowProperty("Camara_IA", cv2.WND_PROP_FULLSCREEN, cv2.WND_PROP_FULLSCREEN)
    contador = 0
    while True:
        tiempo_actual = time.time()
        tiempo_transcurrido = tiempo_actual - tiempo_inicio
        resultado, imagen = captura.read()
        contador += 1
        if not resultado:
            break
        
        imagen = cv2.flip(imagen, 1)
        if contador %6 == 0 : 
         Localizacion_cara_Frames = face_recognition.face_locations(imagen)
        
         if len(Localizacion_cara_Frames) > 0:
            Vectores_cara_Frames = face_recognition.face_encodings(imagen, known_face_locations=Localizacion_cara_Frames)[0]
            result = face_recognition.compare_faces([Vectores_referencia], Vectores_cara_Frames)
            if result[0]:
               
               print("Acceso Confirmado...")
               captura.release()
               cv2.destroyAllWindows()
               return "Bienvenido Marco"
        if tiempo_transcurrido > segundos_maximos:
           break
        
        cv2.imshow("Camara_IA", imagen)

        if cv2.waitKey(33) & 0xFF == ord("q"):
            break
   
    captura.release()
    cv2.destroyAllWindows()
    return "Persona extraña"

def Abrir_Apps(Aplicacion):
   # Abre apps por el BUSCADOR de Windows (tecla Win), sin depender de imagenes.
   # Esto es mucho mas confiable que ubicar un screenshot en pantalla.
   pyautogui.press("win")
   time.sleep(0.6)
   pyautogui.typewrite(Aplicacion, interval=0.04)
   time.sleep(0.7)
   pyautogui.press("enter")
   return f"Abriendo {Aplicacion}, señor."

def Abrir_WhattsApp(Aplicacion_os):
   os.startfile("whatsapp://")

def Abrir_Videos_Youtube(Tipo_Video):
   busqueda_limpia = urllib.parse.quote_plus(f"{Tipo_Video} youtube")
   webbrowser.open(f"https://www.google.com/search?q={busqueda_limpia}&btnI")
   return f"Reproduciendo {Tipo_Video}, señor"

def Buscar_en_Google(Pagina):
   busqueda_limpia = urllib.parse.quote_plus(f"{Pagina}")
   webbrowser.open(f"https://www.google.com/search?q={busqueda_limpia}")
   return f"Buscando {Pagina} en Google, señor"

def Salir(demora=3.0):
   """HERRAMIENTA: cierra AIDEN de verdad.

   Antes esto era un `sys.exit()` a secas, y por eso "salir" no cerraba nada: las herramientas se
   ejecutan en un HILO de trabajo, y sys.exit() solo lanza SystemExit EN ESE HILO — lo recogía el
   manejador de errores del cerebro y el proceso seguía tan vivo como antes. Con Qt corriendo en el
   hilo principal y una veintena de hilos de fondo, la única salida fiable es pedirle a Qt que
   cierre y, pase lo que pase, terminar el proceso.

   La demora existe para que alcance a DESPEDIRSE: se devuelve la frase, AIDEN la dice, y el
   proceso muere después."""
   import threading

   def _apagar():
      time.sleep(max(0.5, float(demora)))
      # 1) Cierre limpio de Qt (quita el icono de la bandeja como es debido). invokeMethod es la
      #    forma segura de pedirlo desde otro hilo; llamar a quit() directo desde aquí no lo es.
      try:
         from PySide6.QtWidgets import QApplication
         from PySide6.QtCore import QMetaObject, Qt as _Qt
         app = QApplication.instance()
         if app is not None:
            QMetaObject.invokeMethod(app, "quit", _Qt.QueuedConnection)
            time.sleep(1.0)
      except Exception:
         pass
      # 2) Garantía: os._exit no espera a ningún hilo ni a ningún bucle de eventos.
      try:
         sys.stdout.flush()
      except Exception:
         pass
      os._exit(0)

   threading.Thread(target=_apagar, daemon=True).start()
   return "Hasta luego, señor. Apagando."

def Programacion_de_Tareas(texto):
   texto = texto.strip()
   partes = texto.split("|")

   if len(partes)==4:

      accion = partes[0].strip()
      target = partes[1].strip()
      info = partes[2].strip()
      hora = partes[3].strip()
      guardar_en_json(accion,target,info,hora)

def limpiar_historial():
   from Funciones_Slide.Productividad.Gestion_datos import RUTA_TAREAS, leer_tareas, escribir_tareas

   if not os.path.exists(RUTA_TAREAS):
      return "No hay historial de tareas que limpiar, señor."

   tareas = leer_tareas()
   # Se conservan solo las pendientes: lo que ya se hizo se va.
   tarea_limpia = [t for t in tareas if t.get("estado") == "pendiente"]
   escribir_tareas(tarea_limpia)

   borradas = len(tareas) - len(tarea_limpia)
   if not borradas:
      return "No había nada completado que limpiar, señor."
   return f"Historial limpiado, señor: quité {borradas} tarea(s) ya completadas."



   

      







   