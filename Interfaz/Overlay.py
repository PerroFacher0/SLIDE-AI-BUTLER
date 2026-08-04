# OVERLAY DE PRESENCIA — el HUD de Jarvis: limpio, sencillo, sin ruido, pero vivo. Una ventanita
# siempre-encima, click-through (no roba el mouse), que muestra lo que AIDEN percibe y piensa AHORA.
#
# Filosofía de diseño (2ª pasada, a pedido de Marco: "más sencillo y clean pero con cosas
# importantes"): UN solo elemento animado (un latido, no un panel lleno de arcos girando y barridos),
# tipografía con aire, un color de acento que se usa con MODERACIÓN (el latido + una palabra de
# estado, no todo el panel teñido), y solo la información que de verdad importa: qué percibe, su
# meta activa, lo más reciente, y su pensamiento — sin adornos que no dicen nada.
#
# Es PySide6 (tkinter está prohibido). Aislado: si algo falla, no toca la app principal. Debe crearse
# en el HILO de Qt (lo hace Main_AlwaysOn tras crear la QApplication).

import math

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QStyleOption, QStyle, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QGuiApplication, QPainter, QPen, QBrush, QColor, QRadialGradient, QLinearGradient,
)

# ── Parámetros ajustables ─────────────────────────────────────────────────────
ANCHO, ALTO = 358, 236
MARGEN = 22
REFRESCO_MS = 1200     # cadencia del CONTENIDO (barato: son unos archivos json chiquitos)
ANIM_MS = 60            # cadencia del latido (puro dibujo vectorial, casi gratis)
_MAX_EVENTOS = 1

from Interfaz import _Estilo as _E

# El MOMENTO de Marco se lee por el BRILLO, nunca por el matiz: normal es plata en calma; lo que
# pide silencio (reunión/gaming/ausente) se atenúa; lo que pide atención (taller, y sobre todo una
# misión activa) se aclara. Esa lógica no cambia — lo único que cambia es de qué color se atenúa.
#
# Antes cada modo era un gris suelto; ahora los seis son EL MISMO plata del resto de AIDEN a
# distinta intensidad. Se conservan exactamente las proporciones de antes (255, 224, 198, 146, 128,
# 96 sobre 255), así que los seis modos siguen separados igual de bien — solo que ahora el overlay
# y la Mira son obviamente la misma herramienta.
_INTENSIDAD = {
    "agente":  1.00,   # misión en curso: lo más brillante, pide que lo mires
    "taller":  0.88,
    "normal":  0.78,
    "reunion": 0.57,   # de aquí para abajo, AIDEN se aparta
    "gaming":  0.50,
    "ausente": 0.38,
}
_ETIQUETAS = {"normal": "en línea", "reunion": "reunión", "taller": "taller",
              "agente": "misión", "gaming": "gaming", "ausente": "ausente"}


def _tema(modo):
    i = _INTENSIDAD.get(modo, _INTENSIDAD["normal"])
    r, g, b = _E.ACENTO
    return (int(r * i), int(g * i), int(b * i), _ETIQUETAS.get(modo, "en línea"))


_TEMAS = {m: _tema(m) for m in _INTENSIDAD}


def _intensidad_de(rgb):
    """De vuelta al 0..1, para modular el resplandor del borde con el mismo criterio."""
    return max(0.25, min(1.0, rgb[0] / max(1, _E.ACENTO[0])))


def _estado():
    try:
        from Nucleo_Slide.Estado_Del_Mundo import obtener
        return obtener() or {}
    except Exception:
        return {}


def _reflexion_corta():
    try:
        from Nucleo_Slide.Reflexion import reflexion_texto
        t = (reflexion_texto() or "").replace("\n", " ").strip()
        return (t[:100] + "…") if len(t) > 100 else t
    except Exception:
        return ""


def _pensamiento():
    try:
        from Nucleo_Slide.Monologo import pensamiento_actual
        return (pensamiento_actual() or "").strip()
    except Exception:
        return ""


def _foco_vivo(est):
    # Foco en TIEMPO REAL desde la percepción (más fresco que el del estado del mundo).
    try:
        from Nucleo_Slide.Percepcion import ventana_activa
        v = ventana_activa()
        if v and v not in ("(desconocida)", "(escritorio)"):
            return v
    except Exception:
        pass
    return est.get("foco_actual") or "—"


def _tema_por_estado(est):
    if not est.get("marco_presente", True):
        return _TEMAS["ausente"]
    if est.get("en_reunion"):
        return _TEMAS["reunion"]
    modo = est.get("modo") or "normal"
    return _TEMAS.get(modo, _TEMAS["normal"])


def _esc(t):
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _construir_html(rgb, etiqueta):
    r, g, b = rgb
    acc = f"rgb({r},{g},{b})"
    est = _estado()

    # Cabecera: deja 28px a la izquierda para el latido pintado por QPainter. Nombre + estado (solo
    # texto, sin pastillas ni fondos) + una línea fina que separa, todo con aire.
    partes = [
        "<div style='margin-left:28px;'>"
        "<span style='font-size:12.5px;font-weight:600;color:#eef0f1;letter-spacing:2.2px;'>AIDEN</span>"
        f"<span style='float:right;font-size:10.5px;color:{acc};letter-spacing:0.3px;'>{_esc(etiqueta)}</span>"
        "</div>",
        "<div style='border-top:1px solid rgba(255,255,255,16);margin:9px 0 10px;'></div>",
    ]

    pen = _pensamiento()
    if pen:
        partes.append(
            f"<div style='color:#a7abae;font-size:11px;font-style:italic;line-height:1.5;"
            f"padding-left:9px;border-left:1.5px solid rgba({r},{g},{b},110);'>{_esc(pen)[:110]}</div>"
        )

    def _fila(etiqueta_fila, valor, top=10):
        return (
            f"<div style='margin-top:{top}px;'>"
            f"<span style='color:#75787c;font-size:9.5px;letter-spacing:0.6px;'>{etiqueta_fila}</span>"
            f"&nbsp;&nbsp;<span style='color:#d6d8da;font-size:11px;'>{valor}</span></div>"
        )

    partes.append(_fila("PERCIBE", _esc(_foco_vivo(est))[:40]))

    metas = [m.get("texto", "") for m in (est.get("metas") or []) if m.get("estado") != "hecha"]
    if metas:
        partes.append(_fila("META", _esc(metas[0])[:40]))

    evs = (est.get("eventos") or [])[-_MAX_EVENTOS:]
    if evs:
        e = evs[-1]
        partes.append(_fila("AHORA", f"{_esc(e.get('texto',''))[:38]}"
                                     f" <span style='color:#75787c;font-size:9.5px;'>· {_esc(e.get('hora',''))}</span>"))

    refl = _reflexion_corta()
    if refl:
        partes.append(
            f"<div style='color:#75787c;font-size:10px;font-style:italic;margin-top:11px;"
            f"border-top:1px solid rgba(255,255,255,12);padding-top:8px;'>{_esc(refl)}</div>"
        )
    return "".join(partes)


class OverlayJarvis(QWidget):
    def __init__(self):
        super().__init__()
        # Sin marco, siempre encima, fuera de la barra de tareas, y SIN robar el foco/los clics.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_StyledBackground, True)   # para que el fondo/borde del QSS se pinte bien

        # El color NUNCA salta de golpe: se acerca suave al objetivo cada tick de animación
        # (mismo idioma que el motor de la esfera: actual += (objetivo-actual)*factor). Así, si
        # Marco entra a una reunión, el acento se atenúa hacia el ámbar en vez de dar un salto brusco.
        self._rgb_obj = _TEMAS["normal"]              # objetivo real (r,g,b,etiqueta)
        self._rgb_actual = list(_TEMAS["normal"][:3])  # r,g,b EN CAMINO hacia el objetivo
        self._fase = 0.0

        self._label = QLabel("")
        self._label.setTextFormat(Qt.RichText)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.addWidget(self._label)

        # Fondo grafito, borde NEUTRO y casi invisible (el color vive en el latido y el estado, no
        # en el marco): así el panel se siente premium y tranquilo, no "todo teñido".
        # Sin fondo ni borde en la hoja de estilo: el panel lo pinta paintEvent con el chaflán
        # compartido. Si se dejara aquí un borde redondeado, se vería POR DEBAJO del chaflán y
        # quedaría un doble contorno con dos formas distintas.
        self.setStyleSheet("QWidget { background: transparent; border: none; }")
        self.resize(ANCHO, ALTO)
        self._reposicionar()

        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(26)
        sombra.setColor(QColor(0, 0, 0, 140))
        sombra.setOffset(0, 6)
        self.setGraphicsEffect(sombra)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refrescar)
        self._timer.start(REFRESCO_MS)

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick_anim)
        self._anim.start(ANIM_MS)

        self._refrescar()

    def _reposicionar(self):
        try:
            geo = QGuiApplication.primaryScreen().availableGeometry()
            self.move(geo.right() - self.width() - MARGEN, geo.bottom() - self.height() - MARGEN)
        except Exception:
            pass

    def _refrescar(self):
        try:
            self._rgb_obj = _tema_por_estado(_estado())
            self._label.setText(_construir_html(self._rgb_entero(), self._rgb_obj[3]))
        except Exception:
            pass

    def _rgb_entero(self):
        return tuple(round(c) for c in self._rgb_actual)

    def _tick_anim(self):
        self._fase += 1.0
        for i in range(3):
            self._rgb_actual[i] += (self._rgb_obj[i] - self._rgb_actual[i]) * 0.08
        self.update()   # solo repinta el filo/latido; el texto no cambia aquí

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)
        self._dibujar_panel(p)
        self._dibujar_latido(p)
        p.end()

    def _dibujar_panel(self, p: QPainter):
        # El panel: mismo chaflán y mismo resplandor que la Mira, y la INTENSIDAD del borde sube o
        # baja con el modo — así "cuánta atención pide" se nota antes de leer una sola palabra.
        rect = (1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        ruta = _E.panel_chamferado(rect, corte=12)
        _E.rellenar_panel(p, ruta)
        _E.borde_resplandor(p, ruta, intensidad=_intensidad_de(self._rgb_entero()))
        # La misma línea de escaneo de los carteles, MUY lenta aquí: el overlay está siempre a la
        # vista, y algo que se mueve rápido delante todo el día cansa.
        _E.linea_escaneo(p, rect, (self._fase * 0.0016) % 1.0)

    def _dibujar_latido(self, p: QPainter):
        # El elemento animado central: un latido suave (respira) cuyo COLOR se desliza hacia el
        # estado real de Marco en vez de saltar de golpe. Nada de arcos ni barridos: menos es más.
        r, g, b = self._rgb_entero()
        cx, cy = 24, 25
        pulso = 0.5 + 0.5 * math.sin(self._fase * 0.05)

        halo = QRadialGradient(cx, cy, 7.5)
        halo.setColorAt(0.0, QColor(r, g, b, int(55 + 70 * pulso)))
        halo.setColorAt(1.0, QColor(r, g, b, 0))
        p.setBrush(QBrush(halo))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 7.5, 7.5)

        # Núcleo con un toque metálico (esfera de plata pulida): brillo blanco descentrado que se
        # funde hacia el gris del estado — no un punto plano, un reflejo real.
        nucleo = QRadialGradient(cx - 1.0, cy - 1.1, 3.4)
        nucleo.setColorAt(0.0, QColor(255, 255, 255, min(255, int(235 + 20 * pulso))))
        nucleo.setColorAt(0.55, QColor(r, g, b, min(255, int(210 + 45 * pulso))))
        nucleo.setColorAt(1.0, QColor(max(0, r - 35), max(0, g - 35), max(0, b - 35),
                                      min(255, int(190 + 45 * pulso))))
        p.setBrush(QBrush(nucleo))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 2.7, 2.7)


def crear_overlay():
    # Crea, muestra y DEVUELVE el overlay (hay que llamarlo dentro del hilo de Qt). None si falla.
    try:
        ov = OverlayJarvis()
        ov.show()
        return ov
    except Exception as e:
        print(f"[overlay] no se pudo crear: {e}")
        return None
