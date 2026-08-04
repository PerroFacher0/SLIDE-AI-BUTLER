# AIDEN — Decisiones de diseño y filosofía (fuente para la wiki)

> Documento-fuente para el segundo cerebro: el PORQUÉ detrás de AIDEN. Cada bloque es una
> decisión con su contexto, qué se eligió, por qué, y qué alternativa se descartó. Ideal para
> crear "páginas de decisión" en la wiki (enlázalas a las entidades/conceptos que tocan).

---

## Principios rectores (la filosofía en 8 frases)
1. **La personalidad es SAGRADA.** El humor pintoresco/descarado de AIDEN es ~50% de quién es.
2. **Acción sobre explicación.** Ejecuta, no anuncia. Las preguntas son órdenes.
3. **Latencia > IQ** para un asistente de voz. Un Jarvis lento no se siente Jarvis.
4. **El bloat de herramientas es real.** Menos tools = mejor precisión de function-calling.
5. **Proactividad con candados.** Lo proactivo debe poder callarse y no molestar.
6. **No editar de más.** Cambios quirúrgicos; analizar antes de tocar.
7. **Verificar todo.** Compilar, contar, probar antes de cantar victoria.
8. **Seguridad primero.** Secretos fuera de git; escanear antes de pushear.

---

## D1 — Cerebro: `gemini-2.5-flash`, no `flash-lite`
- **Contexto**: con muchas tools, flash-lite devolvía `MALFORMED_FUNCTION_CALL` intermitente.
- **Medición**: flash-lite malformaba ~50% (3/6) de las llamadas; flash dio 0 errores, casi igual de rápido (~1.7s vs 1.6s).
- **Elección**: `MODELO = google/gemini-2.5-flash`.
- **Descartado**: flash-lite (barato pero poco confiable con tantas tools).

## D2 — NO subir el cerebro a un modelo pesado; usar DOS niveles
- **Contexto**: tentación de poner gemini-2.5-pro como cerebro para más IQ.
- **Elección**: cerebro = flash (rápido); para lo difícil, herramienta `consultar_experto` → pro.
- **Por qué**: en el 95% de los casos la **latencia importa más que el IQ extra**. Así se tiene lo mejor de ambos: respuestas rápidas con personalidad + razonamiento profundo bajo demanda.
- **Concepto**: [[modelo de dos niveles]].

## D3 — Escalada de temperatura (0.7 → 0), no temperatura plana 0
- **Contexto**: a temperatura alta hay más MALFORMED; a 0 es confiable pero se pierde la chispa.
- **Dato clave**: el error SOLO ocurre al generar una LLAMADA a herramienta, **nunca al escribir texto** (y el humor vive en el texto).
- **Elección**: 1er intento a `TEMPERATURA=0.7` (chispa); si malforma, reintenta a `TEMPERATURA_SEGURA=0` (`MAX_REINTENTOS=5`).
- **Descartado**: temperatura plana 0 (mata la esencia de Jarvis, que Marco valora mucho).

## D4 — La personalidad es sagrada
- **Elección**: el prompt dedica una sección grande a HUMOR/CHISPA (Jarvis seco, descarado con cariño). Las consolidaciones de prompt NUNCA la tocan.
- **Por qué**: Marco quiere a AIDEN precisamente por su carácter; sin chispa es un asistente genérico.
- **Límites**: el roast es cariñoso, nunca cruel, y SOLO sobre cosas reales (nada de alucinar para el chiste).

## D5 — Anti-bloat: consolidar herramientas
- **Contexto**: se llegó a 47 tools (~8k tokens por llamada) y más opciones degradan la precisión.
- **Elección**: 47 → 43 quitando `traducir`/`definir` (el modelo los hace inline) y fusionando finanzas (`mis_acciones`) y resúmenes (`resumir`).
- **Regla**: preferir consolidar SIN perder capacidad; el prompt no es el peso real, las tools sí.

## D6 — Proactividad como COMPORTAMIENTOS, no como tools
- **Elección**: anticipación, presencia, alertas, descanso, etc. son **hilos daemon**, no herramientas.
- **Por qué**: no gastan el cupo de function-calling ni dependen de que el modelo decida llamarlas; corren solos cuando toca.

## D7 — Diseño anti-molestia (para todo lo proactivo)
- **Elección**: cada cosa proactiva tiene candados: límites diarios/cooldowns (anticipación), reconocer a Marco + no abrir el mic + solo al llegar (presencia), pausa total en modo gaming.
- **Por qué**: un asistente que molesta se apaga. La proactividad solo vale si es bienvenida.
- **Concepto**: [[diseño anti-molestia]].

## D8 — Memoria episódica SIN embeddings
- **Elección**: recall por **solapamiento de palabras clave + recencia**, no vector DB.
- **Por qué**: cero dependencias pesadas, cero latencia extra, suficiente a esta escala. Si no cruza nada, no inyecta ruido.
- **Descartado**: embeddings/RAG (overkill para el tamaño actual).

## D9 — Dos cerebros separados (voz y Telegram)
- **Elección**: `proceso_de_ia` (voz, streaming, barge-in) y `procesar_remoto` (texto, no streaming), con **memorias de contexto separadas** y un lock para el remoto.
- **Por qué**: la voz necesita streaming + interrupción; Telegram necesita texto limpio. Memorias separadas evitan que se pisen.

## D10 — Instancia única (candado de socket)
- **Contexto**: corrían DOS AIDEN a la vez (auto-arranque + F5) → OOM / "se duplicaba el bicho".
- **Elección**: bind a `127.0.0.1:50607` al inicio; la 2ª copia se cierra. `AIDEN.bat` lanza solo `Main_AlwaysOn.py`.

## D11 — Login facial en el HILO PRINCIPAL (always-on)
- **Elección**: el reconocimiento facial corre en el hilo principal de Qt.
- **Por qué**: evita un bug de cámara al usarla entre hilos.

## D12 — Wake word con Whisper en CPU
- **Elección**: el Whisper del wake word (`VAD.py`) corre en CPU; solo el Whisper de la petición y Kokoro están en CUDA.
- **Por qué**: así el **modo gaming puede descargar los modelos CUDA sin matar la palabra clave**.

## D13 — Liberar VRAM en modo gaming (Kokoro después de hablar)
- **Contexto**: la RTX 5050 solo tiene 8GB.
- **Elección**: gaming descarga Whisper de voz de una y Kokoro DESPUÉS de la confirmación hablada (un hilo espera `_lock_audio`).
- **Por qué**: si descargara Kokoro de una, no podría decir "modo gaming activado". Beneficio real medido: ~0.6 GB.

## D14 — Telegram arranca ANTES del login facial
- **Elección**: `iniciar_telegram()` se llama antes del reconocimiento facial.
- **Por qué**: poder controlar el PC desde el celular **aunque Marco no esté presente**.

## D15 — Fecha/hora inyectada en el prompt cada turno
- **Contexto**: AIDEN no sabía qué día/hora era (el global `hora` se calculaba 1 vez y no se usaba).
- **Elección**: `_fecha_hora_actual()` (español, sin locale) inyectada cada turno.
- **Por qué**: arregla decir la hora, los recordatorios (`guardar_en_json`) y anclar "hoy/ayer/mañana". Cero latencia, cero tools nuevas.

## D16 — Seguridad: `secretos.py` fuera de git + plantilla
- **Elección**: `secretos.py` en `.gitignore`; se versiona `secretos.ejemplo.py` (plantilla sin datos).
- **Pendiente crítico**: la API key vieja quedó en el HISTORIAL de git (repo público) → hay que **rotarla**.

## D17 — Nada de tkinter para el splash
- **Elección**: el splash NO se usa. Causaba un crash fatal. (Vigilancia con auto-arranque también
  queda off.)
- **Aclaración (revisado en agosto 2026)**: la decisión se aplicó **quitando la llamada, no el
  archivo**. `Interfaz/Pantalla_Carga.py` sigue en el repo y sigue importando tkinter, lo cual a
  primera vista contradice esta decisión — pero **nadie lo importa**: las únicas menciones a
  `Pantalla_Carga` están dentro de su propio docstring, en el ejemplo de uso. Está desconectado, así
  que hoy el riesgo es cero.
- **Qué NO hacer**: volver a engancharlo a `Main.py` / `Main_AlwaysOn.py`. Eso reintroduce
  exactamente el crash que motivó esta decisión. Si algún día hace falta un splash, hay que
  rehacerlo en PySide6 (que ya es dependencia y es lo que usa todo lo demás), no reactivar este.
- **Por qué no se borra**: no molesta a nadie y guarda el trabajo de la animación por si se
  reescribe. Queda avisado en la cabecera del propio archivo.

## D18 — Estética holográfica plata, en UN solo módulo
- **Contexto**: la paleta anterior era gris monocromo plano, y cada superficie la implementaba por
  su cuenta: la Mira con rectángulos redondeados, el overlay con su hoja de estilo, la esfera con
  sus variables CSS. Tres versiones del mismo gris — cada retoque había que hacerlo tres veces, así
  que tarde o temprano una se quedaba atrás y el conjunto se veía descosido.
- **Elección**: `Interfaz/_Estilo.py` como única fuente. Fondo casi negro neutro `RGBA(21,22,26,240)`
  y UN acento plata desaturado `#DCE1E6` (`#F2F4F6` para la línea más viva del borde). Geometría
  angular: paneles con las esquinas cortadas en diagonal — un redondeado dice "aplicación", un corte
  recto dice "instrumento". El resplandor se hace dibujando el borde **cuatro veces** (ancho y casi
  invisible → fino y brillante), no con desenfoque real.
- **Por qué el glow por capas y no `QGraphicsBlurEffect`**: el desenfoque de verdad rehace la textura
  en cada repintado, y esto se repinta ~25 veces por segundo encima de lo que Marco esté haciendo.
  Cuatro trazos cuestan casi nada y se ven igual.
- **Descartado**: cian y azul eléctrico saturados. Se probaron y se sintieron artificiales, de HUD
  de videojuego; esto es una herramienta que Marco tiene delante todo el día. El cian sigue en el
  selector de la esfera, pero ya no es lo que se ve al arrancar.
- **Se mantiene la regla de siempre**: un acento a la vez, nada de arcoíris. El rojo y el verde
  quedan reservados **solo** para valores que suben o bajan — si además decoraran, dejarían de
  significar algo.
- **Los modos del overlay no cambian de lógica**: se siguen leyendo por BRILLO (misión > taller >
  normal > reunión > gaming > ausente), conservando exactamente las proporciones de antes; lo único
  que cambia es que ahora se atenúa el plata en vez de un gris suelto.
- **Mayúsculas solo en etiquetas cortas** ("ESCUCHANDO", "PERCIBE"), nunca en contenido: un dato ya
  formateado por una herramienta (`NVDA $128.50 +3.2%`, un asunto de correo, un nombre propio) se
  destroza en mayúsculas y además dejaría de coincidir con lo que dice la voz.
- **Nota**: Python y JavaScript no pueden compartir la constante, así que la esfera copia el valor
  (`ACENTO_HEX`). Si se cambia en un lado, hay que cambiarlo en el otro — está dicho en ambos.

---

### Para la wiki
- Crear una **página de decisión por cada D#**, enlazada a sus conceptos/entidades.
- Conceptos centrales que emergen: [[modelo de dos niveles]], [[escalada de temperatura]],
  [[diseño anti-molestia]], [[anti-bloat de herramientas]], [[las tres memorias]],
  [[liberación de VRAM]], [[personalidad sagrada]].
