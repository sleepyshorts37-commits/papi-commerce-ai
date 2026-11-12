# PAPI AUTOMATION COORDINATION 1.52

## Purpose
Consolidates task proposals from multiple PAPI departments into one internal
queue, removes duplicate proposals within a department, and identifies
prerequisites that remain incomplete.

## Behavior
- Generates deterministic task IDs from department, task type and pseudonymized reference.
- Removes duplicate task proposals with the same generated ID.
- Keeps tasks from different departments separate.
- Marks tasks `blocked` while declared prerequisite IDs are incomplete.
- Orders blocked tasks first, then by priority.
- Rejects malformed task records.

## Safety
- Read-only planning only; `execution_enabled=false`.
- Every unblocked task remains `awaiting_approval` and requires human approval.
- No external contact, messaging, reminders, scheduling worker, API call,
  publication, purchase, payment or financial action.
- Budget: 0 XOF.
- Use pseudonymized references and sanitized details only.
- This module does not verify that a declared completed prerequisite is truthful;
  the caller must provide trusted completion records.

## Validation
Seven unit tests are included. They have not been executed as part of this PR.
