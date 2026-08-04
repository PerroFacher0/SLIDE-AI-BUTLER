# PUENTE AL HUD: que una herramienta pueda mostrar algo en pantalla sin arriesgar nada.
#
# La Mira vive en Interfaz/ y arrastra PySide6. Si una herramienta la importara directamente, en una
# máquina sin Qt (o corriendo por Telegram, sin interfaz) ese import reventaría y se llevaría por
# delante la herramienta ENTERA — que por lo demás funcionaba perfectamente. Un adorno visual jamás
# puede tumbar la respuesta.
#
# Por eso el import es perezoso y va envuelto: si el HUD no está, esto devuelve False en silencio y
# la herramienta sigue su camino como si nada. La voz nunca depende de que haya pantalla.
#
# Vive en Nucleo_Slide y no en Interfaz para que las herramientas no tengan que importar la capa
# gráfica ni para preguntarle si existe.


def tarjeta(titulo, lineas, segundos=8.0):
    """Muestra datos estructurados en el HUD. Devuelve True si se pintó, False si no había HUD.
    NUNCA lanza: quien llama puede ignorar el resultado sin envolverlo en un try."""
    try:
        from Interfaz.Mira import presentar_tarjeta
        return bool(presentar_tarjeta(titulo, lineas, segundos))
    except Exception:
        return False


def aviso(texto, segundos=5.0):
    """Un cartel de una sola línea. Mismo trato: si no hay HUD, no pasa nada."""
    try:
        from Interfaz.Mira import mensaje
        return bool(mensaje(texto, segundos))
    except Exception:
        return False
