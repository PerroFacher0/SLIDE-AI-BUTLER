# Noticias del dia (titulares recientes con fecha), via DuckDuckGo News (sin API key).
# Distinto de buscar_en_internet: esto trae TITULARES recientes y fechados, no una
# busqueda generica. Ideal para "que noticias hay hoy" o noticias de un tema/pais.


def noticias_del_dia(tema=None):
    """Devuelve los titulares de noticias mas recientes.

    tema: tema opcional (ej. 'tecnologia', 'Colombia', 'futbol'). Si no se da,
    trae titulares generales de Colombia. Devuelve texto para que el LLM lo lea.
    """
    from ddgs import DDGS

    consulta = (tema or "Colombia noticias").strip()
    try:
        with DDGS() as buscador:
            resultados = list(
                buscador.news(consulta, region="co-es", max_results=6)
            )
    except Exception as e:
        return f"No pude traer las noticias, señor: {e}"

    if not resultados:
        return f"No encontré noticias sobre '{consulta}', señor."

    partes = []
    for r in resultados:
        titulo = (r.get("title", "") or "").strip()
        fuente = (r.get("source", "") or "").strip()
        cuerpo = (r.get("body", "") or "").strip()[:160]
        fecha = (r.get("date", "") or "")[:10]
        linea = f"- {titulo}"
        if fuente:
            linea += f" ({fuente}"
            linea += f", {fecha})" if fecha else ")"
        if cuerpo:
            linea += f": {cuerpo}"
        partes.append(linea)

    encabezado = f"Titulares sobre {consulta}:" if tema else "Titulares de hoy:"
    # En el cartel van SOLO los titulares, sin el resumen de cada noticia: en pantalla se ojean los
    # seis de un vistazo y ahí se decide cuál interesa. El detalle ya lo dice la voz.
    try:
        from Nucleo_Slide import HUD
        titulares = [f"· {(r.get('title') or '').strip()[:70]}" for r in resultados
                     if (r.get("title") or "").strip()]
        if titulares:
            HUD.tarjeta(encabezado.rstrip(":"), titulares, segundos=10)
    except Exception:
        pass
    return encabezado + "\n" + "\n".join(partes)
