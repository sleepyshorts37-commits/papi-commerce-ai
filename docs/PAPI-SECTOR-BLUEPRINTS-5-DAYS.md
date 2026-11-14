# Cycle de cinq jours — Modèles sectoriels WEB BUILDER

## Objectif
Fournir des plans de contenu et de pages cohérents pour six secteurs, sans inventer les informations commerciales d'un client.

## Plan
1. Inventorier les secteurs et leurs besoins de pages.
2. Définir les faits obligatoires avant génération.
3. Ajouter des garde-fous sectoriels, notamment santé, commerce et hôtellerie.
4. Implémenter une API locale de consultation et de contrôle de complétude.
5. Ajouter les tests, documenter les limites et soumettre une PR.

## Périmètre livré
- Secteurs : corporate, ecommerce, hospitality, professional_services, education, health.
- Quatre pages recommandées par secteur.
- Types de sections conseillés à partir du vocabulaire existant.
- Faits requis, règles de prudence et contrôle de complétude.
- Copies défensives pour éviter la mutation accidentelle des modèles.

## Sécurité et limites
Le contrôle vérifie uniquement la présence de libellés et de textes non vides. Il ne vérifie ni leur exactitude, ni l'identité du client, ni les autorisations sectorielles. Une validation humaine reste obligatoire. Aucun réseau, publication, réservation, paiement ou contact client n'est exécuté.

## Critères de validation
- Six secteurs listés et accessibles par identifiant strict.
- Les données retournées ne permettent pas de modifier les modèles internes.
- Les faits manquants sont signalés.
- La sortie ne prétend jamais vérifier la véracité des informations.
- Les garde-fous santé sont explicitement testés.
