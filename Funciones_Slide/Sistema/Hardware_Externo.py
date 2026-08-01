# PUENTE A HARDWARE EXTERNO: que AIDEN tenga cuerpo físico fuera de la pantalla.
#
# Un microcontrolador (ESP32/Arduino) conectado por USB da lo que ninguna ventana da: un LED que
# cambia de color según lo que AIDEN esté haciendo y se ve de reojo sin mirar el monitor, un relé
# para encender la lámpara del escritorio, una pantallita con el siguiente evento, y un botón físico
# para hablarle sin decir la palabra clave.
#
# ⚠️  SIN PROBAR CONTRA HARDWARE REAL. Marco todavía no tiene la placa (dijo que la compraría más
#     adelante). El código está completo y el protocolo definido, pero NADA de esto se ha ejecutado
#     contra un ESP32 físico: lo único verificado es que se comporta bien cuando NO hay nada
#     conectado (no cuelga, no revienta, avisa con claridad). Cuando llegue la placa, cárguele el
#     firmware de abajo y pruebe primero 'escanear'.
#
# PROTOCOLO (líneas JSON terminadas en \n, 115200 baudios):
#   PC  -> placa:  {"cmd":"PING"}                          {"cmd":"ESTADO","valor":"pensando"}
#                  {"cmd":"RELE","pin":5,"valor":1}        {"cmd":"DISPLAY","texto":"Hola"}
#   placa -> PC:   {"status":"AIDEN_HW_OK","device":"esp32-escritorio"}
#                  {"evento":"boton","pin":0}
#
# ── FIRMWARE DE REFERENCIA (Arduino / ESP32) ─────────────────────────────────
#   #include <ArduinoJson.h>
#   #include <Adafruit_NeoPixel.h>
#   Adafruit_NeoPixel led(1, 48, NEO_GRB + NEO_KHZ800);
#
#   void setup() {
#     Serial.begin(115200);
#     led.begin(); led.show();
#     pinMode(0, INPUT_PULLUP);   // botón físico
#     pinMode(5, OUTPUT);         // relé
#   }
#
#   void loop() {
#     if (Serial.available()) {
#       StaticJsonDocument<256> d;
#       if (!deserializeJson(d, Serial.readStringUntil('\n'))) {
#         String cmd = d["cmd"] | "";
#         if (cmd == "PING") {
#           Serial.println("{\"status\":\"AIDEN_HW_OK\",\"device\":\"esp32-escritorio\"}");
#         } else if (cmd == "ESTADO") {
#           String v = d["valor"] | "";
#           uint32_t c = led.Color(0, 0, 0);
#           if (v == "escuchando") c = led.Color(0, 80, 255);
#           else if (v == "pensando") c = led.Color(255, 170, 0);
#           else if (v == "ejecutando") c = led.Color(0, 255, 80);
#           else if (v == "error")     c = led.Color(255, 0, 0);
#           led.setPixelColor(0, c); led.show();
#           Serial.println("{\"status\":\"OK\"}");
#         } else if (cmd == "RELE") {
#           digitalWrite(d["pin"] | 5, (int)(d["valor"] | 0));
#           Serial.println("{\"status\":\"OK\"}");
#         } else if (cmd == "DISPLAY") {
#           // ...pintar d["texto"] en la OLED...
#           Serial.println("{\"status\":\"OK\"}");
#         }
#       }
#     }
#     static bool antes = HIGH;
#     bool ahora = digitalRead(0);
#     if (antes == HIGH && ahora == LOW) Serial.println("{\"evento\":\"boton\",\"pin\":0}");
#     antes = ahora;
#   }

import json
import threading
import time

BAUDIOS = 115200
_TIMEOUT_SALUDO = 0.5      # s de espera al PING (una placa viva contesta en milisegundos)
_TIMEOUT_CMD = 1.0

_conexion = None
_puerto_activo = None
_lock = threading.RLock()
_al_pulsar_boton = None    # callback opcional: se llama cuando la placa reporta un botón físico

_COLORES = ("escuchando", "pensando", "ejecutando", "exito", "error", "reposo")


def _serial():
    try:
        import serial
        return serial
    except Exception:
        return None


def _hablar_con(puerto, mensaje, espera=_TIMEOUT_CMD):
    """Manda una línea JSON y devuelve la respuesta decodificada, o None."""
    serial = _serial()
    if serial is None:
        return None
    try:
        with serial.Serial(puerto, BAUDIOS, timeout=espera) as s:
            time.sleep(0.15)                      # el ESP32 se reinicia al abrirse el puerto
            s.reset_input_buffer()
            s.write((json.dumps(mensaje) + "\n").encode())
            s.flush()
            linea = s.readline().decode("utf-8", "replace").strip()
        return json.loads(linea) if linea.startswith("{") else None
    except Exception:
        return None


def _es_nuestra(puerto):
    r = _hablar_con(puerto, {"cmd": "PING"}, _TIMEOUT_SALUDO)
    return r if r and r.get("status") == "AIDEN_HW_OK" else None


def escanear():
    """Busca en todos los puertos COM una placa que conteste el saludo de AIDEN."""
    serial = _serial()
    if serial is None:
        return [], "No tengo la librería de puerto serie, señor. Se instala con: pip install pyserial"
    try:
        from serial.tools import list_ports
        puertos = list(list_ports.comports())
    except Exception as e:
        return [], f"No pude listar los puertos, señor: {e}"
    if not puertos:
        return [], "No hay ningún dispositivo conectado por USB serie, señor."
    encontradas = []
    for p in puertos:
        r = _es_nuestra(p.device)
        if r:
            encontradas.append((p.device, r.get("device", "placa")))
    return encontradas, ""


def _asegurar_puerto(puerto="AUTO"):
    """Devuelve el puerto a usar: el pedido, el ya conocido, o el primero que salude."""
    global _puerto_activo
    with _lock:
        if puerto and puerto != "AUTO":
            _puerto_activo = puerto
            return puerto
        if _puerto_activo and _es_nuestra(_puerto_activo):
            return _puerto_activo
        halladas, _err = escanear()
        _puerto_activo = halladas[0][0] if halladas else None
        return _puerto_activo


def _escuchar_placa(puerto, al_pulsar):
    """Hilo lector: la placa puede hablar sin que le pregunten (el botón físico)."""
    serial = _serial()
    if serial is None:
        return
    try:
        with serial.Serial(puerto, BAUDIOS, timeout=1) as s:
            while True:
                linea = s.readline().decode("utf-8", "replace").strip()
                if not linea.startswith("{"):
                    continue
                try:
                    d = json.loads(linea)
                except Exception:
                    continue
                if d.get("evento") == "boton" and callable(al_pulsar):
                    try:
                        al_pulsar()
                    except Exception:
                        pass
    except Exception:
        return


def iniciar_escucha_hardware(al_pulsar_boton):
    """Arranca el hilo que oye el botón físico, si hay placa. Silencioso si no hay nada."""
    global _al_pulsar_boton
    _al_pulsar_boton = al_pulsar_boton
    puerto = _asegurar_puerto()
    if not puerto:
        return False
    threading.Thread(target=_escuchar_placa, args=(puerto, al_pulsar_boton), daemon=True).start()
    print(f"[Hardware] placa escuchando en {puerto}")
    return True


def hardware(accion="escanear", puerto="AUTO", comando="", valor=0, datos=None):
    """HERRAMIENTA: habla con la placa (ESP32/Arduino) conectada por USB — LED de estado, relés
    para luces, y pantallita.
      accion = escanear | estado | salida | pantalla
      comando = para 'estado': escuchando|pensando|ejecutando|exito|error|reposo
                para 'salida': el pin o el nombre del aparato
      valor   = para 'salida': 0 apaga, 1 enciende (o 0-255 si es PWM)."""
    a = str(accion or "").strip().lower()

    if a.startswith("escan") or a.startswith("busc") or a.startswith("list"):
        halladas, err = escanear()
        if err:
            return err
        if not halladas:
            return ("No encontré ninguna placa de AIDEN conectada, señor. Verifique el cable y que "
                    "tenga cargado el firmware que responde al saludo.")
        return "Placas conectadas, señor: " + "; ".join(f"{d} en {p}" for p, d in halladas)

    p = _asegurar_puerto(puerto)
    if not p:
        return ("No tengo ninguna placa conectada, señor. Conéctela por USB y pídame que escanee.")

    if a.startswith("estad") or a.startswith("color") or a.startswith("luz"):
        c = str(comando or "reposo").strip().lower()
        if c not in _COLORES:
            return f"No conozco el estado «{c}», señor. Tengo: {', '.join(_COLORES)}."
        r = _hablar_con(p, {"cmd": "ESTADO", "valor": c})
        return f"Placa en «{c}», señor." if r else "La placa no me contestó, señor."

    if a.startswith("salid") or a.startswith("rele") or a.startswith("relé") or a.startswith("pin"):
        try:
            pin = int(comando) if str(comando).strip().isdigit() else int((datos or {}).get("pin", 5))
        except (TypeError, ValueError):
            pin = 5
        try:
            v = int(valor)
        except (TypeError, ValueError):
            v = 0
        r = _hablar_con(p, {"cmd": "RELE", "pin": pin, "valor": v})
        estado = "encendida" if v else "apagada"
        return f"Salida {pin} {estado}, señor." if r else "La placa no me contestó, señor."

    if a.startswith("pantall") or a.startswith("display") or a.startswith("escrib"):
        texto = str(comando or (datos or {}).get("texto", "")).strip()
        if not texto:
            return "¿Qué quiere que muestre en la pantallita, señor?"
        r = _hablar_con(p, {"cmd": "DISPLAY", "texto": texto[:64]})
        return f"Puesto en la pantalla, señor: {texto[:40]}" if r else "La placa no me contestó, señor."

    return "¿Qué hago con la placa, señor? (escanear, estado, salida o pantalla)"
