# Ingesta Obsidian — Julio 2026 (desde la última ingesta hasta hoy)

Cubre TODO lo construido entre el 2026-07-01 y el 2026-07-25 que aún no se había documentado en el
segundo cerebro (25 commits, ~3.5 semanas). La última ingesta previa fue `5103157` (Presencia
Continua + dinámicas Jarvis-Tony: co-ingeniero, consejero, preparación, investigar). Todo lo de aquí
en adelante es posterior a eso.

Estado al cierre de este periodo: **65 herramientas**, arquitectura reestructurada (enrutador de voz
compartido, percepción total, control de PC casi instantáneo con y sin LLM), y el overlay pasó por
3 rediseños visuales sucesivos hasta llegar a una paleta monocroma "gris/plata" definitiva.

---

# PARTE A — Coherencia, aprendizaje y cierre de huecos pequeños

## 1. Anticipación cierra el último bypass del Vocero — `Funciones_Slide/Productividad/Anticipacion.py`
`iniciar_anticipacion` era la última voz proactiva que no pasaba por el Vocero (presupuesto global +
silencio en reunión/gaming/ausente). Se envolvió su callback en `Vocero.emitir`. Con esto, TODA la voz
no solicitada de AIDEN queda coordinada por un solo punto — cierre de la "coherencia" que se venía
construyendo desde la Presencia Continua.

## 2. Apertura rica — `Nucleo_Slide/Compania.py::apertura_rica()`
Reemplaza el saludo simple al abrir la app: en UNA sola frase natural (redactada por el LLM) teje
memoria episódica + lo notable que pasó mientras no estabas (hilo de conciencia) + tu momento
(reflexión) + enganche con una meta activa. Resuelve la queja "las funciones no se sienten al solo
abrir la app". Reemplazó `saludo_de_reanudacion` en ambos `Main`.

## 3. Sube un punto la presencia ambiental — tuning
Ajuste de diales tras usar la app un rato: Vocero `MAX_POR_HORA` 5→8 y `GAP` 90→60s; Conciencia
piensa más seguido (3→2min, máx 12→8min, tope 10→12/h) y su prompt cambia de "por defecto NADA" a
"sé PRESENTE, aporta cuando puedas sumar"; Co-ingeniero ayuda antes (atasco 12→8min); Preparación
más seguido (cooldown 3h→1.5h). Todo sigue coordinado por el Vocero.

## 4. AIDEN aprende de tus correcciones — `Nucleo_Slide/Aprendizaje.py`
Cuando Marco corrige algo ("no, prefiero X", "deja de Y", "háblame de tú") AIDEN extrae una REGLA
duradera con el LLM y la inyecta en su prompt PARA SIEMPRE (`preferencias.json`). Diseño pasivo: cero
hilos nuevos, se dispara solo tras un turno que *parece* corrección (heurística barata), extracción en
hilo aparte (cero latencia). Dedup + tope 30 preferencias.

### Para la wiki
- Página de entidad **`Aprendizaje.py`**; enlazar a *Perfil_Marco* (aprender QUIÉN es, distinto de
  aprender CÓMO comportarse) y a *Vocero*.
- Página de concepto: **"aprender de correcciones, no solo de observación"**.

---

# PARTE B — Finanzas automáticas (Nequi/Nu)

## 5. Rastreo de gastos vía Belvo — `Funciones_Slide/Info/Finanzas_Gastos.py`, tool `mis_gastos` (#51)
Primer intento: leer transacciones reales de Nequi/Nu por la API de Belvo (agregador B2B). Suma
`OUTFLOW` del periodo, agrupa por categoría. Requiere credenciales en `secretos.py`.

## 6. Captura AUTOMÁTICA de gastos desde notificaciones — pivote clave
Marco aclaró una restricción dura: **"bajo ningún modo tengo yo que darte las finanzas, sería lo
mismo que escribir en un Excel"** — el registro por voz quedó descartado. `iniciar_vigilante_gastos`
lee las notificaciones de Windows (mismo mecanismo que Bitácora: `wpndatabase.db`) y detecta las de
gasto de Nequi/Nu ("Pagaste $X en Y"), parsea monto+comercio, filtra ingresos, y las guarda solas en
`gastos.json`. Requiere que "Vincular al teléfono" (Phone Link) esté reenviando notificaciones al PC.
`mis_gastos` suma el periodo local (+Belvo si está configurado).

### Para la wiki
- Página de entidad **`Finanzas_Gastos.py`**; enlazar a *Bitácora* (mismo mecanismo de lectura de
  notificaciones) y a la página de decisión **"captura pasiva, nunca registro manual"** (la regla
  dura de Marco sobre finanzas).

---

# PARTE C — Auditoría de arquitectura y refactor estructural

Marco pidió una auditoría "100% seria, como si fuera una IA autónoma real" y luego una mejora grande
de estructura/funcionamiento. Esto destapó y arregló varios errores REALES (no cosméticos):

## 7. Enrutador de voz compartido + centinela revivido — `Nucleo_Slide/Peticiones.py`
- **`iniciar_centinela` nunca se llamaba** — el detector de `SyntaxError` en el código de Marco no
  existía en la práctica pese a estar programado. Revivido: arranca en ambos `Main`, ignora
  venv/`__pycache__`, avisa por el Vocero (antes escuchaba desde un hilo de fondo y peleaba por el
  micrófono con la palabra clave).
- **"abre X" secuestraba frases** ("¿cuándo abre el mercado?" intentaba abrir la app "el mercado").
  Ahora solo dispara si la frase EMPIEZA con "abre" y es corta.
- **Tildes rompían atajos**: Whisper transcribe con tilde ("escríbele", "ocúltate") y los atajos
  comparaban sin tilde — nunca coincidían. Normalizado en todo el enrutador.
- **~125 líneas duplicadas** entre `Main.py` y `Main_AlwaysOn.py` (la fábrica del "lo arreglé en uno
  y olvidé el otro" — pasó literalmente con "descansa"). Unificado en `Peticiones.py`, con
  `decidir_atajo()` como función PURA (sin efectos, testeable) e imports perezosos.
- **Barge-in guardaba `content=null`** sin `tool_calls`, que puede romper la siguiente llamada al API.

### Para la wiki
- Página de entidad **`Peticiones.py`** — es EL punto de entrada de voz/texto de todo AIDEN desde
  aquí en adelante; casi todo lo de las Partes D y E vive como rutas dentro de `decidir_atajo()`.
- Página de decisión: **"un solo enrutador compartido, no dos Main duplicados"**.

## 8. Conversación persistente + murmullo de trabajo + "¿estado?"
- **Conversación continua**: la memoria del diálogo se persiste (`conversacion.json`); si AIDEN se
  reinicia a media charla retoma el hilo (solo si es reciente, <6h).
- **Murmullo de trabajo**: antes de una herramienta LENTA (buscar en internet, experto, visión...),
  suelta un "un momento, señor" variado — mata el silencio muerto. Las tools instantáneas no lo llevan.
- **"¿Estado?"**: atajo sin LLM estilo Iron Man — reporte instantáneo (sistemas + CPU/RAM/GPU + foco
  + metas activas).

## 9. Eficiencia integral — oído, modelos, caché, tokens
- **Oído**: Whisper sube de `small` a `large-v3-turbo` (el oído principal era PEOR que el del
  wake-word, que ya usaba `medium`). `pause_threshold` 2s→1.5s.
- **Modelos por tarea**: `MODELO_LIGERO` (`gemini-2.5-flash-lite`) para la maquinaria interna que
  Marco nunca oye (Perfil, Reflexión, Aprendizaje, sub-preguntas de Investigación) — fracción del
  costo, sin riesgo de malformación (no usan tools). Lo que Marco OYE sigue en `flash`.
- **Prompt cache-friendly**: `_instrucciones_completas` reordenado — bloques ESTABLES primero
  (instrucciones, memoria, perfil, preferencias, reflexión), VOLÁTILES al final (fecha/hora,
  contexto, episodios, sintonía). Antes la fecha iba primera y rompía el caché implícito de Gemini
  de TODO lo que seguía en cada turno.
- **Dieta de tokens**: resultados de herramientas viejos truncados a 300 chars en el historial.

### Para la wiki
- Página de concepto: **"modelos por tarea (flash para lo que se oye, lite para lo interno, pro para
  lo difícil)"**; enlazar a *escalado automático* (de la ingesta anterior).
- Página de decisión: **"orden estable→volátil para el caché de prompt"**.

---

# PARTE D — Dinámicas grandes de Jarvis

## 10. Protocolos personalizados (el "Mark VII" de Marco) + Modo Taller
- **`crear_protocolo`** (#52): "crea un protocolo modo estudio: cierra YouTube, abre Notion y pon
  lo-fi" → AIDEN lo APRENDE para siempre (`protocolos.json`). Desde entonces decir "modo estudio"
  dispara toda la secuencia (el bucle multi-tool del cerebro la orquesta). Actualizar/eliminar/
  listar; los protocolos de Marco mandan sobre los de fábrica (cine/noche/concentración/normal).
- **`modo_taller`** (#53): "acompáñame" → AIDEN mira la pantalla cada 90s durante la sesión (45min
  default, máx 3h) y comenta SOLO cuando suma, vía Vocero. El hilo solo existe durante la sesión
  pedida (no es un vigilante permanente).

### Para la wiki
- Página de entidad **`Protocolos.py`** y **`Taller.py`**; enlazar a *Vocero* y a la dinámica de
  "co-ingeniero" (ambas son variantes de "AIDEN presente en el trabajo, sin que se lo pidan a cada rato").

## 11. Seis mejoras grandes + dos pequeñas, en una tanda
- **Paralelo**: herramientas de SOLO LECTURA (clima, noticias, acciones...) se ejecutan EN PARALELO
  cuando el modelo pide varias a la vez.
- **Self-healing**: si una herramienta falla, Flash ve el error y se corrige solo (otros argumentos,
  otra herramienta) antes de rendirse; solo escala a Pro tras DOS fallos seguidos.
- **Recados condicionales** — `programar_orden` (#54): "en 20 min dime que saque la pizza", "cuando
  abra Chrome recuérdame X". Persisten, sobreviven reinicios, prioridad alta al disparar.
- **Arranque paralelo**: Whisper turbo carga en un hilo mientras avanza el login facial/Kokoro.
- **RAG automático**: si las palabras clave no cruzan nada, el prompt recibe recuerdos por
  SIGNIFICADO (la función `recordar_relevantes_semantico` existía desde la Memoria RAG original y
  nunca se había conectado al flujo normal de conversación).
- **"Por cierto"**: lo que el Vocero calló (presupuesto agotado, reunión, ausencia) se entrega con
  naturalidad en la siguiente charla, una sola vez, si sigue fresco (<30 min).
- *Pequeñas*: frases de escalado variadas; "¿cómo estás?" con salud interna (uptime, hilos vivos).

### Para la wiki
- Página de concepto: **"nada se le pierde a Jarvis"** — enlaza *por cierto*, *recados
  condicionales* y *RAG automático* como las tres formas en que AIDEN no deja caer información.

## 12. Una sola respiración + nunca se cae
- **Una sola respiración**: "Aiden, ¿qué hora es?" ahora responde de una — antes el comando dicho
  CON la palabra clave se descartaba (el bucle de reposo ignoraba el texto capturado por el VAD) y
  tocaba repetirlo. `extraer_comando_tras_wake` (puro, en `Peticiones.py`) limpia la wake word.
- **Nunca se cae**: sin internet, `proceso_de_ia` lanzaba una excepción sin capturar y el hilo de
  conversación moría en silencio. Ahora: reintenta, y si de verdad no hay enlace, dice honestamente
  "perdí el enlace... sigo con los controles locales" (los atajos sin LLM — música, apps, protocolos,
  recados — siguen vivos offline). Red de seguridad adicional en `Peticiones.py`.

## 13. Percepción total + voz viva
- **Percepción total** — `Nucleo_Slide/Percepcion.py`: los sentidos del PC (ventana activa, apps
  abiertas, portapapeles, energía) en un módulo compartido con caché de 5s, inyectado en el prompt
  **en cada turno**. Antes solo la Conciencia veía la "foto" cada ~12 min; el cerebro de conversación
  estaba medio ciego. Con esto, "cierra eso" / "¿qué opinas de esto?" se resuelven solos (deixis por
  percepción, sin herramientas). La Conciencia ahora reusa estos mismos sentidos.
- **Voz viva**: de noche (22:00-7:00) Kokoro habla un punto más calmado (velocidad 0.95, volumen 0.8).

### Para la wiki
- Página de entidad **`Percepcion.py`**; enlazar a *Estado_Del_Mundo* (comparten el rol de "lo que
  AIDEN sabe ahora", pero Percepción es sensorial/inmediata y Estado_Del_Mundo es memoria/hilo).
- Página de concepto: **"resolver deixis por percepción, no por pregunta"**.

## 14. Manos libres turbo + mini consciencia + Overlay 2.0 + ícono nuevo
- **Manos libres turbo**: en sesión de manos libres, el cerebro entra en `modo_rapido` — salta el RAG
  semántico y la reflexión del prompt, exige respuestas ultra-breves. Arranca a hablar antes.
- **Mini consciencia** — `Nucleo_Slide/Monologo.py`: un PENSAMIENTO interno privado que AIDEN rumia
  cada ~2.5 min sobre lo que percibe, con el modelo ligero, y que NUNCA dice — se ve en el overlay y
  le da continuidad al cerebro. Ejemplo real generado: *"Debo prepararle un té antes de que se pierda
  en esa ventana."*
- **Overlay 2.0**: primera vuelta de rediseño (superada por las Partes G.23-25 más abajo).
- Tool #55.

### Para la wiki
- Página de entidad **`Monologo.py`**; enlazar a *Percepcion* (de dónde saca material para pensar) y
  a *Overlay* (dónde se hace visible).
- Página de concepto: **"un pensamiento que nunca se dice — la diferencia con la Conciencia (que sí actúa)"**.

## 15. Subtítulos + día real + retomemos + notis priorizadas + música contextual + mayordomo de archivos
- **Subtítulos en vivo** (`index.html`): un caption grande muestra "lo que le oí" y "lo que dice
  AIDEN". Estado visual "PROCESANDO" llena el vacío entre que terminas de hablar y AIDEN responde.
- **Día real** — `Funciones_Slide/Info/Agenda.py`: correo (IMAP) + calendario (ICS), config en
  `secretos.py`. El briefing matutino ahora incluye clases/entregas + correos sin leer. Tools
  `revisar_correo`, `agenda_hoy`.
- **Retomemos** — `Funciones_Slide/Sistema/Sesion.py`: reabre el espacio de trabajo (apps que tenías
  abiertas), autoguardado cada 5 min. Tool `restaurar_sesion`.
- **Notificaciones priorizadas** — `Bitacora.resumen_priorizado`: al volver, en vez de "llegaron 23
  notificaciones", AIDEN lee y dice SOLO lo que importa (modelo ligero).
- **Música contextual**: "pon lo mío" elige según en qué estés (gaming/estudio/noche), sin LLM.
- **Mayordomo de archivos** — `Mayordomo_Archivos.py`: 1 vez al día ordena capturas del escritorio e
  instaladores viejos de Descargas a subcarpetas (mueve, nunca borra).

### Para la wiki
- Página de entidad **`Agenda.py`**, **`Sesion.py`**, **`Mayordomo_Archivos.py`**.
- Página de decisión: **"conectar a la vida real de estudiante (correo/calendario), no solo al PC"**.

## 16. MODO AGENTE — `Nucleo_Slide/Agente.py`
El salto de responder-comandos a CUMPLIR-metas. "Encárgate de esto, señor" → bucle autónomo de hasta
14 acciones encadenadas: planifica, ejecuta cada paso con TODO el arsenal (herramientas + la llave
maestra de PowerShell, ver Parte E), verifica el resultado, se auto-corrige si falla, y NARRA el
avance en voz mientras trabaja ("Considérelo hecho, señor... primero reviso..."). Cierra con "MISIÓN
CUMPLIDA: <resumen>". NO es una tool del LLM (evita auto-invocarse) — lo dispara Marco por voz
("encárgate de", "ocúpate de", "hazte cargo de").

### Para la wiki
- Página de entidad **`Agente.py`**; página de concepto/hito: **"de responder comandos a cumplir
  metas — el 'considérelo hecho' de Jarvis"**. Es probablemente la página más importante de enlazar
  desde el índice general, junto con la llave maestra de la Parte E.

---

# PARTE E — Control total de la PC (la pregunta de "¿puedes hacer TODO lo que hago yo?")

Marco preguntó explícitamente si AIDEN podía hacer por voz, casi instantáneo, cualquier acción que él
hace con mouse y teclado. La respuesta honesta fue "no del todo" en dos momentos distintos, y ambas
veces se cerró el hueco de verdad (con pruebas reales, no solo el código).

## 17. La llave maestra + dos carriles rápidos — `Funciones_Slide/Sistema/Control_Total.py`, `Nucleo_Slide/Control_Directo.py`
- **`ejecutar_en_pc`** (tool maestra): AIDEN compone y ejecuta PowerShell → puede hacer literalmente
  cualquier cosa que Windows permita, sin necesidad de una tool por cada acción. Red de seguridad
  que bloquea SOLO lo catastrófico/irreversible (formatear, borrar el sistema, `diskpart`,
  `bcdedit`...); todo lo demás se ejecuta. Prohibida en modo autónomo (solo cuando Marco la pide).
- **Acciones instantáneas** (cero LLM): bloquear, suspender, apagar/cancelar, reiniciar, mostrar
  escritorio, vaciar papelera, abrir explorador, captura, silenciar, volumen, brillo.
- **Modo control**: "modo control" abre el mic como manos libres y manda CADA orden a un carril
  rápido — una llamada al modelo LIGERO, SIN el esquema de las 65 herramientas ni el contexto pesado,
  que traduce voz→comando y ejecuta. Mucho más rápido que el cerebro completo.

## 18. Órdenes en cadena + más fluido
"Abre Spotify, sube el volumen y minimiza todo" se parte en 3 órdenes y se ejecutan en orden, de una
— solo si TODAS las partes son atajos rápidos (si alguna es charla, la frase entera va al cerebro).
Más acciones instantáneas: brillo, calculadora, bloc de notas, administrador de tareas, configuración.

## 19-20. Admin mode — Discord, webs, y 44 funciones de Windows por voz
- **Discord** (UI automation, como WhatsApp): abre, salta al DM con Ctrl+K, envía por portapapeles.
- **`abrir_web`**: YouTube (inicio o búsqueda), Gmail, sitios conocidos, o cualquier URL.
- **`Funciones_Slide/Sistema/Windows_Admin.py`** — 24 funciones (primera tanda, `53d5ec6`): red
  (arregla el internet, clave wifi, mi IP), rendimiento/energía (alto rendimiento, mantener
  despierta, hibernar), mantenimiento (limpia temporales, reinicia explorador, espacio en disco, top
  procesos, matar proceso), apariencia (modo oscuro/claro, archivos ocultos), info (specs, batería,
  uptime), y volumen/brillo exactos.
- **+20 funciones más** (segunda tanda, `ecbedf2`, la MISMA fecha — sesión aparte): escritorios
  virtuales (siguiente/anterior/nuevo/cerrar vía `keybd_event`, fiable sin foco), acomodar ventana
  izq/der, maximizar, captura de región (Win+Shift+S); diagnóstico de red (prueba de internet con
  ping→latencia/pérdida, IP pública, versión de Windows, temperatura de GPU); "cuáles son mis
  archivos más grandes" (ayuda a liberar disco — encontró un `.ucas` de 9GB en la prueba real);
  *launchers* (panel de control, administrador de dispositivos, servicios, sonido/red,
  almacenamiento); **portapapeles inteligente** (lee/traduce/resume lo que copiaste, único subgrupo
  que sí usa LLM ligero).

### Para la wiki
- Página de entidad **`Windows_Admin.py`** (44 funciones en total entre las dos tandas) y
  **`Control_Total.py`**/**`Control_Directo.py`**.
- Página de decisión: **"llave maestra + reflejos instantáneos, no una tool por cada acción"** — el
  patrón arquitectónico que evitó explotar el conteo de tools del LLM mientras la capacidad crecía.

## 21. Clic y arrastre guiados por VISIÓN — `Funciones_Slide/Sistema/Control_Pantalla.py`
El hueco que quedaba: el clic solo funcionaba con elementos que Windows sabe NOMBRAR (UI Automation)
— nada en juegos, apps de lienzo, iconos sin texto. Ahora `_clic_en`/`_arrastrar` prueban PRIMERO por
nombre (rápido) y, si no lo encuentran, caen a un respaldo por VISIÓN que mira la pantalla y ubica el
objetivo por su descripción.

**Hallazgo técnico importante durante las pruebas** (vale la pena una página de concepto propia):
pedirle a Gemini "dame las coordenadas X,Y" en texto libre es **poco fiable** — falla incluso con
objetivos obvios (probado en vivo). El formato que SÍ funciona es el **`box_2d`** que Gemini tiene
oficialmente documentado/entrenado para detección espacial: `{"box_2d": [ymin,xmin,ymax,xmax],
"label": "..."}` normalizado 0-1000. Con ese formato localizó con precisión real caras de personajes
en una captura de pantalla real, y rechazó correctamente un objetivo inventado (cero alucinación).

Además, en `Peticiones.py`: ~15 rutas de voz nuevas CERO-LLM para lo más común (clic, arrastrar,
cerrar pestaña, seleccionar todo, scroll, ordenar ventanas, enfocar app, minimizar/maximizar/cerrar/
cambiar ventana, atajos de teclado, escribir texto) — bypasan el cerebro completo. Ninguna es una tool
nueva del LLM: son entradas de voz hacia funciones que ya existían.

### Para la wiki
- Página de concepto: **"box_2d — el formato correcto para pedirle coordenadas a Gemini"** (nota
  técnica reutilizable para cualquier futura función de visión con ubicación espacial).
- Página de decisión: **"nombre primero, visión como respaldo universal"** — mismo patrón de
  "reflejo rápido + fallback capaz" que la llave maestra.

---

# PARTE F — Estudiante

## 22. Redactor de documentos + Solucionador visual
- **`redactar_documento`** — `Funciones_Slide/Info/Redactor.py`: "escríbeme un ensayo sobre X" →
  AIDEN escribe el documento COMPLETO con el cerebro experto (Pro), lo guarda como `.docx` (con
  título, secciones y párrafos formateados, vía `python-docx`) en `Documentos\AIDEN`, y lo abre.
  Ensayo/informe/carta/correo/resumen/discurso/reseña/artículo. Probado generando un ensayo real de
  977 palabras.
- **`resolver_visual`** — `Funciones_Slide/Info/Estudio.py`: "resuelve esto" → captura la pantalla (o
  cámara) y la manda al cerebro EXPERTO con visión para resolver PASO A PASO (mates, física, código).
  Distinta de `analizar_pantalla` (que solo describe).

### Para la wiki
- Página de entidad **`Redactor.py`**, **`Estudio.py`**; enlazar a *consultar_experto* (mismo
  cerebro Pro) y a *Vision.py* (misma infraestructura de captura+visión).
- Página de concepto: **"funciones grandes y útiles > comandos de sistema pequeños"** — la corrección
  de rumbo de Marco tras la primera tanda de funciones de Windows ("nada fue útil, mete cosas útiles
  y grandes").

---

# PARTE G — El overlay: tres rediseños visuales en una semana

## 23. Rediseño total — HUD con reactor animado
Primera pasada (a pedido explícito de "mejora SOLO lo visual, sé creativo"). El overlay pasó de ser
una caja de texto plana a un HUD dibujado con `QPainter` (no solo CSS/HTML): núcleo que respira (glow
radial), anillo segmentado que gira, barrido (scanline) sutil, brackets de esquina tácticos, reloj
vivo, color por MOMENTO real de Marco (normal/reunión/taller/misión/gaming/ausente), pensamiento
interno con cursor parpadeante, sombra flotante.

## 24. Segunda pasada — más sencillo y clean
Marco pidió simplificar: "más sencillo y clean pero con cosas importantes". Se fue el anillo girando,
el barrido, los brackets, el reloj vivo, las pastillas de color sólidas. Se quedó UN solo elemento
animado: un latido suave. Borde neutro casi invisible. Tipografía con más aire. Recortado a 1 meta +
1 evento reciente (lo esencial).

## 25. Refinamiento (easing + filo de cristal) → paleta monocroma final
- **Easing de color**: el acento ya NO salta de golpe al cambiar de estado — se desliza suave (mismo
  patrón `actual += (objetivo-actual)*factor` que ya usaba el motor de la esfera principal).
- **Filo de cristal**: un hilo de luz muy tenue bajo el borde superior (profundidad sin ruido).
- **Paleta monocroma final** (a pedido de Marco: "más serio, gris tonalizado, blanco o plateado"): se
  fue la paleta de 6 matices; ahora TODO es gris/plata neutro (R=G=B) y el momento de Marco se lee
  por el BRILLO, no por el color — `ausente(96) < gaming(128) < reunión(146) < normal(198) <
  taller(224) < misión(255)`. El núcleo del latido tiene un toque metálico (radial gradient con
  brillo blanco descentrado — una esfera de plata pulida). Se creó además `overlay_preview.html`,
  una réplica fiel en HTML/CSS puro (sin Python) para previsualizar el diseño en el navegador con un
  selector de los 6 estados, publicada como Artifact.

### Para la wiki
- Página de entidad **`Overlay.py`** (con nota de que pasó por 3 rediseños — vale la pena documentar
  la EVOLUCIÓN, no solo el estado final, como caso de estudio de iteración de diseño con el usuario).
- Página de entidad **`overlay_preview.html`** — la réplica HTML de previsualización.
- Página de concepto: **"color por brillo, no por matiz — jerarquía monocroma"**.

---

## Resumen para el índice del segundo cerebro

Este periodo (25 commits, 1-25 de julio de 2026) llevó a AIDEN de "agente Jarvis con dinámicas
Tony-Jarvis" a un sistema con **arquitectura de voz unificada** (un solo enrutador, `Peticiones.py`),
**percepción constante** (sabe qué hay en tu pantalla en cada turno, sin preguntarlo), **control total
de la PC** (llave maestra + reflejos instantáneos + clic/arrastre guiados por visión — prácticamente
cualquier acción de mouse/teclado, con matices honestos sobre latencia y objetos muy pequeños), un
**modo agente** que cumple metas complejas solo, y una identidad visual que maduró de "reactor
completo" a una paleta monocroma seria y deliberada. Se corrigieron 7 errores estructurales reales
(centinela muerto, atajos rotos por tildes, duplicación entre Mains, barge-in que podía romper el
API). 65 herramientas al cierre. Patrón arquitectónico repetido y ya establecido: **llave maestra +
reflejos rápidos**, para que la capacidad crezca sin que el conteo de tools explote.

Pendiente de probar EN VIVO (constante en todas las tandas): aunque cada función se probó con datos
reales o mecanismos reales donde fue posible (PowerShell real, visión real, clics reales en apps
desechables), la integración completa de TODO junto, en una sesión de uso normal y prolongada, sigue
siendo la prueba que falta.

Crear página índice **"AIDEN — Julio 2026: control total y percepción"** que enlace este documento
completo con el índice general de "AIDEN como agente Jarvis" de la ingesta anterior.
