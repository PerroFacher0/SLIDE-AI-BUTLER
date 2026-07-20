# SOLUCIONADOR: AIDEN mira lo que tienes en pantalla (o en la cámara) y lo RESUELVE.
#
# El "ayúdame con esto" de un estudiante: un problema de mates/física, una pregunta de un quiz, un
# párrafo que no entiendes, un error de código... "resuelve esto" -> AIDEN captura la pantalla, se lo
# manda a su cerebro MÁS POTENTE (el experto, Pro, que además ve imágenes) y devuelve la solución
# paso a paso. Distinto de analizar_pantalla (que solo describe): esto RESUELVE y explica a fondo.

import base64

import cv2
import numpy as np
from openai import OpenAI
from secretos import OPENROUTER_API_KEY
from Funciones_Slide.Info.Experto import MODELO_EXPERTO

_cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)


def _captura_pantalla():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def _captura_camara():
    try:
        from Funciones_Slide.Sistema.Vigilancia import ultimo_frame
        f = ultimo_frame()
        if f is not None:
            return f
    except Exception:
        pass
    try:
        from Funciones_Slide.Info.Vision import _capturar_propio
        return _capturar_propio()
    except Exception:
        return None


def resolver_visual(fuente="pantalla", consulta=""):
    """HERRAMIENTA: resuelve/explica a fondo lo que Marco tiene delante. fuente 'pantalla' (por
    defecto) o 'camara'. Úsala cuando diga 'resuelve esto', 'ayúdame con este problema', 'cómo
    resuelvo esto', 'explícame esto'. Usa el cerebro experto (ve la imagen y razona paso a paso)."""
    fuente = str(fuente or "pantalla").lower()
    frame = _captura_camara() if ("cam" in fuente or "ves" in fuente) else _captura_pantalla()
    if frame is None:
        return "No pude capturar la imagen, señor."
    try:
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            return "No pude procesar la imagen, señor."
        b64 = base64.b64encode(buf).decode("utf-8")
    except Exception:
        return "No pude procesar la imagen, señor."

    instr = (
        "Eres AIDEN, el tutor personal de Marco (estudiante universitario). En esta imagen está lo que "
        "él tiene delante: puede ser un problema de matemáticas/física, una pregunta, un texto, un "
        "ejercicio o un error de código. RESUÉLVELO o explícalo A FONDO, en español, así:\n"
        "- Si es un problema/ejercicio: resuélvelo PASO A PASO y da la respuesta final clara.\n"
        "- Si es teoría o un texto: explícalo simple, con lo esencial.\n"
        "- Si es código con error: di qué falla y cómo corregirlo.\n"
        "Sé riguroso y ordenado, sin relleno. Trátalo de 'señor'."
    )
    if consulta:
        instr += f"\nMarco pregunta además: {consulta}"
    try:
        r = _cliente.chat.completions.create(
            model=MODELO_EXPERTO,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": instr},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            max_tokens=1400,
        )
        sol = (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"No pude resolverlo, señor: {e}"
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento("Resolví algo de la pantalla para Marco", "estudio")
    except Exception:
        pass
    return sol or "No conseguí una solución, señor; ¿me da más contexto?"
