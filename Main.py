# ── INSTANCIA ÚNICA ───────────────────────────────────────────────────────────
# Si AIDEN ya está corriendo (este Main.py o Main_AlwaysOn.py), esta copia se cierra
# de inmediato para no duplicar el asistente ni gastar el doble de memoria.
import sys as _sys
import socket as _socket
_instancia_lock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
try:
    _instancia_lock.bind(("127.0.0.1", 50607))
except OSError:
    print("AIDEN ya está corriendo; cierro esta instancia para no duplicar.")
    _sys.exit(0)

from Voz_Slide.Transcriptor import escuchador_de_usuario
from Nucleo_Slide.Cerebro import proceso_de_ia, iniciar_centinela, estado_aiden
import Nucleo_Slide.Cerebro as cerebro   # para leer cerebro.ultima_interrumpida
from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
from Funciones_Slide.Productividad.Tareas_Hilos_Comandos import iniciar_hilos
from Funciones_Slide.Sistema.Comandos_Asistente import Reconocimiento_Facial, Abrir_Apps
from Voz_Slide.VAD import Reconocimiento_de_habla
from Interfaz.Interfaz_En_Python import ejecutar_slide
from Funciones_Slide.Comunicacion.Funciones_Variadas import Enviar_mensaje_Whatsapp
from Funciones_Slide.Sistema.Funciones_Sistema import control_musica
from Funciones_Slide.Productividad.Rutina import briefing
from Funciones_Slide.Productividad.Alertas_Mercado import iniciar_alertas
from Funciones_Slide.Productividad.Descanso import iniciar_guardian_descanso
from Funciones_Slide.Info.Bitacora import contar_actividad
from Funciones_Slide.Comunicacion.Telegram_Control import iniciar_telegram
from Funciones_Slide.Productividad.Anticipacion import iniciar_anticipacion
from Funciones_Slide.Sistema.Presencia import iniciar_presencia
from Funciones_Slide.Comunicacion.Vigilante_Llamadas import iniciar_vigilante_llamadas, hay_llamada_activa, mensaje_de_orden
from Funciones_Slide.Comunicacion.Llamadas import contestar_llamada
from Funciones_Slide.Sistema.Vigilante_Pantalla import iniciar_vigilante_pantalla
from Funciones_Slide.Sistema.Vigilante_Portapapeles import iniciar_vigilante_portapapeles
from Funciones_Slide.Sistema.Vigilante_Reunion import iniciar_vigilante_reunion
from Nucleo_Slide.Conciencia_Ambiental import iniciar_conciencia_ambiental
from Nucleo_Slide.Perfil_Marco import iniciar_perfil
from Funciones_Slide.Productividad.Seguimiento_Metas import iniciar_seguimiento_metas
from Nucleo_Slide.Compania import apertura_rica, despedida_del_dia
from Nucleo_Slide.Reflexion import iniciar_reflexion
from Nucleo_Slide.Memoria_RAG import iniciar_rag
from Funciones_Slide.Sistema.Co_Ingeniero import iniciar_co_ingeniero
from Funciones_Slide.Sistema.Preparacion import iniciar_preparacion
iniciar_hilos()



# --- Modo manos libres (sesión) ---------------------------------------------
# Mic abierto: hablas sin clic ni palabra clave y AIDEN responde, hasta que digas
# "descansa"/"modo normal" o pase un buen rato en silencio (sale solo).
_manos_libres = False
_silencios_manos_libres = 0
ESPERA_MANOS_LIBRES = 20          # segundos que escucha en cada turno dentro del modo
MAX_SILENCIOS_MANOS_LIBRES = 15   # 15 turnos x 20s = ~5 min de silencio -> sale solo (anti mic eterno)


def Procesar_Peticion(texto, ventana):
    # El while permite el "barge-in": si AIDEN es interrumpido, volvemos a
    # escuchar al usuario de inmediato (sin repetir la palabra clave).
    global _manos_libres, _silencios_manos_libres
    while texto and texto.strip():
        texto = texto.strip().lower()
        ya_hablado = False

        if "abre " in texto:
            abrir_a_app = texto.split("abre ")[1].strip()
            Abrir_Apps(abrir_a_app)
            respuesta_slide = f"Hecho señor, aplicación {abrir_a_app} abierta."

        elif texto.startswith("escribele a "):
            partes = texto.replace("escribele a ", "").split(" diciendo ")
            if len(partes) == 2:
                contacto = partes[0].strip()
                mensaje = partes[1].strip()
                Enviar_mensaje_Whatsapp(contacto, mensaje)
                respuesta_slide = f"Mensaje enviado a {contacto}, señor."
            else:
                respuesta_slide = "El mensaje no se pudo enviar"

        elif texto in ("pausa", "pausar", "reanuda", "play", "siguiente", "siguiente cancion",
                       "anterior", "cancion anterior", "detener", "parar", "para la musica"):
            # Atajo SIN LLM (cuesta $0): comandos de musica directos.
            _mapa = {"pausa": "pausa", "pausar": "pausa", "reanuda": "play", "play": "play",
                     "siguiente": "siguiente", "siguiente cancion": "siguiente",
                     "anterior": "anterior", "cancion anterior": "anterior",
                     "detener": "parar", "parar": "parar", "para la musica": "parar"}
            respuesta_slide = control_musica(_mapa[texto])
        elif any(p in texto for p in ("contesta", "responde", "atiende", "contestar")) and hay_llamada_activa():
            # Hay una llamada SONANDO y Marco pide contestar: acepta + dice el mensaje (SIN LLM).
            respuesta_slide = contestar_llamada(mensaje_de_orden(texto))
        elif any(p in texto for p in ("quédate", "quedate", "mantente", "no te ocultes", "no te vayas", "no te escondas")):
            ventana.pedir_fijar.emit(True)
            respuesta_slide = "Aquí me quedo, señor."
        elif any(p in texto for p in ("manos libres", "modo conversacion", "modo conversación",
                                      "escucha continua", "escúchame", "escuchame")):
            _manos_libres = True
            _silencios_manos_libres = 0
            respuesta_slide = ("Modo manos libres activado, señor. Le escucho sin que tenga que "
                               "despertarme; dígame 'modo normal' o 'descansa' para parar.")
        elif any(p in texto for p in ("modo normal", "desactiva manos libres",
                                      "sal del modo manos libres", "deja de escuchar")):
            _manos_libres = False
            _silencios_manos_libres = 0
            respuesta_slide = "Modo manos libres desactivado, señor. Volveré a esperar la palabra clave."
        elif any(p in texto for p in ("buenas noches", "buenas noche", "me voy a dormir",
                                      "hasta mañana", "hasta manana", "ya me acuesto", "me voy a la cama")):
            # Fin del DÍA (no solo ocultar): despedida cálida que reconoce tu día + se oculta.
            _manos_libres = False
            respuesta_slide = despedida_del_dia()
            ventana.pedir_fijar.emit(False)
            ventana.pedir_ocultar.emit()
        elif any(p in texto for p in ("descansa", "descansar", "ocúltate", "ocultate", "ocultar",
                                      "escóndete", "escondete", "esconder", "duerme", "duérmete",
                                      "duermete", "a dormir", "ve a dormir", "puedes irte", "retírate", "retirate")):
            _manos_libres = False
            ventana.pedir_fijar.emit(False)
            ventana.pedir_ocultar.emit()
            respuesta_slide = "Como guste, señor."

        elif "cambié de opinión" in texto or "ayúdame con el código" in texto or "ayudame" in texto:
            if estado_aiden["hay_error"]:
                ventana.enviar_texto_a_html("AIDEN >> Revisando la memoria de errores...", "#d500f9")
                prompt = f"Hay un SyntaxError: '{estado_aiden['detalle_error']}' en la línea {estado_aiden['linea']}. Código: \n{estado_aiden['codigo']}\nDame una solución corta."
                respuesta_slide = proceso_de_ia(prompt)
                ya_hablado = True
            else:
                respuesta_slide = "No tengo registros de errores de sintaxis en su código actualmente, señor."

        else:
            respuesta_slide = proceso_de_ia(texto)
            ya_hablado = True

        ventana.enviar_texto_a_html(f"AIDEN >> {respuesta_slide}", "#d500f9")
        print(f"AIDEN: {respuesta_slide}")

        # ¿AIDEN fue interrumpido al hablar?
        if ya_hablado:
            interrumpido = cerebro.ultima_interrumpida          # vino de proceso_de_ia
        else:
            interrumpido = hablado_del_asistente(respuesta_slide)  # frases fijas

        if interrumpido:
            ventana.enviar_texto_a_html("AIDEN >> (te escucho...)", "#00ffcc")
            print("[BARGE-IN] escuchando al usuario sin palabra clave...")
            texto = escuchador_de_usuario()   # captura el nuevo comando
            ventana.enviar_texto_a_html(f"USER (Voz) >> {texto}", "#ffffff")
            print(f"USER (Voz): {texto}")
            continue                          # y lo procesa en la siguiente vuelta

        # Conversación continua / manos libres: escucha el siguiente turno sin palabra clave.
        siguiente = None
        while True:
            if _manos_libres:
                ventana.enviar_texto_a_html("AIDEN >> (manos libres: le escucho, señor...)", "#00ffcc")
                cap = escuchador_de_usuario(timeout=ESPERA_MANOS_LIBRES)
            else:
                ventana.enviar_texto_a_html("AIDEN >> (sigo aquí, señor...)", "#00ffcc")
                cap = escuchador_de_usuario(timeout=5)   # 5s para que sigas hablando

            if cap and cap.strip():
                _silencios_manos_libres = 0
                siguiente = cap
                break

            # No se captó nada en la ventana de escucha.
            if _manos_libres:
                _silencios_manos_libres += 1
                if _silencios_manos_libres < MAX_SILENCIOS_MANOS_LIBRES:
                    continue   # mic sigue abierto, no exige palabra clave
                _manos_libres = False
                _silencios_manos_libres = 0
                hablado_del_asistente("Llevamos un rato en silencio, señor; salgo del modo manos libres.")
            break

        if siguiente:
            texto = siguiente
            ventana.enviar_texto_a_html(f"USER (Voz) >> {texto}", "#ffffff")
            print(f"USER (Voz): {texto}")
            continue
        break

def Voz(ventana_slide):
    ventana_slide.enviar_texto_a_html("AIDEN >> Escuchando...", "#00ffcc")
    texto_escuchado = escuchador_de_usuario()
    ventana_slide.enviar_texto_a_html(f"USER (Voz) >> {texto_escuchado}", "#ffffff")
    Procesar_Peticion(texto_escuchado, ventana_slide)


# El control remoto por Telegram arranca ANTES del login facial y la palabra clave,
# para poder controlar el PC desde el celular AUNQUE Marco no esté presente.
# Su seguridad es independiente: queda bloqueado a tu chat_id (no necesita la cámara).
iniciar_telegram()

hablado_del_asistente("Iniciando sistema de seguridad...")
print("Iniciando sistema de seguridad...")

verificacion = Reconocimiento_Facial()

if verificacion == "Bienvenido Marco":
    # Solo esperamos la palabra clave si el login facial fue exitoso.
    # (Antes esto corria SIEMPRE: si entraba un extrano, AIDEN se quedaba
    #  escuchando para siempre sin negar el acceso hasta que alguien hablara.)
    Activado, Texto = Reconocimiento_de_habla()
    hablado_del_asistente(apertura_rica())   # apertura que canaliza TODO el núcleo (memoria+pendiente+meta+momento)
    hablado_del_asistente(briefing())
    _n_notis = contar_actividad()
    if _n_notis > 0:
        hablado_del_asistente(
            f"Por cierto señor, mientras no estaba llegaron {_n_notis} notificaciones. "
            "Si quiere saber qué pasó, pídame el resumen."
        )
    iniciar_alertas(hablado_del_asistente)
    iniciar_guardian_descanso(hablado_del_asistente)
    iniciar_anticipacion(hablado_del_asistente)   # anticipación proactiva (clima, trasnochadas)
    iniciar_presencia(hablado_del_asistente)      # te saluda al llegar al PC (ve tu cara)
    iniciar_vigilante_llamadas(hablado_del_asistente)  # te avisa de llamadas entrantes al PC
    iniciar_vigilante_pantalla(hablado_del_asistente)  # te avisa si una app se congela / hay un error
    iniciar_vigilante_portapapeles(hablado_del_asistente)  # reacciona a lo que copias (error/YouTube)
    iniciar_vigilante_reunion(hablado_del_asistente)   # modo reunión: silencia distracciones en llamadas
    iniciar_conciencia_ambiental()                     # mira el estado del PC y decide solo qué hacer
    iniciar_perfil()                                   # aprende quién es Marco con el tiempo
    iniciar_seguimiento_metas(hablado_del_asistente)   # PERSIGUE tus metas (te acompaña 1 vez/día)
    iniciar_reflexion()                                # contempla y entiende el momento de Marco
    iniciar_rag()                                      # memoria semántica (búsqueda por significado)
    iniciar_co_ingeniero(hablado_del_asistente)        # te ofrece ayuda al verte atascado (taller)
    iniciar_preparacion(hablado_del_asistente)         # "me tomé la libertad de..." prepara tu contexto
    ejecutar_slide(funcion_texto=Procesar_Peticion, funcion_voz=Voz)
    
    while Activado: 
        hablado_del_asistente("Iniciando sistemas...")
        
        
        ejecutar_slide(funcion_texto=Procesar_Peticion, funcion_voz=Voz) 
        
        Activado, Texto = Reconocimiento_de_habla()

else:
    hablado_del_asistente("Acceso denegado")
    print("Acceso denegado")






    