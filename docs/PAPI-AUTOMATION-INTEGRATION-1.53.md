# PAPI AUTOMATION INTEGRATION 1.53

## Purpose
Connects the existing Sales Engine and Client Manager output snapshots to the
read-only automation planner.

## Contracts checked
- Sales Engine: reads `records[].prospect_id`, `status` and
  `next_follow_up_at`.
- Client Manager: reads `cases.open_case_ids[]`.
- Produces internal follow-up and unresolved-case review tasks.

## Important compatibility finding
The planner's initial input naming did not exactly match the existing module
outputs. This adapter explicitly translates the real output field names rather
than assuming they are interchangeable.

## Safety
- Consumes already-computed in-memory snapshots only.
- No database connection, network access, messaging, client contact, scheduler,
  reminders, publication, purchase, payment or financial operation.
- Execution remains disabled and tasks require human approval.
- Budget: 0 XOF.
- Input snapshots must remain sanitized and pseudonymized.

## Validation
Five unit tests are included for the cross-module contracts. They have not been
executed in this pull request.
