# PAPI GLOBAL WORK — adaptateurs de flux en lecture seule

## Livrable du Jour 2/5

Deux adaptateurs locaux interprètent les payloads de flux fournis par un mécanisme de collecte préalablement autorisé :

- `parse_rss_payload` : RSS 2.0.
- `parse_json_api_payload` : tableau JSON ou objet contenant `items`.

Les résultats sont des candidats non vérifiés. Les informations absentes (pays, rémunération, durée, coût, politiques IA/automatisation et paiement) sont explicitement listées pour qualification ultérieure. Ces candidats ne sont pas injectés automatiquement dans le registre des opportunités validées.

## Limites importantes

Ces adaptateurs ne font aucune requête HTTP, n'ouvrent aucun navigateur et ne contournent aucune authentification. Ils ne constituent pas encore des connecteurs réseau actifs. Le mécanisme qui récupère les payloads doit être séparé, documenté, autorisé par la source et respecter ses limites de débit et conditions d'utilisation.

Les URL des offres doivent être HTTPS publiques. Les payloads sont limités à 1 Mo et 100 éléments. Les DTD et entités XML sont refusées. Aucun secret d'accès ne doit être inclus dans les données.

Aucune candidature, inscription, publication ou prise de contact n'est déclenchée.
