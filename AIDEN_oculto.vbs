' Lanza AIDEN sin mostrar ninguna consola (ventana oculta).
' Los mensajes y errores quedan guardados en AIDEN_log.txt
'
' La ruta se deduce de DONDE ESTA ESTE ARCHIVO, no escrita a mano: la version anterior apuntaba a
' "c:\Users\Usuario\Desktop\Python Proyecto\SLIDE-AI-BUTLER", que es la ruta de la OTRA PC. En esta
' no existe, asi que el acceso directo no arrancaba nada.
Dim fso, carpeta
Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run """" & carpeta & "\AIDEN.bat""", 0, False
