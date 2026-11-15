# Mission 174 — Diagnostic de préparation opérationnelle

## Livrable
- Vérifie stockage privé, permissions, connexion PostgreSQL, présence des migrations et variables d'environnement.
- Vérifie séparément les jetons upload, revue illustrations, sécurité, métadonnées et fabrication.
- Vérifie la présence de configuration Cloudflare sans appeler le fournisseur ni prétendre vérifier son quota.
- Vérifie l'activation explicite du build KDP (désactivée par défaut).
- Retourne uniquement des booléens et noms de variables manquantes ; aucune valeur de secret n'est exposée.
- Dépenses zéro, aucun appel externe, aucune publication.

## Limites
La présence d'un jeton Cloudflare ne prouve ni sa validité ni la gratuité/quota restant. Un test de quota réel nécessitera une vérification fournisseur autorisée et un plafond de dépense confirmé.
