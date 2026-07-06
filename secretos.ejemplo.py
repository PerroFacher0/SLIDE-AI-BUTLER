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
