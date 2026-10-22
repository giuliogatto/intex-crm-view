"""Esegue l'OCR sulle bolle di esempio (golden set) e stampa i campi chiave.

Uso (dalla cartella backend, con OPENAI_APIKEY nell'ambiente o in backend/.env):
    python ../scripts/ocr_bolle_golden.py [cartella_immagini]
Modello/dettaglio: variabili OPENAI_OCR_MODEL / OPENAI_OCR_DETAIL.
"""

import glob
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from bolla_ocr import extract_bolla, sniff_image_mime  # noqa: E402

RIGA_KEYS = (
    "codice_articolo_cliente",
    "descrizione_articolo",
    "tessuto",
    "modello",
    "colore",
    "variante",
    "commessa",
    "composizione_testo",
    "quantita_capi",
    "quantita_kg",
    "fasi_testo",
    "codice_ciclo_manoscritto",
)

_IMAGE_GLOBS = ("*.jp*g", "*.png", "*.webp", "*.pdf", "*.PDF")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "documentation", "esempi-bolle"
    )
    if os.path.isfile(target):
        paths = [target]
    else:
        paths = []
        for pattern in _IMAGE_GLOBS:
            paths.extend(glob.glob(os.path.join(target, pattern)))
        paths = sorted(set(paths))
    for path in paths:
        data = open(path, "rb").read()
        started = time.time()
        try:
            result = extract_bolla(data, sniff_image_mime(data))
        except Exception as e:
            print(f"===== {os.path.basename(path)} ERROR {e}")
            continue
        o = result["ocr"]
        print(f"===== {os.path.basename(path)} {time.time() - started:.1f}s {result['model']}")
        print(f" mittente: {o['mittente_ragione_sociale']} | dest: {o['destinatario_ragione_sociale']}")
        print(
            f" bolla: {o['numero_bolla']} {o['data_bolla']} | cod su ddt: {o['codice_cliente_su_ddt']}"
            f" | rif mano: {o['riferimento_interno_manoscritto']}"
        )
        print(f" codici ciclo documento: {o['codice_ciclo_manoscritto']}")
        print(f" annotazioni a mano: {o.get('annotazioni_manoscritte')}")
        if o["warnings"]:
            print(f" avvisi: {o['warnings']}")
        for r in o["righe"]:
            print(f"  riga {r['riga']}", {k: r[k] for k in RIGA_KEYS if r.get(k)})
            # Hint matching: bolle senza fasi/TINTO dipendono da tessuto+descrizione.
            if not r.get("fasi_testo") and not r.get("codice_ciclo_manoscritto"):
                if r.get("descrizione_articolo") or r.get("tessuto"):
                    print(
                        "    ↳ segnale soft (no fasi/T…): usare descrizione/tessuto "
                        "verso ew2_ds_articolo / qualità"
                    )


if __name__ == "__main__":
    main()
