# PAPI INVENTORY & SUPPLIER MANAGER 1.60

Read-only stock snapshot and supplier registry.

## Capabilities
- Validate anonymized supplier, product and stock-movement records.
- Calculate stock balances from chronological incoming, outgoing and adjustment movements.
- Flag active products at/below reorder level and negative balances.
- Count approved, prospective and suspended suppliers.
- Reject duplicate IDs, unknown supplier/product references, future-dated movements and unknown/personal fields.

## Safety boundaries
- Snapshot analysis only; no database, network or external integration.
- No supplier outreach, purchase order, replenishment, payment, inventory mutation or financial action.
- Low-stock flags are recommendations for human review, not authorization to buy.
- Delivery, supplier status and movement references are not independently authenticated.
- Budget: 0 XOF. Human approval required for all external or financial actions.

## Tests
Unit tests cover balances, outgoing movements, low-stock flags, invalid references, personal fields, duplicate IDs, future dates, negative balances and read-only budget. CI must confirm execution.
