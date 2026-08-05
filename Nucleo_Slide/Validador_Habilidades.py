# VALIDAR UNA HABILIDAD QUE AIDEN SE ESCRIBIÓ A SÍ MISMO.
#
# Auto_Modificacion recarga EN CALIENTE código que AIDEN acaba de escribirse, dentro de su propio
# proceso. La única puerta era `compile()`, que solo dice que el Python está bien escrito — no que
# haga lo que Marco pidió. Una función con sintaxis impecable y la lógica al revés entraba igual, y
# a partir de ahí AIDEN la ofrece como capacidad suya.
#
# Aquí hay DOS puertas más, en este orden:
#
#   1. LEER el código antes de ejecutarlo (AST). No es una lista de prohibiciones — eso ya existe
#      para PowerShell en Control_Total y duplicarla aquí sería tener dos listas divergiendo. Es
#      una comprobación de COHERENCIA: si Marco pidió "calcular el 19%" y la función borra
#      carpetas o toca el registro, algo no cuadra, y da igual que compile.
#
#   2. EJECUTARLA de mentira, EN OTRO PROCESO. Es la única forma de saber si hace lo que dice. Va
#      en un subproceso aparte y con reloj: si la función generada tiene un bucle infinito, se
#      lleva por delante ese proceso desechable y no el de AIDEN.
#
# El orden importa: primero se LEE, después se ejecuta. Al revés sería ejecutar código sin haberlo
# mirado, que es exactamente lo que se quiere evitar.

import ast
import os
import subprocess
import sys
import tempfile

TIMEOUT_PRUEBA = 5          # s: de sobra para una función sencilla, corto para un bucle infinito

# Cosas que una habilidad normal NO necesita. No es "todo lo peligroso del mundo": es lo que, si
# aparece sin que Marco lo haya pedido, delata que el código se fue por donde no era.
_LLAMADAS_FUERA_DE_LUGAR = {
    "rmtree": "borra carpetas enteras",
    "system": "ejecuta comandos del sistema sin control",
    "popen": "lanza procesos ocultos",
    "remove": "borra archivos",
    "unlink": "borra archivos",
    "rmdir": "borra carpetas",
    "eval": "ejecuta texto como código",
    "exec": "ejecuta texto como código",
    "__import__": "importa por nombre en tiempo de ejecución",
    "SetValueEx": "escribe en el registro de Windows",
    "DeleteKey": "borra claves del registro de Windows",
    "terminate": "mata procesos",
    "kill": "mata procesos",
}
# Si Marco PIDIÓ eso, deja de ser sospechoso. Se mira su instrucción, no una lista fija: pedir
# "una habilidad que limpie los temporales" hace que borrar archivos sea justamente el encargo.
_PERDONA = {
    "rmtree": ("borra", "limpia", "elimina", "vacia", "vacía", "papelera", "temporales"),
    "remove": ("borra", "limpia", "elimina", "vacia", "vacía", "papelera", "temporales"),
    "unlink": ("borra", "limpia", "elimina", "temporales"),
    "rmdir": ("borra", "limpia", "elimina", "carpeta"),
    "system": ("comando", "ejecuta", "consola", "powershell", "cmd"),
    "popen": ("comando", "ejecuta", "consola", "proceso"),
    "terminate": ("cierra", "mata", "termina", "proceso", "app"),
    "kill": ("cierra", "mata", "termina", "proceso", "app"),
    "SetValueEx": ("registro", "regedit"),
    "DeleteKey": ("registro", "regedit"),
}


def _nombre_llamada(nodo):
    f = nodo.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def revisar_codigo(codigo_funcion, instruccion=""):
    """Lee la función SIN ejecutarla. Devuelve (ok, motivo)."""
    try:
        arbol = ast.parse(codigo_funcion)
    except SyntaxError as e:
        return False, f"no es Python válido: {e.msg} (línea {e.lineno})"

    pedido = str(instruccion or "").lower()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = _nombre_llamada(nodo)
        motivo = _LLAMADAS_FUERA_DE_LUGAR.get(nombre)
        if not motivo:
            continue
        if any(p in pedido for p in _PERDONA.get(nombre, ())):
            continue          # Marco pidió justamente eso
        return False, (f"el código {motivo} ({nombre}), y eso no tiene nada que ver con lo que "
                       f"usted pidió")
    return True, ""


def extraer_funcion(codigo_archivo, nombre):
    """El texto de UNA función del archivo. Se valida solo la nueva, no todo lo que ya había."""
    try:
        arbol = ast.parse(codigo_archivo)
    except SyntaxError:
        return None
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name == nombre:
            return ast.get_source_segment(codigo_archivo, nodo)
    return None


# La prueba que escribe Claude Code llama a la función por su NOMBRE SUELTO
# ("assert calcular_iva(100) == ..."), que es como se escribiría naturalmente. Pero la función vive
# dentro del módulo recién cargado, así que sin este volcado a globals() la prueba muere con un
# NameError SIEMPRE — y peor: parecería que la habilidad "falló la prueba" cuando en realidad nunca
# llegó a ejecutarse. Se vuelca el módulo entero, no solo la función, para que una prueba que use
# un ayudante del archivo también funcione.
_GUION = """import sys, importlib.util
spec = importlib.util.spec_from_file_location("_hab", r"{ruta}")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
fn = getattr(m, "{nombre}", None)
if fn is None:
    print("FALTA_FUNCION"); sys.exit(2)
for _k, _v in vars(m).items():
    if not _k.startswith("__"):
        globals()[_k] = _v
{prueba}
print("PRUEBA_OK")
"""


def probar_comportamiento(ruta_archivo, nombre, prueba):
    """Ejecuta la prueba EN OTRO PROCESO y con reloj. Devuelve (ok, motivo).

    En otro proceso porque la función es código recién escrito por un modelo: si entra en un bucle
    infinito o revienta el intérprete, se lleva por delante un proceso desechable. Ejecutarla aquí
    dentro sería colgar a AIDEN para comprobar si algo cuelga."""
    if not str(prueba or "").strip():
        return True, "sin prueba que ejecutar"
    guion = _GUION.format(ruta=ruta_archivo, nombre=nombre, prueba=prueba)
    tmp = os.path.join(tempfile.gettempdir(), f"_aiden_prueba_{os.getpid()}.py")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(guion)
        r = subprocess.run([sys.executable, tmp], capture_output=True, text=True,
                           timeout=TIMEOUT_PRUEBA, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return False, (f"la función se quedó colgada más de {TIMEOUT_PRUEBA} segundos; "
                       "probablemente tiene un bucle infinito")
    except Exception as e:
        return False, f"no pude probarla: {e}"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    if "PRUEBA_OK" in (r.stdout or ""):
        return True, ""
    if "FALTA_FUNCION" in (r.stdout or ""):
        return False, "la función no quedó escrita con el nombre pedido"
    error = (r.stderr or r.stdout or "").strip().split("\n")
    return False, f"la prueba falló: {error[-1][:160] if error else 'sin detalle'}"


def validar(ruta_archivo, nombre, instruccion, prueba=""):
    """Las dos puertas, en orden. Devuelve (ok, motivo_legible)."""
    try:
        with open(ruta_archivo, encoding="utf-8") as f:
            codigo = f.read()
    except Exception as e:
        return False, f"no pude leer el archivo de habilidades: {e}"

    try:
        compile(codigo, ruta_archivo, "exec")          # la puerta que ya existía
    except SyntaxError as e:
        return False, f"quedó con un error de sintaxis en la línea {e.lineno}"

    fuente = extraer_funcion(codigo, nombre)
    if fuente is None:
        return False, f"no encontré la función «{nombre}» en el archivo"

    ok, motivo = revisar_codigo(fuente, instruccion)   # 1) leerla
    if not ok:
        return False, motivo
    return probar_comportamiento(ruta_archivo, nombre, prueba)   # 2) probarla aparte
