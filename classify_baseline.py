"""Étape 3 — Baseline de classification de pertinence (TF-IDF + régression logistique).

Entrée : data/annotation/a_annoter*.csv  (colonnes idweb, label, objet, ...)
Sortie : affichage des scores + data/processed/erreurs_baseline.csv

On compare trois approches sur les mêmes 100 avis annotés :
  A. « tout est pertinent »  -> ce que fait la collecte par mots-clés seule
  B. une règle écrite à la main
  C. TF-IDF (mots et paires de mots) + régression logistique

Évaluation : validation croisée stratifiée répétée (5 plis x 10 répétitions),
car 100 exemples sont trop peu pour un simple découpage train/test.

Usage :
    python classify_baseline.py
"""
import csv
import html
import re
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

DATA_DIR = Path("data/annotation")
OUT_DIR = Path("data/processed")
SEED = 42


def clean(text: str) -> str:
    """Minuscules, entités HTML décodées (d&#039; -> d'), espaces normalisés."""
    text = html.unescape(str(text or "")).lower()
    return re.sub(r"\s+", " ", text).strip()


def read_annotations() -> list[dict]:
    """Lit tous les fichiers a_annoter*.csv ; en cas de doublon, le dernier fichier gagne."""
    rows: dict[str, dict] = {}
    for path in sorted(DATA_DIR.glob("a_annoter*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if str(r.get("label", "")).strip() != "":
                    rows[r["idweb"]] = r
    return list(rows.values())


def load() -> tuple[list[str], list[str], np.ndarray, list[str]]:
    rows = read_annotations()
    ids = [r["idweb"] for r in rows]
    texts = [clean(r["objet"]) for r in rows]
    y = np.array([int(float(r["label"])) for r in rows])
    raw = [html.unescape(r["objet"]) for r in rows]
    return ids, texts, y, raw


def rule_based(text: str) -> int:
    """Règle manuelle : publicité + droit d'exploiter, sans « non publicitaire(s) »."""
    has_ad = "publicit" in text
    has_exploit = any(w in text for w in ("exploitation", "concession", "régie", "regie"))
    only_non_ad = "non publicit" in text and not re.search(r"(?<!non )publicitaires?", text)
    return int(has_ad and has_exploit and not only_non_ad)


def make_model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(C=5.0, class_weight="balanced", max_iter=1000),
    )


def scores(y_true, y_pred) -> tuple[float, float, float]:
    return (
        precision_score(y_true, y_pred, zero_division=0),
        recall_score(y_true, y_pred, zero_division=0),
        f1_score(y_true, y_pred, zero_division=0),
    )


def main() -> None:
    ids, texts, y, raw = load()
    X = np.array(texts, dtype=object)
    print(f"{len(y)} avis annotés : {int(y.sum())} pertinents, {int(len(y) - y.sum())} non pertinents\n")

    # A. tout est pertinent
    pa, ra, fa = scores(y, np.ones_like(y))
    # B. règle manuelle (pas d'apprentissage : évaluée sur tout le jeu)
    pred_b = np.array([rule_based(t) for t in texts])
    pb, rb, fb = scores(y, pred_b)

    # C. modèle, validation croisée répétée
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=SEED)
    fold_scores = []
    for train, test in cv.split(X, y):
        model = make_model().fit(X[train], y[train])
        fold_scores.append(scores(y[test], model.predict(X[test])))
    m = np.mean(fold_scores, axis=0)
    s = np.std(fold_scores, axis=0)

    print(f"{'Approche':<44}{'Précision':>10}{'Rappel':>9}{'F1':>7}")
    print(f"{'A. Tout pertinent (mots-clés seuls)':<44}{pa:>10.2f}{ra:>9.2f}{fa:>7.2f}")
    print(f"{'B. Règle écrite à la main':<44}{pb:>10.2f}{rb:>9.2f}{fb:>7.2f}")
    print(f"{'C. TF-IDF + régression logistique (CV)':<44}{m[0]:>10.2f}{m[1]:>9.2f}{m[2]:>7.2f}")
    print(f"{'   écart-type de C sur les plis':<44}{s[0]:>10.2f}{s[1]:>9.2f}{s[2]:>7.2f}")

    # Analyse d'erreurs : une prédiction « hors pli » par avis
    oof = cross_val_predict(
        make_model(), X, y,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    errors = [(i, t, int(a), int(p)) for i, t, a, p in zip(ids, raw, y, oof) if a != p]
    with open(OUT_DIR / "erreurs_baseline.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idweb", "objet", "label_reel", "label_predit"])
        w.writerows(errors)

    print(f"\n{len(errors)} erreurs hors pli (détail dans {OUT_DIR / 'erreurs_baseline.csv'}) :")
    for i, t, a, p in errors:
        kind = "faux négatif (raté)" if a == 1 else "faux positif (bruit)"
        print(f" - [{kind}] {i} : {t[:110]}")

    # Mots les plus utiles au modèle, entraîné sur tous les avis
    model = make_model().fit(X, y)
    vec, clf = model.steps[0][1], model.steps[1][1]
    vocab = np.array(vec.get_feature_names_out())
    order = np.argsort(clf.coef_[0])
    print("\nIndices pour « pertinent » :", ", ".join(vocab[order[-10:]][::-1]))
    print("Indices pour « non pertinent » :", ", ".join(vocab[order[:10]]))


if __name__ == "__main__":
    main()
