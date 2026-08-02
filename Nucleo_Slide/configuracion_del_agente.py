from Funciones_Slide.Comunicacion.Funciones_Variadas import Enviar_mensaje_Whatsapp, llamada_whatsapp, colgar, Auto_Modificacion
from Funciones_Slide.Productividad.Gestion_datos import guardar_en_json
from Funciones_Slide.Sistema.Comandos_Asistente import Abrir_Apps, Abrir_Videos_Youtube, Salir
from Funciones_Slide.Sistema.Funciones_Sistema import cerrar_aplicacion, ver_apps_abiertas, clima, buscar, leer_portapapeles, control_musica, control_volumen, estado_sistema
from Nucleo_Slide.Memoria import memoria
from Funciones_Slide.Info.Vision import analizar
from Funciones_Slide.Info.Finanzas import acciones
from Funciones_Slide.Productividad.Notas import notas
from Funciones_Slide.Comunicacion.Llamadas import contestar_llamada
from Funciones_Slide.Sistema.Control_PC import dictar, abrir_carpeta, control_ventana, controlar_energia, tomar_captura, buscar_archivo
from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
from Nucleo_Slide.Cancelacion import cancelar
from Funciones_Slide.Sistema.Macros import macro
from Funciones_Slide.Sistema.Perifericos import perifericos
from Funciones_Slide.Comunicacion.Telegram_Control import avisar_al_celular
from Nucleo_Slide.Memoria_Visual import memoria_visual
from Funciones_Slide.Sistema.Vigilante_Eventos import esperar_evento
from Funciones_Slide.Sistema.Hardware_Externo import hardware
from Funciones_Slide.Productividad.Metas import gestionar_metas
from Funciones_Slide.Sistema.Misiones import ejecutar_mision
from Nucleo_Slide.Memoria_RAG import recordar
from Funciones_Slide.Info.Investigacion import investigar
from Funciones_Slide.Info.Finanzas_Gastos import mis_gastos
from Funciones_Slide.Productividad.Protocolos import activar_protocolo, crear_protocolo
from Funciones_Slide.Sistema.Taller import modo_taller
from Funciones_Slide.Productividad.Ordenes_Condicionales import programar_orden
from Funciones_Slide.Sistema.Control_Total import ejecutar_en_pc
from Funciones_Slide.Info.Agenda import revisar_correo, agenda_hoy, enviar_correo
from Funciones_Slide.Sistema.Sesion import restaurar_sesion
from Funciones_Slide.Comunicacion.Discord import Enviar_mensaje_Discord
from Funciones_Slide.Info.Web import abrir_web
from Funciones_Slide.Sistema.Navegador_Web import navegar_web
from Funciones_Slide.Sistema.Escucha_Sistema import que_esta_sonando
from Funciones_Slide.Sistema.Gestor_Archivos import gestionar_archivos
from Funciones_Slide.Info.Redactor import redactar_documento
from Funciones_Slide.Info.Estudio import resolver_visual
from Funciones_Slide.Info.Bitacora import resumen_actividad
from Funciones_Slide.Sistema.Modos import modo_gaming
from Funciones_Slide.Info.Documentos import resumir
from Funciones_Slide.Info.Utilidades import calculadora, convertir_moneda
from Funciones_Slide.Info.Noticias import noticias_del_dia
from Funciones_Slide.Info.Experto import consultar_experto
from Funciones_Slide.Info.Codigo import explicar_error
from Funciones_Slide.Sistema.Programador import proyecto



tools = [
    {
        "type": "function",
        "function": {
            "name": "Enviar_mensaje_Whatsapp",
            "description": "Envía un mensaje de WhatsApp de forma INMEDIATA a un contacto específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_contacto": {
                        "type": "string",
                        "description": "El nombre del contacto al que se enviará el mensaje (ej. MAMA, TITO, JOSHUA)."
                    },
                    "mensaje": {
                        "type": "string",
                        "description": "El contenido del mensaje que se va a enviar."
                    }
                },
                "required": ["nombre_contacto", "mensaje"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "llamada_whatsapp",
            "description": "Inicia una llamada de WhatsApp INMEDIATA a un contacto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_contacto": {
                        "type": "string",
                        "description": "El nombre del contacto a llamar."
                    }
                },
                "required": ["nombre_contacto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "colgar",
            "description": "Cuelga o finaliza la llamada en curso.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Abrir_Apps",
            "description": "Abre una aplicación instalada en la computadora (ej. Spotify, Word, Excel).",
            "parameters": {
                "type": "object",
                "properties": {
                    "Aplicacion": {
                        "type": "string",
                        "description": "El nombre de la aplicación a abrir."
                    }
                },
                "required": ["Aplicacion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Abrir_Videos_Youtube",
            "description": "Busca y reproduce un video o música en YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Tipo_Video": {
                        "type": "string",
                        "description": "El tema, nombre de la canción o creador del video a buscar (ej. 'Música electrónica', 'Tutorial de Python')."
                    }
                },
                "required": ["Tipo_Video"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar",
            "description": "Busca en internet. Por defecto LEE los resultados y te los devuelve como texto para que TU le respondas a Marco con datos reales y actuales (informacion reciente, resultados deportivos, datos que cambian, algo que no sabes con certeza). Con abrir=true deja la busqueda EN PANTALLA en el navegador, para cuando Marco pida 'abreme/muestrame X en Google'. NO la uses para conversacion casual, ni para operar un sitio web paso a paso (eso es navegar_web), ni para abrir una pagina conocida por su nombre (eso es abrir_web).",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {
                        "type": "string",
                        "description": "Lo que se va a buscar, redactado como una busqueda concisa (ej. 'resultado partido Real Madrid hoy')."
                    },
                    "abrir": {
                        "type": "boolean",
                        "description": "true = abrir los resultados en el navegador para que Marco los VEA. false (por defecto) = devolverte el texto para que le respondas tu."
                    }
                },
                "required": ["consulta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_en_json",
            "description": "Programa una tarea, recordatorio, mensaje o llamada para el FUTURO (ej. 'en 15 minutos'). Calcula la hora sumando los minutos solicitados a tu hora actual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string",
                        "description": "La acción a realizar. Solo puede ser: WHATSAPP, LLAMAR, COLGAR o NOTIFICAR."
                    },
                    "target": {
                        "type": "string",
                        "description": "El contacto objetivo (ej. MAMA) o 'Yo' si es un recordatorio personal."
                    },
                    "info": {
                        "type": "string",
                        "description": "El contenido del mensaje o el recordatorio."
                    },
                    "hora": {
                        "type": "string",
                        "description": "La hora calculada en el futuro con el formato exacto DD/MM HH:MM (ej. 08/03 15:30)."
                    }
                },
                "required": ["accion", "target", "info", "hora"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Salir",
            "description": "Apaga el sistema, se despide y cierra el asistente.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_volumen",
            "description": "Controla el volumen del sistema: subir, bajar, silenciar, desilenciar, o poner un nivel exacto (0-100). Úsala para cualquier ajuste de volumen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "subir, bajar, silenciar, desilenciar, o un número 0-100."},
                    "nivel": {"type": "number", "description": "Nivel exacto 0-100 (opcional, si Marco pide un número)."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cerrar_aplicacion",
            "description": "Cierra una aplicacion abierta, por su nombre (ej. 'chrome', 'spotify'). Con forzar=true la MATA sin pedirle permiso: eso es lo que hay que hacer con una app COLGADA que no responde ('cierra Chrome a la fuerza', 'mata el proceso X'). Para cerrar solo una VENTANA o una PESTAÑA usa control_ventana o controlar_pantalla.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_app": {
                        "type": "string",
                        "description": "Nombre del programa a cerrar (ej. 'chrome', 'spotify', 'discord'). El .exe es opcional."
                    },
                    "forzar": {
                        "type": "boolean",
                        "description": "true = matarlo a la fuerza (app colgada / no responde). false (por defecto) = cierre normal y ordenado."
                    }
                },
                "required": ["nombre_app"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_apps_abiertas",
            "description": "Lista todas las aplicaciones y procesos que están corriendo actualmente en el sistema.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clima",
            "description": "Consulta el clima de una ciudad: el de AHORA o el PRONÓSTICO de los próximos días. Úsala para CUALQUIER pregunta sobre el clima (actual o futuro).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ciudad": {
                        "type": "string",
                        "description": "Nombre de la ciudad a consultar (ej. 'Bogota', 'Madrid', 'New York')."
                    },
                    "cuando": {
                        "type": "string",
                        "description": "'ahora' para el clima actual, o 'mañana'/'pronóstico'/'próximos días' para el pronóstico. Opcional, por defecto ahora."
                    }
                },
                "required": ["ciudad"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "acciones",
            "description": "Bolsa/inversiones de Marco. Con 'simbolo' consulta el precio, cambio del día, objetivo de analistas y recomendación de ESE activo (acción como NVDA/PLTR/MSTR, o el oro, bitcoin, petróleo...). SIN símbolo, da el resumen de su watchlist (NVDA/CRWV/ISRG/PLTR/MSTR) + su portafolio (cuánto tiene, cuánto vale hoy, cuánto gana/pierde). Úsala para el precio de algo, cómo van sus acciones, su portafolio o cuánto ganó/perdió.",
            "parameters": {
                "type": "object",
                "properties": {
                    "simbolo": {"type": "string", "description": "El activo a consultar (ej. 'NVDA', 'oro', 'bitcoin'). Vacío para el resumen de su watchlist + portafolio."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analizar",
            "description": "AIDEN VE y analiza (describe) lo que hay delante. fuente 'pantalla' (por defecto) mira la PANTALLA del PC (un texto, un error, algo que Marco muestra); fuente 'camara' mira por la CÁMARA (el entorno, un objeto). Úsala cuando Marco pregunte qué ves, que mires/observes algo, o pida tu opinión. Para RESOLVER a fondo un problema/ejercicio de la pantalla, usa resolver_visual (no esta).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fuente": {"type": "string", "description": "pantalla (por defecto) | camara"},
                    "consulta": {"type": "string", "description": "Lo que Marco quiere saber sobre lo que ves (opcional)."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_archivo",
            "description": "Busca un archivo por su nombre en las carpetas de Marco (Descargas, Documentos, Escritorio, etc.) y abre el primero que encuentre. Úsala cuando pida buscar o encontrar un archivo, documento, foto, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre o parte del nombre del archivo a buscar."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_actividad",
            "description": "Resume lo que pasó en el PC mientras Marco no estaba: las notificaciones que llegaron (mensajes de WhatsApp/Discord, correos, alertas). Úsala cuando Marco pregunte qué pasó anoche, qué se perdió, o pida el resumen de notificaciones. Al darle el resultado, RESALTA lo relevante (mensajes, correos) y omite el ruido (actualizaciones, promos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "horas": {"type": "number", "description": "Cuántas horas hacia atrás revisar (por defecto 16). Opcional."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_energia",
            "description": "Controla la energía del PC: apagar, reiniciar, suspender, bloquear, o cancelar un apagado programado. Puede programarse con minutos de retraso. Úsala cuando Marco pida apagar/reiniciar/bloquear/suspender el equipo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "apagar, reiniciar, suspender, bloquear o cancelar."},
                    "minutos": {"type": "number", "description": "Minutos de retraso para apagar/reiniciar (0 = ahora). Opcional."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tomar_captura",
            "description": "Toma una captura de pantalla y la guarda en la carpeta Capturas. Úsala cuando Marco pida un screenshot o captura de pantalla.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "activar_protocolo",
            "description": "Activa un PROTOCOLO (escena que cambia varias cosas a la vez), estilo Jarvis. Disponibles: 'cine' (baja brillo, sube volumen, silencia interrupciones), 'buenas noches' (silencia y deja el equipo en calma), 'concentración' (sin notificaciones para estudiar/trabajar), 'normal' (desactiva todo). Úsala cuando Marco active un modo o ambiente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "cine, buenas noches, concentración, o normal."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modo_gaming",
            "description": "Activa o desactiva el modo gaming: silencia las notificaciones de Windows, pausa los avisos de AIDEN, y LIBERA la VRAM de la GPU descargando los modelos de voz (para que rindan los juegos). Úsala cuando Marco diga que va a jugar, pida modo gaming / no molestar / liberar la GPU, o pida desactivarlo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activar": {"type": "string", "description": "'activar' para encenderlo, 'desactivar' para apagarlo."}
                },
                "required": ["activar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumir",
            "description": "Resume un documento (PDF/texto de Descargas, Documentos o Escritorio, por su nombre) O un video de YouTube (por su enlace) — detecta solo cuál es. Úsala cuando Marco pida resumir un archivo, trabajo, PDF, o un video de YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fuente": {"type": "string", "description": "El nombre del archivo (ej. 'parcial') o el enlace de YouTube a resumir."}
                },
                "required": ["fuente"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dictar",
            "description": "Escribe un texto donde esté el cursor de Marco (en el campo o documento activo). Úsala cuando Marco te dicte algo para escribir: 'escribe...', 'dicta...', 'pon...' en un documento, chat o buscador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "El texto a escribir."}
                },
                "required": ["texto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_carpeta",
            "description": "Abre una carpeta del computador en el explorador. Úsala cuando Marco pida abrir sus descargas, documentos, escritorio, imágenes, música o videos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Carpeta: descargas, documentos, escritorio, imagenes, musica o videos."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_ventana",
            "description": "Controla la VENTANA ENTERA activa de Windows: minimizar, maximizar, cerrar la ventana completa, cambiar de ventana, o mostrar el escritorio. OJO: para cerrar solo una PESTAÑA (de navegador) NO uses esto, usa controlar_pantalla con accion 'cerrar_pestana'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "Una de: minimizar, maximizar, cerrar, cambiar, escritorio."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "contestar_llamada",
            "description": "ACEPTA la llamada ENTRANTE que está sonando y le dice al contacto un mensaje con la voz de AIDEN. AIDEN mismo acepta la llamada; NO necesitas el nombre del contacto (es la llamada que suena ahora). Úsala cuando Marco diga 'contesta/responde/atiende la llamada'. Si Marco dijo qué decir, pásalo tal cual; si NO dijo nada, contesta igual con un mensaje cortés por defecto. NUNCA preguntes 'a quién'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mensaje": {
                        "type": "string",
                        "description": "Lo que se le dirá al contacto, en TERCERA persona y cortés (ej. 'Marco está ocupado, le devolverá la llamada más tarde'). Opcional: si Marco no dijo qué decir, deja vacío y se usará un mensaje cortés por defecto."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leer_portapapeles",
            "description": "Lee lo que Marco tiene copiado (portapapeles) para poder explicarlo, traducirlo o resumirlo. Úsala cuando Marco diga 'explica/traduce/resume lo que copié' o se refiera a algo que acaba de copiar.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_musica",
            "description": "Controla la reproducción de música o video del sistema con las teclas multimedia. Úsala cuando Marco pida pausar, reanudar, poner play, pasar a la siguiente canción, volver a la anterior, o detener la música.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string",
                        "description": "Una de: pausa, play, siguiente, anterior, parar."
                    }
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notas",
            "description": "Notas rápidas de Marco. accion 'guardar' (con texto) apunta una nota ('anota que...', 'apunta...'); accion 'leer' (por defecto) lee sus últimas notas ('¿qué tenía apuntado?').",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "guardar | leer (por defecto)"},
                    "texto": {"type": "string", "description": "El texto de la nota (solo para guardar)."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memoria",
            "description": "Memoria PERMANENTE sobre Marco (persiste entre sesiones: nombre, gustos, fechas, hardware, preferencias). accion 'recordar' (por defecto) guarda un dato; accion 'olvidar' borra los que coincidan. Úsala cuando Marco pida recordar/olvidar algo o cuente algo que valga la pena guardar (una llamada por dato).",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "recordar (por defecto) | olvidar"},
                    "dato": {"type": "string", "description": "El dato a recordar (corto y claro), o la palabra que identifica el recuerdo a olvidar."},
                    "categoria": {"type": "string", "description": "Categoría corta al recordar (ej. 'gustos', 'estudios'). Opcional."}
                },
                "required": ["dato"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Auto_Modificacion",
            "description": "Hace que AIDEN APRENDA UNA HABILIDAD nueva para SÍ MISMO (una función que gana como capacidad), escrita por Claude Code y recargada en vivo. Úsala cuando Marco te ordene 'aprende a...', 'prográmate una función para...', 'automatiza...'. Corre en segundo plano y avisa al terminar. Para crear un PROYECTO o app SEPARADO usa proyecto (accion crear).",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_habilidad": {
                        "type": "string",
                        "description": "El nombre de la función en Python (ej. calcular_impuestos, apagar_luces_cuarto). Debe usar guiones bajos."
                    },
                    "instruccion": {
                        "type": "string",
                        "description": "Qué debe hacer la habilidad, en lenguaje natural y con el detalle necesario (ej. 'calcular el IVA del 19% de un monto y devolverlo')."
                    }
                },
                "required": ["nombre_habilidad", "instruccion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "noticias_del_dia",
            "description": "Trae los TITULARES de noticias más recientes (con fecha y fuente). Úsala cuando Marco pregunte qué noticias hay hoy, las novedades, o noticias de un tema/país específico (tecnología, deportes, Colombia, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tema": {"type": "string", "description": "Tema o país de las noticias (ej. 'tecnología', 'Colombia', 'fútbol'). Opcional; si no se da, trae titulares generales."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculadora",
            "description": "Resuelve una operación matemática EXACTA (sumas, restas, multiplicaciones, potencias, raíces, porcentajes, trigonometría). Úsala SIEMPRE que Marco pida una cuenta o cálculo numérico, en vez de calcularlo tú.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expresion": {"type": "string", "description": "La operación a resolver (ej. '(15*8+100)/2', 'raiz(144)', '200*0.15')."}
                },
                "required": ["expresion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convertir_moneda",
            "description": "Convierte dinero entre monedas con la tasa de cambio ACTUAL. Úsala cuando Marco pregunte cuánto es X en otra moneda (ej. '100 dólares a pesos', 'cuánto son 50 euros en COP').",
            "parameters": {
                "type": "object",
                "properties": {
                    "cantidad": {"type": "number", "description": "La cantidad a convertir."},
                    "desde": {"type": "string", "description": "Moneda de origen en código de 3 letras (USD, EUR, COP)."},
                    "hacia": {"type": "string", "description": "Moneda de destino en código de 3 letras (USD, EUR, COP)."}
                },
                "required": ["cantidad", "desde", "hacia"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estado_sistema",
            "description": "Reporta el estado del PC: batería, uso de CPU, uso de RAM, uso de GPU, VRAM usada y temperatura de la GPU, e IP de red. Úsala cuando Marco pregunte cómo está el equipo, la batería, cuánta RAM/CPU/GPU/VRAM está usando, la temperatura, o su IP.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_experto",
            "description": "Enruta una pregunta GENUINAMENTE DIFÍCIL a un modelo más potente (modo experto) y devuelve su respuesta. Úsala SOLO para razonamiento profundo, matemáticas o lógica complejas, análisis difícil, o problemas de varios pasos que requieran más capacidad de la normal. NO la uses para tareas simples, acciones, conversación, ni datos que otras herramientas ya dan (clima, precios, búsquedas, cálculos sencillos).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pregunta": {"type": "string", "description": "La pregunta o problema difícil, con TODO el contexto necesario para resolverlo."}
                },
                "required": ["pregunta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explicar_error",
            "description": "Explica un ERROR de programación o un traceback y dice cómo arreglarlo (para principiante). Si Marco no dicta el error, lee el que tenga COPIADO en el portapapeles. Úsala cuando Marco diga 'explícame este error', 'qué significa este error', 'por qué me sale este error' o pida ayuda con un error de código. (Si el error está EN PANTALLA y no copiado, usa analizar.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "El texto del error o traceback. Opcional: si se omite, se lee del portapapeles."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recordar",
            "description": "Busca en el HISTORIAL de conversaciones pasadas con Marco. Usala cuando pregunte que hablaron antes, que te conto o le dijiste, '¿te acuerdas cuando...?', '¿de que hablamos ayer?', '¿que hemos hablado de mis estudios?'. Por defecto (modo 'auto') busca primero por SIGNIFICADO — encuentra 'la tesis' aunque Marco diga 'la universidad' — y si no saca nada reintenta por palabras exactas. Solo cambia 'modo' si necesitas forzar uno: 'palabras' para un termino literal o para traer lo mas reciente. NO la uses para datos permanentes que Marco te pidio guardar (eso es memoria) ni para lo que hubo en PANTALLA (eso es memoria_visual).",
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {"type": "string", "description": "Tema o pregunta a buscar. Opcional: si se omite, trae lo mas reciente."},
                    "modo": {"type": "string", "description": "auto (por defecto) | significado | palabras"},
                    "dias": {"type": "number", "description": "Limita a los ultimos N dias (ej. 1 = ayer/hoy). Solo aplica al modo por palabras. Opcional."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "proyecto",
            "description": "Proyectos/programas REALES construidos por Claude Code. accion 'crear' (por defecto, con 'instruccion') delega a Claude Code que escriba los archivos completos en un sandbox ('créame', 'prográmame', 'hazme un programa que...'); tarda, corre en 2do plano y AIDEN avisa al terminar. accion 'ejecutar' corre el código de un proyecto ya creado ('ejecuta el proyecto', 'pruébalo'). NO para una función simple del propio AIDEN (eso es Auto_Modificacion) ni para tareas sobre el código de AIDEN (eso es pedir_a_claude_code).",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "crear (por defecto) | ejecutar"},
                    "instruccion": {"type": "string", "description": "Qué construir, en alto nivel (solo para crear)."},
                    "nombre": {"type": "string", "description": "Nombre corto de la carpeta del proyecto. Opcional."},
                    "archivo": {"type": "string", "description": "Archivo .py específico a correr (solo para ejecutar). Opcional."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_pantalla",
            "description": "Interaccion VISIBLE con la pantalla: AIDEN mueve el MOUSE y el TECLADO sobre lo que YA esta en pantalla, y Marco lo VE. El clic funciona con CUALQUIER cosa visible: primero busca el nombre en la estructura de accesibilidad (instantaneo) y, si no lo encuentra (juegos, apps de lienzo, iconos sin texto), UBICA el objetivo VIENDO la pantalla y hace clic ahi igual (un poco mas lento, pero cubre lo que sea). Funciona en VARIOS MONITORES. USA ESTA para: clic/doble clic/clic derecho en cualquier elemento, IR A UNA PESTANA del navegador por su nombre (accion 'clic' con el nombre de la pestana, ej. objetivo='GitHub'), SENALAR donde esta algo dibujandole un recuadro en pantalla SIN tocarlo (accion 'senalar', para '¿donde esta el boton de exportar?' — mucho mejor que describirlo con palabras), ARRASTRAR una cosa hasta otra, AJUSTAR un control continuo hasta lograr un resultado (slider de brillo/volumen/recorte: mira, mueve y VUELVE A MIRAR hasta que quede bien), ordenar ventanas en mosaico, traer una app al frente, teclear, hacer scroll, CERRAR UNA PESTANA (Ctrl+W), seleccionar, o un atajo de teclas. NO la uses para abrir una app nueva (usa Abrir_Apps), ni para minimizar/maximizar/cerrar la VENTANA entera (usa control_ventana), ni para pegar texto largo de golpe (usa dictar), ni para leer/analizar lo que hay en pantalla (usa analizar). accion posibles: clic, doble_clic, clic_derecho, arrastrar, ajustar, ordenar, enfocar, escribir, scroll, cerrar_pestana, seleccionar, atajo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "clic | doble_clic | clic_derecho | senalar | arrastrar | ajustar | ordenar | enfocar | escribir | scroll | cerrar_pestana | seleccionar | atajo"},
                    "objetivo": {"type": "string", "description": "Para clic/doble_clic/clic_derecho: la descripcion de lo que se ve (nombre del boton, nombre de la pestana, o una descripcion visual si no tiene nombre). Para arrastrar: 'X hasta Y'. Para ajustar: 'CONTROL hasta META' (ej. 'el slider de brillo hasta la mitad'). Para enfocar: nombre de la app. Para escribir: el texto. Para atajo: el combo (ej. 'control + s'). Para scroll: 'arriba'/'abajo'. Vacio para ordenar/seleccionar."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gestionar_metas",
            "description": "Gestiona los OBJETIVOS de alto nivel de Marco que AIDEN acompaña en el tiempo (NO tareas con hora ni notas sueltas). Usala cuando Marco diga 'mi meta es X' / 'quiero lograr X' (accion='agregar'), 'avancé en X / ya hice X de mi meta Y' (accion='avance', meta=cuál, nota=qué avanzó), 'ya cumplí/terminé X' (accion='cerrar'), o '¿cuáles son mis metas?' (accion='listar').",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "agregar | avance | cerrar | listar"},
                    "meta": {"type": "string", "description": "El texto/identificador de la meta (para agregar, avance o cerrar). Vacio para listar."},
                    "nota": {"type": "string", "description": "Solo para accion='avance': qué avanzó Marco en esa meta."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_mision",
            "description": "MISIÓN autónoma: para una ORDEN GRANDE de construir algo ('hazme un programa/script/app que...'), AIDEN lo construye con Claude Code, VERIFICA que de verdad funciona, se autocorrige si falla y reporta. Úsala cuando Marco pida CREAR software de cierta envergadura y quiera que QUEDE funcionando. (Para una app simple o un proyecto sin verificar, está proyecto con accion crear.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "objetivo": {"type": "string", "description": "Qué debe lograr la misión, en lenguaje natural y con el detalle que dio Marco."},
                    "nombre": {"type": "string", "description": "Nombre corto para la misión/carpeta. Opcional."}
                },
                "required": ["objetivo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "investigar",
            "description": "Investiga un tema A FONDO (multi-paso: descompone en sub-preguntas, busca cada una en internet y SINTETIZA un informe), te lo reporta por voz y lo guarda como nota. Úsala cuando Marco diga 'investiga/averigua/analiza a fondo X', 'hazme un informe sobre X'. Distinta de buscar (una sola búsqueda) y consultar_experto (razona sin buscar). Tarda; corre en segundo plano.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tema": {"type": "string", "description": "El tema a investigar a fondo, con el detalle que dio Marco."}
                },
                "required": ["tema"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mis_gastos",
            "description": "Reporta cuánto ha GASTADO Marco (de sus cuentas Nequi y Nu, leídas vía Belvo). Úsala cuando pregunte '¿cuánto llevo gastado?', '¿cuánto gasté este mes/semana/hoy?', 'mis gastos'. Distinta de acciones (eso es inversiones, no gasto diario).",
            "parameters": {
                "type": "object",
                "properties": {
                    "periodo": {"type": "string", "description": "mes (por defecto) | semana | hoy"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crear_protocolo",
            "description": "Marco te ENSEÑA una rutina personalizada con nombre ('crea un protocolo modo estudio: cierra YouTube, abre Notion y pon lo-fi'). Queda guardada PARA SIEMPRE y luego se dispara con activar_protocolo. Con eliminar=true la borras. NO es para ejecutar nada ahora: solo aprende la rutina.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre corto del protocolo (ej. 'modo estudio')."},
                    "pasos": {"type": "string", "description": "Los pasos a ejecutar cuando se active, en lenguaje natural y en orden."},
                    "eliminar": {"type": "boolean", "description": "true para BORRAR el protocolo (no hace falta 'pasos')."}
                },
                "required": ["nombre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modo_taller",
            "description": "Sesión de COPILOTO: acompañas a Marco mirando su pantalla mientras trabaja (como Jarvis en el taller de Tony) y comentas solo cuando aportas. Úsala cuando diga 'acompáñame', 'trabajemos juntos', 'quédate mirando esto' (accion=iniciar) o 'ya terminamos', 'cierra el taller' (accion=parar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "iniciar (por defecto) | parar"},
                    "minutos": {"type": "integer", "description": "Duración de la sesión (0 u omitido = 45 min)."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "programar_orden",
            "description": "RECADOS CONDICIONALES de Marco: 'en 20 minutos dime que saque la pizza', 'a las 9:30 recuérdame llamar a mamá', 'cuando abra Chrome recuérdame revisar el correo'. Guardas el recado y AIDEN lo dice SOLO cuando la condición se cumpla. También listar y cancelar. Distinta de notas (eso es apuntar, esto es DISPARAR un aviso).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string", "description": "tiempo (minutos u hora) | app (cuando esa app esté en foco)"},
                    "valor": {"type": "string", "description": "Si tiempo: minutos (ej. '20') u hora (ej. '21:30'). Si app: nombre de la app (ej. 'chrome')."},
                    "recado": {"type": "string", "description": "QUÉ recordarle a Marco cuando dispare."},
                    "accion": {"type": "string", "description": "crear (por defecto) | listar | cancelar (con recado = subcadena a borrar)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_en_pc",
            "description": "LLAVE MAESTRA: ejecuta un comando de PowerShell en el PC de Marco. Úsala para hacer CUALQUIER cosa que Windows permita y que NO tenga ya una herramienta propia: mover/copiar/renombrar/buscar archivos y carpetas, crear archivos, matar/listar procesos, cambiar ajustes del sistema, red (wifi, IP, ping), energía/apagado programado, tareas, registro, limpiar temporales, información del sistema, abrir cosas con parámetros, etc. TÚ compones el PowerShell correcto. Encadena varias acciones con ';'. Para cosas que YA tienen herramienta (música, volumen, apps comunes, clima, WhatsApp) usa esas. Reporta el resultado a Marco en lenguaje natural y breve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": {"type": "string", "description": "El comando de PowerShell a ejecutar (válido, completo)."},
                    "descripcion": {"type": "string", "description": "En una frase, qué logra (para el registro)."},
                    "respuestas": {"type": "string", "description": "Opcional. Qué contestar SI el comando pregunta algo ([Y/n], '¿Desea continuar?'), en orden y separadas por '|' (ej. 'S|Y'). Si lo dejas vacío se responde que SÍ automáticamente. Ya NO hace falta evitar comandos interactivos."},
                    "timeout": {"type": "integer", "description": "Opcional. Segundos máximos (por defecto 45). Súbelo para instalaciones o descargas largas (ej. 300)."}
                },
                "required": ["comando"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "esperar_evento",
            "description": "Se QUEDA ESPERANDO a que algo pase en el PC y avisa en cuanto ocurre. Usala cuando Marco diga 'avisame cuando termine de compilar', 'espera a que copie el enlace', 'dime cuando acabe de exportar', 'avisame cuando conecte el USB'. tipo='proceso_cierra' con filtro=nombre del programa es la mas util: espera a que ese programa TERMINE. NO la uses para recordatorios con hora (eso es programar_orden) ni para condiciones que ya se cumplieron (mira el estado directamente).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {"type": "string", "description": "ventana | portapapeles | usb | descarga | proceso_cierra"},
                    "filtro": {"type": "string", "description": "Texto que debe aparecer (nombre del proceso o de la app, ej. 'Code.exe'). Vacio = cualquiera."},
                    "timeout_segundos": {"type": "integer", "description": "Cuanto esperar como maximo (por defecto 60, tope 600)."}
                },
                "required": ["tipo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hardware",
            "description": "Habla con la placa fisica (ESP32/Arduino) conectada por USB: LED de estado que se ve de reojo, reles para encender luces, y pantallita. Usala si Marco menciona su placa, el LED, la lampara del escritorio o el panel fisico. OJO: si no hay placa conectada lo dice y no pasa nada, no insistas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "escanear | estado | salida | pantalla"},
                    "comando": {"type": "string", "description": "Para 'estado': escuchando|pensando|ejecutando|exito|error|reposo. Para 'salida': el numero de pin. Para 'pantalla': el texto."},
                    "valor": {"type": "integer", "description": "Solo para 'salida': 0 apaga, 1 enciende."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "macro",
            "description": "Convierte en MACRO reutilizable la secuencia que AIDEN acaba de hacer en pantalla, y la repite despues por su nombre. Usala cuando Marco diga 'guarda eso como X', 'aprendete eso', 'la proxima hazlo directo' (accion='guardar'), o cuando pida repetir algo aprendido: 'haz X', 'ejecuta la macro X' (accion='ejecutar'). Vale MUCHISIMO la pena: los pasos que costaron analisis visual quedan grabados y la repeticion es instantanea y gratis. NO la uses para tareas con hora (eso es programar_orden) ni para rutinas de ajustes del sistema (eso es crear_protocolo).",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "guardar (lo que AIDEN acaba de hacer) | grabar (mirar a Marco hacerlo) | detener (cierra la grabacion) | ejecutar | listar | borrar"},
                    "nombre": {"type": "string", "description": "Como se llama la macro (ej. 'exportar reporte')."},
                    "pasos": {"type": "integer", "description": "Solo para guardar: cuantas de las ULTIMAS acciones incluir. 0 o vacio = todas las recientes."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "perifericos",
            "description": "Hardware CONECTADO al PC, y el BRILLO de las pantallas. accion='brillo': sube, baja o fija el brillo de CUALQUIER monitor, el del portatil y los EXTERNOS (habla DDC/CI por el cable de video). Es la UNICA forma de tocar el brillo: 'sube el brillo', 'pon el brillo en 70', 'baja el brillo del monitor grande'. accion='audio': cambia POR DONDE suena el PC ('pasa el sonido a los audifonos'); sin objetivo, lista las salidas. accion='bateria': cuanta bateria les queda al mouse, teclado o audifonos inalambricos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "brillo | audio | bateria"},
                    "objetivo": {"type": "string", "description": "Parte del nombre del dispositivo o monitor (ej. 'sony', 'audifonos'). Vacio = todos / listar."},
                    "nivel": {"type": "string", "description": "Solo para brillo: un numero 0-100, o 'subir'/'bajar' si Marco no dio cifra. Vacio para solo consultar como esta."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memoria_visual",
            "description": "El PASADO VISUAL de la pantalla de Marco: permite responder '¿que decia la pantalla hace 10 minutos?', '¿cual era ese error que se cerro?', '¿en que estaba yo hace un rato?'. accion='buscar' con consulta (texto) o minutos (hace cuanto). Tambien activar / desactivar / estado / olvidar. Es SENSIBLE: nace apagada, guarda solo texto (nunca imagenes), lee en LOCAL, salta bancos y gestores de contraseñas, y olvida sola a las 24 horas. Si Marco pregunta por algo que estuvo en pantalla y esta apagada, dile que puede encenderla.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "reciente (SEGUNDOS atras: lo que acaba de parpadear) | buscar (MINUTOS u horas atras) | activar | desactivar | estado | olvidar"},
                    "consulta": {"type": "string", "description": "Que texto buscar en lo que hubo en pantalla."},
                    "minutos": {"type": "integer", "description": "Para 'buscar': hace cuantos MINUTOS. Para 'reciente': hace cuantos SEGUNDOS (por defecto 10)."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "avisar_al_celular",
            "description": "Le manda un mensaje al CELULAR de Marco por Telegram, sin que el haya preguntado. Usala cuando termine algo largo que el pidio (una mision, una investigacion, una descarga) y pueda no estar frente al PC, o cuando pase algo que deba saber ya. NO la uses para responder lo que te acaba de preguntar aqui.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mensaje": {"type": "string", "description": "Que decirle, en una o dos frases."}
                },
                "required": ["mensaje"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar",
            "description": "FRENO DE EMERGENCIA: detiene lo que AIDEN este EJECUTANDO ahora mismo (un comando largo en el PC, una secuencia de clics, un ajuste visual). Usala cuando Marco diga 'para', 'detente', 'cancela', 'ya no', 'olvidalo' MIENTRAS algo esta corriendo. Marco tambien puede pararlo el mismo con Ctrl+Alt+P. NO la uses para cerrar el asistente (eso es Salir) ni para cancelar un recado programado (eso es programar_orden con accion='cancelar').",
            "parameters": {
                "type": "object",
                "properties": {
                    "motivo": {"type": "string", "description": "Opcional: por que se detiene (para el registro)."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "revisar_correo",
            "description": "Revisa los correos SIN LEER de Marco (asunto + remitente). Úsala cuando pregunte 'revisa mi correo', '¿me llegó algo?', '¿algo importante en el mail?'.",
            "parameters": {
                "type": "object",
                "properties": {"cuantos": {"type": "integer", "description": "Cuántos correos traer (def 5, máx 10)."}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agenda_hoy",
            "description": "Los eventos del calendario de Marco para HOY o MAÑANA (clases, entregas, citas). Úsala cuando pregunte '¿qué tengo hoy?', '¿qué hay en mi agenda?', '¿tengo algo mañana?'.",
            "parameters": {
                "type": "object",
                "properties": {"dia": {"type": "string", "description": "hoy (por defecto) | mañana"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restaurar_sesion",
            "description": "Reabre el espacio de trabajo que Marco tenía (las apps que estaban abiertas). Úsala cuando diga 'retomemos', 'restaura mi sesión', 'abre lo de antes', 'sigamos donde quedamos'. accion 'guardar' fuerza guardar el estado actual.",
            "parameters": {
                "type": "object",
                "properties": {"accion": {"type": "string", "description": "restaurar (por defecto) | guardar"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Enviar_mensaje_Discord",
            "description": "Envía un mensaje por Discord a una persona (DM) o canal. Úsala cuando Marco diga 'mándale a X por Discord...', 'escríbele a X en Discord diciendo...', 'dile a X en Discord que...'. TÚ separas el destino (a quién) y el mensaje.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destino": {"type": "string", "description": "Nombre de la persona (DM) o del canal/servidor."},
                    "mensaje": {"type": "string", "description": "El texto a enviar."}
                },
                "required": ["destino", "mensaje"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_web",
            "description": "Abre una página web en el navegador: un sitio conocido por nombre (youtube, gmail, github, netflix, drive, canvas...) o una URL cualquiera. Úsala para 'abre youtube', 'abre youtube y busca X' (buscar=X), 'abre mi correo', 'abre <página>'. Distinta de buscar (búsqueda en internet) y de Abrir_Videos_Youtube (reproduce directo).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sitio": {"type": "string", "description": "Nombre del sitio (ej. 'youtube') o URL (ej. 'canvas.com')."},
                    "buscar": {"type": "string", "description": "Opcional: qué buscar dentro del sitio (útil en YouTube/Google)."}
                },
                "required": ["sitio"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navegar_web",
            "description": "LA LLAVE MAESTRA DE INTERNET: abre un navegador REAL (con sesión persistente, como si Marco lo usara él mismo) y lo opera SOLO para cumplir un objetivo completo de navegación: comprar, buscar y comparar productos, rellenar formularios, leer y resumir una página larga, iniciar sesión en un sitio, etc. Cierra pop-ups/cookies sola, hace clic y escribe por descripción (funciona aunque la página cambie de diseño), y puede scrollear y resumir contenido largo. NUNCA confirma un pago/pedido final sin que Marco lo autorice explícitamente por voz. Úsala para CUALQUIER tarea de navegación con varios pasos ('entra a X, busca Y, resúmeme las mejores opciones'); para solo ABRIR una página sin interactuar, usa abrir_web (más rápido).",
            "parameters": {
                "type": "object",
                "properties": {
                    "objetivo": {"type": "string", "description": "El objetivo completo de navegación, en lenguaje natural y con todo el detalle que Marco haya dado (ej. 'entra a Temu, busca teclados mecánicos baratos, resume las 3 mejores opciones')."}
                },
                "required": ["objetivo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "que_esta_sonando",
            "description": "Escucha lo que SUENA en la PC ahora mismo (un video, una llamada, un aviso de Windows -- NO el micrófono de Marco) y te dice qué se está diciendo o reproduciendo. Úsala para 'qué está sonando', 'qué dice ese video', 'sonó algo ahorita', 'de qué está hablando ese video de YouTube'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "segundos": {"type": "number", "description": "Cuántos segundos grabar (2 a 30). Por defecto 6."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gestionar_archivos",
            "description": "EJECUTOR DE SISTEMA PROFUNDO: busca, lee metadatos, mueve o copia archivos en CUALQUIER parte del disco (no solo Descargas/Documentos), directo por Python, SIN abrir el Explorador de Windows. Prefiérela sobre controlar_pantalla para cualquier tarea de archivos/carpetas (más rápida, invisible, no depende de qué se vea en pantalla). accion='buscar' (patron[, raiz]); 'metadatos' (origen=ruta); 'mover'/'copiar' (origen=nombre o ruta del archivo, destino=carpeta o alias como 'appdata', 'mods de minecraft', 'escritorio', 'documentos', 'descargas'). Ej. 'pon ese archivo en la carpeta de mods de Minecraft' -> accion='mover', destino='mods de minecraft'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "'buscar', 'metadatos', 'mover' o 'copiar'."},
                    "patron": {"type": "string", "description": "Para 'buscar': texto que debe contener el nombre del archivo."},
                    "origen": {"type": "string", "description": "Para 'metadatos'/'mover'/'copiar': nombre o ruta del archivo."},
                    "destino": {"type": "string", "description": "Para 'mover'/'copiar': carpeta destino (ruta o alias)."},
                    "raiz": {"type": "string", "description": "Opcional, para 'buscar': dónde buscar (por defecto toda la carpeta de usuario)."}
                },
                "required": ["accion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_correo",
            "description": "ENVÍA un correo electrónico por Marco (distinto de revisar_correo, que solo LEE). Úsala cuando diga 'mándale un correo a X diciendo...', 'escríbele un email a...', 'envíale un correo a mi profesor...'. TÚ redactas un asunto adecuado y el mensaje. 'para' es la dirección de email o el nombre de un contacto guardado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "para": {"type": "string", "description": "Dirección de correo (ej. 'profe@unal.edu.co') o nombre de un contacto guardado."},
                    "asunto": {"type": "string", "description": "El asunto del correo (redáctalo tú, breve y claro)."},
                    "mensaje": {"type": "string", "description": "El cuerpo del correo (redáctalo cortés y completo a partir de lo que pide Marco)."}
                },
                "required": ["para", "mensaje"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "redactar_documento",
            "description": "Escribe un DOCUMENTO completo y lo guarda en Word (y lo abre): ensayo, informe, carta, correo, resumen, discurso, reseña, artículo. Úsala cuando Marco diga 'escríbeme un ensayo sobre X', 'hazme un informe de Y', 'redacta una carta para Z', 'escríbeme un correo diciendo...'. TÚ defines el tipo y el tema a partir de lo que pide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tema": {"type": "string", "description": "El tema/contenido sobre el que escribir (todo el detalle que dé Marco)."},
                    "tipo": {"type": "string", "description": "ensayo | informe | carta | correo | resumen | discurso | reseña | artículo | documento"}
                },
                "required": ["tema"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resolver_visual",
            "description": "Mira lo que Marco tiene en PANTALLA (o en la cámara) y lo RESUELVE/explica a fondo con el cerebro experto: un problema de mates/física, una pregunta, un texto difícil, un error de código. Úsala cuando diga 'resuelve esto', 'ayúdame con este problema', 'cómo resuelvo esto', 'explícame esto que tengo aquí'. Distinta de analizar (que solo describe).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fuente": {"type": "string", "description": "pantalla (por defecto) | camara"},
                    "consulta": {"type": "string", "description": "Opcional: la duda concreta de Marco."}
                },
                "required": []
            }
        }
    }
]

tools_map = {
    "Enviar_mensaje_Whatsapp": Enviar_mensaje_Whatsapp,
    "llamada_whatsapp": llamada_whatsapp,
    "colgar": colgar,
    "Abrir_Apps": Abrir_Apps,
    "Abrir_Videos_Youtube": Abrir_Videos_Youtube,
    "guardar_en_json": guardar_en_json,
    "Salir": Salir,
    "Auto_Modificacion": Auto_Modificacion,
    "control_volumen": control_volumen,
    "cerrar_aplicacion": cerrar_aplicacion,
    "ver_apps_abiertas": ver_apps_abiertas,
    "clima": clima,
    "buscar": buscar,
    "analizar": analizar,
    "leer_portapapeles": leer_portapapeles,
    "control_musica": control_musica,
    "notas": notas,
    "contestar_llamada": contestar_llamada,
    "dictar": dictar,
    "abrir_carpeta": abrir_carpeta,
    "control_ventana": control_ventana,
    "resumen_actividad": resumen_actividad,
    "buscar_archivo": buscar_archivo,
    "controlar_energia": controlar_energia,
    "tomar_captura": tomar_captura,
    "activar_protocolo": activar_protocolo,
    "modo_gaming": modo_gaming,
    "resumir": resumir,
    "acciones": acciones,
    "memoria": memoria,
    "noticias_del_dia": noticias_del_dia,
    "calculadora": calculadora,
    "convertir_moneda": convertir_moneda,
    "estado_sistema": estado_sistema,
    "consultar_experto": consultar_experto,
    "explicar_error": explicar_error,
    "proyecto": proyecto,
    "controlar_pantalla": controlar_pantalla,
    "cancelar": cancelar,
    "macro": macro,
    "perifericos": perifericos,
    "memoria_visual": memoria_visual,
    "avisar_al_celular": avisar_al_celular,
    "esperar_evento": esperar_evento,
    "hardware": hardware,
    "gestionar_metas": gestionar_metas,
    "ejecutar_mision": ejecutar_mision,
    "recordar": recordar,
    "investigar": investigar,
    "mis_gastos": mis_gastos,
    "crear_protocolo": crear_protocolo,
    "modo_taller": modo_taller,
    "programar_orden": programar_orden,
    "ejecutar_en_pc": ejecutar_en_pc,
    "revisar_correo": revisar_correo,
    "agenda_hoy": agenda_hoy,
    "enviar_correo": enviar_correo,
    "navegar_web": navegar_web,
    "que_esta_sonando": que_esta_sonando,
    "gestionar_archivos": gestionar_archivos,
    "restaurar_sesion": restaurar_sesion,
    "Enviar_mensaje_Discord": Enviar_mensaje_Discord,
    "abrir_web": abrir_web,
    "redactar_documento": redactar_documento,
    "resolver_visual": resolver_visual,
}