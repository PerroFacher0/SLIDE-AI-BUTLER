# PETICIONES: el enrutador de voz/texto de AIDEN, COMPARTIDO por Main.py y Main_AlwaysOn.py.
#
# Antes este código vivía DUPLICADO en los dos Main (~125 líneas cada uno): cada arreglo había que
# hacerlo dos veces y era fácil olvidar uno (pasó con "descansa"). Ahora hay UNA sola fuente de verdad.
#
# Arreglos que trae respecto a la versión duplicada:
#   - Los atajos comparan SIN tildes ("escríbele", "para la música", "ocúltate" ya disparan; Whisper
#     transcribe con tildes y antes nunca coincidían).
#   - "abre X" solo dispara si la frase EMPIEZA así y es corta; "cuándo abre el mercado" o
#     "abre chrome y busca gatos" van al cerebro (que sí sabe encadenar).
#   - "ayúdame..." ya no responde "no tengo registros de errores": si el centinela vio un SyntaxError
#     lo usa, y si no, la petición va al cerebro (que ayuda de verdad).
#   - Respuestas enlatadas VARIADAS (no el mismo "Aquí me quedo, señor." robótico siempre).
#
# El enrutado puro está en decidir_atajo() (sin efectos, testeable). Los imports pesados (Whisper,
# cerebro, funciones) van PEREZOSOS dentro de Procesar_Peticion para poder importar este módulo
# (y probarlo) sin levantar CUDA ni el micrófono.

import random

_TILDES = str.maketrans("áéíóúüÁÉÍÓÚÜñ", "aeiouuAEIOUUn")


def _plano(texto):
    # minúsculas y sin tildes (mismo largo por posición: sirve para recortar el original).
    return str(texto or "").strip().lower().translate(_TILDES)


# --- Modo manos libres (estado de sesión, compartido por los dos Main) -------
_manos_libres = False
_silencios_manos_libres = 0
ESPERA_MANOS_LIBRES = 20          # segundos que escucha en cada turno dentro del modo
MAX_SILENCIOS_MANOS_LIBRES = 15   # 15 turnos x 20s = ~5 min de silencio -> sale solo (anti mic eterno)

_MAPA_MUSICA = {
    "pausa": "pausa", "pausar": "pausa", "reanuda": "play", "play": "play",
    "siguiente": "siguiente", "siguiente cancion": "siguiente",
    "anterior": "anterior", "cancion anterior": "anterior",
    "detener": "parar", "parar": "parar", "para la musica": "parar",
}

# VARIEDAD VIVA: respuestas enlatadas con repertorio (que no suene a bot de frase única).
_R_QUEDATE = ("Aquí me quedo, señor.", "No me muevo de aquí.", "A su lado, señor.",
              "Me quedo, por supuesto.")
_R_DESCANSA = ("Como guste, señor.", "Me retiro; aquí estaré si me necesita.",
               "Descanso, señor. Ya sabe cómo llamarme.", "Entendido, me aparto.")
_R_MANOS_ON = ("Modo manos libres activado, señor. Le escucho sin que tenga que despertarme; "
               "dígame 'modo normal' o 'descansa' para parar.",
               "Manos libres, señor: hable cuando quiera, le sigo. 'Modo normal' para volver.")
_R_MANOS_OFF = ("Modo manos libres desactivado, señor. Volveré a esperar la palabra clave.",
                "Entendido, vuelvo a lo discreto: me llama con la palabra clave.")


# "¿Estado?" estilo Iron Man: reporte instantáneo SIN LLM. Solo frases exactas (no
# secuestrar "estado de mi cuenta...", que va al cerebro).
_PEDIR_ESTADO = {"estado", "status", "reporte", "informe", "como vamos", "como estamos",
                 "reporte de estado", "estado del sistema", "dame el estado", "dame un reporte",
                 "como estas", "como te sientes", "todo bien"}
_T0 = __import__("time").time()   # arranque (para el uptime del informe)


def _informe_estado():
    # Reporte crisp: salud propia + sistemas + dónde está Marco + metas. Todo local, cero LLM.
    import threading
    import time
    up = int((time.time() - _T0) / 60)
    uptime = f"{up // 60}h {up % 60}m" if up >= 60 else f"{up} minutos"
    partes = [f"Todos mis sistemas operativos, señor: llevo {uptime} en pie y "
              f"{threading.active_count()} hilos trabajando para usted."]
    try:
        from Funciones_Slide.Sistema.Funciones_Sistema import estado_sistema
        partes.append(str(estado_sistema()))
    except Exception:
        pass
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        est = obtener()
        if est.get("foco_actual"):
            partes.append(f"Su foco: {est['foco_actual']}.")
        metas = [m for m in est.get("metas", []) if m.get("estado") != "hecha"]
        if metas:
            partes.append(f"Sigo {len(metas)} meta{'s' if len(metas) > 1 else ''} suya{'s' if len(metas) > 1 else ''}.")
    except Exception:
        pass
    return " ".join(p for p in partes if p)


def decidir_atajo(texto, llamada_activa=False, hay_error_codigo=False):
    """Enrutado PURO de los atajos sin LLM. Devuelve (tipo, dato) donde tipo es uno de:
    'abrir', 'whatsapp', 'musica', 'contestar', 'estado', 'quedate', 'manos_on', 'manos_off',
    'buenas_noches', 'descansa', 'codigo', 'llm'. Sin efectos secundarios (testeable)."""
    original = str(texto or "").strip().lower()
    p = _plano(original)
    # Tolera el nombre por delante ("aiden, abre spotify").
    for pref in ("aiden, ", "aiden "):
        if p.startswith(pref):
            original = original[len(pref):]
            p = p[len(pref):]
            break

    if p.startswith("abre "):
        app = original[5:].strip(" .")
        # Solo apps de nombre corto; "abre chrome y busca gatos" es una orden compuesta -> cerebro.
        if app and len(app.split()) <= 3 and " y " not in f" {p[5:]} ":
            return ("abrir", app)
        return ("llm", original)

    if p.startswith("escribele a ") and " diciendo " in p:
        cuerpo = original[len("escribele a "):]
        contacto, _, mensaje = cuerpo.partition(" diciendo ")
        if contacto.strip() and mensaje.strip():
            return ("whatsapp", (contacto.strip(), mensaje.strip()))
        return ("llm", original)

    if p in _MAPA_MUSICA:
        return ("musica", _MAPA_MUSICA[p])

    if p.strip(" ?¿") in _PEDIR_ESTADO:
        return ("estado", None)

    # MODO TALLER (copiloto de pantalla): entrar/salir sin gastar LLM.
    if any(k in p for k in ("acompaname", "modo taller", "trabajemos juntos", "trabaja conmigo")):
        return ("taller_on", None)
    if any(k in p for k in ("ya terminamos", "cierra el taller", "sal del taller",
                            "deja de acompanarme", "trabajo solo")):
        return ("taller_off", None)

    if llamada_activa and any(k in p for k in ("contesta", "responde", "atiende", "contestar")):
        return ("contestar", original)

    if any(k in p for k in ("quedate", "mantente", "no te ocultes", "no te vayas", "no te escondas")):
        return ("quedate", None)

    if any(k in p for k in ("manos libres", "modo conversacion", "escucha continua", "escuchame")):
        return ("manos_on", None)

    if any(k in p for k in ("modo normal", "desactiva manos libres",
                            "sal del modo manos libres", "deja de escuchar")):
        return ("manos_off", None)

    if any(k in p for k in ("buenas noches", "buenas noche", "me voy a dormir", "hasta manana",
                            "ya me acuesto", "me voy a la cama")):
        return ("buenas_noches", None)

    if any(k in p for k in ("descansa", "descansar", "ocultate", "ocultar", "escondete", "esconder",
                            "duerme", "duermete", "a dormir", "ve a dormir", "puedes irte", "retirate")):
        return ("descansa", None)

    # Ayuda con el CÓDIGO: solo si el centinela tiene un error registrado; si no, que el
    # cerebro ayude de verdad (antes cualquier "ayudame..." moría en una frase enlatada).
    if hay_error_codigo and any(k in p for k in ("ayudame", "ayuda con el codigo",
                                                 "cambie de opinion", "revisa el error")):
        return ("codigo", None)

    return ("llm", original)


# Palabras que despiertan a AIDEN (espejo de VAD.palabras, en plano). Para extraer el comando
# que Marco dice EN EL MISMO ALIENTO: "aiden, abre spotify" -> "abre spotify".
_WAKE_WORDS = ("papa esta en casa", "papa esta en caza", "te necesito", "despierta", "activate",
               "hey den", "slight", "slide", "aiden", "eiden", "ayden", "oye")


def extraer_comando_tras_wake(texto):
    """Si el texto trae un COMANDO además de la palabra clave, lo devuelve limpio; si era solo
    la palabra clave (o casi), devuelve "". Puro y testeable."""
    p = _plano(texto)
    for w in _WAKE_WORDS:   # ya ordenadas de más larga a más corta (no dejar residuos)
        p = p.replace(w, " ")
    p = " ".join(p.split()).strip(" ,.¿?¡!")
    return p if len(p) >= 3 else ""


def _cerrar_taller_silencioso():
    # Al descansar o despedir el día, la sesión de taller (si la hay) se cierra sola.
    try:
        from Funciones_Slide.Sistema.Taller import detener_taller
        detener_taller(silencioso=True)
    except Exception:
        pass


def Procesar_Peticion(texto, ventana):
    # El while permite el "barge-in": si AIDEN es interrumpido, volvemos a
    # escuchar al usuario de inmediato (sin repetir la palabra clave).
    global _manos_libres, _silencios_manos_libres

    # Imports perezosos: el módulo se puede importar/testear sin levantar CUDA ni micrófono.
    from Voz_Slide.Transcriptor import escuchador_de_usuario
    from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
    import Nucleo_Slide.Cerebro as cerebro
    from Nucleo_Slide.Cerebro import proceso_de_ia, estado_aiden
    from Funciones_Slide.Sistema.Comandos_Asistente import Abrir_Apps
    from Funciones_Slide.Comunicacion.Funciones_Variadas import Enviar_mensaje_Whatsapp
    from Funciones_Slide.Sistema.Funciones_Sistema import control_musica
    from Funciones_Slide.Comunicacion.Vigilante_Llamadas import hay_llamada_activa, mensaje_de_orden
    from Funciones_Slide.Comunicacion.Llamadas import contestar_llamada
    from Nucleo_Slide.Compania import despedida_del_dia

    while texto and texto.strip():
        texto = texto.strip().lower()
        ya_hablado = False

        tipo, dato = decidir_atajo(texto, llamada_activa=hay_llamada_activa(),
                                   hay_error_codigo=estado_aiden["hay_error"])

        if tipo == "abrir":
            # "Abriendo X, señor." — honesto: la función no puede verificar que abrió bien.
            respuesta_slide = Abrir_Apps(dato)
        elif tipo == "whatsapp":
            contacto, mensaje = dato
            Enviar_mensaje_Whatsapp(contacto, mensaje)
            respuesta_slide = f"Mensaje enviado a {contacto}, señor."
        elif tipo == "musica":
            respuesta_slide = control_musica(dato)
        elif tipo == "contestar":
            respuesta_slide = contestar_llamada(mensaje_de_orden(dato))
        elif tipo == "estado":
            respuesta_slide = _informe_estado()
        elif tipo == "taller_on":
            from Funciones_Slide.Sistema.Taller import modo_taller
            respuesta_slide = modo_taller("iniciar")
        elif tipo == "taller_off":
            from Funciones_Slide.Sistema.Taller import detener_taller
            respuesta_slide = detener_taller()
        elif tipo == "quedate":
            ventana.pedir_fijar.emit(True)
            respuesta_slide = random.choice(_R_QUEDATE)
        elif tipo == "manos_on":
            _manos_libres = True
            _silencios_manos_libres = 0
            respuesta_slide = random.choice(_R_MANOS_ON)
        elif tipo == "manos_off":
            _manos_libres = False
            _silencios_manos_libres = 0
            respuesta_slide = random.choice(_R_MANOS_OFF)
        elif tipo == "buenas_noches":
            # Fin del DÍA (no solo ocultar): despedida cálida que reconoce tu día + se oculta.
            _manos_libres = False
            _cerrar_taller_silencioso()
            respuesta_slide = despedida_del_dia()
            ventana.pedir_fijar.emit(False)
            ventana.pedir_ocultar.emit()
        elif tipo == "descansa":
            _manos_libres = False
            _cerrar_taller_silencioso()
            ventana.pedir_fijar.emit(False)
            ventana.pedir_ocultar.emit()
            respuesta_slide = random.choice(_R_DESCANSA)
        elif tipo == "codigo":
            ventana.enviar_texto_a_html("AIDEN >> Revisando la memoria de errores...", "#d500f9")
            prompt = (f"Hay un SyntaxError: '{estado_aiden['detalle_error']}' en la línea "
                      f"{estado_aiden['linea']}. Código: \n{estado_aiden['codigo']}\nDame una solución corta.")
            try:
                respuesta_slide = proceso_de_ia(prompt)
            except Exception:
                respuesta_slide = "No pude analizar el error ahora, señor; intentémoslo de nuevo."
            ya_hablado = True
        else:
            # RED DE SEGURIDAD: pase lo que pase dentro del cerebro, el loop de conversación
            # NUNCA muere en silencio (regla "siempre arriba").
            try:
                respuesta_slide = proceso_de_ia(texto)
            except Exception as e:
                print(f"[peticiones] excepción no prevista del cerebro: {e}")
                respuesta_slide = ("Tuve un tropiezo interno, señor, pero sigo en pie. "
                                   "Intentémoslo de nuevo.")
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
    from Voz_Slide.Transcriptor import escuchador_de_usuario
    ventana_slide.enviar_texto_a_html("AIDEN >> Escuchando...", "#00ffcc")
    texto_escuchado = escuchador_de_usuario()
    ventana_slide.enviar_texto_a_html(f"USER (Voz) >> {texto_escuchado}", "#ffffff")
    Procesar_Peticion(texto_escuchado, ventana_slide)
