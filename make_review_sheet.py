"""Étape 5 — Feuille de vérification des prédictions du modèle.

Entrée : data/processed/predictions.csv  (produit par predict_all.py)
Sortie : data/annotation/a_relire_2.csv

Trois groupes d'avis (jamais annotés par toi) sont à vérifier :
  - transport  : prédits pertinents ET liés au transport (le cœur de cible, à contrôler un par un)
  - aleatoire  : 25 avis prédits pertinents, tirés au hasard, pour estimer la précision réelle
  - incertain  : les 20 prédictions les plus proches de 50 %, pour améliorer le modèle

La colonne `label` est pré-remplie avec la prédiction du modèle : tu la corriges si tu n'es pas
d'accord. `label_modele` garde la prédiction d'origine pour pouvoir mesurer l'accord ensuite.

Usage :
    python make_review_sheet.py
"""
import csv
import random
from pathlib import Path

PRED = Path("data/processed/predictions.csv")
OUT = Path("data/annotation/a_relire_2.csv")
SEED = 42
N_RANDOM = 25
N_UNSURE = 20


def main() -> None:
    with open(PRED, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    model_rows = [r for r in rows if r["source"] == "modèle"]

    chosen: dict[str, tuple[str, dict]] = {}

    def add(group: str, items: list[dict]) -> None:
        for r in items:
            chosen.setdefault(r["idweb"], (group, r))

    add("transport", [r for r in model_rows if r["label"] == "1" and r["transport"] == "1"])

    rest = [r for r in model_rows if r["label"] == "1" and r["idweb"] not in chosen]
    random.Random(SEED).shuffle(rest)
    add("aleatoire", rest[:N_RANDOM])

    unsure = sorted(model_rows, key=lambda r: abs(float(r["proba"]) - 0.5))
    add("incertain", [r for r in unsure if r["idweb"] not in chosen][:N_UNSURE])

    order = {"transport": 0, "aleatoire": 1, "incertain": 2}
    items = sorted(chosen.values(), key=lambda gr: (order[gr[0]], gr[1]["objet"]))

    cols = ["idweb", "label", "label_modele", "groupe", "proba", "nomacheteur", "objet", "url_avis"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for group, r in items:
            w.writerow({
                "idweb": r["idweb"], "label": r["label"], "label_modele": r["label"],
                "groupe": group, "proba": r["proba"], "nomacheteur": r["nomacheteur"],
                "objet": r["objet"], "url_avis": r["url_avis"],
            })

    counts = {g: sum(1 for gr, _ in items if gr == g) for g in order}
    print(f"{len(items)} avis à vérifier : {counts}")
    print(f"Fichier écrit : {OUT.resolve()}")


if __name__ == "__main__":
    main()
