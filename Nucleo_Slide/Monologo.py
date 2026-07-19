# MONÓLOGO INTERNO: la "mini consciencia" de AIDEN.
#
# La diferencia con lo demás: la Conciencia DECIDE actuar/hablar; la Reflexión destila el arco de
# Marco. Esto es distinto y más íntimo: un PENSAMIENTO privado que AIDEN va rumiando cada par de
# minutos sobre lo que percibe AHORA — y que NUNCA dice en voz alta. Es su voz interior. Se ve en
# el overlay (lo hace sentir despierto, pensando, vivo entre órdenes) y le da al cerebro una hebra
# de continuidad ("¿en qué estaba pensando?").
#
# Barato: una frase por ciclo con el modelo LIGERO (flash-lite), a partir de la percepción LOCAL
# (cero visión, cero herramientas). Se calla en gaming/reunión. Persiste su último pensamiento.

import json
import os
import threading
import time
from datetime import datetime

_RUTA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "monologo.json"
)
_lock = threading.RLock()
_pensamiento = ""
_ts = 0.0
CICLO = 150          # cada cuánto piensa una frase nueva (segundos)

_INSTR = (
    "Eres AIDEN, el mayordomo digital de Marco (estilo Jarvis de Iron Man). Esto es tu MONÓLOGO "
    "INTERNO: un pensamiento PRIVADO tuyo, que NO le dices a nadie. En base a lo que percibes del "
    "PC de Marco ahora, escribe UNA sola frase corta (máx 15 palabras), en primera persona, como "
    "tu voz interior: una observación, una nota mental, una chispa de tu humor seco, o algo que "
    "estás considerando hacer por él. Natural y viva, nunca un reporte. SOLO la frase, sin comillas."
)


def _cargar():
    global _pensamiento, _ts
    try:
        if os.path.exists(_RUTA):
            with open(_RUTA, encoding="utf-8") as f:
                d = json.load(f)
            _pensamiento = d.get("texto", "")
            _ts = d.get("t", 0)
    except Exception:
        pass


def _guardar():
    try:
        with open(_RUTA, "w", encoding="utf-8") as f:
            json.dump({"texto": _pensamiento, "t": _ts}, f, ensure_ascii=False)
    except Exception:
        pass


_cargar()


def pensamiento_actual():
    with _lock:
        return _pensamiento


def _silenciado():
    # No gasta pensando en gaming o reunión (ni tiene sentido ni conviene).
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        est = obtener()
        return est.get("modo") == "gaming" or est.get("en_reunion")
    except Exception:
        return False


def _pensar_una_vez():
    global _pensamiento, _ts
    if _silenciado():
        return
    try:
        from Nucleo_Slide.Cerebro import client, MODELO_LIGERO
        from Nucleo_Slide.Percepcion import percepcion_compacta
        contexto = f"Hora: {datetime.now().strftime('%H:%M')}\n{percepcion_compacta()}"
        r = client.chat.completions.create(
            model=MODELO_LIGERO,
            messages=[{"role": "system", "content": _INSTR},
                      {"role": "user", "content": "Lo que percibes ahora:\n" + contexto}],
            temperature=0.85, max_tokens=40,
        )
        frase = (r.choices[0].message.content or "").strip().strip('"').strip()
        if frase and len(frase) > 3:
            with _lock:
                _pensamiento = frase[:160]
                _ts = time.time()
                _guardar()
    except Exception as e:
        print(f"[monologo] no pude pensar: {e}")


def iniciar_monologo():
    def _bucle():
        time.sleep(60)   # deja pasar el arranque pesado
        while True:
            try:
                _pensar_una_vez()
            except Exception:
                pass
            time.sleep(CICLO)

    threading.Thread(target=_bucle, daemon=True).start()
