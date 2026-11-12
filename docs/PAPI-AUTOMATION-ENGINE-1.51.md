# PAPI AUTOMATION ENGINE 1.51

## Purpose
Builds a local, read-only plan for repetitive commercial operations from
sanitized snapshots. It proposes internal work; it does not execute it.

## Supported proposals
- Daily prospect qualification review.
- Overdue follow-up review based on `next_followup_at`.
- Review of unresolved client cases.
- Optional weekly aggregate commercial report.

## Safety and limits
- Budget: 0 XOF.
- `execution_enabled` is always false.
- Every task is `awaiting_approval` and requires human approval.
- No email, WhatsApp, social message, client contact, reminder delivery,
  external API, scheduler worker, purchase, payment, or financial action.
- Supply pseudonymized references only; do not include names, phone numbers,
  email addresses, social handles, or sensitive free text.
- A proposed task is not authorization to execute it.
- Payment figures in supplied snapshots must be independently verified.

## Integration
The caller supplies sanitized prospect and client-case snapshots from existing
PAPI modules. This version does not import or invoke those modules, so it remains
loosely coupled and safe to test independently.

## Validation
Unit tests are included in `tests/test_automation_engine.py`. They have not
been executed as part of creating this pull request.
