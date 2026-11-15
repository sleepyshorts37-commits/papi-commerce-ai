# Mission 114 — Routage des modèles gratuits et mesure du débit

## Routage prudent
`FreeImageModelRouter` accepte uniquement un registre explicite de modèles dont la gratuité est confirmée pour le compte. Aucun modèle n'est découvert, activé ou considéré gratuit implicitement. Le routeur sélectionne le modèle configuré au coût estimé par image le plus bas afin de maximiser le nombre théorique d'images par enveloppe de quota.

Le fournisseur sous-jacent reste responsable de la réservation partagée des quotas avant chaque appel. Une insuffisance de quota est signalée par image ; le routeur ne bascule pas vers un fournisseur payant et ne relance pas une requête ambiguë.

## Mesure réelle
Après chaque lot, le routeur enregistre :
- nombre de résultats confirmés comme générés et correctement corrélés ;
- durée réellement écoulée ;
- images/heure calculées ;
- nombre d'échecs ou résultats incertains ;
- modèle sélectionné et coût estimé.

La métrique est issue du temps mesuré pendant l'exécution, pas d'une simulation. Les tests injectent une horloge déterministe uniquement pour vérifier la formule ; ce chiffre de test n'est pas une performance de production.

## Configuration
Le registre est fourni par l'application et doit contenir le modèle, son coût estimé par image et une confirmation explicite de gratuité sur le compte. Les modèles non confirmés sont refusés à l'initialisation.

## Limites
- Un seul modèle est choisi pour un lot, celui au coût estimé le plus faible. Une sélection plus avancée par disponibilité ou latence nécessite des données de quota et de santé par modèle fiables.
- Le coût estimé n'est pas une mesure garantie de consommation réelle.
- Aucun appel Cloudflare réel, aucune clé, aucun abonnement et aucun fournisseur payant de secours n'ont été utilisés.
