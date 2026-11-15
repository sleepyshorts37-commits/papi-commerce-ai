# Mission 79 — Moteur de scoring marché PAPI KIDS

## Objectif
Transformer la présélection commerciale des idées en processus reproductible, traçable et prudent. Le moteur ne recherche pas le marché et ne fabrique aucune donnée : il calcule uniquement à partir des notes saisies par un évaluateur et des preuves qu'il référence.

## Huit critères et pondérations
Chaque critère reçoit une note entière de 0 à 5, avec justification et au moins une preuve. Pondérations totalisant 100 :

| Critère | Poids |
|---|---:|
| Preuves de demande | 20 |
| Position concurrentielle | 10 |
| Différenciation | 15 |
| Économie unitaire Amazon KDP | 15 |
| Économie unitaire Jumia | 10 |
| Faisabilité éditoriale | 10 |
| Droits et sécurité enfant | 10 |
| Fiabilité des sources | 10 |

Le score final est la moyenne pondérée convertie sur 100. Les poids ne constituent pas des statistiques de marché : ils expriment une politique interne de priorisation et pourront être révisés avec historique de décisions.

## Contrat de preuve
Chaque preuve consigne :
- type de source (officielle, marketplace, éditeur, entretien adulte, devis de coût, revue interne ou autre) ;
- URL ou référence vérifiable ;
- date d'observation ;
- constat exact soutenant la note ;
- limites, biais ou éléments non démontrés.

Les preuves d'entretiens doivent concerner des adultes et être consignées sans données personnelles inutiles. Les pages marketplace, résultats de recherche, avis et classements ne doivent pas être présentés comme des ventes réelles si la source ne le démontre pas. Une hypothèse interne doit être identifiée comme telle et ne remplace pas une source externe.

## Règle de calcul
- Chaque critère commence à `pending`, avec score `null` et preuves vides.
- Un critère `assessed` exige une note 0–5, une justification et au moins une preuve.
- Tant qu'un seul critère est pending, le concept est `not_assessed`, sans score global ni rang.
- Lorsque les huit critères sont documentés, le score et le rang sont calculés de manière déterministe.
- Décision indicative : 70–100 = `GO_TO_PROTOTYPE`; 50–69,99 = `REWORK`; moins de 50 = `STOP`.
- GO signifie uniquement autoriser l'étape de prototype après validation humaine. Ce n'est ni une décision de publication, ni une prévision de vente, ni une garantie de rentabilité.

## Résultats initiaux
Le registre `data/divisions/papi-kids-market-assessments.json` contient les cinq concepts du portefeuille, tous avec les huit critères en attente. Aucun prix, volume de recherche, vente, commission ou coût n'a été inventé. Le rapport initial doit donc afficher cinq concepts non évalués et aucun classement.

## Utilisation locale
`python -m papi_core kids-market-report`

Commande en lecture seule. Elle n'effectue aucune recherche réseau, ne contacte aucun répondant, ne crée aucune annonce et ne modifie aucun statut d'agent.

## Limites et prochaines étapes
1. MAYA/NOVA devront rassembler des preuves publiques datées et des comparables pertinents.
2. PROFIT/FINANCE devront saisir des coûts réels ou devis datés pour chaque canal, en distinguant estimations et montants confirmés.
3. LEX devra documenter les risques de droits et de sécurité, sans présenter le scoring comme un avis juridique.
4. Un réviseur indépendant doit challenger les notes et les limites des sources.
5. Le propriétaire humain décide du passage au prototype.

Aucun compte KDP/Jumia, achat, stock, campagne, contact commercial ou publication n'est activé par ce moteur.
