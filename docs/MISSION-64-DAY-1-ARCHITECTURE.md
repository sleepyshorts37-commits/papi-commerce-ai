# Mission 64 — Jour 1 : audit et architecture

Analyse de la rotation Ed25519 après Mission 63. Le fichier de clé privée et le registre public sont deux fichiers distincts ; un remplacement atomique individuel ne garantit pas l'atomicité du couple. La fenêtre critique est l'arrêt après remplacement de la clé privée et avant publication du registre.

Décision : journal transactionnel local exclusif contenant les états ancien/nouveau et leurs empreintes SHA-256. Le journal sert à prouver quel état est présent, pas à décider à partir d'une supposition. Les états inconnus restent bloqués et le journal est conservé.

Les clés publiques historiques de Mission 63 restent destinées à l'audit ; la vérification d'une signature ancienne n'authentifie jamais une action courante.
