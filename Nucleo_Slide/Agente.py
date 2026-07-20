# MODO AGENTE: "Encárgate de esto, señor". El salto de AIDEN de responder-comandos a CUMPLIR-metas.
#
# Marco da UNA meta compleja en lenguaje natural ("descárgame el paper de X y guárdalo en la carpeta
# de la tesis", "organiza mis descargas por tipo", "búscame los precios de Y y hazme una nota"). AIDEN
# entra en un BUCLE AUTÓNOMO: piensa el plan, EJECUTA cada paso con TODO su arsenal (la llave maestra
# de PowerShell, la visión de pantalla, sus 58 herramientas), VERIFICA que funcionó, se AUTO-CORRIGE
# si algo falla, y NARRA el avance en voz mientras trabaja. Al final reporta. Es el "considérelo hecho"
# de Jarvis: no es una herramienta más, es AIDEN encargándose de verdad.
#
# Reusa el cerebro (mismo cliente, modelo y herramientas). No se auto-invoca (no es una tool del LLM):
# lo dispara Marco con "encárgate de...". El guard de Control_Total sigue bloqueando lo catastrófico.

import json

MAX_PASOS = 14   # techo de acciones encadenadas (una tarea real rara vez pasa de ~8)

_SISTEMA = (
    "Eres AIDEN, el mayordomo digital de Marco (estilo Jarvis), en MODO AGENTE. Marco te encargó una "
    "MISIÓN y tu trabajo es CUMPLIRLA de principio a fin TÚ SOLO, usando tus herramientas — no te "
    "limites a describir lo que se podría hacer: HAZLO.\n"
    "CÓMO TRABAJAS:\n"
    "1. Divide la misión en pasos concretos y ejecútalos UNO POR UNO con tus herramientas.\n"
    "2. Para lo que no tenga herramienta propia, usa ejecutar_en_pc (PowerShell que tú compones): "
    "puedes crear/mover/buscar archivos y carpetas, abrir apps, consultar el sistema, descargar, etc.\n"
    "3. ANTES de cada acción, escribe en tu respuesta UNA frase corta y natural de lo que vas a hacer "
    "(ej. 'Creo la carpeta primero, señor.') — es lo que Marco te oye decir mientras trabajas.\n"
    "4. Tras cada acción MIRA el resultado: si falló, diagnostícalo e inténtalo de otra forma "
    "(otros argumentos, otra herramienta). No te rindas al primer tropiezo.\n"
    "5. Cuando la misión esté CUMPLIDA de verdad, responde una última línea que EMPIECE EXACTAMENTE "
    "con 'MISIÓN CUMPLIDA:' y un resumen de una frase de lo que lograste.\n"
    "6. Si es genuinamente imposible o peligroso, responde una línea que empiece con 'NO PUDE:' y por "
    "qué. No inventes que lo hiciste si no lo verificaste.\n"
    "Sé eficiente y decidido. Trata a Marco de 'señor'. Nada de párrafos: frases cortas de acción."
)


def _formatear_tool_calls(tcs):
    return [{"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tcs]


def modo_agente(objetivo, hablar=None, max_pasos=MAX_PASOS):
    """Toma una meta compleja y la LOGRA sola (plan -> ejecuta -> verifica -> reporta), narrando el
    avance en voz. `hablar` = callback de voz (si None, usa la voz normal). Devuelve el reporte final."""
    from Nucleo_Slide.Cerebro import client, MODELO, _ejecutar_tool_call
    from Nucleo_Slide.configuracion_del_agente import tools

    objetivo = str(objetivo or "").strip()
    if not objetivo:
        return "¿De qué me encargo, señor?"

    if hablar is None:
        try:
            from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente
            hablar = hablado_del_asistente
        except Exception:
            hablar = lambda t: None

    def decir(t):
        t = str(t or "").strip()
        if t:
            try:
                hablar(t)
            except Exception:
                pass

    def _mundo(**kw):
        try:
            from Nucleo_Slide.Estado_Del_Mundo import actualizar, registrar_evento
            if "evento" in kw:
                registrar_evento(kw.pop("evento"), "agente")
            if kw:
                actualizar(**kw)
        except Exception:
            pass

    decir("Considérelo hecho, señor. Me pongo con ello.")
    _mundo(modo="agente", evento=f"Modo agente: {objetivo[:80]}")

    mensajes = [{"role": "system", "content": _SISTEMA},
                {"role": "user", "content": "MISIÓN: " + objetivo}]
    reporte = ""
    acciones = 0

    for paso in range(max_pasos):
        try:
            r = client.chat.completions.create(
                model=MODELO, messages=mensajes, tools=tools,
                tool_choice="auto", temperature=0.3,
            )
        except Exception as e:
            reporte = (f"Perdí el enlace a mitad de la misión, señor. Alcancé {acciones} paso(s). "
                       f"Detalle: {e}")
            decir(reporte)
            _mundo(modo="normal")
            return reporte

        msg = r.choices[0].message
        contenido = (msg.content or "").strip()
        tcs = list(msg.tool_calls or [])

        entrada = {"role": "assistant", "content": msg.content or None}
        if tcs:
            entrada["tool_calls"] = _formatear_tool_calls(tcs)
        mensajes.append(entrada)

        # Señales de fin (en el texto del modelo).
        limpio = contenido.upper()
        if limpio.startswith("MISIÓN CUMPLIDA") or limpio.startswith("MISION CUMPLIDA"):
            reporte = contenido
            decir(contenido)
            break
        if limpio.startswith("NO PUDE"):
            reporte = contenido
            decir(contenido)
            break

        # Narra el "voy a hacer X" antes de actuar (lo que Marco oye trabajar).
        if contenido:
            decir(contenido)

        if tcs:
            for tc in tcs:
                resultado = _ejecutar_tool_call(tc.function.name, tc.function.arguments)
                mensajes.append({"role": "tool", "tool_call_id": tc.id, "content": resultado})
                acciones += 1
            _mundo(evento=f"Agente paso {paso + 1}: {', '.join(tc.function.name for tc in tcs)}")
            continue

        # Sin herramientas y sin señal de fin: si dijo algo, lo tomamos como cierre; si no, empujamos.
        if contenido:
            reporte = contenido
            break
        mensajes.append({"role": "user", "content":
                         "Continúa con el siguiente paso, o si ya terminaste di 'MISIÓN CUMPLIDA:'."})

    _mundo(modo="normal")
    if not reporte:
        reporte = (f"Trabajé la misión, señor, e hice {acciones} acción(es), pero llegué a mi límite "
                   "de pasos sin cerrarla del todo. ¿Reviso algo en concreto?")
        decir(reporte)
    _mundo(evento="Modo agente: fin")
    return reporte
