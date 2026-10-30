# boamp-veille — Veille d'appels d'offres de publicité extérieure (BOAMP) avec du TAL

Outil de veille qui collecte les avis du **BOAMP** (Bulletin officiel des annonces des marchés publics), repère ceux qui donnent à une entreprise le droit d'**exploiter des espaces publicitaires** (mobilier urbain, abris-voyageurs, réseaux de transport, régies publicitaires) et en extrait les informations clés : acheteur, nature de l'avis, durée du contrat, valeur estimée, nombre de lots.

Projet personnel réalisé dans le cadre de mon Master TAL (Université Paris Nanterre), pour un cas d'usage de régie publicitaire dans les transports.

## Le problème

Une recherche par mots-clés (« publicité », « mobilier urbain »…) ramène énormément de bruit. Sur un échantillon aléatoire de 100 avis collectés, **seuls 29 % sont réellement pertinents**. Les autres parlent d'achat d'espaces par une mairie, d'objets publicitaires, d'impression de bulletins, d'entretien de mobilier sans publicité ou de taxe sur la publicité extérieure.

La difficulté est linguistique : les mots se ressemblent mais le sens s'inverse.

| Avis | Pertinent ? |
|---|---|
| « Concession… exploitation des mobiliers urbains **publicitaires** et non publicitaires » | oui |
| « **Achat** d'espaces publicitaires et conseil médias » | non (la collectivité est cliente) |
| « Nettoyage des abris voyageurs **non publicitaires** » | non |
| « **Exploitation du réseau** de transport urbain » | non (exploiter des bus, pas de la publicité) |

## Données

- **Source** : API open data du BOAMP (DILA), dataset `boamp`. Les conditions de réutilisation sont à consulter sur data.gouv.fr.
- **Collecte** : avis parus depuis le 1er janvier 2025, interrogés avec six mots-clés larges (`publicité`, `affichage publicitaire`, `régie publicitaire`, `espaces publicitaires`, `mobilier urbain`, `concession publicitaire`), dédoublonnés : **724 avis**.
- Le texte classé est l'**objet** de l'avis (son titre). Le champ détaillé `donnees` (format européen eForms) sert à l'extraction d'informations.
- Les coordonnées de personnes présentes dans les avis ne sont ni lues ni publiées dans ce dépôt.

## Méthode

1. **Collecte** (`collect_boamp.py`) : interrogation de l'API, dédoublonnage.
2. **Annotation** : 100 avis tirés au hasard, étiquetés `1` (pertinent) ou `0` selon un [guide d'annotation](docs/annotation_guide.md). Le critère : *l'avis donne-t-il à une entreprise le droit de vendre de la publicité sur des supports extérieurs ?*
3. **Classification** (`classify_baseline.py`) : TF-IDF (mots et paires de mots) + régression logistique, comparée à deux références (tout classer pertinent ; une règle écrite à la main). Évaluation par validation croisée stratifiée répétée (5 plis × 10 répétitions).
4. **Prédiction** (`predict_all.py`) sur les 724 avis, avec une colonne `transport` (règle à mots-clés).
5. **Vérification ciblée** (`make_review_sheet.py`, `evaluate_review.py`) : relecture de 67 avis jamais annotés, répartis en trois groupes (avis de transport prédits pertinents, échantillon aléatoire de prédictions pertinentes, prédictions les plus incertaines). Les corrections sont réinjectées dans l'entraînement.
6. **Extraction et digest** (`build_digest.py`) : nature de l'avis, durée, valeur estimée, nombre de lots, puis regroupement des avis d'une même procédure (avis initial, rectificatif, attribution).

### Transparence sur l'annotation

Les labels ont été **pré-remplis par Claude (Anthropic)**, puis **relus et validés par moi**, avec ouverture des avis complets pour les cas incertains. Ce choix accélère l'annotation mais peut orienter le jugement : la relecture des avis de transport a laissé passer plusieurs erreurs (trois délégations d'exploitation de réseau de bus), détectées ensuite grâce aux erreurs du modèle (voir Limites). Les corrections ont été faites avec `fix_label.py`.

## Résultats

### Classification de la pertinence

**Mesure de référence : 100 avis tirés au hasard** (29 pertinents)

| Approche | Précision | Rappel | F1 |
|---|---|---|---|
| A. Tout classer pertinent (= la collecte par mots-clés seule) | 0,29 | 1,00 | 0,45 |
| B. Règle écrite à la main | 0,82 | 0,79 | 0,81 |
| C. TF-IDF + régression logistique | **0,95** | **0,85** | **0,89** |

Écart-type du F1 de C sur les plis : 0,10. Avec seulement 100 exemples, ces chiffres donnent une tendance et pas une performance définitive. La règle B a été écrite après avoir lu ces avis : elle est probablement trop optimiste.

**Après ajout des avis ciblés** (167 avis annotés, 79 pertinents)

| Approche | Précision | Rappel | F1 |
|---|---|---|---|
| A. Tout classer pertinent | 0,47 | 1,00 | 0,64 |
| B. Règle écrite à la main | 0,90 | 0,80 | 0,85 |
| C. TF-IDF + régression logistique | 0,95 | 0,91 | 0,93 |

Ce deuxième jeu contient volontairement des cas difficiles (transport, prédictions incertaines) : ses scores ne sont **pas comparables** au premier.

### Vérification sur des avis jamais annotés

| Groupe | Avis | D'accord avec le modèle |
|---|---|---|
| Transport (prédits pertinents) | 22 | 15 (68 %) |
| Échantillon aléatoire (prédits pertinents) | 25 | 25 (100 %) |
| Prédictions les plus incertaines | 20 | 17 (85 %) |

L'échantillon aléatoire (25 sur 25) laisse une marge d'incertitude importante : avec si peu d'avis, la précision réelle peut raisonnablement se situer autour de 85 à 100 %.

### Application aux 724 avis

- **176 avis pertinents** (79 annotés + 97 prédits), regroupés en **131 procédures**, dont **12 liées au transport**.
- Statuts : 2 procédures encore ouvertes, 49 attribuées, 80 closes (la collecte remonte à janvier 2025).
- Extraction d'informations (sur les 176 avis pertinents) : nombre de lots trouvé pour 109 avis (62 %), durée du contrat pour 80 (45 %), valeur estimée pour 49 (28 %).

Exemples de lignes du digest :

| Acheteur | Objet | Durée | Valeur estimée |
|---|---|---|---|
| Tisséo Voyageurs | Concession d'exploitation des régies publicitaires | 60 mois | 35 M€ |
| RATP | Concession d'exploitation d'une régie publicitaire | 144 mois | 1,8 Md€ |

## Limites

- **Peu de données** : 167 avis annotés au total, dont très peu de transport pertinents au départ (5 sur les 100 premiers). Les scores varient beaucoup d'un tirage à l'autre.
- **Confusion lexicale** : le modèle a d'abord appris que « concession » et « exploitation » signalent la pertinence, et a classé comme pertinentes des délégations de service public d'**exploitation de réseaux de bus** (Le Mans, Boulonnais, Nantes, Montluçon, région Hauts-de-France). Ces cas ont été corrigés par annotation ciblée. En validation croisée, il reste quelques faux positifs sur des avis qui contiennent « publicitaire » ou « régie » sans porter sur de l'affichage extérieur (régie d'un magazine municipal, assistance à maîtrise d'ouvrage pour de l'affichage numérique « non publicitaire »).
- **Expression « et non »** : elle apparaît dans « publicitaires **et non** publicitaires » (pertinent) comme dans « abris voyageurs **non** publicitaires » (non pertinent). Un modèle qui compte les mots ne distingue pas bien ces cas, et des avis pertinents de mobilier urbain sont ratés.
- **Biais d'annotation** : labels pré-remplis par un modèle de langage. La relecture a laissé passer des erreurs sur les avis de transport, retrouvées via les erreurs du modèle.
- **Étiquette « transport » par mots-clés** : elle manque des cas comme la régie sur véhicules du réseau Le Met'.
- **Extraction partielle** : le champ `donnees` suit plusieurs formats ; seul le format européen eForms est exploité, d'où des taux de réussite moyens.
- **Périmètre** : seul le BOAMP est interrogé (pas le JOUE ni les plateformes d'acheteurs), et la collecte repose sur des mots-clés dans les titres. Le rappel de la collecte elle-même n'est pas mesuré : un avis sans ces mots dans son titre n'est jamais vu.
- Seul le **titre** des avis est classé, pas le texte intégral ni les cahiers des charges.
- Aucun réglage des hyperparamètres ; seuil de décision fixé à 0,5.

## Pistes d'amélioration

- Classer le texte intégral de l'avis et pas seulement son titre.
- Tester un modèle contextuel (CamemBERT, embeddings de phrases ou LLM) pour mieux traiter « publicitaires et non publicitaires » et « exploitation du réseau ».
- Annoter davantage d'avis de transport (cas rares mais centraux).
- Étendre l'extraction aux autres formats de `donnees` et ajouter le titulaire des attributions.
- Relancer la collecte chaque semaine pour une vraie veille, et estimer les dates de renouvellement à partir de la date d'attribution et de la durée du contrat.

## Installation et utilisation

```bash
git clone https://github.com/yousraisa05-max/boamp-veille.git
cd boamp-veille
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python collect_boamp.py --since 2025-01-01   # 1. collecte -> data/raw/
python classify_baseline.py                  # 2. évaluation de la classification (nécessite data/annotation/a_annoter*.csv)
python predict_all.py                        # 3. prédictions -> data/processed/predictions.csv
python make_review_sheet.py                  # 4. feuille de vérification -> data/annotation/a_relire_2.csv
python evaluate_review.py                    #    accord modèle / relecture (après export en a_annoter_2.csv)
python build_digest.py                       # 5. digest par procédure -> data/processed/digest.csv
```

Outils annexes : `make_annotation_sheet.py` (échantillon à annoter), `fix_label.py` (corriger des labels dans les CSV), `inspect_record.py` (voir le contenu d'un avis).

## Structure du dépôt

```
collect_boamp.py          collecte via l'API BOAMP
make_annotation_sheet.py  échantillon aléatoire à annoter
classify_baseline.py      baseline + évaluation + analyse d'erreurs
predict_all.py            prédiction sur tous les avis
make_review_sheet.py      feuille de vérification ciblée
evaluate_review.py        accord modèle / relecture
build_digest.py           extraction d'informations + digest
fix_label.py              correction de labels
inspect_record.py         inspection d'un avis
docs/annotation_guide.md  guide d'annotation
data/annotation/          annotations (CSV)
data/processed/           prédictions, erreurs, digest
```

## Auteure

Yousra — Master Traitement automatique des langues, Université Paris Nanterre.
