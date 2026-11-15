# Mission 131 — Tableau de bord mobile PAPI KIDS

## Livrable
Un rendu HTML autonome et responsive, lisible sur iPhone, pour afficher l'état d'un livre, les compteurs, la progression d'approbation, les 24 pages et leurs statuts. Filtres accessibles par statut et échappement HTML de toutes les données éditoriales.

## Réception du manuscrit
Le sélecteur de fichier permet uniquement une prévisualisation locale des fichiers Markdown et texte (2 Mo maximum). Il ne transmet rien au serveur. Cette limite est volontaire : aucun endpoint d'upload authentifié n'existait encore sur la base de cette mission.

## Sécurité et limites
- Aucun secret fournisseur dans le navigateur.
- Aucune génération, approbation, dépense ou publication déclenchée par l'interface.
- Les données affichées sont injectées par le backend appelant ; cette mission ne déploie pas de serveur web.
- La prochaine étape doit raccorder une API authentifiée avec stockage privé et suivi persistant avant de rendre l'envoi de manuscrit opérationnel.
