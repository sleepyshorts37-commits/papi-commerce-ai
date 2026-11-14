# Mission 45 — Prompt de réalisation

Construire une charge utile locale séparée pour les contenus mémoire et PAPI CHAT, liée aux références et empreintes du bundle signé existant.

Exigences :
- Formats canonique, versionné, taille plafonnée et digest propre.
- Lier exactement chaque contenu à event_id, kind, record_id, sequence et content_digest du bundle.
- Mémoire : uniquement remember, shared, normal, auteur connu du registre; exclure décision, owner, agent et supersede.
- CHAT : valider le schéma et les identités à l'aide du registre d'agents.
- Bloquer les secrets et motifs courants de données personnelles/financières; documenter que la détection n'est pas exhaustive.
- Écriture atomique, permissions restrictives, absence d'écrasement, refus des liens symboliques en lecture.
- Aucun import dans les journaux, aucun transport réseau, aucune activation de worker/scheduler.
- Tests adversariaux et documentation complète.
- PR en brouillon, ouverte, jamais fusionnée.
