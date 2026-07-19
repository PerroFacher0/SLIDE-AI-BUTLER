# Generador del icono de AIDEN — reactor arc estilo Jarvis: núcleo con degradado, halo de energía,
# anillos HUD con marcas y una insignia limpia que se lee bien hasta a 16x16.
# Corre: python Pruebas/_gen_icono.py   (escribe AIDEN.ico en la raíz del proyecto).

from PIL import Image, ImageDraw, ImageFilter
import math
import os

S = 1024
AQ = (0, 229, 204)          # aqua AIDEN
AQ_HI = (150, 255, 240)     # brillo interior
BG1 = (10, 18, 26)          # fondo del tile (arriba)
BG2 = (4, 8, 13)            # fondo del tile (abajo)
cx, cy = S // 2, S // 2

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# ── Tile redondeado con degradado vertical ────────────────────────────────────
grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
gp = grad.load()
for y in range(S):
    f = y / S
    r = int(BG1[0] * (1 - f) + BG2[0] * f)
    g = int(BG1[1] * (1 - f) + BG2[1] * f)
    b = int(BG1[2] * (1 - f) + BG2[2] * f)
    for x in range(S):
        gp[x, y] = (r, g, b, 255)
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
img.paste(grad, (0, 0), mask)

# ── Halo de energía radial detrás del núcleo ──────────────────────────────────
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for i in range(80, 0, -1):
    rad = int(S * 0.40 * i / 80)
    a = int(70 * (i / 80) ** 2.2)
    gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(AQ[0], AQ[1], AQ[2], a))
glow = glow.filter(ImageFilter.GaussianBlur(S * 0.04))
img = Image.alpha_composite(img, glow)

d = ImageDraw.Draw(img)

# ── Anillo exterior con SEGMENTOS (estilo HUD reactor) ────────────────────────
r_out = int(S * 0.40)
for k in range(24):
    a0 = k * 15 + 3
    a1 = a0 + 9
    d.arc([cx - r_out, cy - r_out, cx + r_out, cy + r_out], a0, a1,
          fill=(AQ[0], AQ[1], AQ[2], 230), width=max(3, int(S * 0.012)))

# ── Anillo medio continuo + marcas radiales (ticks) ───────────────────────────
r_mid = int(S * 0.30)
d.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
          outline=(AQ[0], AQ[1], AQ[2], 255), width=max(3, int(S * 0.010)))
for j in range(36):
    ang = j * (2 * math.pi / 36)
    r1 = r_mid + int(S * 0.015)
    r2 = r_mid + int(S * 0.035)
    d.line([cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
            cx + math.cos(ang) * r2, cy + math.sin(ang) * r2],
           fill=(AQ[0], AQ[1], AQ[2], 150), width=max(2, int(S * 0.004)))

# ── Núcleo con degradado radial (brillo arriba-izquierda) ─────────────────────
core_r = int(S * 0.17)
core = Image.new("RGBA", (S, S), (0, 0, 0, 0))
cp = core.load()
lx, ly = cx - core_r * 0.35, cy - core_r * 0.35   # centro del brillo
for y in range(cy - core_r, cy + core_r):
    for x in range(cx - core_r, cx + core_r):
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy <= core_r * core_r:
            dl = math.hypot(x - lx, y - ly) / (core_r * 1.6)
            dl = max(0.0, min(1.0, dl))
            r = int(AQ_HI[0] * (1 - dl) + AQ[0] * dl)
            g = int(AQ_HI[1] * (1 - dl) + AQ[1] * dl)
            b = int(AQ_HI[2] * (1 - dl) + AQ[2] * dl)
            cp[x, y] = (r, g, b, 255)
img = Image.alpha_composite(img, core)

# ── Chispa central brillante ──────────────────────────────────────────────────
d = ImageDraw.Draw(img)
sr = int(core_r * 0.30)
d.ellipse([cx - sr, cy - sr, cx + sr, cy + sr], fill=(235, 255, 252, 235))

# ── Guardar en la RAÍZ del proyecto ───────────────────────────────────────────
raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ruta_ico = os.path.join(raiz, "AIDEN.ico")
img.save(ruta_ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.resize((256, 256), Image.LANCZOS).save(os.path.join(raiz, "_preview_icono.png"))
print("Listo: " + ruta_ico + " + _preview_icono.png")
