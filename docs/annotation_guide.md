# Guide d'annotation

Objectif : repérer les avis BOAMP utiles à une régie publicitaire dans les transports
(type Mediatransports).

## label = 1 (pertinent)
L'avis concerne **l'exploitation ou la commercialisation d'espaces publicitaires** :
- publicité sur un réseau de transport (bus, tram, métro, gares, abris voyageurs) ;
- concession ou régie publicitaire ;
- mobilier urbain avec exploitation publicitaire (abribus, panneaux d'affichage, écrans digitaux).

## label = 0 (non pertinent)
- « avis de publicité » au sens juridique (la mention de la publication de l'avis lui-même) ;
- conseil en marketing ou communication, achat d'espace média **par** la collectivité ;
- entretien, pose ou fourniture de mobilier urbain **sans** exploitation publicitaire ;
- impression, signalétique, communication institutionnelle ;
- tout avis hors sujet.

## Cas ambigus
Si le titre ne suffit pas, ouvre `url_avis`. Si tu hésites encore, mets ton meilleur
jugement et note le numéro de ligne : ces cas difficiles seront analysés dans le README.
