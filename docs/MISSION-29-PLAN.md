# Mission 29 — PAPI AGENT SUPERVISOR

## Scope
Operational monitoring, explainable performance evaluation, internal alerts and human escalation. The module observes workers; it does not activate, pause, disable or grant permissions.

## Five-day delivery
1. Architecture and governance boundaries.
2. Heartbeat collection and health register.
3. Explainable scoring and historical evaluation.
4. Internal alerts, manager routing and human acknowledgement.
5. SQL tests, least privilege, rollback safeguards and documentation.

## Score methodology
Reliability 50%, terminal-outcome coverage 30%, timeliness 20% using a 60-minute reference. Operational proxy only; no customer satisfaction or revenue inference. Empty samples are neutral (100) and explicitly marked sample_size=0.

## Governance
Service-role RPCs only. Evaluator must differ from target worker. Alerts recommend review/coaching; human actors acknowledge or resolve. No worker status, identity, hierarchy or permission changes. No production migration, deployment or external action.
