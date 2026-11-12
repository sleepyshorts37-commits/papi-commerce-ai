# PAPI CUSTOMER SERVICE 1.36

## Scope
Read-only intake and triage of anonymized customer-service ticket summaries. Classifies urgency/status, flags stale active tickets, and prepares generic response drafts for human review.

## Accepted data
Opaque ticket ID, business line, channel, ISO-8601 timestamps with timezone, status, category, priority, optional opaque order reference, and a short redacted summary (maximum 500 characters). Unknown fields are rejected. Do not send names, phone numbers, email addresses, physical addresses, account credentials, payment codes, or raw chat transcripts.

## Human review
Every active ticket is marked for human review. Drafts are generic and must be checked against verified order data and current business policies before use. The module does not validate customer claims, payments, delivery events, refund eligibility, or commercial promises.

## Safety boundaries
No message sending, customer lookup, account access, refunds, cancellations, order changes, external API calls, or spending. No autonomous customer-facing action is enabled.
