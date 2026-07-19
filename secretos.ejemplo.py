# PLANTILLA. Copia este archivo como "secretos.py" y rellena tus datos reales.
# El archivo "secretos.py" NO se sube a git (esta en .gitignore), asi tus
# datos privados nunca quedan publicos.

OPENROUTER_API_KEY = "PON_AQUI_TU_API_KEY"

CONTACTOS = {
    "NOMBRE_CONTACTO": "57XXXXXXXXXX",
    # agrega los que necesites con el formato NOMBRE: numero
}

PORTAFOLIO = {
    "NVDA": {"acciones": 0.0, "precio_compra": 0.0},
    # agrega tus acciones: TICKER: {"acciones": cantidad, "precio_compra": promedio}
}

# Para que AIDEN hable dentro de las llamadas: instala VB-CABLE y pon aqui el nombre
# del dispositivo (ej. "CABLE Input"). Deja None si no lo usas.
DISPOSITIVO_LLAMADA = None

# GASTOS via BELVO (para que AIDEN lea tus movimientos de Nequi y Nu). Pasos:
#   1. Crea cuenta en https://belvo.com (dashboard). Copia tus Secret Keys.
#   2. Enlaza tus cuentas (Nequi y Nu) con Belvo Connect -> te da un 'link' por cuenta.
#   3. Rellena aqui. Si tienes dos links, ponlos separados por coma: "linkNequi,linkNu".
# Deja "" (vacio) si aun no lo usas; la herramienta mis_gastos te avisara que falta configurar.
BELVO_SECRET_ID       = ""
BELVO_SECRET_PASSWORD = ""
BELVO_LINK            = ""
BELVO_BASE            = "https://sandbox.belvo.com"   # cambia a https://api.belvo.com en produccion

# CORREO (para que AIDEN revise tu bandeja y arme el briefing con tu dia real). Setup unico:
#   1. Activa IMAP en tu correo. En Gmail/UNAL crea una "Clave de aplicacion" (NO tu clave normal):
#      https://myaccount.google.com/apppasswords  -> pega esa clave de 16 letras en CORREO_PASS.
#   2. Host IMAP: Gmail/UNAL = "imap.gmail.com"; Outlook = "outlook.office365.com".
# Deja "" si no lo usas; revisar_correo te avisara que falta configurar.
CORREO_IMAP = ""
CORREO_USER = ""
CORREO_PASS = ""

# CALENDARIO (para "¿que tengo hoy?" y el briefing). Pega la URL SECRETA en formato ICS de tu
# calendario: Google Calendar -> Configuracion -> "Direccion secreta en formato iCal" (termina en .ics).
# Deja "" si no lo usas; agenda_hoy te avisara que falta.
CALENDARIO_ICS = ""
