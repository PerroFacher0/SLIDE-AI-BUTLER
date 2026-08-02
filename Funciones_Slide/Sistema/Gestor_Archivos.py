# EJECUTOR DE SISTEMA PROFUNDO: mueve/copia/busca archivos en CUALQUIER parte del disco, directo
# con os/shutil/pathlib — sin abrir el Explorador de Windows ni depender de que algo se vea en
# pantalla. Es el complemento de precisión de ejecutar_en_pc (la llave maestra vía PowerShell):
# aquí no se compone un comando de texto cada vez, hay resultados ESTRUCTURADOS (no hay que
# parsear salida de consola) y cero overhead de levantar un proceso de PowerShell por cada
# operación. buscar_archivo (Control_PC.py) sigue viva para su caso rápido (6 carpetas conocidas,
# abre el archivo); esto es para "busca/mueve/copia en TODO el disco, sin abrir nada".
#
# SEGURIDAD: mover/copiar se niega si origen o destino caen dentro de una carpeta protegida del
# sistema (Windows, Program Files, ProgramData\Microsoft) — igual de irreversible que tocar el
# registro o formatear, así que se bloquea aunque Marco sea el dueño. Buscar y leer metadatos NO
# tiene restricción (es de solo lectura).

import os
import re
import shutil
import time
from pathlib import Path

_RAIZ_USUARIO = os.path.expanduser("~")

# Alias en lenguaje natural -> ruta real. Cubre lo que Marco diría por voz sin dictar una ruta
# completa ("ponlo en appdata", "la carpeta de mods de Minecraft").
_ALIAS_CARPETAS = {
    "escritorio": os.path.join(_RAIZ_USUARIO, "Desktop"),
    "documentos": os.path.join(_RAIZ_USUARIO, "Documents"),
    "descargas": os.path.join(_RAIZ_USUARIO, "Downloads"),
    "imagenes": os.path.join(_RAIZ_USUARIO, "Pictures"),
    "musica": os.path.join(_RAIZ_USUARIO, "Music"),
    "videos": os.path.join(_RAIZ_USUARIO, "Videos"),
    "appdata": os.path.join(_RAIZ_USUARIO, "AppData", "Roaming"),
    "appdata roaming": os.path.join(_RAIZ_USUARIO, "AppData", "Roaming"),
    "appdata local": os.path.join(_RAIZ_USUARIO, "AppData", "Local"),
    "mods de minecraft": os.path.join(_RAIZ_USUARIO, "AppData", "Roaming", ".minecraft", "mods"),
    "carpeta de mods": os.path.join(_RAIZ_USUARIO, "AppData", "Roaming", ".minecraft", "mods"),
    "minecraft": os.path.join(_RAIZ_USUARIO, "AppData", "Roaming", ".minecraft"),
}

# Carpetas ruidosas/pesadas que se SALTAN solo al barrer algo amplio (una unidad entera): no tiene
# sentido perder segundos recorriendo Windows/Program Files buscando un archivo del usuario.
_CARPETAS_A_SALTAR = {
    "windows", "program files", "program files (x86)", "$recycle.bin",
    "programdata", "node_modules", "system volume information", ".git",
}

_RUTAS_PROTEGIDAS = tuple(
    os.path.abspath(p) for p in (
        os.environ.get("SystemRoot", r"C:\Windows"),
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\ProgramData\Microsoft",
    )
)


def _es_ruta_protegida(ruta):
    try:
        r = os.path.abspath(ruta).lower()
    except (OSError, ValueError):
        return True   # ruta rara -> mejor negarse que arriesgar
    return any(r.startswith(p.lower()) for p in _RUTAS_PROTEGIDAS)


def _resolver_carpeta(texto):
    """Convierte un alias natural ('appdata', 'mods de minecraft') o una ruta ya escrita (soporta
    %VARS% y ~) en una ruta absoluta real. None si no se pudo resolver de ninguna forma."""
    t = str(texto or "").strip()
    if not t:
        return None
    clave = t.lower()
    if clave in _ALIAS_CARPETAS:
        return _ALIAS_CARPETAS[clave]
    expandido = os.path.expandvars(os.path.expanduser(t))
    if os.path.isabs(expandido) or re.match(r"^[a-zA-Z]:\\", expandido):
        return expandido
    for alias, ruta in _ALIAS_CARPETAS.items():   # coincidencia parcial ("la carpeta de mods")
        if alias in clave or clave in alias:
            return ruta
    return None


def buscar_en_disco(patron, raiz=None, limite=15, segundos_max=15):
    """Busca archivos cuyo NOMBRE contenga 'patron' (sin distinguir mayúsculas/acentos simples),
    recorriendo 'raiz' (por defecto toda la carpeta de usuario: ya cubre Escritorio/Documentos/
    Descargas/AppData). Devuelve lista de dicts {ruta, tamano_mb, modificado}. NUNCA lanza
    excepción: permisos denegados o rutas raras se saltan (es lo esperado al recorrer un disco
    real, no un fallo del programa)."""
    patron_n = str(patron or "").strip().lower()
    if not patron_n:
        return []
    raiz_real = _resolver_carpeta(raiz) if raiz else _RAIZ_USUARIO
    if not raiz_real or not os.path.isdir(raiz_real):
        raiz_real = _RAIZ_USUARIO
    encontrados = []
    inicio = time.time()
    for dirpath, dirs, files in os.walk(raiz_real, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if d.lower() not in _CARPETAS_A_SALTAR]
        for nombre in files:
            if patron_n in nombre.lower():
                ruta = os.path.join(dirpath, nombre)
                try:
                    st = os.stat(ruta)
                except OSError:
                    continue   # borrado/bloqueado justo entre el listado y el stat: se ignora
                encontrados.append({
                    "ruta": ruta,
                    "tamano_mb": round(st.st_size / (1024 * 1024), 2),
                    "modificado": time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
                })
                if len(encontrados) >= limite:
                    return encontrados
        if time.time() - inicio > segundos_max:
            break   # tope de tiempo: mejor una respuesta parcial rápida que colgar la voz
    return encontrados


def metadatos_de(ruta):
    """Metadatos reales de 'ruta' (tamaño, fechas, tipo) vía pathlib.Path.stat(), o None si no
    existe / no se puede leer. Nunca deja escapar una excepción."""
    try:
        p = Path(str(ruta or "").strip())
        if not p.exists():
            return None
        st = p.stat()
        return {
            "ruta": str(p.resolve()),
            "es_carpeta": p.is_dir(),
            "tamano_mb": round(st.st_size / (1024 * 1024), 2) if p.is_file() else None,
            "creado": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_ctime)),
            "modificado": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
            "extension": p.suffix.lower() or None,
        }
    except (OSError, ValueError):
        return None


def mover_o_copiar(origen, destino_carpeta, mover=False):
    """Mueve (mover=True) o copia 'origen' hacia 'destino_carpeta' (ruta o alias como 'appdata'/
    'mods de minecraft'). Si 'origen' no es ya una ruta exacta, lo BUSCA por nombre primero (Marco
    no dicta rutas completas por voz). Crea la carpeta destino si hace falta; nunca pisa un
    archivo existente (le añade _1, _2...). Devuelve (True, ruta_final) o (False, motivo)."""
    origen_p = str(origen or "").strip()
    if not origen_p or not os.path.isfile(origen_p):
        candidatos = buscar_en_disco(origen_p, limite=1) if origen_p else []
        if not candidatos:
            return False, f"no encontré ningún archivo llamado «{origen}»"
        origen_p = candidatos[0]["ruta"]
    destino_real = _resolver_carpeta(destino_carpeta)
    if not destino_real:
        return False, f"no pude ubicar la carpeta destino «{destino_carpeta}»"
    if _es_ruta_protegida(origen_p) or _es_ruta_protegida(destino_real):
        return False, "eso toca una carpeta protegida del sistema (Windows/Program Files); me niego por seguridad"
    try:
        os.makedirs(destino_real, exist_ok=True)
        destino_final = os.path.join(destino_real, os.path.basename(origen_p))
        base, ext = os.path.splitext(destino_final)
        k = 1
        while os.path.exists(destino_final):
            destino_final = f"{base}_{k}{ext}"
            k += 1
        (shutil.move if mover else shutil.copy2)(origen_p, destino_final)
        return True, destino_final
    except PermissionError:
        return False, "no tengo permiso para escribir ahí (¿archivo en uso o carpeta protegida?)"
    except FileNotFoundError:
        return False, "la ruta desapareció a mitad de camino (¿algo lo movió o borró?)"
    except OSError as e:
        return False, f"error del sistema de archivos: {e}"


def _abrir_archivo(nombre):
    """Busca un archivo por nombre en las carpetas de Marco y ABRE el primero que aparezca."""
    from Funciones_Slide.Sistema.Control_PC import buscar_archivo
    return buscar_archivo(nombre)


def _abrir_carpeta(nombre):
    """Abre una carpeta en el Explorador de Windows."""
    from Funciones_Slide.Sistema.Control_PC import abrir_carpeta
    return abrir_carpeta(nombre)


def _resolver(nombre):
    """Acepta una ruta completa o un nombre suelto; si es suelto, lo busca. Devuelve ruta o None."""
    nombre = str(nombre or "").strip().strip('"')
    if not nombre:
        return None
    if os.path.exists(nombre):
        return os.path.abspath(nombre)
    try:
        hallados = buscar_en_disco(nombre, limite=1)   # el buscador que ya usa esta herramienta
        return hallados[0]["ruta"] if hallados else None
    except Exception:
        return None


def _a_la_papelera(que):
    """Borrado REVERSIBLE. Un asistente que borra por voz tiene que poder equivocarse sin que sea
    definitivo: a la Papelera, no al vacío. Si la librería no está, se avisa MUY claro antes de
    borrar de verdad — nunca se hace un borrado irreversible haciéndolo pasar por uno reversible."""
    ruta = _resolver(que)
    if ruta is None:
        return f"No encontré «{que}» para borrarlo, señor."
    if _es_ruta_protegida(ruta):
        return f"No toco «{ruta}», señor: está en una carpeta del sistema."
    try:
        from send2trash import send2trash
    except Exception:
        return (f"Encontré «{os.path.basename(ruta)}», señor, pero no puedo mandarlo a la papelera: "
                "falta la librería (pip install send2trash). No lo borro de forma definitiva sin "
                "que usted lo diga, porque eso no tendría vuelta atrás.")
    try:
        send2trash(ruta)
        return f"Envié «{os.path.basename(ruta)}» a la papelera de reciclaje, señor."
    except Exception as e:
        return f"No pude enviarlo a la papelera, señor: {e}"


def _comprimir(que, destino=""):
    ruta = _resolver(que)
    if ruta is None:
        return f"No encontré «{que}» para comprimir, señor."
    salida = str(destino or "").strip() or os.path.splitext(ruta)[0] + ".zip"
    if not salida.lower().endswith(".zip"):
        salida += ".zip"
    if not os.path.isabs(salida):
        salida = os.path.join(os.path.dirname(ruta), salida)
    try:
        import zipfile
        n = 0
        with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
            if os.path.isdir(ruta):
                for base, _dirs, files in os.walk(ruta):
                    for f in files:
                        completo = os.path.join(base, f)
                        z.write(completo, os.path.relpath(completo, os.path.dirname(ruta)))
                        n += 1
            else:
                z.write(ruta, os.path.basename(ruta))
                n = 1
        mb = os.path.getsize(salida) / 1e6
        return (f"Comprimí {n} archivo(s) en «{os.path.basename(salida)}» ({mb:.1f} MB), señor: "
                f"{salida}")
    except Exception as e:
        return f"No pude comprimirlo, señor: {e}"


def _descomprimir(que, destino=""):
    ruta = _resolver(que)
    if ruta is None:
        return f"No encontré «{que}» para descomprimir, señor."
    if not ruta.lower().endswith(".zip"):
        return f"«{os.path.basename(ruta)}» no es un .zip, señor."
    carpeta = str(destino or "").strip() or os.path.splitext(ruta)[0]
    if not os.path.isabs(carpeta):
        carpeta = os.path.join(os.path.dirname(ruta), carpeta)
    try:
        import zipfile
        with zipfile.ZipFile(ruta) as z:
            # Se ignoran las entradas con rutas que se escapan de la carpeta destino ("../"): un zip
            # puede traerlas y escribirían fuera de donde Marco cree que está extrayendo.
            seguros = [m for m in z.namelist()
                       if not os.path.isabs(m) and ".." not in m.replace("\\", "/").split("/")]
            saltados = len(z.namelist()) - len(seguros)
            z.extractall(carpeta, members=seguros)
        cola = f" (salté {saltados} entrada(s) con rutas sospechosas)" if saltados else ""
        return f"Extraje {len(seguros)} archivo(s) en {carpeta}, señor.{cola}"
    except Exception as e:
        return f"No pude descomprimirlo, señor: {e}"


def gestionar_archivos(accion, patron="", origen="", destino="", raiz=""):
    """HERRAMIENTA: EJECUTOR DE SISTEMA PROFUNDO — busca, lee metadatos, mueve o copia archivos en
    CUALQUIER parte del disco (no solo Descargas/Documentos), directo por Python, SIN abrir el
    Explorador de Windows. accion='buscar' (usa patron[, raiz]); 'metadatos' (usa origen=ruta);
    'mover'/'copiar' (origen=nombre o ruta del archivo, destino=carpeta o alias como 'appdata',
    'mods de minecraft', 'escritorio', 'documentos')."""
    accion = str(accion or "").strip().lower()
    try:
        if accion == "buscar":
            resultados = buscar_en_disco(patron, raiz or None)
            if not resultados:
                return f"No encontré ningún archivo con «{patron}», señor."
            listado = "; ".join(
                f"{os.path.basename(r['ruta'])} ({r['tamano_mb']} MB, {r['modificado']})"
                for r in resultados[:8]
            )
            return f"Encontré {len(resultados)} archivo(s), señor: {listado}"
        if accion == "metadatos":
            m = metadatos_de(origen)
            if not m:
                return f"No encontré «{origen}», señor."
            if m["es_carpeta"]:
                return f"«{origen}» es una carpeta, señor. Modificada el {m['modificado']}."
            return (f"«{os.path.basename(m['ruta'])}», señor: {m['tamano_mb']} MB, "
                    f"tipo {m['extension']}, creado {m['creado']}, modificado {m['modificado']}.")
        if accion in ("mover", "copiar"):
            ok, resultado = mover_o_copiar(origen, destino, mover=(accion == "mover"))
            verbo = "Moví" if accion == "mover" else "Copié"
            if ok:
                return f"{verbo} «{os.path.basename(origen)}» a {resultado}, señor."
            return f"No pude {accion} el archivo, señor: {resultado}"
        # ABRIR: antes vivían aparte como 'buscar_archivo' y 'abrir_carpeta'. Comparten con esta
        # el mismo vocabulario de siempre (descargas, documentos, escritorio) y por tanto competían
        # por cada petición sobre archivos. Todo lo de archivos y carpetas entra por aquí.
        if accion in ("abrir", "abrir_archivo"):
            return _abrir_archivo(patron or origen)
        if accion in ("abrir_carpeta", "carpeta"):
            return _abrir_carpeta(patron or origen or destino)
        if accion in ("borrar_seguro", "borrar", "eliminar", "papelera"):
            return _a_la_papelera(origen or patron)
        if accion in ("comprimir_zip", "comprimir", "zip"):
            return _comprimir(origen or patron, destino)
        if accion in ("descomprimir_zip", "descomprimir", "unzip", "extraer"):
            return _descomprimir(origen or patron, destino)
        return (f"No reconozco la acción «{accion}», señor (uso: buscar/abrir/abrir_carpeta/"
                "metadatos/mover/copiar/borrar_seguro/comprimir_zip/descomprimir_zip).")
    except Exception as e:
        # Red de seguridad final: NINGUNA excepción inesperada debe crashear el turno de voz.
        return f"Algo salió mal gestionando archivos, señor: {e}"
