# Mission 44 — Procédure opérateur

## Préparation
- Utiliser un répertoire local privé pour les paquets reçus.
- Vérifier par un canal indépendant l'identifiant de l'instance destinataire et le registre public de clés.
- Garder la clé privée du propriétaire hors de l'instance destinataire.
- Sauvegarder le registre SQLite selon la politique locale avant traitement.

## Réception
Exécuter la commande `receive-sync-package` avec les cinq paramètres requis. Un code retour 0 signifie que la signature, la destination, la validité et l'inscription du reçu ont été acceptées. Un échec doit être traité comme un refus; ne pas modifier manuellement le registre pour contourner le contrôle.

## Après réception
- Conserver le paquet original et le rapport de réception.
- Le statut `recorded` signifie reçu nouvellement inscrit; `already_recorded` signifie que le même digest avait déjà été reçu avec une nouvelle approbation valide.
- Aucun événement mémoire/chat n'a été importé. Ne pas annoncer la synchronisation des contenus comme achevée.
- Pour tout rejet, conserver les éléments de diagnostic sans publier de secrets.

## Arrêt et limites
La commande n'ouvre aucune connexion réseau et ne démarre aucun processus. Le reçu est local au fichier SQLite configuré. Ne pas déplacer le registre entre plusieurs instances pour simuler un anti-rejeu distribué.
