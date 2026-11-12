# PAPI COMPETITOR INTELLIGENCE — Phase 1.28

## Purpose
Compare competitor offers and prices using structured observations supplied by the owner or an authorized researcher. This is an evidence-processing module, not an autonomous crawler.

## Required observation fields
- Competitor name
- Market
- Offer or service being compared
- Source type: official public page, public catalog, public advertisement, public social post, or user observation
- HTTPS source URL
- Observation timestamp with timezone
- Price explicitly denominated in XOF, or null if unknown

Optional currency and notes are accepted. Non-XOF prices are rejected in this phase to avoid unsafe currency comparisons.

## Outputs
- Freshness based on observation age and configurable window
- Source-quality tier and conservative confidence label
- Explicit price difference and percentage against an optional own price
- Rejection reasons for malformed or unsupported observations
- Duplicate suppression for identical competitor/market/offer/source/timestamp records

A competitor's price being higher or lower does not prove that its offer is equivalent. Scope, quality, taxes, delivery, contract duration and promotions may differ. The engine does not infer these facts.

## Command Center
The optional `competitor_observations` argument feeds the read-only `competitor_intelligence` dashboard section. With no supplied observations, the section reports no valid observations.

## Safety and limitations
- The module does not fetch, visit or verify URLs.
- No scraping, network requests, account access or automated monitoring.
- No private competitor data, credentials or personal customer information should be supplied.
- No competitor is contacted; no messages, purchases, spending, tasks or business actions occur.
- All source claims remain unverified until independently checked by a human.
- No pricing recommendation or automatic repricing is performed.

## Verification
Tests are included in `tests/test_competitor_intelligence.py`, but have not been executed in this environment. CI status must be checked on the PR. This code proposal does not deploy agents, activate workers or apply migrations.
