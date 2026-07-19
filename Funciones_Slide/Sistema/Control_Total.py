# CONTROL TOTAL: la "llave maestra" de AIDEN sobre la PC de Marco.
#
# El salto Jarvis real: en vez de una herramienta por cada cosa, UNA sola que ejecuta PowerShell
# que AIDEN mismo compone. Con esto puede hacer LITERALMENTE cualquier cosa que Windows permita:
# mover/renombrar/buscar archivos, matar procesos, cambiar ajustes, red, energía, registro, abrir
# lo que sea con lo que sea, encadenar acciones... sin que haya que programarle una tool nueva cada
# vez. Es darle a AIDEN las manos que Jarvis tenía sobre la mansión de Tony.
#
# SEGURIDAD (red anti-catástrofe, no censura): se BLOQUEAN solo comandos irreversibles y
# destructivos de sistema (formatear discos, borrar Windows, wipe, deshabilitar el arranque...).
# Todo lo demás — que es reversible o normal — se ejecuta. Marco es el dueño y administrador.

import re
import subprocess

# Patrones CATASTRÓFICOS (irreversibles / rompen el SO). Si aparecen, no se ejecuta.
_PROHIBIDO = (
    r"format\s+[a-z]:",                 # formatear una unidad
    r"format-volume",
    r"diskpart",                         # particionado a bajo nivel
    r"clear-disk",
    r"cipher\s+/w",                      # sobrescritura/wipe
    r"remove-item.*(windows|system32)",  # borrar el SO
    r"rd\s+/s.*(windows|system32)",
    r"rmdir\s+/s.*(windows|system32)",
    r"del\s+/[fsq].*(windows|system32)",
    r"bcdedit",                          # tocar el gestor de arranque
    r"vssadmin\s+delete",                # borrar copias de sombra (típico de ransomware)
    r"wevtutil\s+cl",                    # borrar TODOS los logs de eventos
    r"cipher\s+/k",
    r"reg\s+delete\s+hk.._machine\\\\(system|software\\\\microsoft\\\\windows nt)",
)


def _es_catastrofico(comando):
    c = " ".join(str(comando or "").lower().split())
    return any(re.search(p, c) for p in _PROHIBIDO)


def ejecutar_en_pc(comando, descripcion=""):
    """HERRAMIENTA MAESTRA: ejecuta un comando de PowerShell en la PC de Marco y devuelve el
    resultado. Con esto AIDEN puede hacer CUALQUIER cosa en Windows (archivos, procesos, ajustes,
    red, energía, apps...) sin necesidad de una herramienta específica. `comando` = el PowerShell a
    correr; `descripcion` = qué logra, en una frase (para el registro)."""
    comando = str(comando or "").strip()
    if not comando:
        return "No me diste un comando que ejecutar, señor."
    if _es_catastrofico(comando):
        return ("Me niego a ejecutar eso, señor: es una operación destructiva e irreversible "
                "(formatear/borrar sistema). Si de verdad lo necesita, hágalo usted a mano.")
    try:
        # -NoProfile: arranque limpio y rápido. Timeout generoso pero acotado (no colgar la voz).
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
            capture_output=True, text=True, timeout=45,
            encoding="utf-8", errors="replace",
        )
        salida = (proc.stdout or "").strip()
        error = (proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return "El comando tardó demasiado y lo corté, señor (más de 45 segundos)."
    except Exception as e:
        return f"No pude ejecutar el comando, señor: {e}"

    # Registro en la conciencia compartida (queda en el hilo de eventos).
    try:
        from Nucleo_Slide.Estado_Del_Mundo import registrar_evento
        registrar_evento(f"Ejecuté en el PC: {descripcion or comando[:60]}", "control_total")
    except Exception:
        pass

    if proc.returncode != 0 and error:
        return f"El comando terminó con error, señor: {error[:400]}"
    if not salida and not error:
        return "Hecho, señor. (Sin salida que reportar.)"
    resultado = salida or error
    # Recorta salidas enormes (un 'dir' de miles de archivos): AIDEN resume lo esencial.
    return resultado[:1500] + (" (...recortado)" if len(resultado) > 1500 else "")
