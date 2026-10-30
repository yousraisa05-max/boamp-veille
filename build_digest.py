"""Étape 6 — Extraction d'informations et digest regroupé par procédure.

Entrées : data/processed/predictions.csv  (avis pertinents, produit par predict_all.py)
          data/raw/boamp_raw.jsonl        (champs détaillés, dont `donnees`)
Sortie  : data/processed/digest.csv       (une ligne par procédure, pas par avis)

Pour chaque avis pertinent, on extrait :
  - la nature de l'avis (appel d'offres, rectificatif, attribution) ;
  - la durée prévue du contrat (en mois) et le montant estimé, quand l'avis les donne ;
  - le nombre de lots.
Puis on regroupe les avis qui concernent la même procédure.

Le champ `donnees` suit plusieurs formats selon les avis (eForms européen, formats plus anciens) :
l'extraction est donc « au mieux », et le script affiche le taux de réussite.
Les coordonnées de contact présentes dans `donnees` ne sont volontairement pas lues.

Usage :
    python build_digest.py
"""
import csv
import json
import re
from pathlib import Path

PRED = Path("data/processed/predictions.csv")
RAW = Path("data/raw/boamp_raw.jsonl")
OUT = Path("data/processed/digest.csv")


# ---------- outils pour parcourir le JSON de `donnees` ----------
def parse_donnees(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def walk(node):
    """Rend (clé, valeur) pour chaque clé de dictionnaire, à n'importe quelle profondeur."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from walk(v)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def find_all(tree, name: str) -> list:
    """Toutes les valeurs dont la clé se termine par `name` (préfixe cbc:/cac: ignoré)."""
    return [v for k, v in walk(tree) if k.split(":")[-1] == name]


def text_of(value) -> str:
    if isinstance(value, dict):
        return str(value.get("#text", ""))
    return "" if value is None else str(value)


# ---------- extraction ----------
def duration_months(tree) -> int | str:
    """Durée prévue du contrat, lue dans les blocs PlannedPeriod (pas la validité des offres)."""
    months = []
    for period in find_all(tree, "PlannedPeriod"):
        for v in find_all(period, "DurationMeasure"):
            try:
                n = float(text_of(v).replace(",", "."))
            except ValueError:
                continue
            unit = str(v.get("@unitCode", "")).upper() if isinstance(v, dict) else ""
            factor = {"MONTH": 1, "MON": 1, "YEAR": 12, "ANN": 12, "DAY": 1 / 30, "WEEK": 1 / 4.33}.get(unit)
            if factor:
                months.append(n * factor)
    return round(max(months)) if months else ""


def duration_from_text(text: str) -> int | str:
    """Repli : « durée de 10 ans », « durée … 60 mois » dans le texte libre."""
    m = re.search(r"dur[ée]e[^.\n]{0,60}?(\d{1,3})\s*(ans?|mois)\b", text, flags=re.I)
    if not m:
        return ""
    n = int(m.group(1))
    return n * 12 if m.group(2).lower().startswith("an") else n


def estimated_amount(tree) -> float | str:
    values = []
    for v in find_all(tree, "EstimatedOverallContractAmount"):
        try:
            values.append(float(text_of(v).replace(",", ".")))
        except ValueError:
            pass
    return max(values) if values else ""


def lot_count(tree) -> int | str:
    total = sum(len(v) if isinstance(v, list) else 1 for v in find_all(tree, "ProcurementProjectLot"))
    return total or ""


def notice_nature(rec: dict) -> str:
    label = f"{rec.get('nature_libelle') or ''} {rec.get('famille_libelle') or ''}".lower()
    if re.search(r"attribution|r[ée]sultat", label):
        return "attribution"
    if re.search(r"rectificatif|modificatif", label):
        return "rectificatif"
    if re.search(r"march[ée]|appel|concession|d[ée]l[ée]gation", label):
        return "appel d'offres"
    return str(rec.get("nature_libelle") or "autre")


def group_key(acheteur: str, objet: str) -> str:
    """Même acheteur + même début d'objet (sans « avis d'attribution - ») = même procédure."""
    o = re.sub(r"^\s*avis\s+(d['’]\s*)?(attribution|rectificatif)\s*[-:]?\s*", "", objet, flags=re.I)
    a = re.sub(r"\(.*?\)", " ", acheteur)                       # « Ville de Beaucaire (30) »
    a = re.sub(r"^\s*(la\s+)?(ville|commune|mairie)\s+(de|d['’])\s*", "", a, flags=re.I)
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return norm(a)[:40] + "|" + norm(o)[:60]


def main() -> None:
    with open(PRED, encoding="utf-8-sig", newline="") as f:
        relevant = [r for r in csv.DictReader(f) if r["label"] == "1"]
    ids = {r["idweb"] for r in relevant}

    raw = {}
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("idweb") in ids:
                raw[rec["idweb"]] = rec

    notices = []
    for r in relevant:
        rec = raw.get(r["idweb"], {})
        tree = parse_donnees(rec.get("donnees"))
        duree = duration_months(tree) if tree else ""
        if duree == "":
            duree = duration_from_text(str(rec.get("objet") or ""))
        notices.append({
            **r,
            "nature": notice_nature(rec),
            "duree_mois": duree,
            "montant_estime": estimated_amount(tree) if tree else "",
            "nb_lots": lot_count(tree) if tree else "",
            "groupe": group_key(r["nomacheteur"], r["objet"]),
        })

    # Regroupement par procédure
    groups: dict[str, list[dict]] = {}
    for n in notices:
        groups.setdefault(n["groupe"], []).append(n)

    digest = []
    for g in groups.values():
        g.sort(key=lambda n: n["dateparution"])
        call = next((n for n in g if n["nature"] == "appel d'offres"), g[0])
        natures = sorted({n["nature"] for n in g})
        if "attribution" in natures:
            statut = "attribué"
        elif any(n["en_cours"] == "1" for n in g):
            statut = "en cours"
        else:
            statut = "clos"
        pick = lambda key: next((n[key] for n in g if n[key] != ""), "")
        digest.append({
            "statut": statut,
            "transport": max(int(n["transport"]) for n in g),
            "nb_avis": len(g),
            "natures": " + ".join(natures),
            "nomacheteur": call["nomacheteur"],
            "objet": call["objet"],
            "dateparution": g[0]["dateparution"],
            "datelimitereponse": call["datelimitereponse"],
            "duree_mois": pick("duree_mois"),
            "montant_estime": pick("montant_estime"),
            "nb_lots": pick("nb_lots"),
            "url_avis": call["url_avis"],
        })

    order = {"en cours": 0, "attribué": 1, "clos": 2}
    digest.sort(key=lambda d: (order[d["statut"]], -d["transport"], d["datelimitereponse"] or "9999"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(digest[0].keys()))
        w.writeheader()
        w.writerows(digest)

    n = len(notices)
    print(f"{n} avis pertinents regroupés en {len(digest)} procédures.")
    print(f"Statuts : { {s: sum(1 for d in digest if d['statut'] == s) for s in order} }")
    print(f"Procédures de transport : {sum(d['transport'] for d in digest)}")
    print("\nTaux d'extraction (sur les avis) :")
    for key in ("duree_mois", "montant_estime", "nb_lots"):
        k = sum(1 for x in notices if x[key] != "")
        print(f"  {key:<15}: {k}/{n}")
    nat = {}
    for x in notices:
        nat[x["nature"]] = nat.get(x["nature"], 0) + 1
    print(f"Natures d'avis : {nat}")
    print(f"\nÉcrit : {OUT.resolve()}")


if __name__ == "__main__":
    main()
