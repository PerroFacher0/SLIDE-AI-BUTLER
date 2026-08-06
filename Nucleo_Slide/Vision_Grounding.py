# VISION GROUNDING: localizar algo POR SU DESCRIPCIÓN dentro de una imagen cualquiera, devolviendo
# el punto (x,y) en píxeles reales de esa imagen. Es el mismo mecanismo que ya se probó y funciona
# en Funciones_Slide/Sistema/Control_Pantalla.py (clic guiado por visión en el escritorio) — se
# extrae aquí como helper COMPARTIDO para que también lo use Navegador_Web.py sobre el viewport del
# navegador, sin duplicar la lógica ni tocar el módulo de escritorio que ya está probado y en uso.
#
# HALLAZGO clave (ya validado en producción): pedirle a Gemini "dame las coordenadas X,Y" en texto
# libre es POCO FIABLE. El formato que SÍ funciona es "box_2d", que Gemini tiene entrenado/documentado
# para detección espacial: {"box_2d": [ymin,xmin,ymax,xmax], "label": "..."} normalizado 0-1000.

import json
import re


def localizar_en_imagen(imagen_pil, descripcion, intentos=5):
    """Ubica 'descripcion' dentro de 'imagen_pil' (PIL.Image) y devuelve (x, y) en píxeles reales
    de ESA imagen, o None si no lo ve. Cuesta una consulta al modelo (no es instantáneo).

    REINTENTA hasta 'intentos' veces: probado en la práctica (test real con formas planas sin
    texto) que Gemini a veces dice "no lo veo" para algo que SÍ está ahí — un solo tiro tiene
    ~50% de fallos falsos en esos casos; repetir la consulta lo resuelve casi siempre."""
    if imagen_pil is None:
        return None
    try:
        import io
        import base64
        buf = io.BytesIO()
        imagen_pil.convert("RGB").save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None
    try:
        from openai import OpenAI
        from secretos import OPENROUTER_API_KEY
        # Corre DENTRO de una operación cancelable: sin timeout, el Ctrl+Alt+P de Marco se queda
        # esperando a que vuelva de la red (600 s por defecto en el SDK) sin que nadie lo lea.
        cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY,
                         timeout=30.0, max_retries=1)
    except Exception:
        return None
    prompt = (
        "Detect exactly this: '" + str(descripcion) + "'. Output ONLY a JSON list with one "
        'entry: {"box_2d": [ymin,xmin,ymax,xmax], "label": "..."}, coordinates normalized '
        "0-1000. If it is not visible, output exactly: []"
    )
    for intento in range(max(1, intentos)):
        try:
            r = cliente.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]}],
                max_tokens=150, temperature=0 if intento == 0 else 0.4,
            )
            salida = (r.choices[0].message.content or "").strip()
        except Exception:
            continue
        m = re.search(r"\[\s*\{.*?\}\s*\]", salida, re.DOTALL)
        if not m:
            continue
        try:
            datos = json.loads(m.group(0))
            if not datos:
                continue
            ymin, xmin, ymax, xmax = datos[0]["box_2d"]
        except Exception:
            continue
        w, h = imagen_pil.size
        x = max(0, min(w - 1, round((xmin + xmax) / 2 / 1000 * w)))
        y = max(0, min(h - 1, round((ymin + ymax) / 2 / 1000 * h)))
        return (x, y)
    return None
