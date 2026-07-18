# INVESTIGACIÓN: "investígame esto y vuelve con hallazgos" — el Jarvis que dice "Señor, completé el
# análisis". A diferencia de consultar_experto (un disparo) o buscar_en_internet (una búsqueda), una
# investigación es MULTI-PASO: descompone el tema en sub-preguntas, busca cada una, sintetiza un
# INFORME con el modelo potente (Pro), te lo REPORTA por voz y lo GUARDA como nota. Segundo plano.

import re
import threading

from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente

_MAX_SUB = 4   # sub-preguntas máximas a investigar


def _evento(texto):
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(texto, "investigacion")
    except Exception:
        pass


def _subpreguntas(tema):
    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO as MODELO
        r = client.chat.completions.create(
            model=MODELO,
            messages=[{"role": "user", "content":
                "Para investigar a fondo este tema, lista de 3 a 4 SUB-PREGUNTAS clave (una por línea, "
                "sin numerar, concretas y buscables en internet). SOLO las preguntas.\n\nTEMA: " + tema}],
            temperature=0.3, max_tokens=200,
        )
        lineas = [re.sub(r"^[\-\*\d\.\)\s]+", "", l).strip()
                  for l in (r.choices[0].message.content or "").splitlines() if l.strip()]
        return [l for l in lineas if l][:_MAX_SUB] or [tema]
    except Exception:
        return [tema]


def _sintetizar(tema, hallazgos):
    try:
        from Nucleo_Slide.Cerebro import client
        from Funciones_Slide.Info.Experto import MODELO_EXPERTO
        r = client.chat.completions.create(
            model=MODELO_EXPERTO,
            messages=[{"role": "user", "content":
                "Eres el analista de AIDEN. Con esta información recopilada de internet, redacta un "
                "INFORME claro y útil para Marco sobre el tema: hallazgos clave en viñetas y una "
                "conclusión breve. En español, riguroso, sin relleno. Si algo no quedó claro, dilo.\n\n"
                "TEMA: " + tema + "\n\nINFORMACIÓN RECOPILADA:\n" + "\n\n".join(hallazgos)}],
            max_tokens=900,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"No pude sintetizar el informe, señor: {e}"


def investigar(tema, nombre=""):
    """Investiga un tema A FONDO (multi-paso: sub-preguntas + búsquedas + síntesis), te reporta por voz
    y guarda el informe como nota. Para 'investiga/averigua/analiza a fondo X'. Corre en segundo plano."""
    tema = str(tema or "").strip()
    if not tema:
        return "¿Qué quiere que investigue, señor?"

    def _trabajo():
        _evento(f"Investigando a fondo: {tema}")
        subs = _subpreguntas(tema)
        hallazgos = []
        try:
            from Funciones_Slide.Sistema.Funciones_Sistema import buscar_en_internet
        except Exception:
            buscar_en_internet = None
        for s in subs:
            if buscar_en_internet:
                try:
                    hallazgos.append(f"### {s}\n{buscar_en_internet(s)}")
                except Exception:
                    pass
        if not hallazgos:
            hablado_del_asistente(f"Señor, no logré recopilar información sobre {tema}.")
            return
        informe = _sintetizar(tema, hallazgos)
        # Guarda el informe completo como nota (para que quede).
        try:
            from Funciones_Slide.Productividad.Notas import tomar_nota
            tomar_nota(f"INFORME — {tema}\n\n{informe}")
        except Exception:
            pass
        # Reporta por voz (conciso; el detalle queda en la nota).
        resumen = informe if len(informe) <= 700 else informe[:700] + "… (el resto, en sus notas, señor)."
        hablado_del_asistente(f"Señor, terminé de investigar sobre {tema}. {resumen}")
        _evento(f"Investigación lista y guardada: {tema}")

    threading.Thread(target=_trabajo, daemon=True).start()
    return f"Me pongo a investigar «{tema}», señor. Le traigo un informe en cuanto lo tenga."
