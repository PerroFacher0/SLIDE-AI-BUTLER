r"""Auditoria de RESILIENCIA de las herramientas de AIDEN.

Nace de un caso real: `obtener_clima` llamaba a requests.get SIN timeout, asi que si wttr.in no
respondia el turno de voz se quedaba colgado para siempre y ni siquiera se podia cancelar (el hilo
estaba bloqueado dentro del socket). Lo encontro Marco usando la app. Este script existe para que
el proximo no haya que encontrarlo asi.

COMO USARLO
    Asistente_Slide_311\Scripts\python.exe Pruebas\auditar_resiliencia.py

QUE BUSCA (y por que importa: todo esto corre DENTRO de un turno de voz)
    1. Red o subprocesos sin timeout   -> cuelgan el turno y no se pueden cancelar
    2. Bucles sin tope ni cancelacion  -> lo mismo, pero por dentro
    3. Archivos/procesos sin proteger  -> revientan el turno con una traza
    4. Excepciones mal manejadas       -> el TTS acaba leyendo "WinError 2" en voz alta
    5. Banderas globales sin finally   -> quedan encendidas tras un fallo y envenenan lo siguiente

COMO LEER EL INFORME
    Lo marcado con !! es ALCANZABLE desde una tool: puede pasarle a Marco hablando. La severidad se
    calcula siguiendo la CADENA DE LLAMADAS, no solo la funcion que contiene el fallo — el bug
    semilla vivia en 'obtener_clima', que no es una tool, pero 'clima' si lo es y lo llama.

SOBRE LOS FALSOS POSITIVOS
    La primera version daba 37 hallazgos de los que solo 3 eran reales: 92% de ruido. Un auditor que
    grita en falso se deja de mirar, y entonces el fallo de verdad se esconde entre el ruido. Por eso
    aqui se descartan A PROPOSITO: los bucles con tope propio (range, contador, limite de tiempo),
    los setters de una linea, y el error crudo de _ejecutar_tool_call — que es deliberado, lo lee el
    MODELO y no el TTS, y el self-healing lo detecta justamente por esas palabras.
    Si añades una regla nueva, mira PRIMERO cuantos falsos positivos genera.
"""
import ast
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALTAR = ("Asistente", "__pycache__", ".git", "perfil_navegador_aiden", "Pruebas")

# ── que funciones son TOOLS de verdad (alcanzables por voz) ──
cfg = ast.parse(open(os.path.join(RAIZ, "Nucleo_Slide", "configuracion_del_agente.py"),
                     encoding="utf-8").read())
TOOLS = set()
for n in ast.walk(cfg):
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "tools_map":
        for k, v in zip(n.value.keys, n.value.values):
            TOOLS.add(getattr(v, "id", None) or k.value)

# ── ALCANCE REAL: que se puede llegar a ejecutar desde una tool ──────────────
# La primera version marcaba critico solo si el fallo estaba DENTRO de la funcion registrada como
# tool. Con eso, el bug semilla salia como no critico: 'obtener_clima' no es una tool — pero
# 'clima' si, y la llama. Un cuelgue a dos saltos cuelga igual el turno de voz. Se construye el
# grafo de llamadas y se marca como critico todo lo ALCANZABLE desde una tool.
_llamadas = {}      # funcion -> {funciones que llama}


def _mapear_llamadas(ruta):
    try:
        arbol = ast.parse(open(ruta, encoding="utf-8").read())
    except Exception:
        return
    for n in ast.walk(arbol):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        destinos = set()
        for x in ast.walk(n):
            if isinstance(x, ast.Call):
                f = x.func
                if isinstance(f, ast.Name):
                    destinos.add(f.id)
                elif isinstance(f, ast.Attribute):
                    destinos.add(f.attr)
        _llamadas.setdefault(n.name, set()).update(destinos)


ALCANZABLES = set()


def _calcular_alcance():
    pendientes = list(TOOLS)
    while pendientes:
        f = pendientes.pop()
        if f in ALCANZABLES:
            continue
        ALCANZABLES.add(f)
        pendientes.extend(_llamadas.get(f, ()))


hallazgos = []


def add(cat, archivo, linea, funcion, detalle, critico=False):
    hallazgos.append({"cat": cat, "archivo": archivo, "linea": linea, "func": funcion,
                      "detalle": detalle, "critico": critico})


def archivos():
    for base, dirs, files in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in SALTAR]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(base, f)


def nombre_llamada(n):
    """requests.get -> 'requests.get'"""
    partes = []
    x = n.func
    while isinstance(x, ast.Attribute):
        partes.append(x.attr)
        x = x.value
    if isinstance(x, ast.Name):
        partes.append(x.id)
    return ".".join(reversed(partes))


RED = ("requests.get", "requests.post", "requests.put", "requests.head", "requests.delete",
       "requests.request", "urlopen", "urllib.request.urlopen", "httpx.get", "httpx.post")
PROC = ("subprocess.run", "subprocess.check_output", "subprocess.call",
        "subprocess.check_call", "communicate")

for ruta in archivos():
    _mapear_llamadas(ruta)
_calcular_alcance()

for ruta in archivos():
    rel = os.path.relpath(ruta, RAIZ)
    try:
        codigo = open(ruta, encoding="utf-8").read()
        arbol = ast.parse(codigo)
    except Exception:
        continue

    # padres, para saber en que funcion cae cada nodo
    padre = {}
    for n in ast.walk(arbol):
        for h in ast.iter_child_nodes(n):
            padre[h] = n

    def func_de(n):
        x = padre.get(n)
        while x is not None:
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return x.name
            x = padre.get(x)
        return "(modulo)"

    def dentro_de_with(n):
        x = padre.get(n)
        while x is not None:
            if isinstance(x, ast.withitem):
                return True
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                return False
            x = padre.get(x)
        return False

    def dentro_de_try(n):
        x = padre.get(n)
        while x is not None:
            if isinstance(x, ast.Try):
                return True
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                return False
            x = padre.get(x)
        return False

    for n in ast.walk(arbol):
        # ── 1. RED / SUBPROCESO sin timeout ──
        if isinstance(n, ast.Call):
            nom = nombre_llamada(n)
            kw = {k.arg for k in n.keywords}
            f = func_de(n)
            if nom in RED and "timeout" not in kw:
                add(1, rel, n.lineno, f, f"{nom}() SIN timeout", critico=(f in ALCANZABLES))
            # Popen(...).communicate() sin timeout tambien cuelga. OJO: asyncio.run NO es
            # subprocess.run y no acepta timeout — filtrarlo evita un falso positivo.
            es_proceso = nom in PROC or nom.endswith(".communicate")
            if es_proceso and not nom.startswith("asyncio") and "timeout" not in kw:
                add(1, rel, n.lineno, f, f"{nom}() SIN timeout", critico=(f in ALCANZABLES))

            # ── 3. archivos/procesos fragiles ──
            if nom == "open" and not dentro_de_with(n) and not dentro_de_try(n):
                add(3, rel, n.lineno, f, "open() sin 'with' y sin try")
            if nom in ("os.remove", "os.unlink", "os.rmdir", "shutil.rmtree") and not dentro_de_try(n):
                add(3, rel, n.lineno, f, f"{nom}() sin try/except")

        # ── 4. except pelado ──
        if isinstance(n, ast.ExceptHandler) and n.type is None:
            add(4, rel, n.lineno, func_de(n), "except: pelado (atrapa Ctrl+C)", critico=True)

        # ── 2. bucles largos sin comprobar cancelacion ──
        # Solo cuenta si el bucle puede correr MUCHO. Un bucle ACOTADO (un for sobre un range, un
        # contador con tope, un limite de tiempo) termina solo, y marcarlo seria ruido: la primera
        # version marcaba ocho y siete estaban acotados. Un auditor que grita en falso se ignora, y
        # entonces el fallo de verdad se esconde entre el ruido.
        if isinstance(n, (ast.While, ast.For)):
            # El CODIGO FUENTE del bucle, no su volcado AST: las heuristicas buscan cosas como
            # "escaneados > 60000" o "range(", que en un ast.dump nunca aparecen con esa forma
            # (ahi seria Name(id='escaneados')). Mirando el dump, todo parecia sin tope.
            fuente = ast.get_source_segment(codigo, n) or ast.dump(n)
            largo = any(p in fuente for p in ("sleep(", "os.walk", "glob"))
            if not largo:
                continue
            f = func_de(n)
            revisa = any(p in fuente for p in ("Cancelacion", "cancelado", "revisar()",
                                               "evento", "is_set()", "parar"))
            # ¿tiene tope propio? un range, un contador con limite, o un limite de tiempo.
            acotado = any(p in fuente for p in (
                "range(", "segundos_max", "limite", "maxlen", "_MAX", "escaneados",
                "time.time() - inicio", "monotonic()", "espera_max", "tope", "break"))
            if not revisa and not acotado and f in ALCANZABLES:
                add(2, rel, n.lineno, f, "bucle SIN tope propio y SIN comprobar cancelacion",
                    critico=True)

    # ── 4b. mensajes de error crudos (sin el estilo 'señor') ──
    for n in ast.walk(arbol):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.JoinedStr):
            texto = "".join(v.value for v in n.value.values if isinstance(v, ast.Constant))
            tiene_exc = any(isinstance(v, ast.FormattedValue) for v in n.value.values)
            # _ejecutar_tool_call NO va al TTS: su texto lo lee el MODELO, y el self-healing
            # detecta el fallo justamente por esas palabras. "Arreglarlo" romperia esa deteccion.
            if func_de(n) in ("_ejecutar_tool_call",):
                continue
            if tiene_exc and re.search(r"error|fall|exception|problema", texto, re.I):
                if "señor" not in texto.lower():
                    add(4, rel, n.lineno, func_de(n),
                        f"error devuelto SIN estilo 'señor': {texto.strip()[:48]!r}")

    # ── 5. bandera global sin finally ──
    # El patron PELIGROSO no es "tocar una global": es ENCENDER una bandera, hacer un trabajo largo
    # que puede reventar, y que el apagado quede fuera de un finally. Un `_pausado = bool(x)` de una
    # linea no puede quedarse a medias — marcarlo era ruido puro (25 de 25 falsos positivos).
    for n in ast.walk(arbol):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = ast.dump(n)
            if "Global(" not in cuerpo:
                continue
            enciende = "value=Constant(value=True)" in cuerpo
            hace_trabajo = any(isinstance(x, (ast.While, ast.For)) for x in ast.walk(n))
            if not (enciende and hace_trabajo):
                continue
            asigna = re.findall(r"Global\(names=\['(\w+)'\]", cuerpo)
            if asigna and "finally" not in codigo[n.lineno - 1: n.end_lineno].lower():
                tiene_finally = any(isinstance(x, ast.Try) and x.finalbody for x in ast.walk(n))
                if not tiene_finally and len(asigna) and n.name in ALCANZABLES:
                    add(5, rel, n.lineno, n.name,
                        f"toca la global {asigna[0]!r} sin finally que la restaure")

# ── informe ──
TITULOS = {
 1: "I/O y RED que puede COLGARSE (sin timeout)",
 2: "BUCLES largos sin comprobar cancelacion",
 3: "ARCHIVOS/PROCESOS fragiles",
 4: "EXCEPCIONES mal manejadas o trazas expuestas",
 5: "ESTADO GLOBAL que puede quedar sucio",
}
print("=" * 80)
print(f"AUDITORIA DE RESILIENCIA — {len(TOOLS)} tools alcanzables por voz")
print("=" * 80)
for cat in (1, 2, 3, 4, 5):
    items = [h for h in hallazgos if h["cat"] == cat]
    criticos = [h for h in items if h["critico"]]
    print(f"\n[{cat}] {TITULOS[cat]}   ->  {len(items)} ({len(criticos)} criticos)")
    if not items:
        print("     nada")
        continue
    for h in sorted(items, key=lambda x: (not x["critico"], x["archivo"])):
        marca = "  !! " if h["critico"] else "     "
        tool = ("  <-- ES TOOL" if h["func"] in TOOLS else
                ("  <-- alcanzable desde una tool" if h["func"] in ALCANZABLES else ""))
        print(f"{marca}{os.path.basename(h['archivo']):28} L{h['linea']:<5} "
              f"{h['func']:26} {h['detalle']}{tool}")

print("\n" + "=" * 80)
print(f"TOTAL: {len(hallazgos)} hallazgos | CRITICOS (alcanzables desde una tool): "
      f"{len([h for h in hallazgos if h['critico']])}")
