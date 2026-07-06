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

from datetime import date

try:
    import requests
except Exception:
    requests = None

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
    """Suma tus gastos (OUTFLOW) del periodo vía Belvo. Devuelve un texto listo para hablar."""
    if requests is None:
        return "No tengo el módulo de red disponible, señor (falta 'requests')."
    if not _configurado():
        return ("Aún no he conectado sus cuentas, señor. Configure BELVO_SECRET_ID, "
                "BELVO_SECRET_PASSWORD y BELVO_LINK en secretos.py (tras enlazar Nequi y Nu en Belvo).")

    desde, hasta, etiqueta = _rango(periodo)
    total = 0.0
    n = 0
    por_categoria = {}
    moneda = "COP"
    errores = []
    for link in _links():
        tx, err = _fetch(link, desde, hasta)
        if err:
            errores.append(err)
        for t in tx:
            if str(t.get("type", "")).upper() != "OUTFLOW":   # solo gastos (salidas)
                continue
            monto = abs(float(t.get("amount", 0) or 0))
            total += monto
            n += 1
            moneda = t.get("currency", moneda)
            cat = t.get("category") or "Otros"
            por_categoria[cat] = por_categoria.get(cat, 0) + monto

    if n == 0 and errores:
        return f"No pude leer sus gastos, señor: {errores[0]}"
    if n == 0:
        return f"No registro gastos {etiqueta}, señor."

    top = sorted(por_categoria.items(), key=lambda x: -x[1])[:3]
    detalle = "; ".join(f"{c}: {int(v):,}".replace(",", ".") for c, v in top)
    total_fmt = f"{int(total):,}".replace(",", ".")
    return (f"{etiqueta.capitalize()} lleva gastados {total_fmt} {moneda}, señor, en {n} movimientos. "
            f"Lo más fuerte: {detalle}.")


def mis_gastos(periodo="mes"):
    """HERRAMIENTA: cuánto ha gastado Marco (por Nequi/Nu vía Belvo). periodo: 'mes' (def), 'semana', 'hoy'."""
    return resumen_gastos(periodo)
