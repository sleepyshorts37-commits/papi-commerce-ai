# PAPI ORDER MANAGEMENT 1.35

## Scope
Read-only intake and analysis of explicitly supplied order snapshots. The module validates basic lifecycle fields, summarizes statuses, and flags orders whose expected delivery time has passed or whose update is stale.

## Accepted fields
Opaque `order_id`, `business_line`, `channel`, ISO-8601 timestamps with timezone, lifecycle `status`, optional expected/delivered timestamps, optional `payment_evidence_status`, optional XOF order amount, and item SKU/quantity pairs. Unknown fields are rejected, including customer names, phone numbers, email addresses and delivery addresses.

## Important interpretation
- `total_xof` is a declared order value, not recognized revenue.
- `payment_evidence_status=provider_confirmed` is still caller-supplied metadata; the module does not authenticate a payment provider.
- An overdue flag is a time-based signal, not proof of failed delivery.
- A stale flag means the supplied snapshot has not been updated within the configured threshold.

## Safety boundaries
No order creation, mutation, cancellation, refund, customer contact, delivery dispatch, payment processing, external API request, or spending. Inputs are not independently verified. The dashboard reports analysis only.
