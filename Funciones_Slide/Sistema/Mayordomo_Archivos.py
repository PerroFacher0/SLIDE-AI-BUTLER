# MAYORDOMO DE ARCHIVOS: la limpieza rutinaria del escritorio/Descargas la hace AIDEN, no Marco.
#
# Una vez al dia ordena lo obvio y SEGURO (nunca borra, solo MUEVE a subcarpetas): las capturas del
# escritorio a Escritorio/Capturas, y los instaladores viejos de Descargas a Descargas/Instaladores.
# Te avisa por el Vocero con lo que hizo. Es un habito SUYO, no una tarea tuya.

import os
import shutil
import threading
import time
from datetime import date

_USER = os.path.expanduser("~")
_ESCRITORIO = os.path.join(_USER, "Desktop")
_DESCARGAS = os.path.join(_USER, "Downloads")
_MARCA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".mayordomo_ultimo"
)
_hablar = None

_CAPTURAS = ("screenshot", "captura", "screen shot", "annotation", "recorte")
_INSTALADORES = (".exe", ".msi")


def _ya_corrio_hoy():
    try:
        with open(_MARCA, encoding="utf-8") as f:
            return f.read().strip() == date.today().isoformat()
    except Exception:
        return False


def _marcar_hoy():
    try:
        with open(_MARCA, "w", encoding="utf-8") as f:
            f.write(date.today().isoformat())
    except Exception:
        pass


def _mover_a(archivos, carpeta_destino):
    if not archivos:
        return 0
    os.makedirs(carpeta_destino, exist_ok=True)
    n = 0
    for ruta in archivos:
        try:
            destino = os.path.join(carpeta_destino, os.path.basename(ruta))
            if os.path.abspath(ruta) == os.path.abspath(destino):
                continue
            base, ext = os.path.splitext(destino)
            k = 1
            while os.path.exists(destino):        # no pisar si ya existe
                destino = f"{base}_{k}{ext}"
                k += 1
            shutil.move(ruta, destino)
            n += 1
        except Exception:
            continue
    return n


def ordenar_una_vez():
    # Devuelve un resumen corto de lo movido (o "" si no habia nada).
    hechos = []

    # Capturas del escritorio -> Escritorio/Capturas
    if os.path.isdir(_ESCRITORIO):
        caps = []
        for nombre in os.listdir(_ESCRITORIO):
            ruta = os.path.join(_ESCRITORIO, nombre)
            low = nombre.lower()
            if (os.path.isfile(ruta) and low.endswith((".png", ".jpg", ".jpeg"))
                    and any(k in low for k in _CAPTURAS)):
                caps.append(ruta)
        n = _mover_a(caps, os.path.join(_ESCRITORIO, "Capturas"))
        if n:
            hechos.append(f"{n} captura(s) a Escritorio\\Capturas")

    # Instaladores viejos (>7 dias) de Descargas -> Descargas/Instaladores
    if os.path.isdir(_DESCARGAS):
        insts = []
        limite = time.time() - 7 * 86400
        for nombre in os.listdir(_DESCARGAS):
            ruta = os.path.join(_DESCARGAS, nombre)
            if (os.path.isfile(ruta) and nombre.lower().endswith(_INSTALADORES)):
                try:
                    if os.path.getmtime(ruta) < limite:
                        insts.append(ruta)
                except Exception:
                    pass
        n = _mover_a(insts, os.path.join(_DESCARGAS, "Instaladores"))
        if n:
            hechos.append(f"{n} instalador(es) a Descargas\\Instaladores")

    return "; ".join(hechos)


def iniciar_mayordomo_archivos(hablar=None):
    global _hablar
    _hablar = hablar

    def _bucle():
        time.sleep(180)   # deja pasar el arranque
        while True:
            try:
                if not _ya_corrio_hoy():
                    resumen = ordenar_una_vez()
                    _marcar_hoy()
                    if resumen:
                        try:
                            from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
                            registrar_evento(f"Ordené archivos: {resumen}", "mayordomo")
                        except Exception:
                            pass
                        if _hablar:
                            try:
                                from Nucleo_Slide.Vocero import emitir
                                emitir(_hablar, f"Me tomé la libertad de ordenar, señor: {resumen}.",
                                       origen="mayordomo")
                            except Exception:
                                pass
            except Exception:
                pass
            time.sleep(3 * 3600)   # revisa cada 3h si ya toca el aseo del dia

    threading.Thread(target=_bucle, daemon=True).start()
