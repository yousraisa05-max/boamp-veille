"""Affiche le contenu d'un avis collecté, pour voir quels champs exploiter.

Usage :
    python inspect_record.py 25-131462          # un avis précis
    python inspect_record.py 25-131462 4000     # idem, en montrant plus de caractères de `donnees`
"""
import json
import sys
from pathlib import Path

RAW = Path("data/raw/boamp_raw.jsonl")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    idweb = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 2500

    with open(RAW, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("idweb") != idweb:
                continue
            donnees = rec.pop("donnees", None)
            print("=== CHAMPS SIMPLES ===")
            for key in ("nature_libelle", "famille_libelle", "type_avis", "type_marche",
                        "procedure_libelle", "dateparution", "datelimitereponse",
                        "datefindiffusion", "nomacheteur", "code_departement", "titulaire",
                        "annonce_lie", "criteres", "objet"):
                print(f"{key}: {rec.get(key)}")
            print("\n=== DONNEES (début) ===")
            text = donnees if isinstance(donnees, str) else json.dumps(donnees, ensure_ascii=False)
            print(text[:limit])
            print(f"\n[... {len(text)} caractères au total]")
            return
    print(f"Avis {idweb} introuvable dans {RAW}")


if __name__ == "__main__":
    main()
