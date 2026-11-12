# PAPI ORDER MANAGER 1.59

## Purpose
A read-only, privacy-minimized order lifecycle tracker for PAPI MARKET, PAPI DROPSHIPPING and other commercial units.

## Lifecycle
`draft → confirmed → preparing → ready → dispatched → delivered → returned`

Cancellation is allowed from draft, confirmed, preparing or ready. Skipped transitions and transitions out of terminal states are rejected.

## Data contract
Each order uses an internal `order_id`, pseudonymous `client_ref`, `business_unit`, short `order_summary`, current status, ISO-8601 timestamps and a complete status history. An optional `related_quote_id` can reference a quote in the upstream sales workflow. Direct contact details, addresses, payment credentials and other personal data are not accepted.

## Outputs
- Counts by status and rejected records.
- Active order queue.
- Dispatches unchanged for at least 48 hours, for manual review.
- Validated order snapshots.

## Safety boundaries
This module does not create supplier orders, dispatch couriers, message clients, process payments/refunds, access external systems or spend money. Budget: 0 XOF. Human review remains required. It tracks declared snapshots; it does not independently verify delivery.
