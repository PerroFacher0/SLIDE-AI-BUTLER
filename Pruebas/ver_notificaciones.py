# Diagnóstico: ¿AIDEN está viendo las notificaciones de Windows?
#
# De esa base de datos comen DOS cosas que fallan EN SILENCIO si algo se rompe:
#   · el vigilante de GASTOS (Info/Finanzas_Gastos.py), que caza los pagos de Nequi/Nu
#     leyendo sus notificaciones — si el banco cambia el texto, deja de contar y nadie se entera;
#   · el RESUMEN DE ACTIVIDAD (Info/Bitacora.py), el "qué me perdí mientras no estaba".
#
# ANTES este archivo diagnosticaba la detección de LLAMADAS por notificación. Eso quedó obsoleto:
# se descubrió que WhatsApp no manda toast para las llamadas, sino que abre una VENTANA, así que el
# vigilante se reescribió sobre ventanas y estas funciones dejaron de existir (el script llevaba
# tiempo sin poder ni arrancar). Para las llamadas usa ahora `ver_ventanas.py` y `probar_llamada.py`.
#
# CÓMO USARLO
#   1. Terminal en la carpeta del proyecto (SLIDE-AI-BUTLER).
#   2. Revisar lo de las últimas horas (no hay que esperar a nada):
#        Asistente_Slide_311\Scripts\python.exe Pruebas\ver_notificaciones.py --historial 6
#   3. O quedarse escuchando en vivo y provocar una notificación (hazte un pago pequeño, o
#      pídele a alguien que te escriba):
#        Asistente_Slide_311\Scripts\python.exe Pruebas\ver_notificaciones.py
#   4. Ctrl+C para salir.
#
# CÓMO LEER LA SALIDA
#   [GASTO]  -> AIDEN lo cuenta como gasto, y dice cuánto y en qué. Eso es lo que debe pasar
#               con un pago de Nequi/Nu.
#   [banco]  -> viene de un banco pero NO lo cuenta (¿es un ingreso? ¿cambió el texto?).
#               Si ves un PAGO tuyo aquí, cópiame la línea: hay que afinar las palabras clave.
#   [ ]      -> notificación normal, nada que ver con dinero.

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

# Permite ejecutar el script desde la carpeta Pruebas.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from Funciones_Slide.Info.Finanzas_Gastos import (
    _BANCO_KW, _EPOCH_WIN, _WPN, _es_gasto, _leer_nuevas, _max_arrival,
)


def _hora(ft):
    """FILETIME de Windows -> 'HH:MM:SS'."""
    try:
        return (_EPOCH_WIN + timedelta(microseconds=int(ft) / 10)).strftime("%H:%M:%S")
    except Exception:
        return "??:??:??"


def _clasificar(texto):
    """(etiqueta, detalle) tal y como lo decidiría AIDEN."""
    gasto = _es_gasto(texto)
    if gasto:
        monto, concepto = gasto
        return "GASTO", f"${monto:,.0f}" + (f" en {concepto}" if concepto else "")
    if any(b in (texto or "").lower() for b in _BANCO_KW):
        return "banco", "del banco, pero NO lo cuento como gasto"
    return "", ""


def _mostrar(texto, arrival):
    etiqueta, detalle = _clasificar(texto)
    marca = f"[{etiqueta}]".ljust(9) if etiqueta else "[ ]".ljust(9)
    print(f"  {_hora(arrival)}  {marca} {texto[:120]!r}")
    if detalle:
        print(f"{'':>13}         -> {detalle}")
    return etiqueta


def _revisar_salud():
    print("=" * 78)
    if not _WPN or not os.path.exists(_WPN):
        print("PROBLEMA: no encuentro la base de notificaciones de Windows.")
        print(f"  esperaba: {_WPN or '(ruta vacia)'}")
        print("  Sin ella, AIDEN NO puede capturar sus gastos ni resumir lo que se perdio.")
        return False
    mb = os.path.getsize(_WPN) / 1e6
    print(f"Base de notificaciones: OK ({mb:.1f} MB)")
    print(f"  {_WPN}")
    if _max_arrival() is None:
        print("PROBLEMA: la base existe pero no pude leerla (¿permisos? ¿bloqueada?).")
        return False
    return True


def historial(horas):
    desde = datetime.now() - timedelta(hours=horas)
    desde_ft = int((desde - _EPOCH_WIN).total_seconds() * 10_000_000)
    filas = [(t, a) for t, a in _leer_nuevas(desde_ft) if (t or "").strip()]
    print("=" * 78)
    print(f"ULTIMAS {horas} HORAS — {len(filas)} notificaciones con texto")
    print("=" * 78)
    if not filas:
        print("  (ninguna) Si esperaba ver algo, revise que las apps tengan las notificaciones")
        print("  activadas en Configuracion de Windows > Sistema > Notificaciones.")
        return
    cuenta = {"GASTO": 0, "banco": 0, "": 0}
    for texto, arrival in filas:
        cuenta[_mostrar(texto, arrival)] += 1
    print("-" * 78)
    print(f"RESUMEN: {cuenta['GASTO']} contadas como gasto | "
          f"{cuenta['banco']} del banco sin contar | {cuenta['']} normales")
    if cuenta["banco"] and not cuenta["GASTO"]:
        print("\nOJO: llegaron notificaciones del banco pero NINGUNA se conto como gasto.")
        print("Si alguna era un pago suyo, copieme esa linea: hay que afinar las palabras clave.")


def en_vivo():
    umbral = _max_arrival()
    if umbral is None:
        return
    print("=" * 78)
    print("ESCUCHANDO notificaciones nuevas... (Ctrl+C para salir)")
    print("Provoque una: haga un pago pequeño, o pida que le escriban.")
    print("=" * 78)
    try:
        while True:
            for texto, arrival in _leer_nuevas(umbral):
                if arrival > umbral:
                    umbral = arrival
                if (texto or "").strip():
                    _mostrar(texto, arrival)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nListo, fin del diagnostico.")


def main():
    p = argparse.ArgumentParser(description="¿AIDEN ve las notificaciones de Windows?")
    p.add_argument("--historial", type=int, metavar="HORAS",
                   help="Revisa las ultimas N horas y sale (en vez de escuchar en vivo).")
    args = p.parse_args()

    if not _revisar_salud():
        sys.exit(1)
    if args.historial:
        historial(args.historial)
    else:
        en_vivo()


if __name__ == "__main__":
    main()
