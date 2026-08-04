"""Pantalla de carga (splash) de AIDEN.

⚠️  DESCONECTADO A PROPOSITO — NO LO VUELVAS A ENGANCHAR. Ver D17 en
    docs/DECISIONES_Y_FILOSOFIA.md.

    Este splash usa tkinter y causaba un CRASH FATAL al arrancar. La decision se aplico quitando la
    llamada desde Main.py, no borrando el archivo: hoy NADIE lo importa (comprobado), asi que el
    riesgo es cero mientras siga asi. El codigo se conserva por la animacion, no porque se use.

    Si algun dia hace falta un splash, hay que REHACERLO en PySide6 —que ya es dependencia y es lo
    que usan la Mira, el overlay y la esfera— en vez de reactivar este.

Vive aparte de Main.py para no ensuciarlo. Solo usa librerias livianas
(tkinter / threading / math), asi que importarla es instantaneo.

Uso desde Main.py (el splash corre en el hilo PRINCIPAL; la carga en un hilo aparte):
    from Interfaz.Pantalla_Carga import ejecutar, set_progreso, cerrar
    set_progreso(20, "Cargando...") # (desde el hilo de carga) actualiza barra + texto
    cerrar()                        # (desde el hilo de carga) la barra llega a 100%
    ejecutar()                      # (hilo principal) muestra el splash, bloquea hasta cerrar
"""

import threading
import math
import tkinter as tk

_cerrar = threading.Event()
_progreso = {"v": 0, "txt": "Iniciando..."}   # v = 0..100 (compartido con el hilo)


def set_progreso(v, txt):
    _progreso["v"] = v
    _progreso["txt"] = txt


def cerrar():
    _cerrar.set()


def ejecutar():
    try:
        root = tk.Tk()
        root.overrideredirect(True)
        W, H = 460, 320
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw - W)//2}+{(sh - H)//2}")
        root.configure(bg="#060e10")
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        c = tk.Canvas(root, width=W, height=H, bg="#060e10", highlightthickness=0)
        c.pack()
        cx = W // 2
        cyorb = 95
        bx0, bx1, by, bh = 60, W - 60, 250, 14          # geometria de la barra
        st = {"orb_t": 0.0, "mostrado": 0.0}            # estado de animacion
        MILESTONES = (8, 20, 45, 62, 78, 92, 100)       # hitos reales de carga

        def _techo(real):
            for m in MILESTONES:
                if m > real:
                    return m
            return 100

        def dibujar():
            real = 100 if _cerrar.is_set() else _progreso["v"]
            # nunca retroceder: el piso es lo que YA cargo de verdad
            if st["mostrado"] < real:
                st["mostrado"] = real
            # avance GRADUAL hacia justo antes del siguiente hito (creep)
            techo = max(real, _techo(real) - 2)
            if st["mostrado"] < techo:
                st["mostrado"] = min(techo, st["mostrado"] + 0.25)
            # al cerrar, completa suave hasta 100
            if _cerrar.is_set():
                st["mostrado"] += (100 - st["mostrado"]) * 0.25
            val = st["mostrado"]
            st["orb_t"] += 0.15

            c.delete("dyn")
            # anillos HUD + orbe que late
            for rr in (70, 50):
                c.create_oval(cx - rr, cyorb - rr, cx + rr, cyorb + rr,
                              outline="#0a554d", width=1, tags="dyn")
            pulso = 26 + math.sin(st["orb_t"]) * 3
            c.create_oval(cx - pulso, cyorb - pulso, cx + pulso, cyorb + pulso,
                          fill="#00e5cc", outline="", tags="dyn")
            # titulo + etapa actual
            c.create_text(cx, 175, text="A I D E N", fill="#00e5cc",
                          font=("Consolas", 24, "bold"), tags="dyn")
            c.create_text(cx, 205, text=_progreso["txt"], fill="#1e524d",
                          font=("Consolas", 10), tags="dyn")
            # barra: marco + relleno + porcentaje
            c.create_rectangle(bx0, by, bx1, by + bh, outline="#0e3b36", width=1, tags="dyn")
            ancho = int((bx1 - bx0) * max(0, min(100, val)) / 100)
            if ancho > 0:
                c.create_rectangle(bx0, by, bx0 + ancho, by + bh,
                                   fill="#00e5cc", outline="", tags="dyn")
            c.create_text(cx, by + 34, text=f"{int(val)} %", fill="#00e5cc",
                          font=("Consolas", 11, "bold"), tags="dyn")

            if _cerrar.is_set() and val >= 99:
                root.destroy()
                return
            root.after(33, dibujar)

        dibujar()
        root.mainloop()
    except Exception:
        pass   # si tkinter falla, AIDEN igual arranca (solo no se ve el splash)
