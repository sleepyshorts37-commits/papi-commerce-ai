# PAPI AFFILIATE & PARTNERS 1.38

## Scope
Read-only intake of anonymized partner referral and attributed-sale snapshots. Summarizes referral conversion and calculates provisional commission estimates only for sales marked paid with payment evidence labeled `provider_confirmed`.

## Accepted data
Opaque partner/referral/sale identifiers, business line, channel, timezone-aware timestamps, referral/sale statuses, order value in XOF and commission rate in basis points (0–10,000). Unknown fields are rejected. Do not submit partner names, phone numbers, email addresses, payment account details, customer identities or message contents.

## Financial interpretation
A commission estimate is shown only when the caller marks a sale paid and its evidence `provider_confirmed`. That label is caller-supplied and is not independently authenticated. Estimates are provisional analytical figures, not proof of a payable debt, contractual entitlement or accounting recognition. Unverified and pending sales produce no commission estimate.

## Safety
No partner outreach, contact management, contract changes, purchase, payment, payout, transfer, withdrawal, external API call or spending. No commissions are disbursed. All records are supplied snapshots and are not independently reconciled with payment providers.
