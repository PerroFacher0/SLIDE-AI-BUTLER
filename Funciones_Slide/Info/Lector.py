# LECTOR: AIDEN LEE EN VOZ ALTA lo que hay en pantalla y EXTRAE su texto (OCR). Para estudiar sin
# leer con los ojos: "léeme esto", "léeme la pantalla", "pásame a texto lo que hay en la imagen".
#
#   - leer_en_voz(fuente): saca el texto (de la PANTALLA vía OCR, o del portapapeles) y lo DEVUELVE
#     para que AIDEN lo lea en voz (interrumpible con "para"). Distinto de resumir/analizar: LEE tal cual.
#   - extraer_texto(fuente): transcribe el texto que ve y lo COPIA al portapapeles (para pegarlo).
#
# El OCR usa el modelo de visión (transcribe verbatim); es el mismo mecanismo que ya funciona en el
# resto de AIDEN, así que cubre PDFs, diapositivas, imágenes, cualquier cosa con texto en pantalla.

import base64
import io


def _capturar():
    try:
        from PIL import ImageGrab
        return ImageGrab.grab()
    except Exception:
        return None


def _ocr(imagen):
    # Transcribe VERBATIM todo el texto de la imagen con el modelo de visión. "" si no hay/ falla.
    if imagen is None:
        return ""
    try:
        buf = io.BytesIO()
        imagen.convert("RGB").save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return ""
    try:
        from openai import OpenAI
        from secretos import OPENROUTER_API_KEY
        cliente = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        prompt = ("Transcribe TODO el texto visible en esta imagen, EXACTAMENTE como está escrito, "
                  "en orden de lectura natural. No agregues comentarios, títulos ni explicaciones: "
                  "SOLO el texto. Si no hay texto legible, responde: (sin texto)")
        r = cliente.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]}],
            max_tokens=1500, temperature=0,
        )
        t = (r.choices[0].message.content or "").strip()
        return "" if t.startswith("(sin texto") else t
    except Exception:
        return ""


def _clipboard():
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()
    except Exception:
        return ""


def _texto_de(fuente):
    f = str(fuente or "pantalla").lower()
    if "portapapeles" in f or "copie" in f or "clip" in f or f == "esto":
        return _clipboard()
    return _ocr(_capturar())


def leer_en_voz(fuente="pantalla"):
    """Saca el texto de la fuente y lo DEVUELVE para que AIDEN lo lea en voz alta (interrumpible)."""
    texto = _texto_de(fuente)
    if not texto:
        return "No encontré texto para leer, señor."
    if len(texto) > 4000:                     # tope sensato para no leer 50 páginas de un tirón
        texto = texto[:4000].rsplit(" ", 1)[0] + "… y sigue, señor; dígame si continúo."
    return texto


def extraer_texto(fuente="pantalla"):
    """Transcribe el texto que AIDEN ve y lo COPIA al portapapeles (para pegarlo donde sea)."""
    texto = _ocr(_capturar()) if "clip" not in str(fuente).lower() else _clipboard()
    if not texto:
        return "No vi texto para extraer, señor."
    try:
        import pyperclip
        pyperclip.copy(texto)
        return f"Listo, señor: copié el texto ({len(texto)} caracteres) al portapapeles. Ya puede pegarlo."
    except Exception:
        return f"Extraje el texto pero no pude copiarlo, señor. Dice: {texto[:200]}"
