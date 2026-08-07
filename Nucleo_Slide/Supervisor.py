# EL QUE VIGILA QUE AIDEN SIGA EN PIE.
#
# Main_AlwaysOn corre con app.exec() para siempre y nadie lo mira. Si se cae por una excepción que
# no atrapó ningún try de herramienta, o si se CONGELA —un deadlock, una llamada bloqueante en el
# hilo de Qt—, no pasa nada: no hay reinicio, no hay aviso. Marco se entera cuando le habla y AIDEN
# no contesta, y le toca ir a correr el .bat.
#
# ── LO CONGELADO IMPORTA MÁS QUE LO MUERTO ───────────────────────────────────
# Un proceso Qt de larga duración se cuelga más veces de las que crashea limpio. Y colgado es PEOR:
# el proceso existe, el candado del puerto 50607 sigue tomado, el icono está en la bandeja... y no
# responde. Un supervisor que solo mirara si el proceso vive daría luz verde para siempre.
#
# Por eso el pulso lo escribe el HILO DE QT y no un hilo de fondo: si el bucle de eventos se atasca,
# el pulso se para SOLO. Un latido escrito desde un hilo aparte seguiría llegando con la interfaz
# muerta, y sería peor que no tenerlo, porque daría confianza.
#
# ── LOS DOS FALLOS QUE ESTO NO PUEDE COMETER ─────────────────────────────────
# 1. RELANZAR ALGO QUE MARCO CERRÓ. Si él dice "salir", relanzarlo es lo más molesto que podría
#    hacer AIDEN. Por eso `Salir()` deja una marca en disco antes de morir. El código de salida no
#    basta: vale 0 tanto en un cierre limpio como en un Qt que se apagó por su cuenta.
# 2. UN BUCLE DE REINICIOS. Si AIDEN se cae al arrancar (una dependencia rota, un import malo),
#    reintentar para siempre son cien procesos por minuto. Tres caídas en un minuto y se detiene,
#    avisando — que Marco lo vea es más útil que un bucle silencioso.

import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_PULSO = os.path.join(RAIZ, "heartbeat.txt")
RUTA_SALIDA = os.path.join(RAIZ, ".salida_limpia")

PULSO_MAX = 90           # s sin latir -> congelado (3 latidos perdidos, no uno: un pico de carga no cuenta)
ESPERA_RELANZAR = 2.0
MAX_CAIDAS = 3           # en...
VENTANA_CAIDAS = 60      # ...este rato. Más que eso no es mala suerte, es algo roto.
GRACIA_ARRANQUE = 120    # s que se le dan para cargar Whisper/Kokoro antes de exigirle pulso


def marcar_salida_limpia():
    """La llama Salir() justo antes de morir."""
    try:
        with open(RUTA_SALIDA, "w") as f:
            f.write(str(time.time()))
        return True
    except Exception:
        return False


def _hubo_salida_limpia():
    """Consume la marca: se lee UNA vez y se borra, para que no valga en el arranque siguiente."""
    try:
        if not os.path.exists(RUTA_SALIDA):
            return False
        os.remove(RUTA_SALIDA)
        return True
    except Exception:
        return False


def edad_pulso():
    """Segundos desde el último latido. Un número enorme si no hay archivo (aún no ha latido)."""
    try:
        with open(RUTA_PULSO) as f:
            return time.time() - float(f.read().strip())
    except Exception:
        return float("inf")


def _avisar(texto):
    """Por los dos canales, porque no se sabe dónde está Marco.

    El proyecto no tiene módulo de notificaciones nativas —se comprobó— así que aquí no se inventa
    uno: se usa el aviso al celular que YA existe (Telegram), que además es el único que le llega
    si no está en el PC, y un cuadro de Windows para cuando sí está delante. Ojo: el aviso corre en
    el proceso del SUPERVISOR, que es justamente el que sigue vivo cuando AIDEN no."""
    print(f"[supervisor] {texto}")
    llego = False
    try:
        from Funciones_Slide.Comunicacion.Telegram_Control import avisar
        avisar("AIDEN — " + texto)
        llego = True
    except Exception:
        pass
    try:
        import ctypes
        # MB_ICONWARNING | MB_SETFOREGROUND | MB_SYSTEMMODAL: que se vea aunque haya algo encima.
        ctypes.windll.user32.MessageBoxW(0, texto, "AIDEN", 0x30 | 0x10000 | 0x1000)
        llego = True
    except Exception:
        pass
    return llego


def _matar(proc):
    """El ÁRBOL entero, no solo el proceso. Un Chrome de Playwright o el PowerShell caliente
    sobreviven al padre: quedarían agarrando el perfil y la memoria, y el AIDEN nuevo arrancaría
    peleándose con los restos del viejo.

    Mismo patrón que `_matar_arbol` de Control_Total: psutil si está, y si no, la API de Windows —
    la caída a ctypes ya está escrita y probada en Freno_Duro, así que se usa esa en vez de una
    tercera copia."""
    try:
        import psutil
        for h in psutil.Process(proc.pid).children(recursive=True):
            try:
                h.kill()
            except Exception:
                pass
    except Exception:
        pass
    try:
        proc.kill()
        proc.wait(timeout=10)
    except Exception:
        pass


def _lanzar():
    # sys.executable: el MISMO intérprete que está corriendo esto. Así el supervisor hereda el
    # entorno virtual sin que nadie tenga que escribir su ruta en ningún sitio — que es justo lo
    # que hoy tiene AIDEN.bat, con una ruta de otra PC que aquí ya no existe.
    guion = os.path.join(RAIZ, "Main_AlwaysOn.py")
    try:
        os.remove(RUTA_PULSO)          # que el pulso viejo no cuente como el del proceso nuevo
    except OSError:
        pass
    return subprocess.Popen([sys.executable, guion], cwd=RAIZ)


def vigilar(lanzar=_lanzar, dormir=time.sleep, ahora=time.time):
    """El bucle. Los tres parámetros existen para poder PROBARLO sin arrancar AIDEN de verdad ni
    esperar noventa segundos reales."""
    caidas = []
    while True:
        proc = lanzar()
        arrancado = ahora()
        motivo = None

        while True:
            dormir(5)
            if proc.poll() is not None:
                motivo = "limpia" if _hubo_salida_limpia() else "caida"
                break
            # El pulso solo se exige pasada la gracia: arrancar carga Whisper y Kokoro, y en ese
            # rato el hilo de Qt todavía no late. Sin esto, el supervisor mataría a AIDEN cada vez
            # que arranca, para siempre.
            if ahora() - arrancado > GRACIA_ARRANQUE and edad_pulso() > PULSO_MAX:
                _avisar("AIDEN se congeló (sin pulso). Lo reinicio.")
                _matar(proc)
                motivo = "congelado"
                break

        if motivo == "limpia":
            print("[supervisor] AIDEN se cerró a propósito. No lo relanzo.")
            return "limpia"

        caidas = [t for t in caidas if ahora() - t < VENTANA_CAIDAS] + [ahora()]
        if len(caidas) >= MAX_CAIDAS:
            _avisar(f"AIDEN se cayó {len(caidas)} veces en menos de {VENTANA_CAIDAS}s. "
                    "Dejo de reintentar: hay algo roto que hay que mirar.")
            return "rendido"
        dormir(ESPERA_RELANZAR)


if __name__ == "__main__":
    # Candado propio, en OTRO puerto: el 50607 es de AIDEN y el supervisor no debe competir por él
    # ni quitárselo. Este solo evita dos supervisores.
    import socket
    _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock.bind(("127.0.0.1", 50608))
    except OSError:
        print("Ya hay un supervisor corriendo; cierro este.")
        sys.exit(0)
    print("[supervisor] vigilando AIDEN.")
    vigilar()
