# OVERLAY DE PRESENCIA: hace VISIBLE el núcleo Jarvis. Una ventanita siempre-encima, semi-transparente
# y CLICK-THROUGH (no roba el mouse) en una esquina, que muestra EN VIVO lo que AIDEN percibe y piensa:
# tu foco, tu estado, tus metas, los últimos eventos y su lectura de tu momento. Se refresca sola.
#
# Resuelve la queja de Marco de "no se nota en pantalla": todo el trabajo de fondo (Estado_Del_Mundo,
# metas, reflexión) ahora se VE. Es PySide6 (tkinter está prohibido). Aislado: si algo falla, no toca
# la app principal. Debe crearse en el HILO de Qt (lo hace Main_AlwaysOn tras crear la QApplication).

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

# ── Parámetros ajustables ─────────────────────────────────────────────────────
ANCHO, ALTO = 360, 280
MARGEN = 20
REFRESCO_MS = 2500
_MAX_EVENTOS = 3


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
        return (t[:130] + "…") if len(t) > 130 else t
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


def _construir_html():
    est = _estado()

    # Cabecera con "punto latiendo" (color según si Marco está presente).
    presente = est.get("marco_presente", True)
    punto = "#00ffcc" if presente else "#5a6b7a"
    partes = [
        "<div style='display:flex;align-items:center;'>"
        f"<span style='color:{punto};font-size:15px;'>●</span>"
        "<span style='font-size:14px;font-weight:bold;color:#00ffcc;letter-spacing:2px;"
        "margin-left:6px;'>A I D E N</span></div>",
    ]

    # Pensamiento interno (el corazón vivo): frase tenue con un halo.
    pen = _pensamiento()
    if pen:
        partes.append(
            "<div style='color:#8be9fd;font-size:11px;font-style:italic;margin-top:7px;"
            "padding:6px 8px;background:rgba(0,255,204,18);border-left:2px solid rgba(0,255,204,120);"
            f"border-radius:4px;'>“{_esc(pen)[:120]}”</div>"
        )

    partes.append(
        "<div style='color:#9fb3c8;font-size:11px;margin-top:7px;'>Percibo: "
        f"<span style='color:#e6eef7;'>{_esc(_foco_vivo(est))[:40]}</span></div>"
    )

    chips = []
    if not presente:
        chips.append("ausente")
    if est.get("en_reunion"):
        chips.append("reunión")
    if est.get("modo") and est.get("modo") != "normal":
        chips.append(est["modo"])
    if chips:
        partes.append(
            "<div style='margin-top:5px;'>" + "".join(
                f"<span style='color:#0a0e14;background:#ffb454;font-size:10px;font-weight:bold;"
                f"padding:1px 7px;border-radius:8px;margin-right:4px;'>{_esc(c)}</span>"
                for c in chips) + "</div>"
        )

    metas = [m.get("texto", "") for m in (est.get("metas") or []) if m.get("estado") != "hecha"][:2]
    if metas:
        partes.append("<div style='color:#9fb3c8;font-size:11px;margin-top:6px;'>Metas que sigo:</div>")
        for m in metas:
            partes.append(f"<div style='color:#c3f0e0;font-size:11px;'>› {_esc(m)[:42]}</div>")

    evs = (est.get("eventos") or [])[-_MAX_EVENTOS:]
    if evs:
        partes.append("<div style='color:#9fb3c8;font-size:11px;margin-top:6px;'>Reciente:</div>")
        for e in reversed(evs):
            partes.append(
                f"<div style='color:#aebfcf;font-size:10px;'>· [{_esc(e.get('hora',''))}] "
                f"{_esc(e.get('texto',''))[:44]}</div>"
            )

    refl = _reflexion_corta()
    if refl:
        partes.append(
            f"<div style='color:#7d8ea0;font-size:10px;font-style:italic;margin-top:6px;"
            f"border-top:1px solid rgba(120,140,160,40);padding-top:5px;'>{_esc(refl)}</div>"
        )
    return "".join(partes)


def _esc(t):
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class OverlayJarvis(QWidget):
    def __init__(self):
        super().__init__()
        # Sin marco, siempre encima, fuera de la barra de tareas, y SIN robar el foco/los clics.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._label = QLabel("")
        self._label.setTextFormat(Qt.RichText)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.addWidget(self._label)

        self.setStyleSheet(
            "QWidget { background: rgba(6,10,18,215); border: 1px solid rgba(0,255,204,80);"
            " border-radius: 14px; }"
        )
        self.resize(ANCHO, ALTO)
        self._reposicionar()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refrescar)
        self._timer.start(REFRESCO_MS)
        self._refrescar()

    def _reposicionar(self):
        try:
            geo = QGuiApplication.primaryScreen().availableGeometry()
            self.move(geo.right() - self.width() - MARGEN, geo.bottom() - self.height() - MARGEN)
        except Exception:
            pass

    def _refrescar(self):
        try:
            self._label.setText(_construir_html())
        except Exception:
            pass


def crear_overlay():
    # Crea, muestra y DEVUELVE el overlay (hay que llamarlo dentro del hilo de Qt). None si falla.
    try:
        ov = OverlayJarvis()
        ov.show()
        return ov
    except Exception as e:
        print(f"[overlay] no se pudo crear: {e}")
        return None
