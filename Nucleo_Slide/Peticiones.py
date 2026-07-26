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
import re

_TILDES = str.maketrans("áéíóúüÁÉÍÓÚÜñ", "aeiouuAEIOUUn")


def _plano(texto):
    # minúsculas y sin tildes (mismo largo por posición: sirve para recortar el original).
    return str(texto or "").strip().lower().translate(_TILDES)


# Tipos de atajo que se pueden ENCADENAR (son "hacer algo y devolver texto", sin tocar la ventana).
_ENCADENABLES = {"instant", "abrir", "musica", "musica_contextual", "control_directo", "estado",
                 "web", "web_youtube", "admin", "clic_pantalla", "arrastrar_pantalla",
                 "cerrar_pestana", "seleccionar_todo", "scroll_pantalla", "ordenar_ventanas",
                 "enfocar_app", "ventana_ctrl", "atajo_teclado", "escribir_texto"}
# Conectores que separan varias órdenes en una misma frase.
_SEP_ORDENES = re.compile(r"\s*(?:,|;|\s+y luego\s+|\s+luego\s+|\s+despues\s+|\s+y despues\s+|"
                          r"\s+tambien\s+|\s+y tambien\s+|\s+y\s+)\s*", re.IGNORECASE)


def _dividir_ordenes(texto):
    # Parte "abre spotify y sube el volumen" -> ["abre spotify", "sube el volumen"]. Sobre el texto
    # SIN tildes para que el conector pegue ("después"/"tambien" con o sin tilde).
    plano = _plano(texto)
    if not any(s in plano for s in (",", ";", " y ", " luego ", " despues ", " tambien ")):
        return [texto]
    fragmentos = [f.strip(" ,.;") for f in _SEP_ORDENES.split(plano) if f and f.strip(" ,.;")]
    return fragmentos if len(fragmentos) > 1 else [texto]


# --- Modo manos libres (estado de sesión, compartido por los dos Main) -------
_manos_libres = False
_silencios_manos_libres = 0
# MODO CONTROL: cuando está activo, CADA orden va al carril rápido (voz -> acción, cerebro mínimo)
# en vez del cerebro completo -> control de toda la PC casi instantáneo.
_modo_control = False
ESPERA_MANOS_LIBRES = 20          # segundos que escucha en cada turno dentro del modo
MAX_SILENCIOS_MANOS_LIBRES = 15   # 15 turnos x 20s = ~5 min de silencio -> sale solo (anti mic eterno)

_MAPA_MUSICA = {
    "pausa": "pausa", "pausar": "pausa", "reanuda": "play", "play": "play",
    "siguiente": "siguiente", "siguiente cancion": "siguiente",
    "anterior": "anterior", "cancion anterior": "anterior",
    "detener": "parar", "parar": "parar", "para la musica": "parar",
}

# Atajos de teclado comunes dichos en natural -> combo (lo que Marco hace a diario con Ctrl+letra).
# Se ejecutan al instante (sin LLM) sobre la ventana que tenga el foco.
_ATAJOS_COMUNES = {
    "copia": "ctrl c", "copiar": "ctrl c", "copia esto": "ctrl c",
    "pega": "ctrl v", "pegar": "ctrl v", "pega esto": "ctrl v", "pega aqui": "ctrl v",
    "corta": "ctrl x", "cortar": "ctrl x", "corta esto": "ctrl x",
    "deshaz": "ctrl z", "deshacer": "ctrl z", "deshaz eso": "ctrl z",
    "rehaz": "ctrl y", "rehacer": "ctrl y",
    "guarda": "ctrl s", "guardar": "ctrl s", "guarda el archivo": "ctrl s", "guarda esto": "ctrl s",
    "busca en la pagina": "ctrl f", "buscar en la pagina": "ctrl f", "buscar en esta pagina": "ctrl f",
    "recarga": "f5", "refresca": "f5", "actualiza la pagina": "f5", "recarga la pagina": "f5",
    "nueva pestana": "ctrl t", "abre una pestana": "ctrl t",
    "reabre la pestana": "ctrl shift t", "recupera la pestana": "ctrl shift t",
    "imprime": "ctrl p", "imprimir": "ctrl p",
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


def decidir_atajo(texto, llamada_activa=False, hay_error_codigo=False, modo_control=False):
    """Enrutado PURO de los atajos sin LLM. Devuelve (tipo, dato). Sin efectos secundarios (testeable)."""
    original = str(texto or "").strip().lower()
    p = _plano(original)
    # Tolera el nombre por delante ("aiden, abre spotify").
    for pref in ("aiden, ", "aiden "):
        if p.startswith(pref):
            original = original[len(pref):]
            p = p[len(pref):]
            break

    # WEBS Y YOUTUBE (antes de la división en cadena, para no partir "youtube y busca X").
    #   "abre youtube y busca X" / "busca en youtube X" / "pon X en youtube" -> resultados de YouTube.
    m = re.search(r"(?:abre |pon |busca en |reproduce en )?youtube (?:y busca |y pon |con |busca |)(.+)",
                  p)
    if m and m.group(1).strip() and any(k in p for k in ("busca", "pon", "reproduce", " con ")):
        return ("web_youtube", m.group(1).strip())
    m = re.search(r"busca en youtube (.+)", p)
    if m:
        return ("web_youtube", m.group(1).strip())
    #   "abre <sitio web conocido>" -> abre esa web (no una app).
    if p.startswith(("abre ", "abrir ", "ve a ", "entra a ", "entra en ")):
        objetivo = re.sub(r"^(abre |abrir |ve a |entra a |entra en )", "", p).strip(" .")
        from Funciones_Slide.Info.Web import WEB_DIRECTOS
        if objetivo in WEB_DIRECTOS or objetivo.replace("mi ", "") in WEB_DIRECTOS:
            return ("web", objetivo.replace("mi ", ""))
        if ("." in objetivo and " " not in objetivo):     # una URL dicha ("abre canvas.com")
            return ("web", objetivo)

    # ÓRDENES EN CADENA: varias en una frase ("abre spotify, sube el volumen y minimiza todo").
    # Solo si TODAS las partes son atajos encadenables (si alguna es charla/tarea, va entera al cerebro,
    # que ya sabe encadenar herramientas). Recursivo pero sin bucle (los fragmentos ya no traen conectores).
    fragmentos = _dividir_ordenes(original)
    if len(fragmentos) > 1:
        sub = [decidir_atajo(f, llamada_activa, hay_error_codigo, modo_control) for f in fragmentos[:6]]
        if all(t in _ENCADENABLES for t, _ in sub):
            return ("cadena", sub)

    # Encender/apagar el MODO CONTROL (control de toda la PC casi instantáneo).
    if any(k in p for k in ("modo control", "control por voz", "controla mi pc", "controla el pc",
                            "toma el control")):
        return ("control_on", None)
    if any(k in p for k in ("sal del control", "salir del control", "deja el control",
                            "termina el control", "modo normal")):
        return ("control_off", None)

    # ACCIONES INSTANTÁNEAS de sistema (cero LLM): valen SIEMPRE, con o sin modo control.
    from Nucleo_Slide.Control_Directo import clasificar_instantanea, clasificar_admin
    aid = clasificar_instantanea(p)
    if aid:
        return ("instant", aid)

    # FUNCIONES DE WINDOWS (red/rendimiento/mantenimiento/energía/info): frase exacta -> acción.
    aad = clasificar_admin(p)
    if aad:
        return ("admin", aad)

    # PARAMETRIZADAS (cero LLM): matar proceso por nombre, volumen/brillo exacto.
    mm = re.search(r"^(?:mata|matar|fuerza el cierre de) (?:el proceso |la app |el programa )?(.+)$", p)
    if not mm:
        mm = re.search(r"^cierra (?:el |la |)(.+?) a la fuerza$", p)
    if mm and mm.group(1).strip():
        return ("proc_kill", mm.group(1).strip())
    mv = re.search(r"(?:pon(?:me)? )?(?:el )?volumen (?:en|al|a) (?:el )?(\d{1,3})", p)
    if mv:
        return ("vol_set", mv.group(1))
    mb = re.search(r"(?:pon(?:me)? )?(?:el )?brillo (?:en|al|a) (?:el )?(\d{1,3})", p)
    if mb:
        return ("brillo_set", mb.group(1))

    # ── CONTROL DE PANTALLA por voz, CASI INSTANTÁNEO (cero LLM en el enrutado; la ejecución
    # busca el elemento por nombre primero —rápido— y solo si no lo encuentra recurre a visión).
    # ATAJO DE TECLADO: solo si de verdad trae un modificador o una tecla nombrada (si no, puede ser
    # "pulsa/presiona el botón X", que es un CLIC, no una combinación).
    matajo = re.search(r"^(?:presiona|pulsa|atajo|combinacion)\s+(.+)$", p)
    if matajo:
        combo_txt = matajo.group(1).strip()
        palabras_combo = combo_txt.replace("+", " ").split()
        _MOD_KEYS = ("ctrl", "control", "alt", "shift", "mayus", "win", "windows")
        _SINGLE_KEYS = ("tab", "escape", "esc", "enter", "intro", "supr", "delete", "espacio",
                        "backspace", "borrar")
        if any(k in palabras_combo for k in _MOD_KEYS) or (
                len(palabras_combo) == 1 and palabras_combo[0] in _SINGLE_KEYS):
            return ("atajo_teclado", combo_txt)
        # si no, sigue de largo: probablemente es "pulsa el botón X" (clic, más abajo)

    # ATAJOS COMUNES de teclado por nombre natural (lo que Marco hace con Ctrl+letra), cero LLM.
    if p in _ATAJOS_COMUNES:
        return ("atajo_teclado", _ATAJOS_COMUNES[p])

    mdc = re.search(r"^(?:haz |dame |dale )?doble clic (?:en |sobre |a )?(.+)$", p)
    if mdc and mdc.group(1).strip():
        return ("clic_pantalla", (mdc.group(1).strip(), "doble"))
    mdr = re.search(r"^(?:haz |dame |dale )?clic (?:derecho|secundario) (?:en |sobre |a )?(.+)$", p)
    if mdr and mdr.group(1).strip():
        return ("clic_pantalla", (mdr.group(1).strip(), "derecho"))
    mc = re.search(r"^(?:haz |dame |dale )?clic (?:en |sobre |a )?(.+)$", p)
    if mc and mc.group(1).strip():
        return ("clic_pantalla", (mc.group(1).strip(), "clic"))
    mpb = re.search(r"^(?:pulsa|presiona)\s+(?:el boton |el boton de |la opcion |la opcion de |)(.+)$", p)
    if mpb and mpb.group(1).strip():
        return ("clic_pantalla", (mpb.group(1).strip(), "clic"))

    mar = re.search(r"^arrastra\s+(.+?\s+(?:hasta|hacia|a)\s+.+)$", p)
    if mar:
        return ("arrastrar_pantalla", mar.group(1).strip())

    if p in ("cierra la pestana", "cierra esta pestana", "cierra la pestana actual"):
        return ("cerrar_pestana", None)
    if p in ("selecciona todo", "seleccionar todo", "selecciona esto"):
        return ("seleccionar_todo", None)
    if p in ("scroll arriba", "desplaza arriba", "sube la pagina", "sube la pantalla"):
        return ("scroll_pantalla", "arriba")
    if p in ("scroll abajo", "desplaza abajo", "baja la pagina", "baja la pantalla"):
        return ("scroll_pantalla", "abajo")
    if p in ("ordena las ventanas", "acomoda las ventanas", "pon las ventanas en mosaico",
             "organiza las ventanas", "mosaico de ventanas"):
        return ("ordenar_ventanas", None)

    menf = re.search(r"^(?:enfoca|trae|pon)\s+(?:la ventana de |a )?(.+?)\s+al frente$", p)
    if not menf:
        menf = re.search(r"^enfoca (?:la ventana de |)(.+)$", p)
    if menf and menf.group(1).strip():
        return ("enfocar_app", menf.group(1).strip())

    if p in ("minimiza esta ventana", "minimiza la ventana", "minimiza la ventana actual"):
        return ("ventana_ctrl", "minimizar")
    if p in ("maximiza esta ventana", "maximiza la ventana", "maximiza la ventana actual"):
        return ("ventana_ctrl", "maximizar")
    if p in ("cierra esta ventana", "cierra la ventana actual"):
        return ("ventana_ctrl", "cerrar")
    if p in ("cambia de ventana", "siguiente ventana", "cambia a la siguiente ventana"):
        return ("ventana_ctrl", "cambiar")

    # En MODO CONTROL, todo lo demás va al carril rápido (voz -> PowerShell, cerebro mínimo).
    if modo_control and len(p) >= 3:
        return ("control_directo", original)

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

    # REDACTOR: "escríbeme un ensayo sobre X" / "hazme un informe de Y" -> escribe el documento y lo guarda.
    mr = re.search(r"(?:escribe|escribeme|hazme|redacta|redactame|arma|armame|prepara|preparame)"
                   r"(?:me)?\s+(?:un |una |el |la )?"
                   r"(ensayo|informe|reporte|carta|correo|resumen|discurso|resena|articulo|"
                   r"texto|documento|monografia|redaccion)\b(.*)", p)
    if mr and mr.group(2).strip(" ,.:") and len(mr.group(2).strip(" ,.:sobredeparaacerc")) >= 3:
        tipo = mr.group(1)
        tema = re.sub(r"^\s*(sobre|de|acerca de|para|del|de la|que trate de)\s+", "",
                      mr.group(2).strip(" ,.:")).strip()
        if len(tema) >= 3:
            return ("redactar", (tipo, tema))

    # ESCRIBIR/DICTAR texto donde esté el cursor (cero LLM). Va DESPUÉS del redactor a propósito:
    # "escribe un ensayo sobre X" ya lo capturó el bloque de arriba; esto es solo texto suelto.
    mesc = re.search(r"^(?:escribe|dicta|teclea)(?:\s*:\s*|\s+)(.+)$", p)
    if mesc and mesc.group(1).strip():
        return ("escribir_texto", mesc.group(1).strip())

    # SOLUCIONADOR VISUAL: "resuelve esto" / "ayúdame con este problema" -> lo resuelve con el experto.
    if any(k in p for k in ("resuelve lo que ves", "resuelve lo que tengo en la camara",
                            "que ves en la camara")):
        return ("resolver", "camara")
    if any(k in p for k in ("resuelve esto", "resuelve el problema", "resuelve lo que hay en pantalla",
                            "resuelve el ejercicio", "ayudame con este problema", "ayudame con esto",
                            "como resuelvo esto", "resuelveme esto", "explicame esto que tengo",
                            "resuelve la pregunta")):
        return ("resolver", "pantalla")

    # VOZ -> CLAUDE CODE: "dile a claude que X" / "pídele a claude code que Y" -> AIDEN le dicta la
    # tarea de programación a Claude Code sobre su propio repo (en 2do plano, con latido de avance).
    for gatillo in ("dile a claude code que ", "pidele a claude code que ", "claude code ",
                    "dile a claude que ", "pidele a claude que ", "encargale a claude que ",
                    "dictale a claude que "):
        if p.startswith(gatillo):
            tarea = original[len(gatillo):].strip()
            if len(tarea) >= 4:
                return ("claude_code", tarea)

    # MODO AGENTE: "encárgate de X" -> AIDEN cumple la meta sola. Captura el objetivo (lo que sigue).
    for gatillo in ("encargate de ", "ocupate de ", "hazte cargo de ", "modo agente ",
                    "encargate ", "resuelveme "):
        if p.startswith(gatillo):
            objetivo = original[len(gatillo):].strip()
            if len(objetivo) >= 4:
                return ("agente", objetivo)

    # RETOMEMOS: reabrir el espacio de trabajo (sin LLM).
    if any(k in p for k in ("retomemos", "retomar sesion", "restaura mi sesion", "restaurar sesion",
                            "abre lo de antes", "donde lo deje")):
        return ("retomar", None)

    # MÚSICA CONTEXTUAL: "pon lo mío" -> según en qué esté Marco (sin LLM).
    if p in ("pon lo mio", "pon mi musica", "musica", "ponme musica", "pon musica"):
        return ("musica_contextual", None)

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


def _correr_uno(tipo, dato):
    # Ejecuta UN atajo encadenable y devuelve su confirmación (texto).
    try:
        if tipo == "instant":
            from Nucleo_Slide.Control_Directo import ejecutar_instantanea
            return ejecutar_instantanea(dato)
        if tipo == "abrir":
            from Funciones_Slide.Sistema.Comandos_Asistente import Abrir_Apps
            return Abrir_Apps(dato)
        if tipo == "musica":
            from Funciones_Slide.Sistema.Funciones_Sistema import control_musica
            return control_musica(dato)
        if tipo == "musica_contextual":
            return _musica_contextual()
        if tipo == "control_directo":
            from Nucleo_Slide.Control_Directo import control_directo
            return control_directo(dato)
        if tipo == "estado":
            return _informe_estado()
        if tipo == "admin":
            from Nucleo_Slide.Control_Directo import ejecutar_admin
            return ejecutar_admin(dato)
        if tipo == "web":
            from Funciones_Slide.Info.Web import abrir_web
            return abrir_web(dato)
        if tipo == "web_youtube":
            from Funciones_Slide.Info.Web import abrir_web
            return abrir_web("youtube", dato)
        if tipo == "clic_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            objetivo, tipo_clic = dato
            accion = {"doble": "doble_clic", "derecho": "clic_derecho"}.get(tipo_clic, "clic")
            return controlar_pantalla(accion, objetivo)
        if tipo == "arrastrar_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("arrastrar", dato)
        if tipo == "cerrar_pestana":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("cerrar_pestana")
        if tipo == "seleccionar_todo":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("seleccionar")
        if tipo == "scroll_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("scroll", dato)
        if tipo == "ordenar_ventanas":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("ordenar")
        if tipo == "enfocar_app":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("enfocar", dato)
        if tipo == "ventana_ctrl":
            from Funciones_Slide.Sistema.Control_PC import control_ventana
            return control_ventana(dato)
        if tipo == "atajo_teclado":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            return controlar_pantalla("atajo", dato)
        if tipo == "escribir_texto":
            from Funciones_Slide.Sistema.Control_PC import dictar
            return dictar(dato)
    except Exception:
        return ""
    return ""


def _correr_cadena(sub):
    # Ejecuta varias órdenes en orden y junta las confirmaciones en una frase fluida.
    partes = [_correr_uno(t, d) for t, d in sub]
    return " ".join(p for p in partes if p)


def _musica_contextual():
    # "Pon lo mío": elige música según en qué está Marco y qué hora es (cero LLM).
    import datetime as _dt
    foco = ""
    try:
        from Nucleo_Slide.Percepcion import ventana_activa
        foco = ventana_activa().lower()
    except Exception:
        pass
    juegos = ("steam", "league", "valorant", "game", "riot", "epic", "minecraft", "fortnite")
    trabajo = ("code", "visual studio", "word", "excel", "pdf", "notion", "docs", "overleaf")
    if any(j in foco for j in juegos):
        query, etiqueta = "epic gaming music mix", "algo con energía para el juego"
    elif any(t in foco for t in trabajo):
        query, etiqueta = "lofi hip hop radio beats to study", "lo-fi para concentrarse"
    elif _dt.datetime.now().hour >= 22 or _dt.datetime.now().hour < 6:
        query, etiqueta = "chill relaxing music night", "algo tranquilo para la hora"
    else:
        query, etiqueta = "musica variada mix", "una mezcla para el momento"
    try:
        from Funciones_Slide.Sistema.Comandos_Asistente import Abrir_Videos_Youtube
        Abrir_Videos_Youtube(query)
        return f"Marchando {etiqueta}, señor."
    except Exception:
        return "No pude poner la música, señor."


def _set_modo_rapido(activo):
    try:
        from Nucleo_Slide.Cerebro import set_modo_rapido
        set_modo_rapido(activo)
    except Exception:
        pass


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
    global _manos_libres, _silencios_manos_libres, _modo_control

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
                                   hay_error_codigo=estado_aiden["hay_error"],
                                   modo_control=_modo_control)

        if tipo == "cadena":
            # Varias órdenes en una frase, ejecutadas en orden (fluidez).
            respuesta_slide = _correr_cadena(dato)
        elif tipo == "instant":
            # Acción de sistema al INSTANTE (cero LLM): bloquear, volumen, escritorio, etc.
            from Nucleo_Slide.Control_Directo import ejecutar_instantanea
            respuesta_slide = ejecutar_instantanea(dato)
        elif tipo == "control_directo":
            # MODO CONTROL: voz -> acción con cerebro mínimo (rápido, propósito general).
            from Nucleo_Slide.Control_Directo import control_directo
            respuesta_slide = control_directo(dato)
        elif tipo == "control_on":
            _modo_control = True
            _manos_libres = True          # mic abierto: dispara órdenes seguidas sin despertarlo
            _silencios_manos_libres = 0
            respuesta_slide = ("Modo control activo, señor: manejo toda la PC al vuelo, dígame las "
                               "órdenes seguidas y las ejecuto. 'Modo normal' para salir.")
        elif tipo == "control_off":
            _modo_control = False
            _manos_libres = False
            respuesta_slide = "Salgo del modo control, señor. Vuelvo a ser todo oídos."
        elif tipo == "abrir":
            # "Abriendo X, señor." — honesto: la función no puede verificar que abrió bien.
            respuesta_slide = Abrir_Apps(dato)
        elif tipo == "whatsapp":
            contacto, mensaje = dato
            Enviar_mensaje_Whatsapp(contacto, mensaje)
            respuesta_slide = f"Mensaje enviado a {contacto}, señor."
        elif tipo == "musica":
            respuesta_slide = control_musica(dato)
        elif tipo == "web":
            from Funciones_Slide.Info.Web import abrir_web
            respuesta_slide = abrir_web(dato)
        elif tipo == "web_youtube":
            from Funciones_Slide.Info.Web import abrir_web
            respuesta_slide = abrir_web("youtube", dato)
        elif tipo == "admin":
            # Función de Windows (red/rendimiento/mantenimiento/info) al instante, cero LLM.
            from Nucleo_Slide.Control_Directo import ejecutar_admin
            respuesta_slide = ejecutar_admin(dato)
        elif tipo == "proc_kill":
            from Funciones_Slide.Sistema.Windows_Admin import matar_proceso
            respuesta_slide = matar_proceso(dato)
        elif tipo == "vol_set":
            from Funciones_Slide.Sistema.Windows_Admin import volumen_exacto
            respuesta_slide = volumen_exacto(dato)
        elif tipo == "brillo_set":
            from Funciones_Slide.Sistema.Windows_Admin import brillo_exacto
            respuesta_slide = brillo_exacto(dato)
        elif tipo == "clic_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            objetivo, tipo_clic = dato
            accion = {"doble": "doble_clic", "derecho": "clic_derecho"}.get(tipo_clic, "clic")
            respuesta_slide = controlar_pantalla(accion, objetivo)
        elif tipo == "arrastrar_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("arrastrar", dato)
        elif tipo == "cerrar_pestana":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("cerrar_pestana")
        elif tipo == "seleccionar_todo":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("seleccionar")
        elif tipo == "scroll_pantalla":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("scroll", dato)
        elif tipo == "ordenar_ventanas":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("ordenar")
        elif tipo == "enfocar_app":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("enfocar", dato)
        elif tipo == "ventana_ctrl":
            from Funciones_Slide.Sistema.Control_PC import control_ventana
            respuesta_slide = control_ventana(dato)
        elif tipo == "atajo_teclado":
            from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
            respuesta_slide = controlar_pantalla("atajo", dato)
        elif tipo == "escribir_texto":
            from Funciones_Slide.Sistema.Control_PC import dictar
            respuesta_slide = dictar(dato)
        elif tipo == "contestar":
            respuesta_slide = contestar_llamada(mensaje_de_orden(dato))
        elif tipo == "estado":
            respuesta_slide = _informe_estado()
        elif tipo == "redactar":
            _tipo_doc, _tema = dato
            hablado_del_asistente(random.choice(
                ("Déjeme escribirlo, señor; un momento.", "Me pongo a redactarlo, señor.",
                 "Enseguida se lo tengo, señor.")))
            from Funciones_Slide.Info.Redactor import redactar_documento
            from Nucleo_Slide.Latido_Trabajo import latido
            with latido(hablado_del_asistente):   # avisa "sigo en ello" si tarda
                respuesta_slide = redactar_documento(_tema, _tipo_doc)
        elif tipo == "resolver":
            hablado_del_asistente("Déjeme verlo, señor.")
            from Funciones_Slide.Info.Estudio import resolver_visual
            from Nucleo_Slide.Latido_Trabajo import latido
            with latido(hablado_del_asistente):
                respuesta_slide = resolver_visual(dato)
        elif tipo == "claude_code":
            from Funciones_Slide.Sistema.Programador import pedir_a_claude_code
            respuesta_slide = pedir_a_claude_code(dato)
        elif tipo == "agente":
            # AIDEN se encarga de la meta completa (narra el avance él mismo por voz).
            from Nucleo_Slide.Agente import modo_agente
            respuesta_slide = modo_agente(dato, hablar=hablado_del_asistente)
            ya_hablado = True                     # el agente ya narró y dijo el reporte final
            cerebro.ultima_interrumpida = False   # evita un barge-in fantasma tras la misión
        elif tipo == "retomar":
            from Funciones_Slide.Sistema.Sesion import restaurar_sesion
            respuesta_slide = restaurar_sesion()
        elif tipo == "musica_contextual":
            respuesta_slide = _musica_contextual()
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
            _set_modo_rapido(True)      # LLM en modo veloz mientras dure la sesión
            respuesta_slide = random.choice(_R_MANOS_ON)
        elif tipo == "manos_off":
            _manos_libres = False
            _silencios_manos_libres = 0
            _set_modo_rapido(False)
            respuesta_slide = random.choice(_R_MANOS_OFF)
        elif tipo == "buenas_noches":
            # Fin del DÍA (no solo ocultar): despedida cálida que reconoce tu día + se oculta.
            _manos_libres = False
            _set_modo_rapido(False)
            _cerrar_taller_silencioso()
            respuesta_slide = despedida_del_dia()
            ventana.pedir_fijar.emit(False)
            ventana.pedir_ocultar.emit()
        elif tipo == "descansa":
            _manos_libres = False
            _set_modo_rapido(False)
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
                _set_modo_rapido(False)
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
