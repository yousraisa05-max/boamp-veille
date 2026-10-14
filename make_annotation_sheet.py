"""Étape 2 — Prépare la feuille d'annotation (échantillon aléatoire reproductible).

Entrée : data/raw/boamp_raw.jsonl
Sortie : data/annotation/a_annoter.csv  (à ouvrir dans Excel / Numbers)

Tu remplis uniquement la colonne `label` (1 = pertinent, 0 = non pertinent),
en suivant docs/annotation_guide.md.

Usage :
    python make_annotation_sheet.py            # 100 avis
    python make_annotation_sheet.py --n 120
"""
import argparse
import csv
import json
import random
from pathlib import Path

RAW = Path("data/raw/boamp_raw.jsonl")
OUT_DIR = Path("data/annotation")
SEED = 42  # même échantillon à chaque lancement


def as_text(value) -> str:
    """Certains champs sont des listes : on les met à plat."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()

    with open(RAW, encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    random.Random(SEED).shuffle(records)
    sample = records[: args.n]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = [
        "idweb", "label", "nomacheteur", "objet",
        "descripteur_libelle", "type_marche", "dateparution", "url_avis",
    ]
    out_path = OUT_DIR / "a_annoter.csv"
    # utf-8-sig : Excel sur Mac lit bien les accents
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for rec in sample:
            row = {c: as_text(rec.get(c)) for c in cols}
            row["label"] = ""
            writer.writerow(row)

    print(f"{len(sample)} avis écrits dans {out_path.resolve()}")


if __name__ == "__main__":
    main()
