import cv2
import time
import base64
import numpy as np
from openai import OpenAI
from secretos import OPENROUTER_API_KEY
from Funciones_Slide.Sistema.Vigilancia import ultimo_frame

_cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)


def _frame_a_base64(frame):
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return base64.b64encode(buffer).decode("utf-8")


def _describir_imagen(frame, instruccion):
    b64 = _frame_a_base64(frame)
    if b64 is None:
        return "No pude procesar la imagen, señor."
    try:
        r = _cliente.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": instruccion},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
            max_tokens=400,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"No pude analizar la imagen, señor: {e}"


def _capturar_propio():
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        return None
    frame = None
    for _ in range(5):
        ok, f = cam.read()
        if ok:
            frame = f
    cam.release()
    return frame


def analizar_vision(consulta=""):
    frame = ultimo_frame()
    if frame is None:
        for _ in range(20):
            time.sleep(0.1)
            frame = ultimo_frame()
            if frame is not None:
                break
    if frame is None:
        frame = _capturar_propio()
    if frame is None:
        return "No pude acceder a la cámara, señor."
    instruccion = (
        "Eres AIDEN, el mayordomo digital de Marco. Observa la imagen (cámara) y responde como Jarvis: "
        "identifica lo importante y, si ves algo roto, gastado o mejorable, da una sugerencia util "
        "y concreta (como repararlo o si conviene reemplazarlo). Se breve y directo, maximo 3 lineas."
    )
    if consulta:
        instruccion += f" Marco pregunta: {consulta}"
    return _describir_imagen(frame, instruccion)


def analizar(fuente="pantalla", consulta=""):
    """HERRAMIENTA unificada de visión: describe/analiza lo que AIDEN ve. fuente 'pantalla' (por
    defecto) mira la PANTALLA; fuente 'camara' mira por la CÁMARA. Reemplaza analizar_pantalla +
    analizar_vision sin perder nada. (Para RESOLVER un problema a fondo usa resolver_visual.)"""
    f = str(fuente or "pantalla").lower()
    if "cam" in f or "camara" in f or "ves" in f or "webcam" in f:
        return analizar_vision(consulta)
    return analizar_pantalla(consulta)


def analizar_pantalla(consulta=""):
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        return f"No pude capturar la pantalla, señor: {e}"
    instruccion = (
        "Eres AIDEN, el asistente de Marco. Esta es una captura de su PANTALLA de computador. "
        "Mira lo que hay y ayúdalo: si es un error de código o de programación, explícalo y di cómo "
        "solucionarlo; si es un texto o artículo, resúmelo; si pide algo concreto, respóndelo. "
        "Sé claro y directo, máximo 4 líneas."
    )
    if consulta:
        instruccion += f" Marco pregunta: {consulta}"
    return _describir_imagen(frame, instruccion)
