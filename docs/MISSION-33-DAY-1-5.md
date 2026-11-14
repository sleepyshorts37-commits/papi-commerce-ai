# Mission 33 — Jours 1 à 5 : contrats et sécurité

1. Audit des modules mémoire, chat, identité partagée, stockage, pagination, réconciliation et readiness.
2. Inventaire des champs sémantiques et des frontières de visibilité déjà appliquées.
3. Canonicalisation JSON triée et empreinte SHA-256 pour garantir la reproductibilité des plans.
4. Politique explicite : seules les entrées shared/normal et les messages destinés à l'agent ou à all sont candidates.
5. Modèle de menace : service_role reste exclusivement serveur ; les snapshots sont non fiables ; secrets et contenus restreints sont exclus.

**État :** audit statique effectué ; les contrats s'appuient sur les validations existantes et sont complétés par le nouveau protocole.
