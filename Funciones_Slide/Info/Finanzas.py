import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

try:
    from secretos import PORTAFOLIO
except ImportError:
    PORTAFOLIO = {}

_ALIAS = {
    "ORO": "GC=F", "GOLD": "GC=F",
    "PLATA": "SI=F", "SILVER": "SI=F",
    "PETROLEO": "CL=F", "OIL": "CL=F",
    "BITCOIN": "BTC-USD", "BTC": "BTC-USD",
    "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
}

_REC = {
    "strong_buy": "compra fuerte",
    "buy": "compra",
    "hold": "mantener",
    "underperform": "rendimiento inferior",
    "sell": "venta",
    "strong_sell": "venta fuerte",
}

_WATCHLIST = ["NVDA", "CRWV", "ISRG", "PLTR", "MSTR"]


def consultar_accion(simbolo):
    simbolo = str(simbolo).strip().upper()
    simbolo = _ALIAS.get(simbolo, simbolo)
    try:
        t = yf.Ticker(simbolo)

        try:
            info = t.get_info() or {}
        except Exception:
            info = {}

        precio = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose")
        if precio is None:
            fi = t.fast_info
            precio = fi.get("lastPrice")
            prev = fi.get("previousClose")
        if precio is None:
            return f"No encontré datos de {simbolo}, señor."

        nombre = info.get("shortName") or simbolo
        moneda = info.get("currency") or "USD"

        cambio = info.get("regularMarketChange")
        cambio_pct = info.get("regularMarketChangePercent")
        if cambio is None and prev:
            cambio = precio - prev
            cambio_pct = (cambio / prev * 100) if prev else 0

        objetivo = info.get("targetMeanPrice")
        if objetivo is None:
            try:
                apt = t.analyst_price_targets
                if apt:
                    objetivo = apt.get("mean")
            except Exception:
                pass

        rec = info.get("recommendationKey")
        n_analistas = info.get("numberOfAnalystOpinions")

        partes = [f"{nombre} ({simbolo}): {precio:.2f} {moneda}"]

        if cambio is not None:
            verbo = "subió" if cambio >= 0 else "bajó"
            pct = f" ({abs(cambio_pct):.2f}%)" if cambio_pct is not None else ""
            partes.append(f"hoy {verbo} {abs(cambio):.2f}{pct}")

        if objetivo:
            falta = objetivo - precio
            if falta >= 0:
                partes.append(f"objetivo de analistas {objetivo:.2f}, le faltan {falta:.2f} para llegar")
            else:
                partes.append(f"objetivo de analistas {objetivo:.2f}, ya está {abs(falta):.2f} por encima")

        if rec:
            extra = f" segun {int(n_analistas)} analistas" if n_analistas else ""
            partes.append(f"recomendación: {_REC.get(rec, rec)}{extra}")

        pos = PORTAFOLIO.get(simbolo)
        if pos:
            acciones = pos["acciones"]
            compra = pos["precio_compra"]
            valor = acciones * precio
            pl = valor - acciones * compra
            pl_pct = (pl / (acciones * compra) * 100) if compra else 0
            verbo = "ganando" if pl >= 0 else "perdiendo"
            partes.append(
                f"tú tienes {acciones:.4f} acciones compradas a {compra:.2f}, "
                f"hoy valen {valor:.2f} ({verbo} {abs(pl):.2f}, {abs(pl_pct):.2f}%)"
            )

        return ". ".join(partes) + "."
    except Exception as e:
        return f"No pude consultar {simbolo}, señor: {e}"


def resumen_acciones():
    return "\n".join(consultar_accion(s) for s in _WATCHLIST)


def _precio_actual(simbolo):
    t = yf.Ticker(simbolo)
    try:
        p = t.fast_info.get("lastPrice")   # rapido: solo el precio, sin fundamentals
        if p:
            return p
    except Exception:
        pass
    try:
        info = t.get_info() or {}
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None


def mi_portafolio():
    if not PORTAFOLIO:
        return "No tienes un portafolio configurado, señor."
    simbolos = list(PORTAFOLIO.keys())
    # Pedimos todos los precios EN PARALELO (mucho mas rapido que uno por uno)
    with ThreadPoolExecutor(max_workers=max(1, len(simbolos))) as ex:
        precios = dict(zip(simbolos, ex.map(_precio_actual, simbolos)))

    lineas = []
    total_valor = 0.0
    total_costo = 0.0
    for simbolo in simbolos:
        pos = PORTAFOLIO[simbolo]
        precio = precios.get(simbolo)
        if precio is None:
            lineas.append(f"{simbolo}: no pude obtener el precio")
            continue
        acciones = pos["acciones"]
        compra = pos["precio_compra"]
        valor = acciones * precio
        costo = acciones * compra
        pl = valor - costo
        pl_pct = (pl / costo * 100) if costo else 0
        total_valor += valor
        total_costo += costo
        verbo = "ganas" if pl >= 0 else "pierdes"
        lineas.append(
            f"{simbolo}: {acciones:.4f} acciones a {precio:.2f}, valen {valor:.2f} USD "
            f"({verbo} {abs(pl):.2f}, {abs(pl_pct):.2f}%)"
        )
    total_pl = total_valor - total_costo
    total_pct = (total_pl / total_costo * 100) if total_costo else 0
    verbo = "ganando" if total_pl >= 0 else "perdiendo"
    lineas.append(
        f"TOTAL: invertiste {total_costo:.2f} USD, hoy vale {total_valor:.2f} USD, "
        f"{verbo} {abs(total_pl):.2f} ({abs(total_pct):.2f}%)"
    )
    # Además de decirlo, DEJARLO EN PANTALLA. Cinco cifras seguidas ("NVDA a ciento veintiocho con
    # cincuenta, más tres coma dos por ciento, AAPL a doscientos veinticuatro...") no hay forma de
    # retenerlas de oído: se olvidan antes de que termine la frase. Verlas sí sirve.
    # Se arma una versión CORTA para el cartel: en pantalla cabe poco y se lee de un vistazo.
    try:
        from Nucleo_Slide import HUD
        filas = []
        for simbolo in simbolos:
            p = precios.get(simbolo)
            if p is None:
                continue
            pos = PORTAFOLIO[simbolo]
            val = pos["acciones"] * p
            pct = ((p - pos["precio_compra"]) / pos["precio_compra"] * 100) if pos["precio_compra"] else 0
            filas.append(f"{simbolo:<6} ${p:,.2f}   {pct:+.1f}%   ({val:,.0f} USD)")
        if filas:
            filas.append(f"{'TOTAL':<6} ${total_valor:,.0f}   {total_pct:+.1f}%")
            HUD.tarjeta("Tu portafolio", filas, segundos=10)
    except Exception:
        pass          # el cartel es un extra: si falla, la respuesta hablada sigue intacta
    return "\n".join(lineas)


def mis_acciones(tipo="todo"):
    # Une el RESUMEN de mercado de la watchlist + el PORTAFOLIO (posiciones y ganancia/pérdida).
    # tipo: 'resumen' = solo mercado, 'portafolio' = solo tus posiciones, 'todo' = ambos (por defecto).
    t = str(tipo or "todo").lower()
    if "porta" in t:
        return mi_portafolio()
    if "resum" in t or "mercado" in t or "watch" in t:
        return resumen_acciones()
    return resumen_acciones() + "\n\n" + mi_portafolio()


def acciones(simbolo=""):
    """HERRAMIENTA unificada de bolsa. Con 'simbolo' (ej. NVDA, ORO, BTC) consulta ESA acción/activo;
    SIN símbolo, da el resumen de tu watchlist + tu portafolio. Reemplaza consultar_accion +
    mis_acciones sin perder nada."""
    s = str(simbolo or "").strip()
    if s and s.lower() not in ("todo", "todas", "mis acciones", "portafolio", "resumen"):
        return consultar_accion(s)
    return mis_acciones("todo" if not s else s)
