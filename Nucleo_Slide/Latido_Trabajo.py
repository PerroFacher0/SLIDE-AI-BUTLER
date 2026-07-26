# LATIDO DE TRABAJO: para que Marco SEPA que AIDEN sigue en ello cuando una acción tarda.
#
# Problema que resuelve: algunas acciones tardan (una misión, redactar un documento con el experto,
# resolver un problema en pantalla, un encargo a Claude Code). Si AIDEN se queda callado 2 minutos,
# Marco no sabe si está trabajando o si se colgó. Este "latido" habla cada cierto tiempo ("sigo en
# ello, señor") SOLO si la tarea se alarga — las acciones rápidas no dicen nada (cero ruido).
#
# Uso como context manager:
#     with latido(hablar):        # 'hablar' = hablado_del_asistente o el 'decir' del cerebro
#         resultado = tarea_lenta()
# O manual: l = latido(hablar); l.iniciar(); ...; l.detener().

import random
import threading

_FRASES = (
    "Sigo en ello, señor.",
    "Un momento más; sigo trabajando.",
    "Aún procesando, señor; no me he olvidado.",
    "Sigo en la tarea, señor; deme un instante.",
    "Casi, señor; sigo trabajando en ello.",
)

# A los cuántos segundos suelta el PRIMER aviso (y luego cada tanto). 50s: dentro del primer minuto
# Marco ya oye que sigue vivo, mucho antes de los 2 minutos de silencio que le preocupaban.
INTERVALO = 50


class latido:
    def __init__(self, hablar, cada=INTERVALO):
        self._hablar = hablar
        self._cada = max(12, int(cada or INTERVALO))
        self._stop = threading.Event()
        self._hilo = None

    def iniciar(self):
        if self._hablar and self._hilo is None:
            self._hilo = threading.Thread(target=self._bucle, daemon=True)
            self._hilo.start()
        return self

    def _bucle(self):
        # wait() devuelve False si expiró el tiempo (la tarea sigue) -> avisa; True si ya se detuvo.
        while not self._stop.wait(self._cada):
            try:
                self._hablar(random.choice(_FRASES))
            except Exception:
                pass

    def detener(self):
        self._stop.set()

    def __enter__(self):
        return self.iniciar()

    def __exit__(self, *a):
        self.detener()
        return False
