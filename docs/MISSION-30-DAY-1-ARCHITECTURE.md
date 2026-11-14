# Day 1 — Architecture and governance

Reviewed Mission 28 worker assignments and Mission 29 supervisor alerts. Mission 30 adds an incident layer without changing worker identities, permissions, status or hierarchy.

Defined categories, severity levels, target windows and a finite lifecycle. Human identities are stored separately from worker identities. Every decision is associated with an actor and recorded in an append-only event stream plus the existing audit journal.

The service-role boundary is not proof of a human identity by itself: the trusted backend must authenticate and authorize the human before calling mutation RPCs.
