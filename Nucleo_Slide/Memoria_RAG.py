# MEMORIA RAG: búsqueda SEMÁNTICA (por significado) sobre todo el historial de conversaciones.
#
# La memoria episódica busca por PALABRAS CLAVE (si no comparten palabras, no encuentra). Esto busca
# por SIGNIFICADO: preguntar "cómo va mi trabajo de la universidad" encuentra lo de "la tesis" aunque
# no compartan ninguna palabra. Usa embeddings (sentence-transformers, modelo multilingüe) en CPU para
# no competir VRAM con Whisper/Kokoro. Indexa en segundo plano y re-indexa cada cierto tiempo.
#
# Casi-hoja: numpy + Memoria_Episodica (hoja); el modelo se carga PEREZOSO. Si algo falla, degrada a
# "no disponible" sin romper nada.

import threading
import time

import numpy as np

from Nucleo_Slide.Memoria_Episodica import _cargar as _cargar_episodios

_MODELO_NOMBRE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_UMBRAL = 0.30          # similitud mínima para considerar un episodio "relacionado"
_REINDEX_SEG = 1800     # re-indexa cada 30 min (recoge conversaciones nuevas)

_lock = threading.RLock()
_modelo = None
_emb = None             # matriz (n, d) de embeddings normalizados
_eps = []               # episodios correspondientes a cada fila de _emb


def _cargar_modelo():
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer
        _modelo = SentenceTransformer(_MODELO_NOMBRE, device="cpu")
    return _modelo


def _texto_ep(e):
    return (str(e.get("usuario", "")) + " . " + str(e.get("aiden", ""))).strip()


def reindexar():
    """Re-calcula los embeddings de todos los episodios. Pesado; corre en segundo plano."""
    global _emb, _eps
    eps = _cargar_episodios() or []
    if not eps:
        with _lock:
            _emb, _eps = None, []
        return
    m = _cargar_modelo()
    vecs = m.encode([_texto_ep(e) for e in eps], normalize_embeddings=True,
                    convert_to_numpy=True, batch_size=32)
    with _lock:
        _emb, _eps = vecs, eps


def buscar(consulta, n=4):
    """Top-n episodios más parecidos por SIGNIFICADO a 'consulta'. Lista de (episodio, similitud)."""
    consulta = str(consulta or "").strip()
    if not consulta:
        return []
    with _lock:
        emb, eps = _emb, list(_eps)
    if emb is None or not eps:
        return []
    try:
        q = _cargar_modelo().encode([consulta], normalize_embeddings=True, convert_to_numpy=True)[0]
        sims = emb @ q                      # coseno (todo está normalizado)
        idx = np.argsort(-sims)[:n]
        return [(eps[i], float(sims[i])) for i in idx if sims[i] >= _UMBRAL]
    except Exception:
        return []


def recordar_a_fondo(consulta):
    """HERRAMIENTA: recuerda por SIGNIFICADO (no por palabras). 'busca a fondo qué hablamos de X'."""
    res = buscar(consulta, 4)
    if not res:
        with _lock:
            listo = _emb is not None
        if not listo:
            return "Aún estoy organizando mi memoria profunda, señor; inténtelo en un momento."
        return "No encuentro nada relacionado con eso en nuestras conversaciones, señor."
    lineas = ["Esto es lo que recuerdo relacionado, señor:"]
    for e, _s in res:
        lineas.append(f'- [{e.get("fecha","")}] Marco: "{e.get("usuario","")}" '
                      f'-> tú: "{str(e.get("aiden",""))[:80]}"')
    return "\n".join(lineas)


def recordar_relevantes_semantico(consulta, n=3):
    """Para inyectar en el prompt: episodios relacionados por significado, o "" si nada/no listo."""
    res = buscar(consulta, n)
    if not res:
        return ""
    lineas = ["CONVERSACIONES PASADAS RELACIONADAS (por significado; menciónalo solo si viene al caso):"]
    for e, _s in res:
        lineas.append(f'- [{e.get("fecha","")} {e.get("hora","")}] Marco: "{e.get("usuario","")}" '
                      f'-> tú: "{str(e.get("aiden",""))[:80]}"')
    return "\n".join(lineas)


def iniciar_rag():
    """Carga el modelo e indexa en segundo plano; re-indexa periódicamente."""
    def _bucle():
        time.sleep(45)                      # deja pasar el arranque pesado (Whisper/Kokoro)
        try:
            reindexar()
            print("[rag] memoria semántica lista.")
        except Exception as e:
            print(f"[rag] no se pudo indexar: {e}")
        while True:
            time.sleep(_REINDEX_SEG)
            try:
                reindexar()
            except Exception:
                pass

    threading.Thread(target=_bucle, daemon=True).start()


def recordar(consulta="", modo="auto", dias=None):
    """HERRAMIENTA: busca en las conversaciones pasadas con Marco.
      modo='auto'      -> intenta por SIGNIFICADO y, si no saca nada, reintenta por palabras.
      modo='significado' -> solo semántica (encuentra "la tesis" al preguntar por "la universidad").
      modo='palabras'  -> solo literal (útil con un término exacto, o para traer lo más reciente).
      dias -> limita a los últimos N días (solo aplica al modo por palabras).

    Antes esto eran dos herramientas, 'recordar_conversacion' y 'recordar_a_fondo', con un 19% de
    vocabulario común en sus descripciones: ambas decían "busca en el historial de conversaciones".
    Marco nunca va a pedir "búscalo por embeddings" — pide que te acuerdes de algo. CÓMO se busca es
    decisión de AIDEN, no una herramienta aparte que el modelo tenga que adivinar."""
    from Nucleo_Slide.Memoria_Episodica import recordar_conversacion

    m = str(modo or "auto").strip().lower()
    consulta = str(consulta or "").strip()

    # Sin texto no hay nada semántico que hacer: se pide "lo último", que es literal.
    if not consulta or m.startswith("palabra") or m.startswith("literal"):
        return recordar_conversacion(consulta, dias)

    if m.startswith("signific") or m.startswith("fondo") or m.startswith("semant"):
        return recordar_a_fondo(consulta)

    # auto: primero por significado (más potente); si no encuentra, por palabras.
    profunda = recordar_a_fondo(consulta)
    if not profunda.startswith("No encuentro") and not profunda.startswith("Aún estoy"):
        return profunda
    literal = recordar_conversacion(consulta, dias)
    if literal.startswith("No encontré") or literal.startswith("Todavía no"):
        return profunda        # ninguna encontró: se devuelve el mensaje más informativo
    return literal
