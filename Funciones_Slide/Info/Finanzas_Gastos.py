# GASTOS vía BELVO: AIDEN lee tus transacciones REALES de Nequi + Nu a través del agregador Belvo y
# calcula cuánto gastas (mes/semana/hoy). Es la vía automática y ~100% (lee el historial del banco,
# no notificaciones que se pueden perder).
#
# CONFIGURACIÓN (en secretos.py) — tú lo llenas una vez:
#   BELVO_SECRET_ID       = "..."   # de tu panel Belvo (Secret Keys)
#   BELVO_SECRET_PASSWORD = "..."
#   BELVO_LINK            = "..."   # el 'link' que sale al enlazar Nequi/Nu con Belvo Connect
#   BELVO_BASE            = "https://sandbox.belvo.com"   # o https://api.belvo.com en producción
# Si falta algo, la herramienta te lo dice con claridad (no crashea).
#
# NOTA: si tienes DOS cuentas (Nequi y Nu) puede que necesites un link por banco; BELVO_LINK acepta
# una lista separada por comas ("linkNequi,linkNu") y AIDEN suma ambos.

import json
import os
import re
from datetime import date, datetime

try:
    import requests
except Exception:
    requests = None

# Registro MANUAL de gastos (lo que Marco le dice a AIDEN). 100% fiable, local, sin depender de nada.
_RUTA_MANUAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "gastos.json"
)

try:
    from secretos import BELVO_SECRET_ID, BELVO_SECRET_PASSWORD
except Exception:
    BELVO_SECRET_ID, BELVO_SECRET_PASSWORD = "", ""
try:
    from secretos import BELVO_LINK
except Exception:
    BELVO_LINK = ""
try:
    from secretos import BELVO_BASE
except Exception:
    BELVO_BASE = "https://sandbox.belvo.com"


def _configurado():
    return bool(BELVO_SECRET_ID and BELVO_SECRET_PASSWORD and BELVO_LINK)


# ── Registro MANUAL de gastos ─────────────────────────────────────────────────
def _parse_monto(v):
    # Acepta 20000, "20.000", "20 mil", "1.5 millones", "$30k". Devuelve float en COP o None.
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").lower().strip()
    if not s:
        return None
    mult = 1
    if "millon" in s or "milló" in s or "palo" in s:
        mult = 1_000_000
    elif "mil" in s or re.search(r"\bk\b", s):
        mult = 1000
    num = re.findall(r"[\d.,]+", s.replace(".", "").replace(",", "."))
    if not num:
        return None
    try:
        base = float(num[0])
    except ValueError:
        return None
    # Si ya venía con separador de miles grande (ej. "20.000" -> 20000) y no dijo "mil", no multiplicar.
    if mult == 1000 and base >= 1000:
        mult = 1
    return base * mult


def _cargar_manual():
    try:
        if os.path.exists(_RUTA_MANUAL):
            with open(_RUTA_MANUAL, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        pass
    return []


def _guardar_manual(datos):
    try:
        with open(_RUTA_MANUAL, "w", encoding="utf-8") as f:
            json.dump(datos[-2000:], f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def registrar_gasto(monto, concepto="", banco=""):
    """HERRAMIENTA: registra un gasto que Marco dice ('gasté 30 mil en el almuerzo'). monto puede ser
    número o texto ('30 mil'); concepto en qué; banco opcional (Nequi/Nu/efectivo)."""
    m = _parse_monto(monto)
    if not m or m <= 0:
        return "¿Cuánto gastó exactamente, señor?"
    datos = _cargar_manual()
    ahora = datetime.now()
    datos.append({
        "fecha": ahora.strftime("%d/%m/%Y"), "hora": ahora.strftime("%H:%M"),
        "monto": float(m), "concepto": str(concepto or "").strip(), "banco": str(banco or "").strip(),
    })
    _guardar_manual(datos)
    m_fmt = f"{int(m):,}".replace(",", ".")
    detalle = f" en {concepto}" if concepto else ""
    return f"Anotado, señor: {m_fmt}{detalle}. Se lo sumo a sus gastos."


def _manual_periodo(desde, hasta):
    # Suma y agrupa los gastos manuales en [desde, hasta] (fechas ISO).
    d0 = datetime.fromisoformat(desde).date()
    d1 = datetime.fromisoformat(hasta).date()
    total, n, por = 0.0, 0, {}
    for g in _cargar_manual():
        try:
            f = datetime.strptime(g.get("fecha", ""), "%d/%m/%Y").date()
        except ValueError:
            continue
        if d0 <= f <= d1:
            total += float(g.get("monto", 0) or 0)
            n += 1
            c = g.get("concepto") or "Otros"
            por[c] = por.get(c, 0) + float(g.get("monto", 0) or 0)
    return total, n, por


def _links():
    return [l.strip() for l in str(BELVO_LINK or "").split(",") if l.strip()]


def _fetch(link, desde, hasta):
    # Trae las transacciones de un link en el rango [desde, hasta]. Maneja paginación de Belvo.
    tx = []
    try:
        r = requests.post(
            BELVO_BASE.rstrip("/") + "/api/transactions/",
            auth=(BELVO_SECRET_ID, BELVO_SECRET_PASSWORD),
            json={"link": link, "date_from": desde, "date_to": hasta},
            timeout=45,
        )
        if r.status_code >= 400:
            return [], f"Belvo respondió {r.status_code}"
        data = r.json()
        # Belvo puede devolver una lista directa o {results, next}.
        if isinstance(data, list):
            return data, ""
        tx = data.get("results", []) or []
        siguiente = data.get("next")
        paginas = 0
        while siguiente and paginas < 20:
            rr = requests.get(siguiente, auth=(BELVO_SECRET_ID, BELVO_SECRET_PASSWORD), timeout=45)
            if rr.status_code >= 400:
                break
            d2 = rr.json()
            tx += d2.get("results", []) or []
            siguiente = d2.get("next")
            paginas += 1
        return tx, ""
    except Exception as e:
        return [], str(e)


def _rango(periodo):
    hoy = date.today()
    p = str(periodo or "mes").lower()
    if "hoy" in p or "dia" in p or "día" in p:
        return hoy.isoformat(), hoy.isoformat(), "hoy"
    if "seman" in p:
        desde = hoy.fromordinal(hoy.toordinal() - hoy.weekday())   # lunes de esta semana
        return desde.isoformat(), hoy.isoformat(), "esta semana"
    return hoy.replace(day=1).isoformat(), hoy.isoformat(), "este mes"


def resumen_gastos(periodo="mes"):
    """Suma tus gastos del periodo: los CAPTURADOS AUTOMÁTICAMENTE de las notificaciones de Nequi/Nu,
    (+ Belvo si algún día se configura). Devuelve un texto listo para hablar."""
    desde, hasta, etiqueta = _rango(periodo)
    total, n, por = _manual_periodo(desde, hasta)   # el registro local (auto-capturado por notis)
    moneda = "COP"

    # Si además hay Belvo configurado, súmalo.
    if _configurado() and requests is not None:
        for link in _links():
            tx, _err = _fetch(link, desde, hasta)
            for t in tx:
                if str(t.get("type", "")).upper() != "OUTFLOW":
                    continue
                monto = abs(float(t.get("amount", 0) or 0))
                total += monto
                n += 1
                moneda = t.get("currency", moneda)
                c = t.get("category") or "Otros"
                por[c] = por.get(c, 0) + monto

    if n == 0:
        return (f"No he capturado gastos {etiqueta}, señor. Si acaba de activarlo, verifique que "
                "'Vincular al teléfono' esté reenviando las notificaciones de Nequi y Nu al PC.")

    top = sorted(por.items(), key=lambda x: -x[1])[:3]
    detalle = "; ".join(f"{c}: {int(v):,}".replace(",", ".") for c, v in top if c)
    total_fmt = f"{int(total):,}".replace(",", ".")
    cola = f" Lo más fuerte: {detalle}." if detalle else ""
    # El dinero es de lo que peor se oye: "cuatrocientos treinta y dos mil ochocientos" no se
    # retiene. En pantalla, además, se ve de un vistazo en qué se fue.
    try:
        from Nucleo_Slide import HUD
        filas = [f"{c[:22]:<22} {int(v):>12,}".replace(",", ".")
                 for c, v in sorted(por.items(), key=lambda x: -x[1])[:6] if c]
        filas.append(f"{'TOTAL':<22} {int(total):>12,}".replace(",", ".") + f"  {moneda}")
        HUD.tarjeta(f"Gastos — {etiqueta}", filas, segundos=10)
    except Exception:
        pass
    return f"{etiqueta.capitalize()} lleva gastados {total_fmt} {moneda}, señor, en {n} movimientos.{cola}"


def mis_gastos(periodo="mes"):
    """HERRAMIENTA: cuánto ha gastado Marco (capturado auto de las notis de Nequi/Nu). periodo:
    'mes' (def), 'semana', 'hoy'."""
    return resumen_gastos(periodo)


# ── CAPTURA AUTOMÁTICA desde las notificaciones de Windows (Phone Link reenvía las del celu) ──────
# Marco NO ingresa nada: cada noti "Pagaste $X en Y" de Nequi/Nu se detecta y se registra sola.
import shutil
import sqlite3
import tempfile
import threading
import time
from datetime import datetime as _dt
from xml.etree import ElementTree

_WPN = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                    "Microsoft", "Windows", "Notifications", "wpndatabase.db")
_EPOCH_WIN = _dt(1601, 1, 1)
_ULTIMO_FT = None
_PAUSADO_G = False

_RX_MONTO = re.compile(r"\$\s?([\d][\d.,]*)")
_BANCO_KW = ("nequi", "nubank", "nu colombia", " de nu", "cuenta nu", "nu:", "banco nu")
_GASTO_KW = ("pagaste", "pago de", "pago por", "compra", "compraste", "retiraste", "retiro",
             "enviaste", "transferiste", "sacaste", "débito", "debito")
_INGRESO_KW = ("recibiste", "te enviaron", "te consignaron", "abono", "ingreso", "recibió", "recibio")


def pausar_vigilante_gastos(pausar=True):
    global _PAUSADO_G
    _PAUSADO_G = bool(pausar)


def _texto_payload(payload):
    if not payload:
        return ""
    try:
        if isinstance(payload, (bytes, bytearray)):
            payload = bytes(payload).decode("utf-8", "ignore")
        root = ElementTree.fromstring(payload)
        return " ".join(e.text.strip() for e in root.iter()
                        if e.tag.split("}")[-1] == "text" and e.text and e.text.strip())
    except Exception:
        return ""


def _con_bd():
    if not os.path.exists(_WPN):
        return None, None
    tmp = os.path.join(tempfile.gettempdir(), "aiden_wpn_gastos.db")
    try:
        shutil.copy2(_WPN, tmp)
        return sqlite3.connect(tmp), tmp
    except Exception:
        return None, None


def _max_arrival():
    con, tmp = _con_bd()
    if con is None:
        return 0
    try:
        cur = con.cursor()
        cur.execute("SELECT MAX(ArrivalTime) FROM Notification")
        f = cur.fetchone()
        return int(f[0]) if f and f[0] else 0
    except Exception:
        return 0
    finally:
        con.close()
        try:
            os.remove(tmp)
        except Exception:
            pass


def _leer_nuevas(desde_ft):
    con, tmp = _con_bd()
    if con is None:
        return []
    out = []
    try:
        cur = con.cursor()
        cur.execute("SELECT Payload, ArrivalTime FROM Notification WHERE ArrivalTime > ? "
                    "ORDER BY ArrivalTime ASC", (desde_ft,))
        for payload, arrival in cur.fetchall():
            out.append((_texto_payload(payload), int(arrival)))
    except Exception:
        pass
    finally:
        con.close()
        try:
            os.remove(tmp)
        except Exception:
            pass
    return out


def _es_gasto(texto):
    # Devuelve (monto, concepto) si el texto es un GASTO de Nequi/Nu; None si no.
    t = (texto or "").lower()
    if not any(b in t for b in _BANCO_KW):
        return None
    if any(k in t for k in _INGRESO_KW):
        return None
    if not any(k in t for k in _GASTO_KW):
        return None
    m = _RX_MONTO.search(texto)
    if not m:
        return None
    val = _parse_monto(m.group(1))
    if not val or val <= 0:
        return None
    concepto = ""
    mc = re.search(r"\ben\s+([A-Za-zÁÉÍÓÚÑñ0-9 &\-]{2,40})", texto)   # se corta en el primer '.'/','
    if mc:
        concepto = mc.group(1).strip(" .-")
    return val, concepto


def _revisar_gastos():
    global _ULTIMO_FT
    if _PAUSADO_G:
        return
    for texto, ft in _leer_nuevas(_ULTIMO_FT or 0):
        if _ULTIMO_FT is None or ft > _ULTIMO_FT:
            _ULTIMO_FT = ft
        g = _es_gasto(texto)
        if g:
            registrar_gasto(g[0], g[1], "Nequi/Nu")
            try:
                from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
                registrar_evento(f"Gasto capturado: {int(g[0]):,}".replace(",", ".")
                                 + (f" en {g[1]}" if g[1] else ""), "gastos")
            except Exception:
                pass


def iniciar_vigilante_gastos():
    # Captura gastos de las notificaciones de Windows en segundo plano (arcaico pero automático).
    def _bucle():
        global _ULTIMO_FT
        time.sleep(30)
        _ULTIMO_FT = _max_arrival()   # ignora las notis viejas de antes de arrancar
        while True:
            try:
                _revisar_gastos()
            except Exception:
                pass
            time.sleep(12)

    threading.Thread(target=_bucle, daemon=True).start()
