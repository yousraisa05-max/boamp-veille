"""Étape 1 — Collecte d'avis BOAMP liés à la publicité dans les transports.

Source : API Opendatasoft du BOAMP (DILA), dataset "boamp".
Sortie  : data/raw/boamp_raw.jsonl (un avis par ligne, tous les champs)
          data/raw/boamp_apercu.csv (quelques colonnes pour regarder les données)

Usage :
    python collect_boamp.py --since 2025-01-01
    python collect_boamp.py --since 2025-01-01 --max-per-keyword 300
"""
import argparse
import csv
import json
import time
from pathlib import Path

import requests

BASE_URL = (
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/boamp/records"
)
PAGE_SIZE = 100  # maximum par requête côté Opendatasoft
API_WINDOW = 10_000  # offset + limit ne peut pas dépasser ce plafond

# Mots-clés larges : on filtre finement plus tard (classification).
KEYWORDS = [
    "publicité",
    "affichage publicitaire",
    "régie publicitaire",
    "espaces publicitaires",
    "mobilier urbain",
    "concession publicitaire",
]

OUT_DIR = Path("data/raw")


def fetch_keyword(keyword: str, since: str, max_records: int) -> list[dict]:
    """Récupère les avis dont l'objet contient `keyword`, parus depuis `since`."""
    records: list[dict] = []
    offset = 0
    where = f"search(objet, \"{keyword}\") AND dateparution >= date'{since}'"

    while offset < min(max_records, API_WINDOW):
        params = {
            "where": where,
            "order_by": "dateparution desc",
            "limit": min(PAGE_SIZE, API_WINDOW - offset),
            "offset": offset,
        }
        resp = requests.get(BASE_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"[ERREUR {resp.status_code}] mot-clé « {keyword} »")
            print(resp.text[:500])
            break

        batch = resp.json().get("results", [])
        records.extend(batch)
        print(f"  « {keyword} » : {len(records)} avis récupérés")

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.3)  # on reste poli avec l'API

    return records[:max_records]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2025-01-01", help="date AAAA-MM-JJ")
    parser.add_argument("--max-per-keyword", type=int, default=300)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    unique: dict[str, dict] = {}
    for kw in KEYWORDS:
        for rec in fetch_keyword(kw, args.since, args.max_per_keyword):
            key = str(rec.get("idweb") or rec.get("id") or json.dumps(rec)[:80])
            unique.setdefault(key, rec)

    records = list(unique.values())
    print(f"\nTotal après dédoublonnage : {len(records)} avis")
    if not records:
        print("Aucun avis : vérifie le message d'erreur ci-dessus.")
        return

    # Les noms de champs peuvent évoluer : on les affiche pour vérifier.
    print("Champs disponibles :", sorted(records[0].keys()))

    with open(OUT_DIR / "boamp_raw.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    cols = ["idweb", "dateparution", "nomacheteur", "objet", "datelimitereponse", "url_avis"]
    with open(OUT_DIR / "boamp_apercu.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({c: rec.get(c, "") for c in cols})

    print("\nFichiers écrits dans", OUT_DIR.resolve())
    print("\nTrois exemples d'objets d'avis :")
    for rec in records[:3]:
        print(" -", str(rec.get("objet", ""))[:150])


if __name__ == "__main__":
    main()
