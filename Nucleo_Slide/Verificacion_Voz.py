# ¿QUIEN ESTÁ HABLANDO? — verificación de locutor, local y proporcional al riesgo.
#
# El hueco: el login es FACIAL y ocurre UNA vez, al arrancar. A partir de ahí, cualquier voz que
# diga la palabra clave es obedecida. Y AIDEN manda mensajes en nombre de Marco, ejecuta PowerShell
# arbitrario y puede auto-elevarse a administrador. Nada comprueba que quien da la orden siga
# siendo él.
#
# ── DOS DECISIONES DE DISEÑO QUE IMPORTAN MÁS QUE EL MODELO ───────────────────
#
# 1. PROPORCIONAL, NO UNIVERSAL. Verificar "sube el volumen" añade latencia a cambio de nada: el
#    peor caso de que un impostor suba el volumen es que sube el volumen. Se comprueba solo antes
#    de las herramientas con PODER REAL (mandar mensajes en su nombre, ejecutar comandos, elevarse
#    a admin, borrar archivos). Lo demás pasa sin fricción.
#
# 2. SE COMPRUEBA AL EJECUTAR LA HERRAMIENTA, NO AL TRANSCRIBIR. Cuando Marco habla todavía no se
#    sabe qué va a hacer AIDEN — eso lo decide el modelo después. Comprobando en el punto por donde
#    pasan las 59 herramientas, la huella se calcula SOLO si de verdad va a pasar algo serio. En un
#    turno normal, el coste es exactamente cero.
#
# ── HONESTIDAD SOBRE EL ESTADO ────────────────────────────────────────────────
# NACE APAGADA y así se queda hasta que Marco enrole su voz (Pruebas/enrolar_voz.py). Sin huella no
# hay verificación: no se inventa una, no se "aproxima". Una autenticación a medias es peor que
# ninguna, porque se confía en ella.
#
# Y LOS UMBRALES HAY QUE CALIBRARLOS CON SU VOZ REAL. Los de aquí son un punto de partida
# razonable, no un valor verificado: nadie ha medido todavía cuánto se parece Marco a sí mismo con
# este micrófono, en esta habitación. Si se queda fuera de su propio asistente, o si pasa alguien
# que no debería, se tocan estas dos constantes.

import os
import threading
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fuera de git, igual que secretos.py: es un dato biométrico de Marco.
RUTA_HUELLA = os.path.join(_RAIZ, "huella_marco.npy")

UMBRAL_OK = 0.70        # a partir de aquí, es él: pasa sin fricción
UMBRAL_DUDA = 0.50      # entre ambos: puede ser él resfriado, con ruido, u otro micrófono

# Herramientas que hacen algo IRREVERSIBLE o en nombre de Marco. Solo estas se verifican.
# Criterio: ¿el peor caso de que lo haga un impostor es algo que Marco no pueda deshacer, o algo
# que salga de este PC con su nombre? Si la respuesta es no, no está en la lista.
TOOLS_DE_RIESGO = {
    "enviar_mensaje",        # habla POR Marco a otras personas
    "llamada_whatsapp",
    "avisar_al_celular",
    "ejecutar_en_pc",        # la llave maestra
    "permisos",              # elevarse a administrador
    "gestionar_archivos",    # borrar / mover
    "controlar_energia",     # apagar, reiniciar
    "Auto_Modificacion",     # reescribe el propio código de AIDEN
    "proyecto",
    "macro",                 # reproduce una secuencia de clics grabada
    "hardware",
    # LA PUERTA DE ATRÁS: programar(hacer='whatsapp'|'llamar') manda un mensaje o hace una llamada
    # en nombre de Marco, igual que enviar_mensaje — solo que más tarde. Verificar enviar_mensaje y
    # dejar esta fuera era pedir la contraseña en la puerta y dejar la ventana abierta: bastaba con
    # decir "programa un WhatsApp a X en un minuto". Se comprueba al PROGRAMARLA, que es cuando hay
    # una voz que comprobar; cuando se dispara ya no hay nadie hablando.
    "programar",
}

CADUCIDAD_AUDIO = 60      # s: pasado ese rato, el audio guardado ya no representa "quien manda ahora"

_lock = threading.RLock()
_audio_turno = None       # el audio de la ORDEN en curso; se calcula la huella solo si hace falta
_audio_en = 0.0
_huella = None
_modelo = None
_ultimo_motivo = ""


def _cargar_huella():
    global _huella
    if _huella is not None:
        return _huella
    try:
        import numpy as np
        if os.path.exists(RUTA_HUELLA):
            _huella = np.load(RUTA_HUELLA)
    except Exception:
        _huella = None
    return _huella


def esta_activa():
    """Solo si Marco enroló su voz Y el modelo está disponible."""
    if _cargar_huella() is None:
        return False
    try:
        import speechbrain  # noqa: F401
        return True
    except Exception:
        return False


def _cargar_modelo():
    """ECAPA-TDNN en CPU, a propósito: la GPU ya la pelean Whisper, Kokoro y la visión."""
    global _modelo
    if _modelo is not None:
        return _modelo
    from speechbrain.inference.speaker import EncoderClassifier
    _modelo = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=os.path.join(_RAIZ, ".modelos", "ecapa"),
        run_opts={"device": "cpu"},
    )
    return _modelo


def embedding_de(datos_wav, frecuencia=16000):
    """Huella de un audio (bytes PCM 16 bits). None si no se puede."""
    try:
        import numpy as np
        import torch
        m = np.frombuffer(datos_wav, dtype=np.int16).astype(np.float32) / 32768.0
        if m.size < frecuencia * 0.6:       # menos de 0.6 s no da para identificar a nadie
            return None
        with torch.inference_mode():
            emb = _cargar_modelo().encode_batch(torch.from_numpy(m).unsqueeze(0))
        return emb.squeeze().cpu().numpy()
    except Exception:
        return None


def _similitud(a, b):
    import numpy as np
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if not na or not nb:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def recordar_audio(datos_wav):
    """Lo llama el transcriptor con el audio de la orden. NO calcula nada todavía: la mayoría de
    los turnos no tocan ninguna herramienta de riesgo, así que calcular siempre sería pagar por
    algo que casi nunca se usa."""
    global _audio_turno, _audio_en
    with _lock:
        _audio_turno, _audio_en = datos_wav, time.time()


def olvidar_audio():
    global _audio_turno, _audio_en
    with _lock:
        _audio_turno, _audio_en = None, 0.0


def guardar_huella(embeddings):
    """Promedia los audios del enrolamiento en una sola huella."""
    import numpy as np
    global _huella
    media = np.mean(np.stack(embeddings), axis=0)
    np.save(RUTA_HUELLA, media)
    _huella = media
    return RUTA_HUELLA


def verificar_para(nombre_tool):
    """¿Puede ejecutarse esa herramienta con la voz que dio la orden?

    Devuelve ('OK', sim) | ('DUDA', sim) | ('RECHAZO', sim) | ('SIN_VERIFICAR', 0.0).
    'SIN_VERIFICAR' es el caso normal hoy: sin huella enrolada esto no bloquea NADA — no se
    inventa una verificación que no se puede hacer."""
    if nombre_tool not in TOOLS_DE_RIESGO:
        return "SIN_VERIFICAR", 0.0
    if not esta_activa():
        return "SIN_VERIFICAR", 0.0
    with _lock:
        # El audio CADUCA. Sin esto, la última frase que dijo Marco seguiría validando órdenes una
        # hora después — incluidas las que no vinieron de su voz. Un audio viejo no es prueba de
        # quién está mandando ahora, y aceptarlo convertiría la comprobación en teatro.
        audio = _audio_turno if (time.time() - _audio_en) <= CADUCIDAD_AUDIO else None
    if not audio:
        # Orden por texto o por Telegram: no hay voz que comprobar. No se bloquea por eso —
        # Telegram tiene su propia puerta (solo el chat autorizado de Marco).
        return "SIN_VERIFICAR", 0.0
    emb = embedding_de(audio)
    if emb is None:
        return "SIN_VERIFICAR", 0.0
    sim = _similitud(emb, _cargar_huella())
    if sim >= UMBRAL_OK:
        return "OK", sim
    if sim >= UMBRAL_DUDA:
        return "DUDA", sim
    return "RECHAZO", sim


def registrar_rechazo(nombre_tool, similitud):
    """Deja constancia y avisa al celular: si no fue Marco quien hablo, hay que enterarse aunque
    él no esté delante del PC."""
    texto = (f"Alguien intentó usar «{nombre_tool}» con una voz que no reconozco "
             f"(parecido {similitud:.0%}). No lo ejecuté.")
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(texto, "seguridad")
    except Exception:
        pass
    try:
        from Funciones_Slide.Comunicacion.Telegram_Control import avisar
        avisar("AIDEN — " + texto)
    except Exception:
        pass
    return texto
