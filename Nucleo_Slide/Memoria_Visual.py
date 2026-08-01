# MEMORIA VISUAL RETROACTIVA: poder preguntar "¿qué decía en pantalla hace diez minutos?".
#
# El caso real: se cerró un error antes de leerlo, pasó un dato en una reunión, había una cifra en
# una tabla que ya no está. AIDEN veía la pantalla solo cuando se le pedía; lo de hace un rato se
# perdía para siempre. Esto le da un pasado visual sobre el que se puede buscar por TEXTO, usando
# el índice de texto completo de SQLite (FTS5).
#
# ─────────────────────────────────────────────────────────────────────────────
# ESTO ES SENSIBLE Y ESTÁ TRATADO COMO TAL. Grabar lo que pasa por la pantalla es grabar TODO:
# contraseñas, banca, conversaciones privadas. Por eso, por diseño y no como opción escondida:
#   1. Nace APAGADA. Marco tiene que encenderla a propósito ("activa la memoria visual").
#   2. Guarda TEXTO, nunca imágenes. No hay álbum de capturas que se pueda filtrar.
#   3. Lista de EXCLUSIÓN: bancos, gestores de contraseñas y ventanas de incógnito no se tocan —
#      ni el título se guarda. Si la ventana activa es una de esas, esa ronda se salta entera.
#   4. Se OLVIDA sola: por defecto solo conserva 24 horas, y purga en cada ronda.
#   5. Se pausa en modo gaming/reunión, como los demás vigilantes.
#   6. El OCR es LOCAL: nada de esto sale del PC ni se le manda a ningún modelo en la nube.
# ─────────────────────────────────────────────────────────────────────────────
#
# El OCR local se resuelve con lo que haya, en este orden: el motor de Windows (winsdk, gratis y ya
# viene con el sistema) -> Tesseract -> ninguno. Sin motor NO se apaga: sigue registrando qué
# aplicación y qué ventana estuvieron activas, que ya responde "¿en qué andaba yo a las 3?".

import json
import os
import re
import sqlite3
import threading
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BD = os.path.join(_RAIZ, "memoria_visual.db")
_CONF = os.path.join(_RAIZ, "memoria_visual.json")

INTERVALO = 45          # seg entre miradas (barato: solo si la pantalla cambió de verdad)
RETENCION_H = 24        # horas que se conserva; más viejo que eso, se borra solo
_MIN_TEXTO = 12         # menos caracteres que esto no vale la pena guardar

# Ventanas que NO se miran jamás. Se comparan en minúsculas contra el título y el proceso.
_EXCLUIDAS = (
    "bancolombia", "nequi", "davivienda", "bbva", "banco", "nubank", "nu colombia",
    "paypal", "binance", "coinbase", "1password", "bitwarden", "keepass", "lastpass",
    "dashlane", "incognito", "incógnito", "privada", "inprivate", "private browsing",
    "contraseña", "password", "administrador de credenciales", "credential manager",
)

_pausado = False
_activa = False
_hilo = None
_lock = threading.RLock()
_motor_ocr = None       # "windows" | "tesseract" | None (se resuelve una sola vez)


# ── Configuración persistente ────────────────────────────────────────────────
def _cargar_conf():
    try:
        if os.path.exists(_CONF):
            with open(_CONF, encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _guardar_conf(d):
    try:
        with open(_CONF, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ── Base de datos ────────────────────────────────────────────────────────────
def _conectar():
    con = sqlite3.connect(_BD, timeout=10)
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS pantallazos "
                "USING fts5(app, titulo, texto, t UNINDEXED)")
    return con


def _purgar(con):
    limite = time.time() - RETENCION_H * 3600
    try:
        con.execute("DELETE FROM pantallazos WHERE CAST(t AS REAL) < ?", (limite,))
        con.commit()
    except Exception:
        pass


# ── OCR local ────────────────────────────────────────────────────────────────
def _elegir_motor():
    global _motor_ocr
    if _motor_ocr is not None:
        return _motor_ocr
    try:
        import winsdk.windows.media.ocr  # noqa: F401
        _motor_ocr = "windows"
        return _motor_ocr
    except Exception:
        pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _motor_ocr = "tesseract"
        return _motor_ocr
    except Exception:
        pass
    _motor_ocr = "ninguno"
    return _motor_ocr


def _ocr_windows(img):
    # Motor de OCR que ya trae Windows: local, gratis y sin binarios extra.
    import asyncio
    import io
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.graphics.imaging import BitmapDecoder
    from winsdk.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

    async def _leer():
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        flujo = InMemoryRandomAccessStream()
        escritor = DataWriter(flujo.get_output_stream_at(0))
        escritor.write_bytes(buf.getvalue())
        await escritor.store_async()
        decodificador = await BitmapDecoder.create_async(flujo)
        mapa = await decodificador.get_software_bitmap_async()
        motor = OcrEngine.try_create_from_user_profile_languages()
        if motor is None:
            return ""
        resultado = await motor.recognize_async(mapa)
        return resultado.text or ""

    return asyncio.run(_leer())


def _extraer_texto(img):
    motor = _elegir_motor()
    try:
        if motor == "windows":
            return _ocr_windows(img)
        if motor == "tesseract":
            import pytesseract
            return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        return ""
    return ""


# ── Captura ──────────────────────────────────────────────────────────────────
def _ventana_activa():
    try:
        import win32gui
        import win32process
        h = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(h) or ""
        app = ""
        try:
            import psutil
            _, pid = win32process.GetWindowThreadProcessId(h)
            app = psutil.Process(pid).name()
        except Exception:
            pass
        return app, titulo
    except Exception:
        return "", ""


def _prohibida(app, titulo):
    objetivo = f"{app} {titulo}".lower()
    return any(p in objetivo for p in _EXCLUIDAS)


def _huella(img):
    """Firma barata de la pantalla: si no cambió, no vale la pena volver a leerla."""
    try:
        chica = img.convert("L").resize((32, 32))
        return list(chica.getdata())
    except Exception:
        return None


def _muy_parecidas(a, b):
    if not a or not b or len(a) != len(b):
        return False
    dif = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return dif < 4.0       # prácticamente la misma imagen


def _bucle():
    ultima_huella = None
    while True:
        time.sleep(INTERVALO)
        try:
            if not _activa or _pausado:
                continue
            app, titulo = _ventana_activa()
            if _prohibida(app, titulo):
                continue                     # ni el título se guarda
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
            except Exception:
                continue
            huella = _huella(img)
            if _muy_parecidas(huella, ultima_huella):
                continue                     # nada cambió: no ensuciamos la base
            ultima_huella = huella

            texto = " ".join((_extraer_texto(img) or "").split())
            if len(texto) < _MIN_TEXTO and not titulo:
                continue
            with _lock:
                con = _conectar()
                con.execute("INSERT INTO pantallazos (app, titulo, texto, t) VALUES (?,?,?,?)",
                            (app, titulo, texto[:12000], str(time.time())))
                con.commit()
                _purgar(con)
                con.close()
        except Exception:
            continue


def pausar_memoria_visual(pausar=True):
    # Silencia la captura (lo usa el modo gaming / reunión).
    global _pausado
    _pausado = bool(pausar)


def iniciar_memoria_visual():
    """Arranca el hilo. Solo captura de verdad si Marco la dejó activada."""
    global _hilo, _activa
    _activa = bool(_cargar_conf().get("activa", False))
    if _hilo is None:
        _hilo = threading.Thread(target=_bucle, daemon=True)
        _hilo.start()
    print(f"[MemoriaVisual] {'ACTIVA' if _activa else 'apagada'} (OCR: {_elegir_motor()})")
    return True


# ── Consulta ─────────────────────────────────────────────────────────────────
def _limpiar_consulta(c):
    """FTS5 se atraganta con signos sueltos; se deja solo palabras y se piden todas."""
    palabras = re.findall(r"\w+", str(c or ""), re.UNICODE)
    return " AND ".join(f'"{p}"' for p in palabras if len(p) > 1)


def _hace_cuanto(t):
    seg = max(0, time.time() - float(t))
    if seg < 90:
        return "hace un momento"
    if seg < 3600:
        return f"hace {int(seg // 60)} minutos"
    return f"hace {seg / 3600:.1f} horas"


def memoria_visual(accion="buscar", consulta="", minutos=0):
    """HERRAMIENTA: el pasado VISUAL de la pantalla de Marco. Permite responder '¿qué decía la
    pantalla hace 10 minutos?', '¿cuál era ese error que se cerró?', '¿en qué estaba yo a las 3?'.
      accion  = buscar | activar | desactivar | estado | olvidar
      consulta= qué texto buscar (para 'buscar')
      minutos = hace cuántos minutos mirar (para 'buscar' sin texto)."""
    global _activa
    a = str(accion or "").strip().lower()

    if a.startswith("activ") or a.startswith("encend") or a.startswith("prend"):
        conf = _cargar_conf()
        conf["activa"] = True
        _guardar_conf(conf)
        _activa = True
        motor = _elegir_motor()
        if motor == "ninguno":
            return ("Memoria visual ACTIVADA, señor, pero sin motor de lectura: solo registraré qué "
                    "aplicación y qué ventana estuvieron activas, no lo que decían. Para leer el "
                    "texto en la pantalla instale el motor local con: pip install winsdk")
        return (f"Memoria visual ACTIVADA, señor. Leo la pantalla cada {INTERVALO} segundos con el "
                f"motor local ({motor}), guardo solo texto, conservo {RETENCION_H} horas y salto "
                "bancos, gestores de contraseñas y ventanas de incógnito.")

    if a.startswith("desactiv") or a.startswith("apag"):
        conf = _cargar_conf()
        conf["activa"] = False
        _guardar_conf(conf)
        _activa = False
        return "Memoria visual apagada, señor. Dejo de mirar la pantalla."

    if a.startswith("olvid") or a.startswith("borr"):
        try:
            with _lock:
                con = _conectar()
                con.execute("DELETE FROM pantallazos")
                con.commit()
                con.close()
            return "Borré toda la memoria visual, señor. No queda nada de lo que hubo en pantalla."
        except Exception as e:
            return f"No pude borrar la memoria visual, señor: {e}"

    if a.startswith("estad"):
        try:
            with _lock:
                con = _conectar()
                n = con.execute("SELECT COUNT(*) FROM pantallazos").fetchone()[0]
                con.close()
        except Exception:
            n = 0
        return (f"Memoria visual: {'activa' if _activa else 'apagada'}, señor. "
                f"Motor de lectura: {_elegir_motor()}. Tengo {n} instantáneas de las últimas "
                f"{RETENCION_H} horas.")

    # ── buscar ──
    if not _activa:
        return ("La memoria visual está apagada, señor, así que no tengo registro de lo que hubo en "
                "pantalla. Puede encenderla diciéndome 'activa la memoria visual'.")
    try:
        mins = int(minutos or 0)
    except (TypeError, ValueError):
        mins = 0

    try:
        with _lock:
            con = _conectar()
            texto_fts = _limpiar_consulta(consulta)
            if texto_fts:
                filas = con.execute(
                    "SELECT app, titulo, texto, t FROM pantallazos WHERE pantallazos MATCH ? "
                    "ORDER BY CAST(t AS REAL) DESC LIMIT 6", (texto_fts,)).fetchall()
            elif mins > 0:
                desde, hasta = time.time() - mins * 60 - 150, time.time() - mins * 60 + 150
                filas = con.execute(
                    "SELECT app, titulo, texto, t FROM pantallazos "
                    "WHERE CAST(t AS REAL) BETWEEN ? AND ? ORDER BY CAST(t AS REAL) DESC LIMIT 4",
                    (desde, hasta)).fetchall()
            else:
                filas = con.execute(
                    "SELECT app, titulo, texto, t FROM pantallazos "
                    "ORDER BY CAST(t AS REAL) DESC LIMIT 4").fetchall()
            con.close()
    except Exception as e:
        return f"No pude consultar la memoria visual, señor: {e}"

    if not filas:
        if consulta:
            return f"No encontré «{consulta}» en lo que pasó por su pantalla, señor."
        return "No tengo nada registrado de ese momento, señor."

    trozos = []
    for app, titulo, texto, t in filas:
        cabeza = f"[{_hace_cuanto(t)}"
        if titulo:
            cabeza += f", en {titulo[:60]}"
        elif app:
            cabeza += f", en {app}"
        cabeza += "]"
        trozos.append(f"{cabeza} {texto[:600]}" if texto else f"{cabeza} (sin texto legible)")
    return "Esto había en su pantalla, señor:\n" + "\n\n".join(trozos)
