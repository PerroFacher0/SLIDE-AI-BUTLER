# WEB: abrir CUALQUIER página por voz — YouTube (inicio o búsqueda), Gmail, un sitio conocido, o una
# URL cualquiera. Lo que Marco haría abriendo el navegador, dicho en voz alta.

import urllib.parse
import webbrowser

# Sitios conocidos por nombre -> URL de inicio.
_SITIOS = {
    "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com",
    "correo": "https://mail.google.com", "outlook": "https://outlook.office.com/mail",
    "github": "https://github.com", "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv", "spotify": "https://open.spotify.com",
    "drive": "https://drive.google.com", "chatgpt": "https://chat.openai.com",
    "gpt": "https://chat.openai.com", "whatsapp": "https://web.whatsapp.com",
    "maps": "https://maps.google.com", "wikipedia": "https://es.wikipedia.org",
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "twitter": "https://x.com", "x": "https://x.com", "reddit": "https://www.reddit.com",
    "amazon": "https://www.amazon.com", "google": "https://www.google.com",
    "discord": "https://discord.com/app", "canvas": "https://unal.instructure.com",
    "moodle": "https://moodle.com", "chess": "https://www.chess.com",
    "gemini": "https://gemini.google.com", "claude": "https://claude.ai",
}

# Nombres que en un "abre X" deben ir a la WEB (no a una app instalada).
WEB_DIRECTOS = {"youtube", "gmail", "correo", "outlook", "github", "netflix", "twitch", "drive",
                "chatgpt", "gpt", "maps", "wikipedia", "instagram", "facebook", "twitter", "reddit",
                "amazon", "canvas", "moodle", "chess", "gemini", "claude"}

_TILDES = str.maketrans("áéíóúü", "aeiouu")


def _norm(s):
    return str(s or "").strip().lower().translate(_TILDES)


def abrir_web(sitio, buscar=""):
    """HERRAMIENTA: abre una página web. 'sitio' = nombre conocido (youtube, gmail, github...) o una
    URL. 'buscar' opcional = qué buscar dentro (útil en YouTube o Google). Úsala para 'abre youtube',
    'abre youtube y busca X', 'abre mi correo', 'abre <página>'."""
    s = _norm(sitio)
    q = str(buscar or "").strip()

    # YouTube con búsqueda -> página de resultados (no reproduce, MUESTRA).
    if "youtube" in s and q:
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q))
        return f"YouTube con '{q}', señor."

    # Sitio conocido por nombre.
    for nombre, url in _SITIOS.items():
        if nombre in s.split() or s == nombre:
            webbrowser.open(url)
            return f"Abriendo {nombre}, señor."

    # Parece una URL directa.
    if "." in s and " " not in s:
        url = s if s.startswith("http") else "https://" + s
        webbrowser.open(url)
        return f"Abriendo {sitio}, señor."

    # Nada reconocido -> búsqueda en Google.
    termino = q or sitio
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(str(termino)))
    return f"Buscando {termino} en Google, señor."
