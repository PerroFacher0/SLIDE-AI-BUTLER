# NAVEGADOR WEB AGÉNTICO: la "llave maestra" de AIDEN para internet — el mismo papel que
# ejecutar_en_pc cumple para Windows. Un navegador REAL (Playwright/Chromium, VISIBLE, con sesión
# persistente) que AIDEN opera con el MISMO patrón ya probado en el escritorio:
#
#   1. Ubica cada elemento de forma SEMÁNTICA primero (rol/nombre/texto accesible de Playwright —
#      instantáneo, sin IA, y sobrevive a que la página cambie de diseño mañana).
#   2. Si la página no expone eso (un diseño raro, contenido en canvas), cae a VISIÓN — el MISMO
#      formato box_2d de Gemini que ya se probó y funciona en Control_Pantalla.py (ver
#      Nucleo_Slide/Vision_Grounding.py), apuntado ahora al viewport del navegador.
#
# Piezas propias de la web:
#   - Sesión PERSISTENTE (perfil en disco): cookies/logins sobreviven entre usos.
#   - Cierre de pop-ups/cookies SOLO (patrones conocidos + respaldo visual).
#   - "Explorar y resumir": scrollea sola, junta lo que va viendo, lo sintetiza con el LLM.
#   - FRENO DE SEGURIDAD innegociable: jamás confirma un pago/pedido final sin que Marco lo apruebe
#     por voz explícitamente — se detecta la pantalla de checkout y AHÍ SE DETIENE, siempre.
#
# navegar_web(objetivo) es la única tool que ve el LLM principal (respeta "no más tools"): por
# dentro corre su PROPIO mini-agente con un puñado de acciones de navegación — mucho más barato y
# rápido que arrastrar el esquema de las 61 herramientas completas en cada paso de scroll.

import json
import os
import re
import threading
import time

_lock = threading.RLock()
_pw = None
_contexto = None
_page = None

_PERFIL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "perfil_navegador_aiden",
)
MAX_PASOS = 20            # tope duro del mini-agente (como Agente.MAX_PASOS)
MAX_SCROLLS = 8           # tope de "explorar y resumir"
TIMEOUT_ACCION = 8000     # ms: no esperar eternamente un elemento que no aparece


# ── Ciclo de vida del navegador ───────────────────────────────────────────────
def _asegurar_navegador():
    global _pw, _contexto, _page
    with _lock:
        if _page is not None:
            try:
                _page.title()   # si la página murió (la cerraron a mano), esto lanza excepción
                return _page
            except Exception:
                _pw = _contexto = _page = None
        from playwright.sync_api import sync_playwright
        os.makedirs(_PERFIL, exist_ok=True)
        _pw = sync_playwright().start()
        # Perfil PERSISTENTE: las cookies/logins de Marco sobreviven entre sesiones. VISIBLE
        # (headless=False) — el principio de todo AIDEN: si actúa, Marco lo VE.
        #
        # channel="chrome": usa el Chrome REAL instalado (el mismo binario que Marco ya usa a
        # diario), NO el Chromium suelto que trae Playwright. Un sitio que huella el navegador
        # (Cloudflare, Datadome) ve un Chrome genuino con su firma real — no estamos disfrazando
        # nada, LO ES. Deliberadamente NO se usa playwright-stealth (parchar el fingerprint para
        # simular ser humano): eso sí es evasión activa de un sistema de seguridad. Si Chrome no
        # está instalado, cae al Chromium de Playwright para no dejar a Marco sin navegador.
        try:
            _contexto = _pw.chromium.launch_persistent_context(
                _PERFIL, headless=False, viewport={"width": 1280, "height": 800},
                args=["--start-maximized"], channel="chrome",
            )
        except Exception:
            _contexto = _pw.chromium.launch_persistent_context(
                _PERFIL, headless=False, viewport={"width": 1280, "height": 800},
                args=["--start-maximized"],
            )
        _page = _contexto.pages[0] if _contexto.pages else _contexto.new_page()
        return _page


def cerrar_navegador():
    """HERRAMIENTA: cierra el navegador de AIDEN (no toca tus otras ventanas de Chrome/Edge)."""
    global _pw, _contexto, _page
    with _lock:
        try:
            if _contexto:
                _contexto.close()
            if _pw:
                _pw.stop()
        except Exception:
            pass
        _pw = _contexto = _page = None
    return "Navegador cerrado, señor."


# ── Cierre de pop-ups / cookies (patrones conocidos + respaldo visual) ────────
_TEXTOS_ACEPTAR = re.compile(
    r"^(aceptar( todo| todas|)|accept( all|)|i accept|entendido|de acuerdo|ok|got it|"
    r"continuar|allow all|permitir todo)$", re.I,
)
_SELECTORES_COOKIES = (
    "#onetrust-accept-btn-handler",       # OneTrust (muy común)
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",   # Cookiebot
    "#cookiescript_accept",               # CookieScript
    ".cookie-consent-accept", ".cc-accept", ".cc-allow",
    "[aria-label*='cookie' i] button", "[id*='cookie' i] button[class*='accept' i]",
)


def cerrar_popups():
    """HERRAMIENTA: cierra pop-ups de cookies/publicidad/modales que estén tapando la página. Se
    llama sola tras navegar, pero también puedes pedirla directo si algo sigue estorbando."""
    page = _asegurar_navegador()
    cerrados = 0
    # 1) Selectores conocidos de las librerías de consentimiento más comunes.
    for sel in _SELECTORES_COOKIES:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=400):
                loc.click(timeout=1500)
                cerrados += 1
                page.wait_for_timeout(250)
        except Exception:
            continue
    # 2) Genérico: cualquier botón visible cuyo texto sea "Aceptar/Accept/..." dentro de un
    #    diálogo/banner (evita clicar un "Aceptar" que esté dentro del contenido normal).
    try:
        for loc in page.get_by_role("button").all()[:40]:
            try:
                txt = (loc.inner_text(timeout=200) or "").strip()
                if _TEXTOS_ACEPTAR.match(txt) and loc.is_visible(timeout=150):
                    loc.click(timeout=1200)
                    cerrados += 1
                    page.wait_for_timeout(250)
            except Exception:
                continue
    except Exception:
        pass
    # 3) Genérico: botones de CERRAR (X) en diálogos modales.
    try:
        cerrar_btn = page.get_by_role(
            "button", name=re.compile("cerrar|close|✕|×", re.I)
        ).first
        if cerrar_btn.is_visible(timeout=400):
            cerrar_btn.click(timeout=1200)
            cerrados += 1
    except Exception:
        pass
    # 4) Respaldo VISUAL: si sigue habiendo un modal/overlay visible cubriendo buena parte de la
    #    pantalla, busca una "X" de cerrar por visión (mismo mecanismo que el escritorio).
    if _hay_overlay_bloqueando(page):
        xy = _localizar_visual(page, "el botón X o 'cerrar' de la ventana emergente/modal")
        if xy:
            try:
                page.mouse.click(*xy)
                cerrados += 1
            except Exception:
                pass
    return f"Cerré {cerrados} ventana(s) emergente(s), señor." if cerrados else "No vi pop-ups que cerrar, señor."


def _hay_overlay_bloqueando(page):
    # Heurística barata (sin IA): ¿hay un elemento fixed/absolute grande, semi-transparente o con
    # z-index alto, que sugiera un modal aún abierto? Si algo falla, asume que no (no bloquea el flujo).
    try:
        return bool(page.evaluate(
            """() => {
                const els = document.querySelectorAll('div,section');
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    const st = getComputedStyle(el);
                    const area = r.width * r.height;
                    const areaPantalla = window.innerWidth * window.innerHeight;
                    if (area > areaPantalla * 0.5 &&
                        (st.position === 'fixed' || st.position === 'absolute') &&
                        parseInt(st.zIndex || '0') > 100 && st.display !== 'none') {
                        return true;
                    }
                }
                return false;
            }"""
        ))
    except Exception:
        return False


# ── Localización SEMÁNTICA (rol/nombre/texto — instantánea, sin IA) ───────────
def _localizar_semantico(page, descripcion, tipo="cualquiera"):
    """Prueba varias estrategias de Playwright (rol+nombre, label, placeholder, texto) hasta
    encontrar UN elemento visible que calce. Devuelve el Locator o None."""
    d = str(descripcion or "").strip()
    if not d:
        return None
    patron = re.compile(re.escape(d), re.I)
    estrategias = []
    if tipo in ("cualquiera", "boton"):
        estrategias.append(lambda: page.get_by_role("button", name=patron))
        estrategias.append(lambda: page.get_by_role("link", name=patron))
    if tipo in ("cualquiera", "campo"):
        estrategias.append(lambda: page.get_by_label(patron))
        estrategias.append(lambda: page.get_by_placeholder(patron))
        estrategias.append(lambda: page.get_by_role("textbox", name=patron))
        estrategias.append(lambda: page.get_by_role("combobox", name=patron))
    estrategias.append(lambda: page.get_by_text(patron, exact=False))
    for hacer in estrategias:
        try:
            loc = hacer()
            n = loc.count()
            if n == 0:
                continue
            visibles = [i for i in range(min(n, 8)) if loc.nth(i).is_visible(timeout=250)]
            if visibles:
                return loc.nth(visibles[0])
        except Exception:
            continue
    return None


def _localizar_visual(page, descripcion):
    # Respaldo universal, en DOS pasadas (el elemento puede estar fuera del viewport actual):
    #   1) foto de TODA la página (full_page) -> sabe en qué zona vertical está, aunque no se vea.
    #   2) se desplaza hasta ahí y vuelve a mirar solo el viewport -> coordenadas YA listas para
    #      hacer clic de verdad (page.mouse.click usa coordenadas relativas al viewport, no a la
    #      página completa).
    try:
        import io
        from PIL import Image
        from Nucleo_Slide.Vision_Grounding import localizar_en_imagen
        alto_viewport = (page.viewport_size or {}).get("height", 800)
        try:
            alto_pagina = page.evaluate("() => document.body.scrollHeight")
        except Exception:
            alto_pagina = alto_viewport
        # Página razonable -> foto completa; página absurdamente larga (feed infinito) -> solo
        # el viewport actual, para no mandar una imagen gigante al modelo.
        usar_full_page = alto_pagina <= 15000
        if usar_full_page:
            # Siempre arrancar la captura completa desde scroll 0: un scroll "colgado" de una
            # acción anterior (quedó a mitad, ej. scrollY=9) descuadra el recorte/costurado
            # interno que hace Playwright para armar la foto de toda la página, y eso confunde
            # la detección (visto en pruebas reales: mismo elemento, mismo prompt, falla SOLO
            # cuando el scroll de partida no era 0).
            page.evaluate("window.scrollTo(0, 0)")
        png = page.screenshot(full_page=usar_full_page)
        img = Image.open(io.BytesIO(png))
        xy = localizar_en_imagen(img, descripcion)
        if xy is None:
            return None
        if not usar_full_page:
            return xy   # ya era del viewport: coordenadas directamente utilizables
        # Coordenada en la foto COMPLETA -> hay que centrar la vista ahí y re-mirar el viewport
        # para una coordenada más precisa. Si ese segundo repaso falla (el elemento queda pegado
        # al borde del recorte, o la página ya cabía entera y no hubo scroll real posible), NO se
        # tira el resultado: cae a la coordenada de la foto completa, traducida al scroll ACTUAL
        # (una coordenada aproximada es mejor que ninguna).
        destino_scroll = max(0, xy[1] - alto_viewport // 2)
        page.evaluate(f"window.scrollTo(0, {destino_scroll})")
        page.wait_for_timeout(250)
        scroll_real = page.evaluate("() => window.scrollY") or 0
        png_viewport = page.screenshot()
        img_viewport = Image.open(io.BytesIO(png_viewport))
        xy_preciso = localizar_en_imagen(img_viewport, descripcion)
        if xy_preciso is not None:
            return xy_preciso
        y_relativo = xy[1] - scroll_real
        if 0 <= y_relativo <= alto_viewport:
            return (xy[0], y_relativo)
        return None
    except Exception:
        return None


# ── Acciones (nombre primero, visión de respaldo — mismo patrón que el escritorio) ─────────────
def clic_en(descripcion):
    """HERRAMIENTA: hace clic en 'descripcion' (un botón, enlace o elemento) dentro de la página
    actual. Primero por su rol/nombre accesible (instantáneo); si no lo encuentra, lo ubica VIENDO
    la página. Bloquea el clic si detecta que es un botón de PAGO/CONFIRMAR PEDIDO final."""
    page = _asegurar_navegador()
    if _es_boton_de_pago(descripcion) and estado_pagina().get("es_pago_final"):
        return ("Me detengo, señor: esto parece confirmar un PAGO o pedido final. No lo hago sin "
                "que usted lo autorice explícitamente por voz. Dígame 'confirma el pago' si de "
                "verdad quiere seguir.")
    loc = _localizar_semantico(page, descripcion)
    if loc is not None:
        try:
            loc.scroll_into_view_if_needed(timeout=TIMEOUT_ACCION)
            loc.click(timeout=TIMEOUT_ACCION)
            return f"Hice clic en «{descripcion}», señor."
        except Exception:
            pass
    xy = _localizar_visual(page, descripcion)
    if xy:
        try:
            page.mouse.click(*xy)
            return f"Hice clic en «{descripcion}», señor (lo ubiqué viendo la página)."
        except Exception as e:
            return f"Lo vi pero no pude hacer clic, señor: {e}"
    return f"No encontré «{descripcion}» en la página, señor."


def escribir_en(campo, texto):
    """HERRAMIENTA: escribe 'texto' en el campo descrito (buscador, formulario, login...)."""
    page = _asegurar_navegador()
    texto = str(texto or "")
    loc = _localizar_semantico(page, campo, tipo="campo")
    if loc is not None:
        try:
            loc.scroll_into_view_if_needed(timeout=TIMEOUT_ACCION)
            loc.fill(texto, timeout=TIMEOUT_ACCION)
            return f"Escribí en «{campo}», señor."
        except Exception:
            pass
    xy = _localizar_visual(page, campo)
    if xy:
        try:
            page.mouse.click(*xy)
            page.keyboard.type(texto, delay=15)
            return f"Escribí en «{campo}», señor (lo ubiqué viendo la página)."
        except Exception as e:
            return f"Lo vi pero no pude escribir, señor: {e}"
    return f"No encontré el campo «{campo}», señor."


def mantener_cursor_en(descripcion):
    """HERRAMIENTA: deja el cursor QUIETO sobre 'descripcion' (hover) sin hacer clic — para que
    aparezca un submenú o tooltip que dependa de eso, antes del siguiente clic."""
    page = _asegurar_navegador()
    loc = _localizar_semantico(page, descripcion)
    if loc is not None:
        try:
            loc.scroll_into_view_if_needed(timeout=TIMEOUT_ACCION)
            loc.hover(timeout=TIMEOUT_ACCION)
            return f"Dejé el cursor sobre «{descripcion}», señor."
        except Exception:
            pass
    xy = _localizar_visual(page, descripcion)
    if xy:
        try:
            page.mouse.move(*xy)
            return f"Dejé el cursor sobre «{descripcion}», señor (lo ubiqué viendo la página)."
        except Exception as e:
            return f"Lo vi pero no pude dejar el cursor ahí, señor: {e}"
    return f"No encontré «{descripcion}» en la página, señor."


def arrastrar_de_a(origen, destino):
    """HERRAMIENTA: arrastra el elemento 'origen' y lo suelta sobre 'destino' (tableros tipo
    Trello, reordenar listas, sliders)."""
    page = _asegurar_navegador()
    loc_o = _localizar_semantico(page, origen)
    loc_d = _localizar_semantico(page, destino)
    if loc_o is not None and loc_d is not None:
        try:
            loc_o.scroll_into_view_if_needed(timeout=TIMEOUT_ACCION)
            loc_o.drag_to(loc_d, timeout=TIMEOUT_ACCION)
            return f"Arrastré «{origen}» hasta «{destino}», señor."
        except Exception:
            pass
    # Dos blancos visuales en la MISMA jugada (origen Y destino) componen el riesgo de que uno
    # falle: un segundo intento completo, barato, sube bastante la fiabilidad real.
    xy_o = _localizar_visual(page, origen) or _localizar_visual(page, origen)
    xy_d = _localizar_visual(page, destino) or _localizar_visual(page, destino)
    if xy_o and xy_d:
        try:
            page.mouse.move(*xy_o)
            page.mouse.down()
            pasos = 8   # varios pasos intermedios: algunos sitios solo detectan el drag si el
            for i in range(1, pasos + 1):   # mouse se movió de a poco, no si "saltó" directo.
                x = xy_o[0] + (xy_d[0] - xy_o[0]) * i / pasos
                y = xy_o[1] + (xy_d[1] - xy_o[1]) * i / pasos
                page.mouse.move(x, y)
                page.wait_for_timeout(30)
            page.mouse.up()
            return f"Arrastré «{origen}» hasta «{destino}», señor (lo ubiqué viendo la página)."
        except Exception as e:
            return f"Lo vi pero no pude arrastrarlo, señor: {e}"
    return f"No encontré «{origen}» o «{destino}» para arrastrar, señor."


# ── Scratchpad de sesión (memoria entre pestañas/sitios) ───────────────────────
# Sin esto, al saltar de un sitio a otro (p.ej. "compara Temu con Amazon") el LLM olvida los
# precios/datos exactos que vio en el primero. Notas cortas, con vencimiento (no se acarrea
# contexto viejo de tareas de hace horas), inyectadas en el prompt de CADA navegar_web nuevo.
_notas_sesion = []            # [(timestamp, texto), ...]
_NOTAS_VENCEN_SEG = 30 * 60    # 30 min de inactividad -> se consideran obsoletas


def anotar_nota(texto):
    """HERRAMIENTA: anota un dato clave (precio, nombre, lo que sea) para recordarlo en el resto
    de la tarea, incluso si después navegas a OTRO sitio. Úsala ANTES de cambiar de sitio si el
    objetivo implica comparar cosas entre varias páginas."""
    texto = str(texto or "").strip()
    if not texto:
        return "¿Qué anoto, señor?"
    _notas_sesion.append((time.time(), texto))
    del _notas_sesion[:-20]
    return f"Anotado: {texto}"


def _notas_vigentes():
    ahora = time.time()
    return [t for (ts, t) in _notas_sesion if ahora - ts <= _NOTAS_VENCEN_SEG]


def limpiar_notas_sesion():
    """HERRAMIENTA: borra las notas acumuladas de sesión (para empezar una tarea nueva sin
    arrastrar contexto de la anterior)."""
    _notas_sesion.clear()
    return "Notas limpias, señor."


def ir_a(destino):
    """HERRAMIENTA: navega a una URL, o si no parece una URL, lo busca en Google."""
    page = _asegurar_navegador()
    d = str(destino or "").strip()
    if not d:
        return "¿A dónde navego, señor?"
    if re.match(r"^[a-z][a-z0-9+.-]*://", d, re.I):     # ya trae un esquema (http/https/file/...)
        url = d
    elif "." in d.split()[0] and " " not in d.split()[0]:
        url = "https://" + d
    else:
        import urllib.parse
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(d)
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(600)
        if _hay_reto_seguridad(page):
            return (f"Llegué a {page.title() or d}, señor, pero hay un reto de verificación humana "
                    "(CAPTCHA/Cloudflare) bloqueando el paso. Me detengo aquí: resuélvalo usted en "
                    "la ventana del navegador y avíseme cuando siga.")
        cerrar_popups()
        return f"Estoy en {page.title() or d}, señor."
    except Exception as e:
        return f"No pude navegar ahí, señor: {e}"


# ── Conciencia de estado de la página ──────────────────────────────────────────
_PATRON_PAGO = re.compile(
    r"confirmar pedido|confirmar compra|realizar pedido|place order|pay now|pagar ahora|"
    r"finalizar compra|complete purchase|checkout", re.I,
)

# Retos de verificación humana (Cloudflare Turnstile, Datadome, reCAPTCHA interactivo...): esto
# NO se intenta resolver ni rodear NUNCA — el sitio está pidiendo verificar que hay un humano, y
# lo correcto es que Marco lo resuelva él mismo en la ventana visible del navegador (igual que
# haría si estuviera navegando a mano). El mini-agente se detiene y avisa, punto.
_PATRON_RETO = re.compile(
    r"verifying you are human|verificando que eres humano|just a moment|checking your browser|"
    r"attention required.*cloudflare|cf-browser-verification|datadome|"
    r"please verify you are a human|unusual traffic|solve the challenge|security check|"
    r"confirma que no eres un robot|no soy un robot", re.I,
)


def _es_boton_de_pago(descripcion):
    return bool(_PATRON_PAGO.search(str(descripcion or "")))


def _hay_reto_seguridad(page):
    try:
        titulo = page.title() or ""
        texto = (page.evaluate("() => document.body.innerText") or "")[:2000]
    except Exception:
        return False
    return bool(_PATRON_RETO.search(titulo) or _PATRON_RETO.search(texto))


def estado_pagina():
    """HERRAMIENTA: dice si la página terminó de cargar, si PARECE una pantalla de pago/checkout
    final, y si hay un reto de verificación humana (CAPTCHA/Cloudflare/Datadome) bloqueando el paso."""
    page = _asegurar_navegador()
    cargando = True
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
        cargando = False
    except Exception:
        pass
    texto = ""
    try:
        texto = page.evaluate("() => document.body.innerText") or ""
    except Exception:
        pass
    es_pago = bool(_PATRON_PAGO.search(texto)) and ("$" in texto or "total" in texto.lower())
    return {
        "cargando": cargando, "es_pago_final": es_pago,
        "es_reto_seguridad": _hay_reto_seguridad(page), "titulo": _titulo_seguro(page),
    }


def _titulo_seguro(page):
    try:
        return page.title()
    except Exception:
        return ""


# ── Explorar y resumir (scroll autónomo + síntesis) ────────────────────────────
def explorar_y_resumir(consulta, max_scrolls=MAX_SCROLLS):
    """HERRAMIENTA: scrollea la página SOLA, juntando el contenido visible, hasta reunir suficiente
    o llegar al final, y luego RESUME/RESPONDE 'consulta' con el LLM a partir de lo que vio."""
    page = _asegurar_navegador()
    fragmentos, vistos = [], set()
    altura_anterior = -1
    for _ in range(max(1, int(max_scrolls or MAX_SCROLLS))):
        try:
            texto = (page.evaluate("() => document.body.innerText") or "").strip()
        except Exception:
            texto = ""
        trozo = texto[:6000]
        firma = hash(trozo[:400])   # detecta si ya vimos este mismo tramo (llegamos al fondo)
        if firma not in vistos and trozo:
            vistos.add(firma)
            fragmentos.append(trozo)
        try:
            altura = page.evaluate("() => document.body.scrollHeight")
            if altura == altura_anterior:
                break   # ya no hay más que scrollear
            altura_anterior = altura
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(500)
        except Exception:
            break
    contenido = "\n---\n".join(fragmentos)[-14000:]   # tope razonable de contexto
    if not contenido.strip():
        return "No conseguí leer contenido de la página, señor."
    try:
        from Nucleo_Slide.Cerebro import client, MODELO
        prompt = (
            "Estuviste leyendo una página web mientras hacías scroll. Con este contenido, responde "
            "lo que Marco pidió: '" + str(consulta) + "'. Sé concreto, en español, para que se lo "
            "digas por voz (nada de markdown ni listas largas; si son varias opciones, menciona 3-4 "
            "máximo con lo esencial de cada una).\n\nCONTENIDO VISTO:\n" + contenido
        )
        r = client.chat.completions.create(
            model=MODELO, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=500,
        )
        return (r.choices[0].message.content or "").strip() or "No pude resumir lo que vi, señor."
    except Exception as e:
        return f"Vi la página pero no pude resumirla, señor: {e}"


# ── El mini-agente: navegar_web(objetivo) — la única tool que ve el cerebro principal ──────────
_HERRAMIENTAS_WEB = [
    {"type": "function", "function": {"name": "ir_a", "description": "Navega a una URL o busca algo en Google si no es una URL.",
     "parameters": {"type": "object", "properties": {"destino": {"type": "string"}}, "required": ["destino"]}}},
    {"type": "function", "function": {"name": "clic_en", "description": "Hace clic en un botón/enlace/elemento por su descripción.",
     "parameters": {"type": "object", "properties": {"descripcion": {"type": "string"}}, "required": ["descripcion"]}}},
    {"type": "function", "function": {"name": "escribir_en", "description": "Escribe texto en un campo (buscador, formulario, login).",
     "parameters": {"type": "object", "properties": {"campo": {"type": "string"}, "texto": {"type": "string"}}, "required": ["campo", "texto"]}}},
    {"type": "function", "function": {"name": "cerrar_popups", "description": "Cierra cookies/pop-ups/modales que estorben.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "explorar_y_resumir", "description": "Scrollea la página sola y resume/responde una consulta con lo que ve.",
     "parameters": {"type": "object", "properties": {"consulta": {"type": "string"}}, "required": ["consulta"]}}},
    {"type": "function", "function": {"name": "mantener_cursor_en", "description": "Deja el cursor quieto sobre un elemento (hover) para revelar un submenú/tooltip, sin hacer clic.",
     "parameters": {"type": "object", "properties": {"descripcion": {"type": "string"}}, "required": ["descripcion"]}}},
    {"type": "function", "function": {"name": "arrastrar_de_a", "description": "Arrastra un elemento y lo suelta sobre otro (tableros, reordenar, sliders).",
     "parameters": {"type": "object", "properties": {"origen": {"type": "string"}, "destino": {"type": "string"}}, "required": ["origen", "destino"]}}},
    {"type": "function", "function": {"name": "anotar_nota", "description": "Anota un dato clave (precio, nombre) para no olvidarlo si luego navegas a otro sitio a comparar.",
     "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}},
    {"type": "function", "function": {"name": "estado_pagina", "description": "Dice si la página cargó, si es una pantalla de pago final, y si hay un reto de verificación humana (CAPTCHA/Cloudflare) bloqueando.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "subir_archivo", "description": "Adjunta un archivo DEL PC a un formulario de la página (subir un currículum, una foto, un PDF).",
     "parameters": {"type": "object", "properties": {"descripcion": {"type": "string", "description": "El botón/zona de subida, por si hay que pulsarlo."}, "ruta": {"type": "string", "description": "Nombre o ruta del archivo en el PC (ej. 'curriculum.pdf')."}}, "required": ["ruta"]}}},
    {"type": "function", "function": {"name": "descargar_archivo", "description": "Pulsa un enlace/botón de descarga y guarda el archivo, devolviendo dónde quedó.",
     "parameters": {"type": "object", "properties": {"descripcion": {"type": "string", "description": "El enlace o botón de descarga."}}, "required": ["descripcion"]}}},
    {"type": "function", "function": {"name": "pedir_a_marco", "description": "Le pregunta algo a Marco AL CELULAR y espera su respuesta. Úsala SOLO para lo que es imposible saber desde aquí: un código de verificación de dos pasos (2FA) que le llegó por SMS o a una app, o un dato personal que falta en un formulario. Jamás para saltarse un CAPTCHA ni un pago.",
     "parameters": {"type": "object", "properties": {"pregunta": {"type": "string"}}, "required": ["pregunta"]}}},
    {"type": "function", "function": {"name": "terminar", "description": "Termina la tarea de navegación: da el reporte final para Marco.",
     "parameters": {"type": "object", "properties": {"reporte": {"type": "string"}}, "required": ["reporte"]}}},
]


def subir_archivo(descripcion, ruta):
    """Adjunta un archivo del PC a un formulario web.

    ⚠️ SIN PROBAR contra un sitio real: aquí no hay Playwright instalado.

    Se usa set_input_files sobre el <input type=file>, que es la vía nativa de Playwright: NO abre
    el diálogo de Windows, así que no hay que pelearse con una ventana del sistema operativo (que
    es justo donde este tipo de automatización se suele romper). Si el sitio insiste en abrir el
    selector nativo, se atiende el evento 'filechooser', que es la forma soportada de interceptarlo."""
    from Funciones_Slide.Sistema.Gestor_Archivos import _resolver

    completa = _resolver(ruta)
    if completa is None:
        return f"No encontré el archivo «{ruta}» en el PC, así que no puedo subirlo."
    page = _asegurar_navegador()
    try:
        entrada = page.locator("input[type=file]").first
        if entrada.count() > 0:
            entrada.set_input_files(completa, timeout=TIMEOUT_ACCION)
            return f"Adjunté {os.path.basename(completa)} al formulario."
    except Exception:
        pass
    # Respaldo: el sitio abre el selector nativo al pulsar un botón.
    try:
        with page.expect_file_chooser(timeout=TIMEOUT_ACCION) as info:
            clic_en(descripcion or "subir archivo")
        info.value.set_files(completa)
        return f"Adjunté {os.path.basename(completa)} al formulario."
    except Exception as e:
        return f"No pude adjuntar el archivo: {e}"


def descargar_archivo(descripcion):
    """Pulsa el enlace/botón de descarga y GUARDA lo que baje, devolviendo dónde quedó.

    ⚠️ SIN PROBAR contra un sitio real.

    Se usa expect_download, que entrega el archivo de forma determinista. La alternativa —vigilar
    la carpeta de Descargas a ver qué aparece— es adivinar: no se sabe cuándo terminó ni cuál de
    los archivos nuevos era el nuestro si hay varios bajando."""
    page = _asegurar_navegador()
    destino_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(destino_dir, exist_ok=True)
    try:
        with page.expect_download(timeout=45000) as info:
            clic_en(descripcion or "descargar")
        bajada = info.value
        destino = os.path.join(destino_dir, bajada.suggested_filename or "descarga")
        bajada.save_as(destino)
        return f"Descargado en {destino}"
    except Exception as e:
        return f"No pude descargar: {e}"


def pedir_a_marco(pregunta):
    """Le pregunta algo a Marco al CELULAR y espera. Para el código 2FA que llega al teléfono: sin
    esto, una tarea que topaba con la verificación en dos pasos se moría ahí mismo."""
    try:
        from Funciones_Slide.Comunicacion.Telegram_Control import preguntar, hay_celular
    except Exception:
        return "No tengo puente con el celular de Marco; no puedo preguntarle nada estando él fuera."
    if not hay_celular():
        return ("No hay puente con el celular (falta configurar Telegram). Si Marco está frente al "
                "PC, puede escribirlo él mismo en la ventana del navegador.")
    r = preguntar(f"AIDEN necesita esto para seguir navegando:\n{pregunta}", timeout=180)
    return f"Marco respondió: {r}" if r else "Marco no respondió a tiempo; no puedo continuar con eso."


_FUNCIONES_WEB = {
    "ir_a": ir_a, "clic_en": clic_en, "escribir_en": escribir_en,
    "cerrar_popups": cerrar_popups, "explorar_y_resumir": explorar_y_resumir,
    "mantener_cursor_en": mantener_cursor_en, "arrastrar_de_a": arrastrar_de_a,
    "anotar_nota": anotar_nota, "estado_pagina": estado_pagina,
    "pedir_a_marco": pedir_a_marco,
    "subir_archivo": subir_archivo, "descargar_archivo": descargar_archivo,
}

_SISTEMA_WEB = (
    "Eres AIDEN navegando la web por Marco. Cumple su objetivo paso a paso usando SOLO estas "
    "herramientas de navegador (ir_a, clic_en, escribir_en, cerrar_popups, explorar_y_resumir, "
    "mantener_cursor_en, arrastrar_de_a, anotar_nota, estado_pagina, pedir_a_marco, "
    "subir_archivo, descargar_archivo). "
    "Si hay que ADJUNTAR un archivo del PC usa subir_archivo con su nombre; si hay que BAJAR algo "
    "usa descargar_archivo y luego di dónde quedó. Ninguna de las dos salta el freno de pagos. "
    "Si la página pide un CÓDIGO DE VERIFICACIÓN (2FA) que le llegó al teléfono a Marco, o un dato "
    "personal que no tienes, usa pedir_a_marco: él te lo contesta al celular y sigues. Eso NO "
    "aplica a CAPTCHAs ni a pagos: esos se reportan y se termina. "
    "Tras cada acción, antes de la siguiente, considera si conviene cerrar_popups. Si un clic dice "
    "que se detuvo por ser un PAGO/pedido final, NO insistas: repórtalo tal cual con 'terminar' — "
    "jamás intentes rodear ese freno. Si ir_a o estado_pagina reportan un RETO DE SEGURIDAD "
    "(CAPTCHA/Cloudflare/Datadome), tampoco insistas ni intentes resolverlo: termina de inmediato "
    "explicando que Marco debe resolverlo él mismo en la ventana visible del navegador. Si un menú "
    "solo aparece al pasar el mouse, usa mantener_cursor_en antes de clic_en. Si el objetivo implica "
    "COMPARAR varios sitios (p.ej. 'compara Temu con Amazon'), usa anotar_nota para guardar los "
    "datos clave de un sitio ANTES de saltar al siguiente. Cuando termines (o si algo no se puede), "
    "llama a 'terminar' con un reporte breve y claro para decirle a Marco por voz. Máximo unos pocos "
    "pasos; sé directo."
)


def navegar_web(objetivo):
    """HERRAMIENTA (la llave maestra de internet): Marco te da un objetivo de navegación completo,
    en lenguaje natural ('entra a Temu, busca teclados mecánicos baratos y resúmeme los 3 mejores').
    AIDEN abre un navegador REAL (con sesión persistente) y lo opera solo: navega, cierra pop-ups,
    hace clic/escribe por descripción (con respaldo de visión si la página no tiene nombres
    accesibles), y puede leer/scrollear y resumir contenido. NUNCA confirma un pago/pedido final sin
    autorización explícita de Marco. Úsala para CUALQUIER tarea que implique navegar un sitio web
    (comprar, buscar, leer, rellenar formularios) más allá de solo abrir una página (para eso usa
    abrir_web)."""
    objetivo = str(objetivo or "").strip()
    if not objetivo:
        return "¿Qué quiere que haga en internet, señor?"
    from Nucleo_Slide.Cerebro import client, MODELO
    from Nucleo_Slide.Latido_Trabajo import latido
    try:
        from Voz_Slide.Herramientas_del_asistente import hablado_del_asistente as _hablar
    except Exception:
        _hablar = lambda t: None

    notas = _notas_vigentes()
    sistema = _SISTEMA_WEB
    if notas:
        sistema += ("\n\nNOTAS DE ESTA SESIÓN (de sitios/pasos anteriores; úsalas si el objetivo "
                    "actual las necesita, p.ej. para comparar):\n- " + "\n- ".join(notas))
    mensajes = [{"role": "system", "content": sistema},
                {"role": "user", "content": "OBJETIVO: " + objetivo}]
    reporte = ""
    with latido(_hablar):
        for _paso in range(MAX_PASOS):
            try:
                r = client.chat.completions.create(
                    model=MODELO, messages=mensajes, tools=_HERRAMIENTAS_WEB,
                    tool_choice="auto", temperature=0.2,
                )
            except Exception as e:
                reporte = f"Perdí el enlace navegando, señor: {e}"
                break
            msg = r.choices[0].message
            tcs = list(msg.tool_calls or [])
            mensajes.append({"role": "assistant", "content": msg.content or None,
                             "tool_calls": [{"id": tc.id, "type": "function",
                                            "function": {"name": tc.function.name,
                                                        "arguments": tc.function.arguments}}
                                           for tc in tcs] or None})
            if not tcs:
                reporte = (msg.content or "").strip() or "Terminé, señor."
                break
            fin = False
            for tc in tcs:
                nombre = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                if nombre == "terminar":
                    reporte = str(args.get("reporte") or "Listo, señor.")
                    fin = True
                    resultado = reporte
                else:
                    fn = _FUNCIONES_WEB.get(nombre)
                    try:
                        resultado = str(fn(**args)) if fn else f"No existe {nombre}."
                    except Exception as e:
                        resultado = f"Error: {e}"
                mensajes.append({"role": "tool", "tool_call_id": tc.id, "content": resultado})
            if fin:
                break
        else:
            reporte = reporte or "Llegué al límite de pasos navegando, señor; ¿sigo o lo dejamos ahí?"
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Navegación web: {objetivo[:60]} -> {reporte[:80]}", "navegador_web")
    except Exception:
        pass
    return reporte
