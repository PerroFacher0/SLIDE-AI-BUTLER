# EL ESTILO DE AIDEN, EN UN SOLO SITIO.
#
# Antes cada superficie pintaba su propio panel: la Mira con sus rectángulos redondeados, el Overlay
# con su hoja de estilo, la esfera con sus colores en el HTML. Tres sitios con tres versiones del
# mismo gris — y cada retoque había que hacerlo tres veces, así que tarde o temprano una se quedaba
# atrás y el conjunto se veía descosido. Aquí está la paleta y aquí están las primitivas: quien
# quiera pintar algo, lo pide.
#
# LA PALETA: fondo casi negro y UN SOLO acento plata desaturado.
# El color saturado (cian, azul eléctrico) se probó y se descartó: se veía a HUD de videojuego, y
# esto es una herramienta que Marco tiene delante todo el día. El plata desaturado da el acabado
# técnico sin disfrazarse de nada.
#
# El color se reserva para UNA cosa: los números que suben y bajan. Si el rojo y el verde también
# decoraran, dejarían de significar algo — que es justo lo que se quiere evitar.

# ── Paleta ───────────────────────────────────────────────────────────────────
FONDO_PANEL = (21, 22, 26, 240)     # gris muy oscuro NEUTRO (no azul marino)
ACENTO = (220, 225, 230)            # #DCE1E6 — plata desaturado, para bordes y resplandor
ACENTO_BRILLO = (242, 244, 246)     # #F2F4F6 — la línea central del borde, la más viva
TEXTO = (238, 240, 241)
TEXTO_TENUE = (150, 154, 158)
SUBE = (150, 190, 155)              # verde apagado — SOLO para valores que suben
BAJA = (200, 140, 140)              # rojo apagado  — SOLO para valores que bajan

# El mismo acento en hexadecimal, para la esfera (WebGL). No hay forma de compartir código entre
# Python y JavaScript aquí, así que se comparte el VALOR y se deja dicho de dónde sale.
ACENTO_HEX = "#DCE1E6"

# Monoespaciada: da el aire técnico y, sobre todo, alinea las columnas de números — que es medio
# motivo por el que existe la tarjeta. Consolas viene con Windows desde siempre.
FUENTE_MONO = "Consolas"
_ALTERNATIVAS_MONO = ("Cascadia Mono", "Consolas", "Courier New")

CORTE = 10                          # cuánto se come cada esquina en diagonal


def color(rgb, alfa=255):
    from PySide6.QtGui import QColor
    r, g, b = rgb[:3]
    return QColor(r, g, b, rgb[3] if len(rgb) > 3 else alfa)


def fuente(tam=10, negrita=False):
    """La monoespaciada del proyecto. Se piden varias por orden: si la primera no está en el
    equipo, Qt cae a la siguiente sin que haya que comprobar nada."""
    from PySide6.QtGui import QFont
    f = QFont(FUENTE_MONO)
    f.setFamilies(list(_ALTERNATIVAS_MONO))
    f.setPointSize(tam)
    f.setBold(negrita)
    return f


def panel_chamferado(rect, corte=CORTE):
    """El octágono con las esquinas cortadas en diagonal: cuatro lados rectos y cuatro chaflanes.

    La esquina cortada es lo que separa esto de una ventana cualquiera. Un redondeado dice
    'aplicación'; un corte recto dice 'instrumento'. Devuelve el camino para que quien llama decida
    si lo rellena, lo bordea o las dos cosas."""
    from PySide6.QtGui import QPainterPath
    x, y, w, h = float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])
    c = min(corte, w / 2.5, h / 2.5)          # en un panel pequeño, el chaflán se encoge con él
    p = QPainterPath()
    p.moveTo(x + c, y)
    p.lineTo(x + w - c, y)
    p.lineTo(x + w, y + c)
    p.lineTo(x + w, y + h - c)
    p.lineTo(x + w - c, y + h)
    p.lineTo(x + c, y + h)
    p.lineTo(x, y + h - c)
    p.lineTo(x, y + c)
    p.closeSubpath()
    return p


def rellenar_panel(painter, path, fondo=FONDO_PANEL):
    from PySide6.QtCore import Qt
    painter.setPen(Qt.NoPen)
    painter.setBrush(color(fondo))
    painter.drawPath(path)


# Las cuatro pasadas del resplandor: (grosor, opacidad, usa el tono más vivo).
# De fuera hacia dentro: ancha y casi invisible -> fina y brillante. Superpuestas dan la sensación
# de luz derramándose desde el borde.
_PASADAS = ((10.0, 13, False), (6.0, 28, False), (3.0, 64, False), (1.0, 235, True))


def borde_resplandor(painter, path, acento=ACENTO, intensidad=1.0):
    """Dibuja el borde varias veces, cada vez más fino y más opaco.

    Es un desenfoque falso, y a propósito: el desenfoque de verdad (QGraphicsBlurEffect) rehace la
    textura en cada repintado, y esto se repinta ~25 veces por segundo encima de todo lo que Marco
    está haciendo. Cuatro trazos cuestan casi nada y se ven igual.

    'intensidad' (0..1) sube o baja TODO el resplandor de golpe: es lo que usa el Overlay para
    decir cuánta atención merece el momento, sin cambiar de color."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPen
    intensidad = max(0.0, min(1.0, float(intensidad)))
    painter.setBrush(Qt.NoBrush)
    for grosor, alfa, vivo in _PASADAS:
        c = color(ACENTO_BRILLO if vivo else acento, int(alfa * intensidad))
        painter.setPen(QPen(c, grosor))
        painter.drawPath(path)


def linea_escaneo(painter, rect, progreso):
    """Una línea fina que recorre el panel de arriba abajo, desvaneciéndose por los extremos.

    Es el único elemento que se mueve. Sirve para que un panel quieto no parezca una captura de
    pantalla pegada: dice 'esto está vivo' sin pedir que lo mires."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QLinearGradient, QPen, QBrush
    x, y, w, h = rect
    py = y + (h * max(0.0, min(1.0, float(progreso))))
    grad = QLinearGradient(x, 0, x + w, 0)
    grad.setColorAt(0.0, color(ACENTO, 0))
    grad.setColorAt(0.5, color(ACENTO, 100))
    grad.setColorAt(1.0, color(ACENTO, 0))
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QBrush(grad), 1.0))
    painter.drawLine(QPointF(x, py), QPointF(x + w, py))


def etiqueta(texto):
    """Mayúsculas SOLO para etiquetas cortas de estado ('ESCUCHANDO', 'PERCIBE').

    Deliberadamente NO se aplica al contenido: un dato que ya viene formateado por una herramienta
    ('NVDA $128.50 +3.2%', el asunto de un correo, un nombre propio) se destroza en mayúsculas, y
    además dejaría de coincidir con lo que la voz dice."""
    return str(texto or "").upper()
