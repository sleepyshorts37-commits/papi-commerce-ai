# PAPI MARKET OPPORTUNITY SCANNER — Phase 1.27

## Scope
This phase adds a deterministic intake and triage pipeline for opportunity signals explicitly supplied to PAPI COMMAND CENTER. It is not a live market crawler and does not independently discover demand.

## Accepted signal fields
Required: source, source_ref, observed_at (ISO 8601 with timezone), business_line, market, customer_segment and offer.

Optional enrichment: problem_observed, proposed_solution, contact_channel, expected_price_xof, variable_cost_xof, acquisition_cost_xof, fulfillment_cost_xof, estimated_monthly_volume, time_to_first_revenue_days and upfront_cost_xof.

The scanner rejects unknown fields, malformed numbers, future timestamps and obvious sensitive-data markers. It fingerprints source + reference + business line + market + offer to suppress duplicates. Freshness is configurable from 1 to 365 days. A deterministic triage score combines completeness (70%) and freshness (30%).

## Triage outcomes
- `ready_for_business_analysis`: minimum enrichment fields present; forwarded to the phase 1.26 analysis engine.
- `needs_enrichment`: required commercial details remain unknown.
- `stale`: signal is older than the configured freshness window.
- Rejected: malformed, future-dated, unknown-field or sensitive-looking input.

The phase 1.26 engine still requires all financial inputs and evidence before it can recommend a small test. Unknown values remain unknown.

## Command Center
`build_command_center` accepts an optional `opportunity_signals` list. When omitted, it processes an empty list. Ready signals are converted into candidates for phase 1.26; no records are persisted.

## Safety and limitations
- No web scraping, network requests, live market research or platform access.
- No customer personal data collection, prospect contact or outbound messages.
- No spending, purchasing, paid APIs, task creation or execution.
- Source references are user-provided and not independently verified.
- Scores are triage aids, not proof of demand or profitability.
- Budget remains 0 XOF; external and financial actions remain disabled.

## Verification
Tests are added in `tests/test_opportunity_scanner.py`, but have not been executed in this environment. CI must be checked on the PR. This code proposal does not deploy agents, activate workers or apply migrations.
