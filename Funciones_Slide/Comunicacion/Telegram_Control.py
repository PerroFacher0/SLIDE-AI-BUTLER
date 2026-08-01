# Control REMOTO de AIDEN desde el celular vía Telegram (sin librerias extra: usa requests).
# Marco le escribe a un bot de Telegram y AIDEN ejecuta la orden en el PC y le responde.
#
# SETUP (una vez): ver CONTROL_CELULAR.md. Resumen:
#   1. En Telegram, habla con @BotFather -> /newbot -> te da un TOKEN.
#   2. Pon ese token en secretos.py:  TELEGRAM_TOKEN = "123456:ABC..."
#   3. Escríbele algo al bot; AIDEN te responderá tu chat_id. Ponlo en secretos.py:
#         TELEGRAM_CHAT_ID = "tu_chat_id"
#   4. Reinicia AIDEN. Desde ahí, solo TÚ podrás controlarlo por Telegram.

import time
import threading
import requests

from Nucleo_Slide.Cerebro import procesar_remoto

try:
    from secretos import TELEGRAM_TOKEN
except ImportError:
    TELEGRAM_TOKEN = None
try:
    from secretos import TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_CHAT_ID = None

_API = "https://api.telegram.org/bot{token}/{metodo}"

# Credenciales vivas (las fija iniciar_telegram) para poder ESCRIBIRLE a Marco sin que él haya
# preguntado nada. Antes el bot solo sabía RESPONDER: una misión de 20 minutos terminaba y Marco
# se enteraba únicamente si estaba frente al PC para oírlo.
_token_vivo = None
_chat_vivo = None

# Un "turno de palabra": cuando AIDEN necesita que Marco le conteste algo (un código 2FA, un sí/no),
# reserva este canal y el siguiente mensaje que llegue va a él en vez de tratarse como una orden.
_espera = {"activa": False, "evento": threading.Event(), "respuesta": None}
_lock_espera = threading.Lock()


def _enviar(token, chat_id, texto):
    try:
        requests.post(
            _API.format(token=token, metodo="sendMessage"),
            json={"chat_id": chat_id, "text": texto},
            timeout=15,
        )
    except Exception as e:
        print(f"[Telegram] no pude enviar: {e}")


def _bucle(token, chat_autorizado):
    offset = None
    if chat_autorizado:
        _enviar(token, chat_autorizado, "AIDEN en línea, señor. Listo para recibir órdenes.")

    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(
                _API.format(token=token, metodo="getUpdates"),
                params=params, timeout=40,
            )
            data = r.json()

            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = str(msg.get("chat", {}).get("id"))
                texto = (msg.get("text") or "").strip()
                if not texto:
                    continue

                # SEGURIDAD: si aun no hay chat autorizado, dile su id y NO ejecutes nada.
                if not chat_autorizado:
                    _enviar(token, chat_id,
                            f"Tu chat_id es {chat_id}. Ponlo en secretos.py como "
                            f"TELEGRAM_CHAT_ID = \"{chat_id}\" y reinicia AIDEN para autorizarte, señor.")
                    continue
                # Solo responde al chat de Marco; a desconocidos los ignora.
                if chat_id != str(chat_autorizado):
                    continue

                # ¿AIDEN está esperando que Marco le conteste algo? Entonces este mensaje ES la
                # respuesta (el código 2FA, un sí/no), no una orden nueva que ejecutar.
                with _lock_espera:
                    esperando = _espera["activa"]
                    if esperando:
                        _espera["respuesta"] = texto
                        _espera["activa"] = False
                if esperando:
                    _espera["evento"].set()
                    _enviar(token, chat_id, "Recibido, señor. Sigo.")
                    continue

                try:
                    respuesta = procesar_remoto(texto)
                except Exception as e:
                    respuesta = f"Tuve un problema procesando eso, señor: {e}"
                _enviar(token, chat_id, respuesta)

        except Exception as e:
            print(f"[Telegram] error en el bucle: {e}")
            time.sleep(5)   # error de red: espera y reintenta


def hay_celular():
    """True si el puente con el celular está configurado y operativo."""
    return bool(_token_vivo and _chat_vivo)


def avisar(texto):
    """Le ESCRIBE a Marco al celular sin que él haya preguntado nada. Para avances de una misión
    larga, un aviso importante, o el resultado de algo que terminó mientras no estaba."""
    if not hay_celular():
        return False
    _enviar(_token_vivo, _chat_vivo, str(texto or "").strip()[:3500])
    return True


def preguntar(pregunta, timeout=180):
    """Le pregunta algo a Marco AL CELULAR y espera su respuesta (hasta 'timeout' segundos).
    Devuelve el texto que contestó, o None si no contestó a tiempo.

    Para lo que AIDEN no puede resolver solo aunque tenga todas las manos del mundo: un código 2FA
    que llega al teléfono, o una confirmación que no debe inventarse. Antes, el navegador agéntico
    se estrellaba contra esa pared y ahí moría la tarea."""
    if not hay_celular():
        return None
    with _lock_espera:
        if _espera["activa"]:
            return None                      # ya hay otra pregunta en curso; no las encimamos
        _espera["activa"] = True
        _espera["respuesta"] = None
        _espera["evento"].clear()

    _enviar(_token_vivo, _chat_vivo, str(pregunta or "").strip()[:3500])
    llego = _espera["evento"].wait(timeout=max(5, int(timeout)))

    with _lock_espera:
        _espera["activa"] = False
        respuesta = _espera["respuesta"]
    if not llego:
        _enviar(_token_vivo, _chat_vivo, "Se me agotó la espera, señor. Sigo sin eso.")
        return None
    return respuesta


def avisar_al_celular(mensaje):
    """HERRAMIENTA: le manda un mensaje al celular de Marco por Telegram. Úsala cuando termine algo
    largo que él pidió, o cuando pase algo que deba saber y no esté frente al PC."""
    if not hay_celular():
        return "No tengo el puente con su celular configurado, señor (falta el token de Telegram)."
    return ("Le escribí al celular, señor." if avisar(mensaje)
            else "No pude enviarle el mensaje al celular, señor.")


def iniciar_telegram():
    # Arranca el control remoto por Telegram en un hilo de fondo, si hay token.
    global _token_vivo, _chat_vivo
    if not TELEGRAM_TOKEN:
        print("[Telegram] sin TELEGRAM_TOKEN en secretos.py — control remoto desactivado.")
        return False
    _token_vivo, _chat_vivo = TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    hilo = threading.Thread(target=_bucle, args=(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID), daemon=True)
    hilo.start()
    print("[Telegram] control remoto activo.")
    return True
