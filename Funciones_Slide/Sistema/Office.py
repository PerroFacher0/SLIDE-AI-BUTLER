# OFICINA POR DENTRO: hablarle a Excel y a Word directamente, no a través de la pantalla.
#
# Hoy "pon 1500 en la celda B4" se resuelve con controlar_pantalla: localizar la celda mirando,
# clicar, teclear. Funciona, pero depende de que la hoja esté visible, en la posición correcta, sin
# nada encima, y de acertar el clic. Excel y Word exponen una interfaz de automatización (COM) que
# permite pedir exactamente eso mismo sin mirar nada: es más rápido, no falla por un scroll, y
# funciona aunque la ventana esté detrás de otra.
#
# ⚠️ SIN PROBAR CONTRA OFFICE REAL: en esta máquina no hay Office ni pywin32 instalado. El código
#    está completo y usa la API documentada, pero necesita una prueba en la máquina de Marco.
#    Lo que sí está verificado es que degrada con claridad cuando Office no está.
#
# Se trabaja SOBRE LO QUE MARCO YA TIENE ABIERTO (GetActiveObject), no se abre una instancia nueva
# invisible: si va a tocar su hoja, que la vea cambiar. Solo si no hay nada abierto y se pide un
# archivo concreto, se abre.

import os


def _com(app):
    """Conecta con Excel/Word YA ABIERTO. Devuelve (objeto, error_legible)."""
    try:
        import win32com.client as win32
    except Exception:
        return None, ("No tengo el puente con Office, señor. Se activa con: pip install pywin32")
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    try:
        return win32.GetActiveObject(f"{app}.Application"), None
    except Exception:
        return None, (f"No tiene {app} abierto, señor. Ábralo (o dígame qué archivo abrir) y "
                      "repítamelo.")


def _abrir(app, archivo):
    try:
        import win32com.client as win32
        import pythoncom
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass
        obj = win32.Dispatch(f"{app}.Application")
        obj.Visible = True                    # que Marco lo VEA, nunca a escondidas
        if app == "Excel":
            obj.Workbooks.Open(os.path.abspath(archivo))
        else:
            obj.Documents.Open(os.path.abspath(archivo))
        return obj, None
    except Exception as e:
        return None, f"No pude abrir «{archivo}» en {app}, señor: {e}"


def _excel(accion, celda, valor, hoja, archivo):
    app, err = (_abrir("Excel", archivo) if archivo else _com("Excel"))
    if app is None:
        return err
    try:
        libro = app.ActiveWorkbook
        if libro is None:
            return "Excel está abierto pero sin ningún libro, señor."
        h = libro.Worksheets(hoja) if hoja else libro.ActiveSheet

        if accion == "leer":
            if not celda:
                return "¿Qué celda leo, señor?"
            v = h.Range(celda).Value
            return f"{celda} tiene: {v}" if v is not None else f"{celda} está vacía, señor."
        if accion == "escribir":
            if not celda:
                return "¿En qué celda escribo, señor?"
            # Si parece un número, se escribe como número: si va como texto, Excel no lo suma.
            try:
                h.Range(celda).Value = float(str(valor).replace(",", "."))
            except (TypeError, ValueError):
                h.Range(celda).Value = valor
            return f"Puse «{valor}» en {celda} de «{h.Name}», señor."
        if accion == "guardar":
            libro.Save()
            return f"Guardado «{libro.Name}», señor."
        if accion == "resumen":
            usado = h.UsedRange
            return (f"«{libro.Name}», hoja «{h.Name}»: {usado.Rows.Count} filas x "
                    f"{usado.Columns.Count} columnas con datos, señor.")
        return f"No sé hacer «{accion}» en Excel, señor (leer, escribir, guardar, resumen)."
    except Exception as e:
        return f"Excel no me dejó hacer eso, señor: {e}"


def _word(accion, valor, archivo):
    app, err = (_abrir("Word", archivo) if archivo else _com("Word"))
    if app is None:
        return err
    try:
        doc = app.ActiveDocument
        if doc is None:
            return "Word está abierto pero sin ningún documento, señor."
        if accion == "leer":
            texto = doc.Range().Text or ""
            return f"El documento dice: {texto[:1200]}" if texto.strip() else "Está vacío, señor."
        if accion == "escribir":
            # Al FINAL del documento, no encima de lo que ya hay: sobrescribir lo escrito por
            # Marco sería destruir trabajo suyo sin preguntar.
            doc.Content.InsertAfter(str(valor or ""))
            return f"Añadí el texto al final de «{doc.Name}», señor."
        if accion == "guardar":
            doc.Save()
            return f"Guardado «{doc.Name}», señor."
        if accion == "resumen":
            return (f"«{doc.Name}»: {doc.Words.Count} palabras, {doc.Paragraphs.Count} párrafos, "
                    f"señor.")
        return f"No sé hacer «{accion}» en Word, señor (leer, escribir, guardar, resumen)."
    except Exception as e:
        return f"Word no me dejó hacer eso, señor: {e}"


def office(programa="excel", accion="leer", celda="", valor="", hoja="", archivo=""):
    """HERRAMIENTA: trabaja DENTRO de Excel o Word directamente, sin clicar en la pantalla.
      programa = excel | word
      accion   = leer | escribir | guardar | resumen
      celda    = solo Excel (ej. 'B4', 'A1:C10')
      valor    = qué escribir
      hoja     = solo Excel, nombre de la hoja (vacío = la que esté activa)
      archivo  = solo si hay que ABRIRLO; si ya está abierto, se deja vacío."""
    p = str(programa or "excel").strip().lower()
    a = str(accion or "leer").strip().lower()
    for clave in ("leer", "escribir", "guardar", "resumen"):
        if a.startswith(clave[:4]):
            a = clave
            break
    if "word" in p or "document" in p:
        return _word(a, valor, archivo)
    return _excel(a, str(celda or "").strip(), valor, str(hoja or "").strip(), archivo)
