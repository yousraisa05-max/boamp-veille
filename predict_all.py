"""Étape 4 — Applique le modèle à tous les avis collectés.

Entrées : data/raw/boamp_raw.jsonl        (tous les avis collectés)
          data/annotation/a_annoter*.csv  (tes labels, utilisés comme référence)
Sortie  : data/processed/predictions.csv  (un avis par ligne, pertinents en premier)
          data/processed/a_verifier.csv   (les 20 prédictions les moins sûres)

Règles :
  - un avis que tu as annoté garde TON label (source = « humain ») ;
  - les autres reçoivent la prédiction du modèle entraîné sur tes 100 avis (source = « modèle ») ;
  - `transport` = 1 si l'objet évoque un réseau de transport (règle à mots-clés) ;
  - `en_cours` = 1 si la date limite de réponse n'est pas dépassée.

Usage :
    python predict_all.py
"""
import csv
import json
import re
from datetime import date
from pathlib import Path

import numpy as np

from classify_baseline import clean, make_model, read_annotations

RAW = Path("data/raw/boamp_raw.jsonl")
OUT_DIR = Path("data/processed")

TRANSPORT_RE = re.compile(
    r"\b(r[ée]seaux? de transports?|transports? (?:en commun|public|publics|urbains?)"
    r"|bus|tram|tramway|m[ée]tro|gares?|a[ée]ro(?:port|gare)|ratp|sncf|stcl|tcl"
    r"|abris?[- ]voyageurs?)\b"
)


def as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return " ".join(str(value).split())


def deadline_open(value, today: date) -> int | str:
    """1 si la date limite est aujourd'hui ou plus tard, 0 si dépassée, '' si inconnue."""
    try:
        return int(date.fromisoformat(str(value)[:10]) >= today)
    except ValueError:
        return ""


def main() -> None:
    with open(RAW, encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    human = {r["idweb"]: int(float(r["label"])) for r in read_annotations()}

    # Entraînement du modèle sur les avis annotés qui sont dans la collecte
    train = [r for r in records if r.get("idweb") in human]
    X_train = np.array([clean(r.get("objet")) for r in train], dtype=object)
    y_train = np.array([human[r["idweb"]] for r in train])
    model = make_model().fit(X_train, y_train)
    print(f"Modèle entraîné sur {len(train)} avis annotés ({int(y_train.sum())} pertinents).")

    texts = np.array([clean(r.get("objet")) for r in records], dtype=object)
    proba = model.predict_proba(texts)[:, 1]

    today = date.today()
    rows = []
    for rec, text, p in zip(records, texts, proba):
        idweb = rec.get("idweb")
        is_human = idweb in human
        label = human[idweb] if is_human else int(p >= 0.5)
        rows.append({
            "idweb": idweb,
            "label": label,
            "source": "humain" if is_human else "modèle",
            "proba": "" if is_human else f"{p:.2f}",
            "transport": int(bool(TRANSPORT_RE.search(text + " " + clean(rec.get("nomacheteur"))))),
            "en_cours": deadline_open(rec.get("datelimitereponse"), today),
            "datelimitereponse": as_text(rec.get("datelimitereponse"))[:10],
            "dateparution": as_text(rec.get("dateparution"))[:10],
            "nomacheteur": as_text(rec.get("nomacheteur")),
            "objet": as_text(rec.get("objet")),
            "type_marche": as_text(rec.get("type_marche")),
            "url_avis": as_text(rec.get("url_avis")),
        })

    # Pertinents d'abord, transport en tête, puis date limite la plus proche
    rows.sort(key=lambda r: (-r["label"], -r["transport"], r["datelimitereponse"] or "9999"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with open(OUT_DIR / "predictions.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # Les prédictions du modèle les moins sûres : à relire pour améliorer le modèle
    unsure = sorted(
        (r for r in rows if r["source"] == "modèle"),
        key=lambda r: abs(float(r["proba"]) - 0.5),
    )[:20]
    with open(OUT_DIR / "a_verifier.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(unsure)

    model_rows = [r for r in rows if r["source"] == "modèle"]
    pos = [r for r in rows if r["label"] == 1]
    print(f"\n{len(rows)} avis au total")
    print(f"  annotés par toi : {len(rows) - len(model_rows)}")
    print(f"  prédits par le modèle : {len(model_rows)}, dont {sum(r['label'] for r in model_rows)} pertinents")
    print(f"  pertinents au total : {len(pos)}, dont transport : {sum(r['transport'] for r in pos)}"
          f", dont délai non dépassé : {sum(1 for r in pos if r['en_cours'] == 1)}")
    print(f"\nÉcrit : {OUT_DIR / 'predictions.csv'} et {OUT_DIR / 'a_verifier.csv'}")

    print("\nAvis pertinents liés au transport :")
    for r in [r for r in pos if r["transport"]][:15]:
        print(f" - {r['idweb']} | {r['nomacheteur'][:35]} | {r['objet'][:90]} | limite : {r['datelimitereponse'] or '?'}")


if __name__ == "__main__":
    main()
