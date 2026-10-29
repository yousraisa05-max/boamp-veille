"""Corrige des labels directement dans le CSV, sans passer par Numbers.

Usage :
    python fix_label.py 0 25-134107 26-74330        # met label = 0 pour ces avis
    python fix_label.py 1 26-12345                  # met label = 1
    python fix_label.py --show transport            # affiche les avis d'un groupe

Par défaut le fichier modifié est data/annotation/a_annoter_2.csv.
"""
import csv
import sys
from pathlib import Path

PATH = Path("data/annotation/a_annoter_2.csv")


def read() -> tuple[list[dict], list[str]]:
    with open(PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    rows, cols = read()

    if args[0] == "--show":
        group = args[1] if len(args) > 1 else "transport"
        for r in rows:
            if r["groupe"] == group:
                print(f"{r['idweb']:<11}| label={r['label']} | {r['nomacheteur'][:28]:<28} | {r['objet'][:100]}")
        return

    new_label, ids = args[0], set(args[1:])
    if new_label not in {"0", "1"} or not ids:
        print("Usage : python fix_label.py 0|1 idweb [idweb ...]")
        return
    found = set()
    for r in rows:
        if r["idweb"] in ids:
            print(f"{r['idweb']} : {r['label']} -> {new_label}")
            r["label"] = new_label
            found.add(r["idweb"])
    for missing in sorted(ids - found):
        print(f"Introuvable : {missing}")

    with open(PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Fichier mis à jour : {PATH}")


if __name__ == "__main__":
    main()
