"""Étape 5 (suite) — Mesure l'accord entre le modèle et ta vérification.

Entrée : data/annotation/a_annoter_2.csv  (a_relire_2.csv relu, corrigé, exporté en CSV)
Sortie : affichage dans le terminal

Pour les groupes `transport` et `aleatoire`, tous les avis étaient prédits pertinents :
le taux d'accord est donc la PRÉCISION réelle du modèle sur des avis jamais vus.
Pour le groupe `incertain`, c'est la justesse du modèle sur les cas les plus difficiles.

Usage :
    python evaluate_review.py
"""
import csv
from pathlib import Path

PATH = Path("data/annotation/a_annoter_2.csv")

EXPLAIN = {
    "transport": "avis liés au transport (cœur de cible)",
    "aleatoire": "échantillon aléatoire de prédictions pertinentes",
    "incertain": "prédictions les plus incertaines (cas difficiles)",
}


def main() -> None:
    with open(PATH, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if str(r.get("label", "")).strip() != ""]

    stats: dict[str, list[int]] = {}
    changed: list[dict] = []
    for r in rows:
        agree = int(float(r["label"]) == float(r["label_modele"]))
        stats.setdefault(r["groupe"], []).append(agree)
        if not agree:
            changed.append(r)

    print(f"{len(rows)} avis vérifiés\n")
    print(f"{'Groupe':<12}{'Avis':>5}{'D’accord':>10}{'Taux':>8}   Signification")
    for g in ("transport", "aleatoire", "incertain"):
        if g in stats:
            n, k = len(stats[g]), sum(stats[g])
            print(f"{g:<12}{n:>5}{k:>10}{k / n:>8.0%}   {EXPLAIN[g]}")

    print(f"\n{len(changed)} corrections de ta part :")
    for r in changed:
        print(f" - [{r['groupe']}] modèle={r['label_modele']} -> toi={r['label']} | {r['objet'][:100]}")


if __name__ == "__main__":
    main()
