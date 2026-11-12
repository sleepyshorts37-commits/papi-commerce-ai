# PAPI AUTONOMOUS BUSINESS INTELLIGENCE — Phase 1.26

## Objective
Provide Astou with a deterministic, auditable first-pass analysis of manually supplied business-opportunity candidates across PAPI MARKET, DROPSHIPPING, AFFILIATION, FREELANCE, SERVICES and BUSINESS PARTNERS.

## Inputs
Each candidate carries a unique ID, source and source reference, observation timestamp with timezone, business line, market, customer segment, offer, estimated price and cost components, estimated monthly volume, time to first revenue, upfront cost, evidence references and explicit risk flags. Missing numeric data remains unknown; evidence is recorded as supplied and is not independently verified.

## Analysis
- Computes unit contribution after supplied variable, acquisition and fulfillment costs.
- Computes break-even units and conservative/base/upside monthly contribution scenarios only when the necessary inputs exist.
- Applies transparent risk points to compliance, platform dependency, fulfillment, refunds, supplier reliability, data gaps, upfront cost and legal/regulatory concerns.
- Returns one of: `small_test_candidate`, `investigate`, `reject`, or `insufficient_data`.
- Generates proposal-only milestones for review by Astou, Marietou Diouf and the owner.

All projections are hypothetical contribution estimates, not realized sales, profit guarantees or verified revenue. Fixed costs and taxes are excluded unless separately supplied (not modeled in this phase).

## Safety boundaries
- Reads manually supplied candidates only; no live market scan or external research is performed.
- Requires budget to remain 0 XOF; execution and external actions must remain disabled.
- Does not send messages, contact prospects, buy products, subscribe, spend, create tasks, execute plans or recognize revenue.
- No financial, legal or public-facing action is authorized.
- Command Center integration is read-only and currently receives an empty candidate list until an approved data source is designed.

## Verification status
Tests are added in `tests/test_business_intelligence.py` but have not been executed in this environment. CI status must be checked on the pull request. This PR is a code proposal only; it does not deploy agents, activate workers or apply infrastructure migrations.
