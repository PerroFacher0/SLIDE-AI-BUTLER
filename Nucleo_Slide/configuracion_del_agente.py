from Funciones_Slide.Comunicacion.Funciones_Variadas import enviar_mensaje, llamada_whatsapp, colgar, Auto_Modificacion
from Funciones_Slide.Sistema.Comandos_Asistente import Abrir_Apps, Abrir_Videos_Youtube, Salir
from Funciones_Slide.Sistema.Funciones_Sistema import cerrar_aplicacion, ver_apps_abiertas, clima, buscar, leer_portapapeles, control_musica, control_volumen, estado_sistema
from Nucleo_Slide.Memoria import memoria
from Funciones_Slide.Info.Vision import analizar
from Funciones_Slide.Info.Finanzas import acciones
from Funciones_Slide.Productividad.Notas import notas
from Funciones_Slide.Comunicacion.Llamadas import contestar_llamada
from Funciones_Slide.Sistema.Control_PC import dictar, control_ventana, controlar_energia, tomar_captura
from Funciones_Slide.Sistema.Control_Pantalla import controlar_pantalla
from Nucleo_Slide.Cancelacion import cancelar
from Funciones_Slide.Sistema.Macros import macro
from Funciones_Slide.Sistema.Perifericos import perifericos
from Funciones_Slide.Comunicacion.Telegram_Control import avisar_al_celular
from Nucleo_Slide.Memoria_Visual import memoria_visual
from Funciones_Slide.Sistema.Vigilante_Eventos import esperar_evento
from Funciones_Slide.Sistema.Hardware_Externo import hardware
from Funciones_Slide.Sistema.Elevacion import permisos
from Funciones_Slide.Sistema.Office import office
from Funciones_Slide.Productividad.Metas import gestionar_metas
from Nucleo_Slide.Memoria_RAG import recordar
from Funciones_Slide.Info.Investigacion import investigar
from Funciones_Slide.Info.Finanzas_Gastos import mis_gastos
from Funciones_Slide.Productividad.Protocolos import protocolo
from Funciones_Slide.Sistema.Taller import modo_taller
from Funciones_Slide.Productividad.Ordenes_Condicionales import programar
from Funciones_Slide.Sistema.Control_Total import ejecutar_en_pc
from Funciones_Slide.Info.Agenda import revisar_correo, agenda_hoy
from Funciones_Slide.Sistema.Sesion import restaurar_sesion
from Funciones_Slide.Info.Web import abrir_web
from Funciones_Slide.Sistema.Navegador_Web import navegar_web
from Funciones_Slide.Sistema.Escucha_Sistema import que_esta_sonando
from Funciones_Slide.Sistema.Gestor_Archivos import gestionar_archivos
from Funciones_Slide.Info.Redactor import redactar_documento
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
                    "name": "enviar_mensaje",
                    "description": "Le ESCRIBE a alguien, por el canal que Marco indique. canal='whatsapp' (el mas habitual), 'discord' o 'correo'. Usala para 'mandale a X diciendo...', 'escribele a X en Discord que...', 'mandale un correo a mi profesor...'. Tu separas a QUIEN va (destino) de QUE se dice (mensaje), y si es correo REDACTAS tu un asunto adecuado. Para LLAMAR usa llamada_whatsapp; para LEER el correo usa revisar_correo; para mandarlo MAS TARDE usa programar.",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "canal": {
                                            "type": "string",
                                            "description": "whatsapp | discord | correo"
                                    },
                                    "destino": {
                                            "type": "string",
                                            "description": "A quien: nombre del contacto (MAMA, TITO...), usuario o canal de Discord, o direccion de correo."
                                    },
                                    "mensaje": {
                                            "type": "string",
                                            "description": "El contenido del mensaje."
                                    },
                                    "asunto": {
                                            "type": "string",
                                            "description": "Solo para correo: el asunto. Redactalo tu si Marco no lo dijo."
                                    }
                            },
                            "required": [
                                    "canal",
                                    "destino",
                                    "mensaje"
                            ]
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
            "description": "Cierra una aplicacion abierta, por su nombre (ej. 'chrome', 'spotify'). Con forzar=true la MATA sin pedirle permiso: eso es lo que hay que hacer con una app COLGADA que no responde ('cierra Chrome a la fuerza', 'mata el proceso X'). Si la app tiene cambios sin guardar puede NO cerrarse y te lo dira: en ese caso preguntale a Marco si forzar (se pierde lo no guardado) antes de reintentar con forzar=true. Para cerrar solo una VENTANA o una PESTAÑA usa control_ventana o controlar_pantalla.",
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
                    "description": "AIDEN MIRA lo que Marco tiene delante. fuente 'pantalla' (por defecto) mira la PANTALLA del PC; fuente 'camara' mira por la CAMARA (el entorno, un objeto). Con a_fondo=false solo lo DESCRIBE, rapido ('¿que ves?', 'mira esto', '¿que opinas de esto?'). Con a_fondo=true lo RESUELVE razonando paso a paso con el cerebro experto: usa a_fondo=true cuando Marco diga 'resuelve esto', 'ayudame con este problema', 'explicame esto a fondo', o cuando sea un ejercicio de mates/fisica, un error de codigo o un texto dificil. NO la uses para GUARDAR una captura (eso es tomar_captura) ni para recuperar algo que YA no esta en pantalla (eso es memoria_visual).",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "fuente": {
                                            "type": "string",
                                            "description": "pantalla (por defecto) | camara"
                                    },
                                    "consulta": {
                                            "type": "string",
                                            "description": "Que quiere saber Marco sobre lo que se ve. Opcional."
                                    },
                                    "a_fondo": {
                                            "type": "boolean",
                                            "description": "true = resolver/explicar a fondo con el experto (tarda mas). false (por defecto) = solo describir."
                                    }
                            },
                            "required": []
                    }
            }
    },
{
        "type": "function",
        "function": {
            "name": "resumen_actividad",
            "description": "Dos preguntas parecidas, un solo sitio. que='notificaciones' (por defecto): lo que pasó en el PC mientras Marco no estaba — mensajes de WhatsApp/Discord, correos, alertas; al darle el resultado RESALTA lo relevante y omite el ruido (actualizaciones, promos). que='autonomo': lo que TÚ hiciste POR TU CUENTA, sin que él lo pidiera — avisos proactivos, recados que entregaste, archivos que ordenaste solo, habilidades que te programaste. Usa 'autonomo' cuando pregunte '¿qué has hecho por tu cuenta?', '¿qué decidiste sin preguntarme?', '¿qué hiciste mientras no estaba?' referido a TI y no al PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "horas": {"type": "number", "description": "Cuántas horas hacia atrás revisar (por defecto 16). Opcional."},
                    "que": {"type": "string", "description": "'notificaciones' (por defecto) = lo que pasó en el PC. 'autonomo' = lo que AIDEN decidió y ejecutó por su cuenta."}
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
                    "name": "protocolo",
                    "description": "PROTOCOLOS: escenas que cambian varias cosas del PC a la vez, estilo Jarvis. accion='activar' dispara uno: 'cine' (baja brillo, sube volumen, silencia interrupciones), 'buenas noches', 'concentracion', 'normal' (restaura todo), o cualquiera que Marco haya enseñado. accion='crear' es cuando Marco te ENSEÑA una rutina nueva ('crea un protocolo modo estudio: cierra YouTube, abre Notion y pon lo-fi') — queda guardada para siempre y NO se ejecuta en ese momento. Tambien 'borrar' y 'listar'.",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "accion": {
                                            "type": "string",
                                            "description": "activar (por defecto) | crear | borrar | listar"
                                    },
                                    "nombre": {
                                            "type": "string",
                                            "description": "Como se llama el protocolo (ej. 'cine', 'modo estudio')."
                                    },
                                    "pasos": {
                                            "type": "string",
                                            "description": "Solo para crear: los pasos de la rutina, en lenguaje natural, separados por comas."
                                    }
                            },
                            "required": [
                                    "accion"
                            ]
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
            "description": "Escribe donde este el cursor de Marco (campo o documento activo). Con 'texto' escribe ESO una vez: 'escribe...', 'pon...'. Con continuo=true entra en modo DICTADO: se queda escuchando y va escribiendo TODO lo que Marco diga, frase por frase y TAL CUAL, hasta que diga 'fin del dictado' — usa continuo=true cuando pida 'tomame dictado', 'voy a dictarte algo largo', 'escribe lo que te voy diciendo'. En ese modo el texto NO pasa por ti: sale como el lo dijo. NO la uses para REDACTAR un texto tu mismo a partir de un tema (eso es redactar_documento).",
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string", "description": "El texto a escribir (para una sola vez)."},
                    "continuo": {"type": "boolean", "description": "true = modo dictado: escribe todo lo que Marco vaya diciendo hasta que pare."}
                },
                "required": []
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
                    "description": "Programas y proyectos REALES construidos por Claude Code en un sandbox del Escritorio. accion='crear' (por defecto) delega en Claude Code que escriba los archivos a partir de 'instruccion' ('creame', 'programame', 'hazme un programa que...'). Pon verificar=true cuando Marco quiera que QUEDE FUNCIONANDO y no solo escrito: AIDEN lo ejecuta, comprueba que corre y se autocorrige si falla — usalo para encargos grandes. accion='ejecutar' corre uno ya creado. Tarda; corre en segundo plano y AIDEN avisa al terminar. Para que AIDEN se programe una habilidad A SI MISMO usa Auto_Modificacion.",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "accion": {
                                            "type": "string",
                                            "description": "crear (por defecto) | ejecutar"
                                    },
                                    "instruccion": {
                                            "type": "string",
                                            "description": "Que debe construir, con el detalle que dio Marco."
                                    },
                                    "nombre": {
                                            "type": "string",
                                            "description": "Nombre corto de la carpeta del proyecto."
                                    },
                                    "archivo": {
                                            "type": "string",
                                            "description": "Solo para ejecutar: el archivo a correr. Opcional."
                                    },
                                    "verificar": {
                                            "type": "boolean",
                                            "description": "true = ademas de construirlo, ejecutarlo y autocorregirlo hasta que funcione."
                                    }
                            },
                            "required": []
                    }
            }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_pantalla",
            "description": "Interaccion VISIBLE con la pantalla: AIDEN mueve el MOUSE y el TECLADO sobre lo que YA esta en pantalla, y Marco lo VE. El clic funciona con CUALQUIER cosa visible: primero busca el nombre en la estructura de accesibilidad (instantaneo) y, si no lo encuentra (juegos, apps de lienzo, iconos sin texto), UBICA el objetivo VIENDO la pantalla y hace clic ahi igual (un poco mas lento, pero cubre lo que sea). Funciona en VARIOS MONITORES. USA ESTA para: clic/doble clic/clic derecho en cualquier elemento, IR A UNA PESTANA del navegador por su nombre (accion 'clic' con el nombre de la pestana, ej. objetivo='GitHub'), HOVER (dejar el cursor encima SIN clicar, para desplegar un menu o un tooltip), SENALAR donde esta algo dibujandole un recuadro en pantalla SIN tocarlo (accion 'senalar', para '¿donde esta el boton de exportar?' — mucho mejor que describirlo con palabras), ARRASTRAR una cosa hasta otra, AJUSTAR un control continuo hasta lograr un resultado (slider de brillo/volumen/recorte: mira, mueve y VUELVE A MIRAR hasta que quede bien), ordenar ventanas en mosaico, traer una app al frente, teclear, hacer scroll, CERRAR UNA PESTANA (Ctrl+W), seleccionar, o un atajo de teclas. NO la uses para abrir una app nueva (usa Abrir_Apps), ni para minimizar/maximizar/cerrar la VENTANA entera (usa control_ventana), ni para pegar texto largo de golpe (usa dictar), ni para leer/analizar lo que hay en pantalla (usa analizar). MOSTRAR_ELEMENTOS numera en pantalla TODO lo clicable de la ventana activa y te devuelve la lista: usalo cuando no encuentres algo por su nombre o cuando Marco pregunte 'que puedo tocar aqui' — despues Marco (o tu) puede decir simplemente el NUMERO como objetivo ('4') y es instantaneo. COLOCAR mueve una ventana a un MONITOR concreto (objetivo='chrome en el monitor 2'). AISLAR oscurece todo el escritorio menos una ventana, para concentrarse; 'normal' lo quita. Un protocolo personalizado puede encadenar colocar + Abrir_Apps + aislar para armar un 'modo investigar' — no hace falta una herramienta aparte para eso. accion posibles: clic, doble_clic, clic_derecho, hover, senalar, arrastrar, ajustar, ordenar, colocar, aislar, normal, mostrar_elementos, enfocar, escribir, scroll, cerrar_pestana, seleccionar, atajo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "clic | doble_clic | clic_derecho | hover | senalar | arrastrar | ajustar | ordenar | colocar | aislar | normal | mostrar_elementos | enfocar | escribir | scroll | cerrar_pestana | seleccionar | atajo"},
                    "objetivo": {"type": "string", "description": "Para clic/doble_clic/clic_derecho: la descripcion de lo que se ve (nombre del boton, nombre de la pestana, o una descripcion visual si no tiene nombre). Para arrastrar: 'X hasta Y'. Para ajustar: 'CONTROL hasta META' (ej. 'el slider de brillo hasta la mitad'). Para enfocar: nombre de la app. Para escribir: el texto. Para atajo: el combo (ej. 'control + s'). Para scroll: 'arriba'/'abajo'. Para colocar: 'chrome en el monitor 2' (o solo 'en el monitor 2' para la ventana activa). Para aislar: nombre de la app, o vacio para la activa. UN NUMERO SUELTO ('4') hace clic en ese elemento de la ultima lista de mostrar_elementos. Vacio para ordenar/seleccionar/normal/mostrar_elementos."}
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
                    "name": "programar",
                    "description": "Deja algo listo para MAS TARDE. 'cuando' es el disparador: minutos ('20'), una hora ('21:30'), o el nombre de una app ('chrome' = cuando la abra). Por defecto (hacer='recordar') AIDEN solo lo DICE cuando llegue el momento: 'en 20 minutos dime que saque la pizza', 'a las 9:30 recuerdame llamar a mama', 'cuando abra Chrome recuerdame revisar el correo'. Con hacer='whatsapp' o 'llamar' AIDEN lo EJECUTA solo a esa hora (necesita contacto). Tambien listar y cancelar. Distinta de notas (eso es apuntar, esto DISPARA) y de esperar_evento (eso se queda esperando AHORA, esto lo agenda).",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "cuando": {
                                            "type": "string",
                                            "description": "Minutos ('20'), hora ('21:30') o nombre de app ('chrome')."
                                    },
                                    "recado": {
                                            "type": "string",
                                            "description": "Que decirle a Marco, o que texto mandar si es un WhatsApp."
                                    },
                                    "hacer": {
                                            "type": "string",
                                            "description": "recordar (por defecto) | whatsapp | llamar | colgar"
                                    },
                                    "contacto": {
                                            "type": "string",
                                            "description": "A quien, solo para whatsapp/llamar."
                                    },
                                    "accion": {
                                            "type": "string",
                                            "description": "crear (por defecto) | listar | cancelar"
                                    }
                            },
                            "required": []
                    }
            }
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_en_pc",
            "description": "LLAVE MAESTRA: ejecuta un comando de PowerShell en el PC de Marco. Úsala para hacer CUALQUIER cosa que Windows permita y que NO tenga ya una herramienta propia: mover/copiar/renombrar/buscar archivos y carpetas, crear archivos, matar/listar procesos, cambiar ajustes del sistema, red (wifi, IP, ping), energía/apagado programado, tareas, registro, limpiar temporales, información del sistema, abrir cosas con parámetros, etc. TÚ compones el PowerShell correcto. Encadena varias acciones con ';'. Para cosas que YA tienen herramienta (música, volumen, apps comunes, clima, WhatsApp) usa esas. Reporta el resultado a Marco en lenguaje natural y breve. La CARPETA DE TRABAJO se recuerda entre llamadas: si un comando entra en una carpeta, el siguiente empieza ahi (las variables si se limpian). Si el comando abre una ventana, se te dice cual, para que puedas actuar sobre ella con controlar_pantalla.",
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
            "description": "Se QUEDA ESPERANDO a que algo pase en el PC y avisa en cuanto ocurre. Usala cuando Marco diga 'avisame cuando termine de compilar', 'espera a que copie el enlace', 'dime cuando acabe de exportar', 'avisame cuando conecte el USB'. tipo='proceso_cierra' con filtro=nombre del programa es la mas util: espera a que ese programa TERMINE. NO la uses para recordatorios con hora (eso es programar) ni para condiciones que ya se cumplieron (mira el estado directamente).",
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
            "name": "permisos",
            "description": "Los permisos con los que corre AIDEN en Windows. Usala cuando algo falle por FALTA DE PERMISOS de administrador, o cuando Marco pregunte si va como admin. accion='elevar' se reabre como administrador (a Marco le sale UN dialogo de Windows que debe aceptar el; despues ya no vuelve a salir). accion='arranque' deja que arranque elevado solo al iniciar sesion, sin mas dialogos. OJO: el dialogo del UAC vive en un escritorio aislado por el kernel y NINGUNA herramienta puede pulsarlo — por eso la salida es elevarse ANTES, no intentar clicarlo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "estado (por defecto) | elevar | arranque | quitar_arranque"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "office",
            "description": "Trabaja DENTRO de Excel o Word directamente, sin clicar en la pantalla: leer o escribir una celda concreta, añadir texto a un documento, guardar, o resumir que hay. Usala siempre que la tarea sea sobre una HOJA DE CALCULO o un DOCUMENTO ('pon 1500 en la celda B4', '¿que dice la celda A1?', 'guarda el Excel', 'añade este parrafo al documento'). Es mas fiable que controlar_pantalla para esto: no depende de que la celda este visible ni de acertar el clic. Trabaja sobre lo que Marco YA tiene abierto salvo que se le de un archivo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "programa": {"type": "string", "description": "excel | word"},
                    "accion": {"type": "string", "description": "leer | escribir | guardar | resumen"},
                    "celda": {"type": "string", "description": "Solo Excel: la celda o rango (ej. 'B4', 'A1:C10')."},
                    "valor": {"type": "string", "description": "Que escribir."},
                    "hoja": {"type": "string", "description": "Solo Excel: nombre de la hoja. Vacio = la activa."},
                    "archivo": {"type": "string", "description": "Solo si hay que ABRIRLO. Si ya esta abierto, dejar vacio."}
                },
                "required": ["programa", "accion"]
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
            "description": "Convierte en MACRO reutilizable la secuencia que AIDEN acaba de hacer en pantalla, y la repite despues por su nombre. Usala cuando Marco diga 'guarda eso como X', 'aprendete eso', 'la proxima hazlo directo' (accion='guardar'), o cuando pida repetir algo aprendido: 'haz X', 'ejecuta la macro X' (accion='ejecutar'). Vale MUCHISIMO la pena: los pasos que costaron analisis visual quedan grabados y la repeticion es instantanea y gratis. NO la uses para tareas con hora (eso es programar) ni para rutinas de ajustes del sistema (eso es protocolo).",
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
            "description": "Hardware CONECTADO al PC, y el BRILLO de las pantallas. accion='brillo': sube, baja o fija el brillo de CUALQUIER monitor, el del portatil y los EXTERNOS (habla DDC/CI por el cable de video). Es la UNICA forma de tocar el brillo: 'sube el brillo', 'pon el brillo en 70', 'baja el brillo del monitor grande'. accion='audio': cambia POR DONDE suena el PC ('pasa el sonido a los audifonos'); sin objetivo, lista las salidas. accion='volumen_app': volumen de UNA aplicacion sin tocar el resto ('bajale a Spotify', 'sube Chrome') — objetivo=nombre de la app, nivel=0-100; para el volumen GENERAL usa control_volumen. accion='bateria': cuanta bateria les queda al mouse, teclado o audifonos inalambricos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "description": "brillo | audio | volumen_app | bateria"},
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
            "description": "FRENO DE EMERGENCIA: detiene lo que AIDEN este EJECUTANDO ahora mismo (un comando largo en el PC, una secuencia de clics, un ajuste visual). Usala cuando Marco diga 'para', 'detente', 'cancela', 'ya no', 'olvidalo' MIENTRAS algo esta corriendo. Marco tambien puede pararlo el mismo con Ctrl+Alt+P. NO la uses para cerrar el asistente (eso es Salir) ni para cancelar un recado agendado (eso es programar con accion='cancelar').",
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
                    "description": "TODO lo de archivos y carpetas. accion='abrir': busca un archivo por nombre en las carpetas de Marco y lo ABRE ('abreme el pdf de la tarea', 'busca el archivo X'). accion='abrir_carpeta': abre una carpeta en el Explorador ('abre mis descargas'). accion='buscar': lo localiza en CUALQUIER parte del disco y te dice donde esta, SIN abrirlo. accion='metadatos': tamaño, tipo y fechas. accion='mover'/'copiar': lo mueve o copia entre carpetas. accion='borrar_seguro': lo manda a la PAPELERA (reversible; usala siempre en vez de borrar de verdad). accion='comprimir_zip'/'descomprimir_zip': lo empaqueta o lo extrae (origen=que, destino=donde). Admite alias de voz ('mods de minecraft', 'appdata'). Prefierela sobre controlar_pantalla para cualquier tarea de archivos: es mas rapida y no depende de lo que se vea en pantalla.",
                    "parameters": {
                            "type": "object",
                            "properties": {
                                    "accion": {
                                            "type": "string",
                                            "description": "abrir | abrir_carpeta | buscar | metadatos | mover | copiar | borrar_seguro | comprimir_zip | descomprimir_zip"
                                    },
                                    "patron": {
                                            "type": "string",
                                            "description": "Nombre o trozo del nombre del archivo (para abrir/buscar), o de la carpeta (para abrir_carpeta: descargas, documentos, escritorio, imagenes, musica, videos)."
                                    },
                                    "origen": {
                                            "type": "string",
                                            "description": "Archivo de partida (para metadatos/mover/copiar)."
                                    },
                                    "destino": {
                                            "type": "string",
                                            "description": "Carpeta de destino (para mover/copiar). Admite alias."
                                    },
                                    "raiz": {
                                            "type": "string",
                                            "description": "Donde buscar, si Marco lo acota. Opcional."
                                    }
                            },
                            "required": [
                                    "accion"
                            ]
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
]

tools_map = {
    "enviar_mensaje": enviar_mensaje,
    "llamada_whatsapp": llamada_whatsapp,
    "colgar": colgar,
    "Abrir_Apps": Abrir_Apps,
    "Abrir_Videos_Youtube": Abrir_Videos_Youtube,
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
    "control_ventana": control_ventana,
    "resumen_actividad": resumen_actividad,
    "controlar_energia": controlar_energia,
    "tomar_captura": tomar_captura,
    "protocolo": protocolo,
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
    "permisos": permisos,
    "office": office,
    "gestionar_metas": gestionar_metas,
    "recordar": recordar,
    "investigar": investigar,
    "mis_gastos": mis_gastos,
    "modo_taller": modo_taller,
    "programar": programar,
    "ejecutar_en_pc": ejecutar_en_pc,
    "revisar_correo": revisar_correo,
    "agenda_hoy": agenda_hoy,
    "navegar_web": navegar_web,
    "que_esta_sonando": que_esta_sonando,
    "gestionar_archivos": gestionar_archivos,
    "restaurar_sesion": restaurar_sesion,
    "abrir_web": abrir_web,
    "redactar_documento": redactar_documento,
}