# AGENDA: correo + calendario de Marco (su vida de estudiante), para que el briefing sea REAL.
#
# El hueco mas grande que le quedaba a AIDEN: no sabia que tiene HOY ni que le llego. Con esto,
# "¿que tengo hoy?" / "¿algo importante en el correo?" y el briefing matutino dejan de ser "clima y
# noticias" y pasan a ser su dia de verdad: clases, entregas, correos de profesores.
#
# CONFIG (setup unico, en secretos.py; si falta, avisa con tacto y no rompe nada):
#   CORREO_IMAP = "imap.gmail.com"   (UNAL suele ser Google Workspace; Outlook: "outlook.office365.com")
#   CORREO_USER = "mgarciavil@unal.edu.co"
#   CORREO_PASS = "clave de aplicacion"  (NO la normal: una App Password)
#   CALENDARIO_ICS = "https://.../basic.ics"  (URL secreta ICS de Google/Outlook Calendar)
# Nada se sube a git: secretos.py esta en .gitignore.

import email
import imaplib
import re
import smtplib
from datetime import datetime, date, timedelta
from email.header import decode_header
from email.mime.text import MIMEText

try:
    import requests
except Exception:
    requests = None


def _cfg(nombre, defecto=""):
    try:
        import secretos
        return getattr(secretos, nombre, defecto)
    except Exception:
        return defecto


# Host SMTP a partir del IMAP (mismo proveedor, misma clave de aplicación).
_SMTP_POR_IMAP = {
    "imap.gmail.com": ("smtp.gmail.com", 587),
    "outlook.office365.com": ("smtp.office365.com", 587),
    "imap-mail.outlook.com": ("smtp-mail.outlook.com", 587),
}


def _resolver_correo(para):
    # 'para' puede ser una dirección o el nombre de un contacto (CONTACTOS_CORREO en secretos.py).
    p = str(para or "").strip()
    if "@" in p and "." in p:
        return p
    agenda = _cfg("CONTACTOS_CORREO", {}) or {}
    for nombre, direccion in agenda.items():
        if str(nombre).strip().lower() == p.lower():
            return direccion
    return ""


def enviar_correo(para, asunto="", mensaje=""):
    """HERRAMIENTA: ENVÍA un correo (no lo lee). 'para' = dirección de email o nombre de un contacto
    guardado (CONTACTOS_CORREO en secretos.py). Úsala cuando Marco diga 'mándale un correo a X
    diciendo...', 'escríbele un email a...'. Requiere el correo configurado en secretos.py."""
    host = _cfg("CORREO_IMAP")
    user = _cfg("CORREO_USER")
    pw = _cfg("CORREO_PASS")
    if not (host and user and pw):
        return ("Aún no tengo su correo configurado para enviar, señor. Ponga CORREO_IMAP/USER/PASS "
                "en secretos.py y podré escribir por usted.")
    destino = _resolver_correo(para)
    if not destino:
        return (f"No tengo el correo de «{para}», señor. Dígame la dirección, o guárdela en "
                "CONTACTOS_CORREO dentro de secretos.py.")
    mensaje = str(mensaje or "").strip()
    if not mensaje:
        return "¿Qué le escribo en el correo, señor?"
    asunto = str(asunto or "").strip() or "Mensaje de Marco"
    smtp_host, puerto = _SMTP_POR_IMAP.get(str(host).lower(), (str(host).replace("imap", "smtp"), 587))
    try:
        msg = MIMEText(mensaje, "plain", "utf-8")
        msg["Subject"] = asunto
        msg["From"] = user
        msg["To"] = destino
        with smtplib.SMTP(smtp_host, puerto, timeout=20) as s:
            s.starttls()
            s.login(user, pw)
            s.sendmail(user, [destino], msg.as_string())
        return f"Correo enviado a {destino}, señor. Asunto: «{asunto}»."
    except smtplib.SMTPAuthenticationError:
        return ("El correo rechazó la clave, señor: revise que CORREO_PASS sea una clave de "
                "aplicación (no la normal).")
    except Exception as e:
        return f"No pude enviar el correo, señor: {e}"


# ── CORREO (IMAP) ─────────────────────────────────────────────────────────────
def _decodificar(cabecera):
    if not cabecera:
        return ""
    partes = []
    for texto, enc in decode_header(cabecera):
        if isinstance(texto, bytes):
            try:
                partes.append(texto.decode(enc or "utf-8", "ignore"))
            except Exception:
                partes.append(texto.decode("utf-8", "ignore"))
        else:
            partes.append(texto)
    return "".join(partes).strip()


def revisar_correo(cuantos=5):
    """HERRAMIENTA: los ultimos correos NO leidos de Marco (asunto + remitente). 'revisa mi correo',
    '¿me llego algo importante?'. Requiere config de correo en secretos.py."""
    host = _cfg("CORREO_IMAP")
    user = _cfg("CORREO_USER")
    pw = _cfg("CORREO_PASS")
    if not (host and user and pw):
        return ("Aun no tengo acceso a su correo, señor. Cuando quiera, ponga CORREO_IMAP, "
                "CORREO_USER y CORREO_PASS (una clave de aplicacion) en secretos.py y lo reviso.")
    try:
        cuantos = max(1, min(int(cuantos or 5), 10))
    except (ValueError, TypeError):
        cuantos = 5
    try:
        M = imaplib.IMAP4_SSL(host)
        M.login(user, pw)
        M.select("INBOX")
        typ, datos = M.search(None, "UNSEEN")
        if typ != "OK" or not datos or not datos[0]:
            M.logout()
            return "No tiene correos sin leer, señor. Bandeja limpia."
        ids = datos[0].split()[-cuantos:]
        correos = []
        for i in reversed(ids):
            typ, msg_data = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            asunto = _decodificar(msg.get("Subject")) or "(sin asunto)"
            de = _decodificar(msg.get("From"))
            de_corto = de.split("<")[0].strip().strip('"') or de
            correos.append(f"- de {de_corto[:35]}: {asunto[:70]}")
        M.close()
        M.logout()
        if not correos:
            return "No tiene correos sin leer, señor."
        # Remitente + asunto de varios correos: escuchado se mezcla todo; leído se decide en dos
        # segundos cuál abrir. (Van solo los encabezados, no el cuerpo: eso es correo de Marco.)
        try:
            from Nucleo_Slide import HUD
            HUD.tarjeta(f"{len(correos)} correo(s) sin leer",
                        [c.lstrip("- ") for c in correos], segundos=10)
        except Exception:
            pass
        return f"Tiene {len(correos)} correo(s) sin leer, señor:\n" + "\n".join(correos)
    except imaplib.IMAP4.error:
        return ("No pude entrar a su correo, señor: revise el usuario o la clave de aplicacion en "
                "secretos.py.")
    except Exception as e:
        return f"No pude consultar el correo, señor: {e}"


# ── CALENDARIO (ICS) ──────────────────────────────────────────────────────────
def _desdoblar_ics(texto):
    # ICS parte lineas largas con salto+espacio; hay que volverlas a unir.
    lineas = []
    for ln in texto.splitlines():
        if ln[:1] in (" ", "\t") and lineas:
            lineas[-1] += ln[1:]
        else:
            lineas.append(ln)
    return lineas


def _parse_dt(linea):
    # De "DTSTART;TZID=...:20260719T100000" o "DTSTART;VALUE=DATE:20260719" saca el datetime.
    v = linea.split(":", 1)[-1].strip().rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(v[:15] if "T" in v else v[:8], fmt)
        except ValueError:
            continue
    return None


def agenda_hoy(dia="hoy"):
    """HERRAMIENTA: los eventos del calendario de Marco para HOY (o 'manana'). '¿que tengo hoy?',
    '¿que hay en mi agenda?'. Requiere CALENDARIO_ICS en secretos.py."""
    url = _cfg("CALENDARIO_ICS")
    if not url:
        return ("Aun no tengo su calendario, señor. Ponga la URL secreta ICS de su calendario en "
                "CALENDARIO_ICS (secretos.py) y le canto su dia.")
    if requests is None:
        return "Me falta la libreria 'requests' para leer el calendario, señor."
    objetivo = date.today() + (timedelta(days=1) if str(dia).lower().startswith("man") else timedelta(0))
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        lineas = _desdoblar_ics(r.text)
    except Exception as e:
        return f"No pude descargar su calendario, señor: {e}"
    eventos = []
    dtstart = summary = None
    dentro = False
    for ln in lineas:
        if ln.startswith("BEGIN:VEVENT"):
            dentro = True
            dtstart = summary = None
        elif ln.startswith("END:VEVENT"):
            if dtstart and dtstart.date() == objetivo:
                eventos.append((dtstart, summary or "(evento)"))
            dentro = False
        elif dentro and ln.startswith("DTSTART"):
            dtstart = _parse_dt(ln)
        elif dentro and ln.startswith("SUMMARY"):
            summary = ln.split(":", 1)[-1].strip()
    if not eventos:
        cuando = "mañana" if objetivo != date.today() else "hoy"
        return f"No tiene nada agendado para {cuando}, señor. El dia es suyo."
    eventos.sort(key=lambda e: e[0])
    cuando = "Mañana" if objetivo != date.today() else "Hoy"
    partes = [f"{e[0].strftime('%H:%M')} {e[1][:50]}" for e in eventos]
    # Una agenda dicha de corrido ("a las nueve, a las once y media, a la una...") obliga a Marco a
    # ir memorizando horas. En columna se ve de un golpe qué tiene y cuánto hueco le queda.
    try:
        from Nucleo_Slide import HUD
        HUD.tarjeta(f"{cuando} en tu agenda",
                    [f"{e[0].strftime('%H:%M')}   {e[1][:46]}" for e in eventos], segundos=10)
    except Exception:
        pass
    return f"{cuando} tiene, señor: " + "; ".join(partes) + "."


def resumen_dia():
    """Texto para el briefing matutino: agenda de hoy + correos sin leer (lo que se pueda)."""
    trozos = []
    a = agenda_hoy("hoy")
    if a and "Aun no tengo" not in a:
        trozos.append(a)
    c = revisar_correo(3)
    if c and "Aun no tengo acceso" not in c and "No tiene correos" not in c:
        trozos.append(c)
    return "\n".join(trozos)
