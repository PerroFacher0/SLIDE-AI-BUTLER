# OVERLAY DE PRESENCIA — el HUD de Jarvis, hecho realidad. Una ventanita siempre-encima,
# click-through (no roba el mouse), que muestra EN VIVO lo que AIDEN percibe y piensa: su reactor
# de estado (respira, gira, cambia de color según tu momento), tu foco, sus metas, lo reciente y su
# lectura de fondo. Nada de esto es un panel estático: está VIVO — por eso se dibuja con QPainter
# (arcos, degradados, barrido) además del texto, no solo CSS.
#
# Resuelve la queja de Marco de "no se nota en pantalla": todo el trabajo de fondo (Estado_Del_Mundo,
# metas, reflexión, monólogo) ahora se VE, y se ve como Jarvis, no como una consola de depuración.
# Es PySide6 (tkinter está prohibido). Aislado: si algo falla, no toca la app principal. Debe crearse
# en el HILO de Qt (lo hace Main_AlwaysOn tras crear la QApplication).

import math
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QStyleOption, QStyle, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QGuiApplication, QPainter, QPen, QBrush, QColor, QRadialGradient, QLinearGradient

# ── Parámetros ajustables ─────────────────────────────────────────────────────
ANCHO, ALTO = 388, 306
MARGEN = 22
REFRESCO_MS = 1000     # cadencia del CONTENIDO (reloj, pensamiento, percepción...): 1x/seg, se siente vivo
ANIM_MS = 55            # cadencia de la ANIMACIÓN del reactor (respirar/girar/barrido): ~18 fps, fluido y barato
_MAX_EVENTOS = 2

# Paleta por MOMENTO de Marco: el reactor y todo el acento de color cambian según el estado real
# (nada decorativo-al-azar: es la MISMA información que antes, solo que ahora se SIENTE).
_TEMAS = {
    "normal":  (0, 229, 204, "EN LÍNEA"),
    "reunion": (255, 176, 74, "REUNIÓN"),
    "taller":  (176, 120, 255, "TALLER"),
    "agente":  (255, 90, 170, "MISIÓN"),
    "gaming":  (255, 110, 90, "GAMING"),
    "ausente": (110, 128, 142, "AUSENTE"),
}


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
        return (t[:110] + "…") if len(t) > 110 else t
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
    # Devuelve (r, g, b, etiqueta) según el momento real de Marco. Prioridad: ausente > reunión >
    # modo especial (taller/agente/gaming) > normal.
    if not est.get("marco_presente", True):
        return _TEMAS["ausente"]
    if est.get("en_reunion"):
        return _TEMAS["reunion"]
    modo = est.get("modo") or "normal"
    return _TEMAS.get(modo, _TEMAS["normal"])


def _esc(t):
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _construir_html(rgb, blink):
    r, g, b, etiqueta = rgb
    acc = f"rgb({r},{g},{b})"
    est = _estado()

    cursor = "▍" if blink else " "
    reloj = time.strftime("%H:%M:%S")

    # Cabecera: deja 34px a la izquierda para el reactor pintado por QPainter (ver _draw_hud),
    # el wordmark, y a la derecha el reloj vivo + la etiqueta de estado como pastilla con glow.
    partes = [
        "<div style='margin-left:34px;display:flex;'>"
        f"<span style='font-size:14px;font-weight:bold;color:{acc};letter-spacing:3px;'>AIDEN</span>"
        "</div>",
        "<div style='margin-left:34px;margin-top:-2px;'>"
        f"<span style='color:rgba({r},{g},{b},160);font-size:9px;letter-spacing:1px;'>{reloj}</span>"
        f"<span style='float:right;color:#060a0f;background:{acc};font-size:8.5px;font-weight:bold;"
        f"letter-spacing:1.5px;padding:1px 8px;border-radius:7px;'>{_esc(etiqueta)}</span>"
        "</div>",
    ]

    # Pensamiento interno: el corazón vivo del HUD, con cursor parpadeante (como si lo escribiera ahora).
    pen = _pensamiento()
    if pen:
        partes.append(
            f"<div style='color:#bfe9ff;font-size:11px;font-style:italic;margin-top:10px;"
            f"padding:7px 9px;background:rgba({r},{g},{b},16);border-left:2px solid rgba({r},{g},{b},150);"
            f"border-radius:0 5px 5px 0;'>“{_esc(pen)[:118]}{cursor}”</div>"
        )

    partes.append(
        f"<div style='color:#7f95a8;font-size:10.5px;margin-top:8px;letter-spacing:0.5px;'>PERCIBO&nbsp; "
        f"<span style='color:#e6eef7;'>{_esc(_foco_vivo(est))[:42]}</span></div>"
    )

    metas = [m.get("texto", "") for m in (est.get("metas") or []) if m.get("estado") != "hecha"][:2]
    if metas:
        partes.append(
            f"<div style='color:#7f95a8;font-size:10.5px;margin-top:7px;letter-spacing:0.5px;'>METAS</div>")
        for m in metas:
            partes.append(f"<div style='color:#cdeee0;font-size:11px;'>&nbsp;&nbsp;▸ {_esc(m)[:42]}</div>")

    evs = (est.get("eventos") or [])[-_MAX_EVENTOS:]
    if evs:
        partes.append(
            f"<div style='color:#7f95a8;font-size:10.5px;margin-top:7px;letter-spacing:0.5px;'>RECIENTE</div>")
        for e in reversed(evs):
            partes.append(
                f"<div style='color:#93a8ba;font-size:10px;'>&nbsp;&nbsp;[{_esc(e.get('hora',''))}] "
                f"{_esc(e.get('texto',''))[:44]}</div>"
            )

    refl = _reflexion_corta()
    if refl:
        partes.append(
            f"<div style='color:#6f8494;font-size:10px;font-style:italic;margin-top:8px;"
            f"border-top:1px solid rgba({r},{g},{b},35);padding-top:6px;'>{_esc(refl)}</div>"
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

        self._rgb = _TEMAS["normal"]   # (r,g,b,etiqueta) del momento actual — anima el reactor
        self._fase = 0.0               # ángulo/tiempo de la animación (respirar, girar, barrer)
        self._tick = 0                 # contador de refrescos de contenido (para el cursor parpadeante)

        self._label = QLabel("")
        self._label.setTextFormat(Qt.RichText)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.addWidget(self._label)

        self.setStyleSheet(
            "QWidget { background: rgba(5,9,16,222); border: 1px solid rgba(0,229,204,70);"
            " border-radius: 15px; }"
        )
        self.resize(ANCHO, ALTO)
        self._reposicionar()

        # Una sombra flotante sutil: que el HUD parezca suspendido sobre el escritorio, no pegado.
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(34)
        sombra.setColor(QColor(0, 0, 0, 165))
        sombra.setOffset(0, 7)
        self.setGraphicsEffect(sombra)

        # DOS relojes: uno LENTO para el contenido (texto/datos, barato) y uno RÁPIDO solo para
        # animar el reactor (QPainter), que es puro dibujo vectorial y no cuesta casi nada.
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
            est = _estado()
            self._rgb = _tema_por_estado(est)
            self._tick += 1
            self._label.setText(_construir_html(self._rgb, self._tick % 2 == 0))
        except Exception:
            pass

    def _tick_anim(self):
        self._fase += 1.0
        self.update()   # solo repinta (paintEvent); el contenido de texto no cambia aquí

    def paintEvent(self, event):
        # 1) Deja que el QSS pinte el fondo/borde redondeado (comportamiento normal de Qt).
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)
        # 2) Encima, el HUD vivo: brackets de esquina, barrido y el reactor que respira y gira.
        self._draw_hud(p)
        p.end()

    def _draw_hud(self, p: QPainter):
        w, h = self.width(), self.height()
        r, g, b, _ = self._rgb

        # ── Brackets de esquina (el marco táctico, como el HUD de la esfera principal) ──
        L, off = 15, 9
        pen = QPen(QColor(r, g, b, 110))
        pen.setWidthF(1.5)
        p.setPen(pen)
        for (x, y, dx, dy) in ((off, off, 1, 1), (w - off, off, -1, 1),
                               (off, h - off, 1, -1), (w - off, h - off, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + L * dx, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + L * dy))

        # ── Barrido sutil (scanline) recorriendo el panel de arriba a abajo, muy tenue ──
        scan_y = (self._fase * 0.55) % h
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(r, g, b, 0))
        grad.setColorAt(0.5, QColor(r, g, b, 22))
        grad.setColorAt(1.0, QColor(r, g, b, 0))
        p.fillRect(QRectF(10, scan_y, w - 20, 1.3), grad)

        # ── El REACTOR: núcleo que respira (glow radial) + anillo segmentado que gira lento ──
        cx, cy, cr = 27, 26, 9.5
        pulso = 0.5 + 0.5 * math.sin(self._fase * 0.055)

        halo = QRadialGradient(cx, cy, cr * 2.1)
        halo.setColorAt(0.0, QColor(r, g, b, int(70 + 90 * pulso)))
        halo.setColorAt(1.0, QColor(r, g, b, 0))
        p.setBrush(QBrush(halo))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), cr * 2.1, cr * 2.1)

        anillo = QPen(QColor(r, g, b, 225))
        anillo.setWidthF(1.7)
        p.setPen(anillo)
        p.setBrush(Qt.NoBrush)
        segmentos, hueco = 7, 24   # grados de arco visible / grados de hueco -> anillo "táctico"
        rect = QRectF(cx - cr, cy - cr, cr * 2, cr * 2)
        for i in range(segmentos):
            a0 = (i * (360 / segmentos) + self._fase * 0.9) % 360
            p.drawArc(rect, int(a0 * 16), int((360 / segmentos - hueco) * 16))

        p.setBrush(QBrush(QColor(r, g, b, 240)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 2.6, 2.6)


def crear_overlay():
    # Crea, muestra y DEVUELVE el overlay (hay que llamarlo dentro del hilo de Qt). None si falla.
    try:
        ov = OverlayJarvis()
        ov.show()
        return ov
    except Exception as e:
        print(f"[overlay] no se pudo crear: {e}")
        return None
