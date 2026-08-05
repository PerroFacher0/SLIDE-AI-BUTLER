# ENROLAR LA VOZ DE MARCO. Esto lo corre ÉL, con su micrófono. Yo no puedo hacerlo por él, y por
# eso la verificación nace apagada: sin este paso no hay con qué comparar.
#
# Además de guardar la huella, MIDE. Al final dice cuánto se parece Marco a sí mismo entre frases
# distintas, que es el único dato que permite saber si el umbral por defecto (0.70) le sirve o le
# va a dejar fuera de su propio asistente. Un umbral sin medir es una adivinanza.
#
#   python Pruebas/enrolar_voz.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRASES = [
    "AIDEN, abre el navegador y busca el clima de hoy",
    "Envía un mensaje a mi hermano diciendo que llego tarde",
    "Ejecuta el comando para listar los archivos de esta carpeta",
    "Apaga el computador en diez minutos, por favor",
    "Aiden, ¿qué tengo pendiente para mañana en la mañana?",
]


def main():
    try:
        import speech_recognition as sr
    except Exception:
        print("Falta speech_recognition."); return 1
    try:
        import speechbrain  # noqa: F401
    except Exception:
        print("Falta speechbrain. Instálalo con:\n    pip install speechbrain")
        return 1

    from Nucleo_Slide import Verificacion_Voz as V

    print("=" * 70)
    print("ENROLAMIENTO DE VOZ")
    print("Vas a leer 5 frases. Habla como le hablas a AIDEN normalmente: misma")
    print("distancia al micrófono, mismo tono. Si lo haces impostando la voz, el")
    print("umbral quedará calibrado para una voz que nunca vuelves a usar.")
    print("=" * 70)

    r = sr.Recognizer()
    embeddings, crudos = [], []
    with sr.Microphone(sample_rate=16000) as fuente:
        print("\nCalibrando ruido de fondo, no hables...")
        r.adjust_for_ambient_noise(fuente, duration=1.0)
        for i, frase in enumerate(FRASES, 1):
            input(f"\n[{i}/5] Pulsa ENTER y di:\n      «{frase}»\n> ")
            print("      escuchando...")
            try:
                audio = r.listen(fuente, phrase_time_limit=8, timeout=10)
            except Exception as e:
                print(f"      no te oí ({e}). Repetimos esta.")
                continue
            crudo = audio.get_raw_data(convert_rate=16000, convert_width=2)
            emb = V.embedding_de(crudo)
            if emb is None:
                print("      demasiado corto o no se pudo procesar. Repetimos esta.")
                continue
            embeddings.append(emb)
            crudos.append(crudo)
            print(f"      guardada ({len(crudo) / 32000:.1f} s)")

    if len(embeddings) < 3:
        print("\nCon menos de 3 frases la huella no es fiable. No guardo nada.")
        return 1

    ruta = V.guardar_huella(embeddings)
    print(f"\nHuella guardada en: {ruta}")

    # LA PARTE QUE DE VERDAD IMPORTA: ¿cuánto se parece Marco a sí mismo?
    print("\n" + "=" * 70)
    print("CALIBRACIÓN — cada frase contra la huella de las demás")
    import numpy as np
    sims = []
    for i in range(len(embeddings)):
        otras = np.mean(np.stack([e for j, e in enumerate(embeddings) if j != i]), axis=0)
        s = V._similitud(embeddings[i], otras)
        sims.append(s)
        print(f"   frase {i + 1}: {s:.3f}")
    peor, medio = min(sims), sum(sims) / len(sims)
    print(f"\n   peor caso: {peor:.3f}   |   medio: {medio:.3f}")
    print(f"   umbral actual OK={V.UMBRAL_OK}  DUDA={V.UMBRAL_DUDA}")

    if peor < V.UMBRAL_DUDA:
        print("\n   ⚠  Tu peor frase queda por DEBAJO del umbral de duda: con esta")
        print("      configuración AIDEN te rechazaría a TI. Baja UMBRAL_OK en")
        print("      Nucleo_Slide/Verificacion_Voz.py o repite el enrolamiento en")
        print("      un sitio más silencioso.")
    elif peor < V.UMBRAL_OK:
        print("\n   ⚠  Pasarías, pero a veces por la vía de 'duda' (te pedirá repetir).")
        print(f"      Si molesta, baja UMBRAL_OK a ~{peor - 0.05:.2f}.")
    else:
        print("\n   ✓ Tu peor frase supera el umbral: no deberías tener falsos rechazos.")

    print("\n   OJO: esto mide que te pareces a ti mismo. NO mide que un impostor")
    print("   sea rechazado — para eso hace falta que alguien más grabe frases.")
    print("   Si quieres esa mitad, pide a otra persona que corra este script")
    print("   apuntando a una huella distinta y compara.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
