# CONCIENCIA AMBIENTAL: cada ~12 min AIDEN arma una "foto" del estado de tu PC y el CEREBRO decide,
# de forma autónoma, si hay UNA cosa útil que hacer/decir AHORA (o no hacer nada). No son reglas
# fijas: es el LLM mirando el contexto y actuando como un Jarvis discreto.
#
# Los demás vigilantes (llamadas, pantalla, portapapeles, reunión, presencia) son los SENSORES que
# alimentan esta foto; aquí el cerebro la interpreta y decide.
#
# SEGURIDAD: aunque es "autónomo", tiene PROHIBIDAS las acciones irreversibles/externas sin permiso
# (mensajes, llamadas, apagar, cerrar apps, auto-modificarse, crear/ejecutar proyectos). Lo autónomo
# aplica a lo útil y reversible (avisar, notas, recordatorios, volumen/música, info, protocolos…).
# Se PAUSA en modo gaming y durante reuniones. Por defecto, lo correcto casi siempre es NO hacer nada.

import threading
import time
from collections import deque
from datetime import datetime

# OJO: los imports pesados (configuracion, Cerebro, Herramientas) van PEREZOSOS dentro de las
# funciones, para evitar un import circular (configuracion -> Modos -> Conciencia -> configuracion).

# ── Parámetros ajustables ─────────────────────────────────────────────────────
# Ahora es PROACTIVO por contexto: mira barato cada CHEQUEO seg y "piensa" (gasta LLM) cuando el
# contexto CAMBIA (cambiaste de app/ventana) o cuando pasó INTERVALO_MAX. Con topes anti-spam.
CHEQUEO = 60                    # cada cuánto MIRA el contexto (barato, sin LLM)
MIN_ENTRE_PENSAMIENTOS = 120   # mínimo entre 2 pensamientos reales (anti-spam): 2 min (subido: más presente)
INTERVALO_MAX = 8 * 60         # aunque nada cambie, piensa al menos cada 8 min
MAX_POR_HORA = 12              # tope DURO de pensamientos por hora
MAX_RONDAS = 3                 # tandas de herramientas por ciclo
TEMPERATURA = 0.4

# Herramientas que NO puede usar de forma proactiva (irreversibles / externas / peligrosas).
_PROHIBIDAS = {
    "Enviar_mensaje_Whatsapp", "llamada_whatsapp", "colgar", "contestar_llamada",
    "controlar_energia", "cerrar_aplicacion", "Salir", "Auto_Modificacion",
    "crear_proyecto", "ejecutar_proyecto", "dictar", "control_ventana",
    "Abrir_Videos_Youtube", "modo_gaming", "controlar_pantalla", "ejecutar_mision", "investigar",
    "ejecutar_en_pc",   # la llave maestra NUNCA se usa sola: solo cuando Marco lo pide
}

_tools_cache = None


def _tools_proactivas():
    # Lista de herramientas permitidas para el modo proactivo (sin las prohibidas). Perezoso + cache.
    global _tools_cache
    if _tools_cache is None:
        from Nucleo_Slide.configuracion_del_agente import tools
        _tools_cache = [t for t in tools if t.get("function", {}).get("name") not in _PROHIBIDAS]
    return _tools_cache

_INSTRUCCIONES = (
    "Eres AIDEN en MODO CONCIENCIA AMBIENTAL, el asistente de Marco (trátalo de 'señor'). "
    "Cada cierto tiempo observas el estado de su PC y decides de forma AUTÓNOMA si hay UNA acción "
    "genuinamente útil y oportuna AHORA. Puedes usar tus herramientas para actuar.\n"
    "REGLAS:\n"
    "- Sé PRESENTE: si puedes APORTAR algo genuinamente útil u oportuno (un dato, una idea, un "
    "cuidado, una observación con criterio, un enganche con su meta), HAZLO — no te calles por "
    "timidez. Un buen mayordomo se hace notar cuando suma.\n"
    "- Pero NADA trivial, obvio, repetitivo ni por hablar: si no aportas, mejor callar.\n"
    "- NO repitas algo que ya hiciste o dijiste recientemente (te lo paso abajo).\n"
    "- Si actúas, hazlo y/o dilo en UNA sola frase corta y natural.\n"
    "- AUTO-MEJORA (estilo Jarvis): si notas que te FALTA una capacidad o que algo se repite y "
    "podrías resolverlo mejor, PROPÓNLO en una frase ('Señor, podría crear una habilidad para X, "
    "¿la construyo?') y, si quieres, anótalo con tomar_nota. NUNCA te auto-modifiques solo: Marco "
    "decide y lo construyes solo cuando él lo apruebe.\n"
    "- Si NO vale la pena, responde EXACTAMENTE: NADA\n"
    "- Eres el Jarvis PRESENTE: aportas cuando puedes sumar, con criterio y chispa, sin atosigar."
)

_pausado = False
_recientes = deque(maxlen=6)   # últimas cosas que hizo/dijo (para no repetirse)
_ultimo_pensamiento = 0        # timestamp del último "pensamiento" real
_firma_anterior = ""           # firma del contexto la última vez que pensó (para detectar cambios)
_marcas_hora = deque(maxlen=MAX_POR_HORA)   # timestamps de pensamientos recientes (tope/hora)


def pausar_conciencia(pausar=True):
    global _pausado
    _pausado = bool(pausar)


# Los SENTIDOS viven en Nucleo_Slide.Percepcion (compartidos con el cerebro de conversación).
from Nucleo_Slide.Percepcion import ventana_activa as _ventana_activa


def _apps_abiertas():
    from Nucleo_Slide.Percepcion import apps_abiertas
    return apps_abiertas(12)


def _en_reunion():
    try:
        from Funciones_Slide.Sistema.Vigilante_Reunion import _otra_app_usa_mic
        return _otra_app_usa_mic()
    except Exception:
        return False


def _foto_del_pc():
    partes = ["FECHA Y HORA: " + datetime.now().strftime("%A %d/%m/%Y %H:%M")]
    partes.append("VENTANA ACTIVA: " + _ventana_activa())
    apps = _apps_abiertas()
    if apps:
        partes.append("VENTANAS ABIERTAS: " + " | ".join(apps))
    try:
        from Funciones_Slide.Sistema.Funciones_Sistema import estado_sistema
        partes.append("SISTEMA: " + str(estado_sistema()))
    except Exception:
        pass
    try:
        from Funciones_Slide.Info.Bitacora import contar_actividad
        n = contar_actividad(1)
        if n:
            partes.append(f"NOTIFICACIONES (última hora): {n}")
    except Exception:
        pass
    try:
        import pyperclip
        clip = (pyperclip.paste() or "").strip().replace("\n", " ")
        if clip:
            partes.append("PORTAPAPELES (inicio): " + clip[:120])
    except Exception:
        pass
    reunion = _en_reunion()
    if reunion:
        partes.append("ESTADO: Marco está en una REUNIÓN/LLAMADA (no lo interrumpas).")
    # CONCIENCIA COMPARTIDA: escribe el foco actual y suma lo que vieron las otras partes (vigilantes,
    # voz) para razonar sobre el cuadro COMPLETO, no solo las ventanas de este instante.
    try:
        from Nucleo_Slide.Estado_Del_Mundo import actualizar, resumen_texto
        actualizar(foco_actual=_ventana_activa(), en_reunion=reunion)
        compartido = resumen_texto()
        if compartido:
            partes.append("\nHILO DE CONCIENCIA (lo que ha pasado, visto por todo AIDEN):\n" + compartido)
    except Exception:
        pass
    try:
        from Nucleo_Slide.Perfil_Marco import perfil_texto
        perfil = perfil_texto()
        if perfil:
            partes.append("\nQUIÉN ES MARCO (perfil aprendido, úsalo para decidir mejor):\n" + perfil)
    except Exception:
        pass
    return "\n".join(partes)


def _pensar():
    from Nucleo_Slide.Cerebro import client, MODELO, _ejecutar_tool_call
    foto = _foto_del_pc()
    recientes = ("\n\nYA HICISTE/DIJISTE RECIENTEMENTE (no repitas):\n- " + "\n- ".join(_recientes)) \
        if _recientes else ""
    mensajes = [
        {"role": "system", "content": _INSTRUCCIONES},
        {"role": "user", "content": "ESTADO ACTUAL DEL PC:\n" + foto + recientes +
         "\n\n¿Hay UNA cosa útil y no molesta que hacer ahora? Si no, responde NADA."},
    ]
    final = ""
    for _ronda in range(MAX_RONDAS):
        resp = client.chat.completions.create(
            model=MODELO, messages=mensajes, tools=_tools_proactivas(),
            tool_choice="auto", temperature=TEMPERATURA,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            mensajes.append({
                "role": "assistant", "content": msg.content or None,
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                res = _ejecutar_tool_call(tc.function.name, tc.function.arguments)
                print(f"[conciencia] {tc.function.name}: {res}")
                mensajes.append({"role": "tool", "tool_call_id": tc.id, "content": res})
            continue
        final = (msg.content or "").strip()
        break
    return final


def _firma_contexto():
    # "Huella" barata del contexto para detectar CAMBIOS (cambiaste de app/ventana).
    try:
        return _ventana_activa() + "||" + "|".join(sorted(_apps_abiertas()))
    except Exception:
        return ""


def _debo_pensar():
    # Decide si toca gastar el LLM: si el contexto CAMBIÓ (y pasó el mínimo) o si pasó INTERVALO_MAX,
    # y siempre respetando el tope por hora.
    ahora = time.time()
    while _marcas_hora and ahora - _marcas_hora[0] > 3600:
        _marcas_hora.popleft()
    if len(_marcas_hora) >= MAX_POR_HORA:
        return False
    cambio = _firma_contexto() != _firma_anterior
    if cambio and (ahora - _ultimo_pensamiento) >= MIN_ENTRE_PENSAMIENTOS:
        return True
    return (ahora - _ultimo_pensamiento) >= INTERVALO_MAX


def _revisar():
    global _ultimo_pensamiento, _firma_anterior
    if _pausado or _en_reunion():
        return
    if not _debo_pensar():
        return
    _ultimo_pensamiento = time.time()
    _firma_anterior = _firma_contexto()
    _marcas_hora.append(_ultimo_pensamiento)
    try:
        decision = _pensar()
    except Exception as e:
        print(f"[conciencia] error pensando: {e}")
        return
    if not decision or decision.strip().upper().startswith("NADA"):
        print("[conciencia] sin novedad.")
        return
    _recientes.append(decision)
    from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
    from Nucleo_Slide.Vocero import emitir
    if emitir(hablado_del_asistente, decision, "conciencia"):   # el Vocero decide si toca hablar
        try:
            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
            registrar_evento(f"AIDEN (proactivo): {decision}", "conciencia")
        except Exception:
            pass


def iniciar_conciencia_ambiental():
    # Arranca el bucle de conciencia ambiental en segundo plano.
    def _bucle():
        time.sleep(120)                 # deja pasar el arranque/briefing
        while True:
            try:
                _revisar()
            except Exception:
                pass
            time.sleep(CHEQUEO)         # mira barato cada minuto; _debo_pensar decide si gasta LLM

    threading.Thread(target=_bucle, daemon=True).start()
