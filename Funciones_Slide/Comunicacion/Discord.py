# DISCORD: AIDEN manda mensajes por Discord por voz, COMO Marco (no como un bot).
#
# Mismo espíritu que el WhatsApp de AIDEN: automatiza la app real. Abre/enfoca Discord, usa el
# buscador rápido (Ctrl+K) para saltar al DM o canal, y pega el mensaje (por PORTAPAPELES, para que
# funcionen tildes, ñ y emojis — typewrite de pyautogui los rompe). Luego Enter para enviar.

import os
import time

import pyautogui

try:
    import pyperclip
except Exception:
    pyperclip = None


def _abrir_discord():
    try:
        os.startfile("discord://")          # el protocolo abre/enfoca Discord si está instalado
        return True
    except Exception:
        try:
            import subprocess
            subprocess.Popen(["cmd", "/c", "start", "", "discord://"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False


def _escribir(texto):
    # Pega el texto (soporta cualquier carácter); si no hay portapapeles, cae a typewrite.
    if pyperclip is not None:
        try:
            pyperclip.copy(texto)
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "v")
            return
        except Exception:
            pass
    pyautogui.typewrite(texto, interval=0.02)


def Enviar_mensaje_Discord(destino, mensaje):
    """HERRAMIENTA: envía un mensaje de Discord al DM o canal 'destino' (nombre de la persona o del
    canal/servidor). Úsala cuando Marco diga 'mándale a X por Discord...', 'escríbele a X en Discord'."""
    destino = str(destino or "").strip()
    mensaje = str(mensaje or "").strip()
    if not destino or not mensaje:
        return "Necesito a quién y qué mensaje, señor."
    if not _abrir_discord():
        return "No pude abrir Discord, señor. ¿Está instalado?"
    try:
        time.sleep(4)                        # deja que Discord tome el foco
        pyautogui.hotkey("ctrl", "k")        # buscador rápido (saltar a DM/canal)
        time.sleep(1.2)
        _escribir(destino)
        time.sleep(1.6)                      # deja que aparezca el resultado
        pyautogui.press("enter")             # entra al chat de 'destino'
        time.sleep(1.6)
        _escribir(mensaje)
        time.sleep(0.4)
        pyautogui.press("enter")             # envía
        return f"Mensaje enviado a {destino} por Discord, señor."
    except Exception as e:
        return f"Abrí Discord pero no pude completar el envío, señor: {e}"
