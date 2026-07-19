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

from Nucleo_Slide.Cerebro import iniciar_centinela
from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
from Funciones_Slide.Productividad.Tareas_Hilos_Comandos import iniciar_hilos
from Funciones_Slide.Sistema.Comandos_Asistente import Reconocimiento_Facial
from Voz_Slide.VAD import Reconocimiento_de_habla
from Interfaz.Interfaz_En_Python import ejecutar_slide
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
# con Main_AlwaysOn.py: cada arreglo aplica a los dos a la vez (antes estaba duplicado y divergía).
from Nucleo_Slide.Peticiones import Procesar_Peticion, Voz
iniciar_hilos()


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
    _dia = resumen_dia()                      # tu día real: agenda + correos sin leer (si está configurado)
    if _dia:
        hablado_del_asistente(_dia)
    _prior = resumen_priorizado()             # notificaciones priorizadas (solo lo que importa)
    if _prior:
        hablado_del_asistente(_prior)
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
    iniciar_vigilante_gastos()                         # captura tus gastos de las notis de Nequi/Nu (auto)
    iniciar_centinela()                                # detecta SyntaxError al guardar tu código (estaba muerto)
    iniciar_ordenes(hablado_del_asistente)             # recados condicionales ("en 20 min...", "cuando abra X...")
    iniciar_monologo()                                 # mini consciencia: pensamiento interno vivo (se ve en el overlay)
    iniciar_sesion_autoguardado()                      # recuerda tu espacio de trabajo (para "retomemos")
    iniciar_mayordomo_archivos(hablado_del_asistente)  # ordena capturas/instaladores 1 vez al día (habito suyo)
    ejecutar_slide(funcion_texto=Procesar_Peticion, funcion_voz=Voz)
    
    while Activado: 
        hablado_del_asistente("Iniciando sistemas...")
        
        
        ejecutar_slide(funcion_texto=Procesar_Peticion, funcion_voz=Voz) 
        
        Activado, Texto = Reconocimiento_de_habla()

else:
    hablado_del_asistente("Acceso denegado")
    print("Acceso denegado")






    