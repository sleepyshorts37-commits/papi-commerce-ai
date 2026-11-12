# External audit checkpoint anchor — implementation contract

## Status and scope

Design only. This document defines the contract required before connecting an external service. It does not select a provider, create credentials, publish records, or claim that the current local journal is externally protected.

The local SHA-256 journal remains tamper-evident, not tamper-proof against an attacker able to rewrite the complete file. External anchoring is a release gate for deployments that require resistance to privileged local-file tampering.

## Security objectives

1. Detect local rollback or rewrite of any prefix that has already been externally anchored.
2. Prevent two publishers from silently replacing the same checkpoint with conflicting successors.
3. Make retries safe after timeouts and uncertain network outcomes.
4. Keep external credentials and signing keys outside the worker process and its filesystem.
5. Make checkpoint verification possible independently of the worker.

## Checkpoint record

The signed payload must use a versioned canonical serialization and contain at least:

- `record_schema_version`
- `journal_id`: stable, non-secret identifier for this journal
- `checkpoint`: the exact local checkpoint fields `schema_version`, `sequence`, and `head_hash`
- `previous_record_digest`: digest of the exact previously accepted signed record, or a fixed genesis value
- `publisher_key_id`
- `created_at`: UTC timestamp for operations and diagnostics, not ordering authority

The signature covers every field above except the signature field itself. The record digest is calculated over the canonical signed record. Reject unknown schema versions, malformed hashes, invalid signatures, unexpected journal IDs, and non-canonical encodings. Do not include job payloads, customer data, credentials, lease tokens, or event contents.

The signature algorithm and canonical serialization must be selected and pinned in implementation; do not accept algorithm negotiation from an untrusted record.

## Required external store semantics

The store must provide two logically separate capabilities:

1. **Immutable record insertion** keyed by `record_digest`. Re-inserting the identical record is idempotent; attempting to associate different bytes with the same key is rejected.
2. **Atomic latest-pointer compare-and-swap (CAS)** scoped to `journal_id`. The update succeeds only when the stored latest record digest exactly equals the caller's expected previous digest. The new pointer may reference only an already inserted, authenticated record.

The store must enforce append-only retention for accepted records, monotonic checkpoint sequence, and a single successor for each previous record. A plain mutable object/file or a database row writable by the worker is not sufficient.

A successful CAS is the publication commit point. If a request times out, the publisher must read the latest pointer and immutable record before retrying; it must not assume the operation failed or succeeded.

## Trusted publisher protocol

The publisher is a separate, narrowly permissioned component. It is not the job worker and does not expose its signing key to agents or handlers.

For each publication:

1. Retrieve and authenticate the current external latest record.
2. Read and fully verify the local journal using the existing audit reader.
3. If an external checkpoint exists, call `verify_checkpoint(local_journal, previous.checkpoint)`. Publication must stop if the local journal does not contain that exact previously anchored prefix.
4. Build the candidate checkpoint from the verified local journal.
5. Require the candidate sequence to be strictly greater than the previous sequence. A no-op publication is an idempotent success only if it is the exact same record; conflicting same-sequence hashes are rejected.
6. Construct a signed record whose `previous_record_digest` equals the exact current external record digest.
7. Insert the immutable record, then CAS the latest pointer from the expected previous digest to the new record digest.
8. On CAS conflict, reload and restart verification from step 1. Never overwrite or force the pointer.
9. After publication, independently read back the latest record and verify its signature, digest, journal ID, sequence, and head hash.

For the first publication, the expected predecessor is the configured genesis value and the checkpoint must be derived from the verified journal beginning at sequence zero.

The trusted publisher's local-prefix check is essential: a larger sequence number alone does not prove that a new checkpoint extends the previous checkpoint. The publisher must prove extension by verifying that the current local journal still contains the prior checkpoint's exact prefix before deriving the new head.

## Verification and recovery

A verifier that does not trust the worker must obtain the signed latest record directly from the external store, validate the signature and record chain, then compare its checkpoint against the local journal with `verify_checkpoint`.

- A local sequence shorter than the external sequence is a rollback or incomplete restore: raise an incident; do not silently reset the external pointer.
- A different hash at the anchored sequence is an integrity incident.
- A local suffix after the anchored sequence is unanchored and must be reported as such.
- A missing external record, invalid signature, broken predecessor link, or unavailable store is not equivalent to a clean verification.
- Recovery must preserve the external history and create a new journal identity only through an explicit, reviewed procedure. Never overwrite an anchor to accommodate a restored or divergent local journal.

## Key and permission separation

- Signing keys belong in a managed KMS/HSM or equivalent independently controlled secret boundary.
- The worker receives no signing key and no permission to update the external latest pointer.
- The publisher identity may append records and perform CAS only for its assigned journal; it cannot delete records or alter retention.
- Read-only verifiers use separate credentials.
- Key rotation must retain verification of historical signatures and record the key ID used for each record.
- No secrets belong in source control, logs, test fixtures, agent prompts, or worker environment dumps.

## Failure policy and operations

- Before a deployment is approved, define an explicit maximum anchoring lag and alert threshold.
- If anchoring is required by policy and the external store is unavailable, the system must report the journal as not currently anchored. Do not claim high-assurance audit status.
- Do not block or reverse already committed business outcomes merely because a later checkpoint publication failed; instead raise a durable operational alert and apply the configured release/operations policy.
- Monitor last successful anchor time, anchored sequence, unanchored suffix length, CAS conflicts, signature failures, and store availability.
- Retain independent backups and test restoration without rewriting external history.

## Contract test matrix

A provider adapter is not acceptable until tests demonstrate:

- first publication from genesis;
- valid forward publication after proving the old checkpoint is a local prefix;
- rejection of local rollback and rewritten anchored prefixes;
- rejection of same-sequence conflicting hashes and sequence regression;
- CAS conflict under two concurrent publishers, with only one accepted successor;
- immutable-record idempotency on retry;
- timeout-after-commit recovery by reading the latest pointer;
- rejection of invalid signatures, altered payloads, unknown key IDs, wrong journal IDs, and broken predecessor links;
- rejection of deletion or mutation attempts against accepted records;
- read-only verifier operation without publisher credentials;
- key rotation while preserving historical verification;
- external-store outage and recovery without silently claiming successful anchoring.

Use a deterministic in-memory fake only for contract tests. Such tests validate adapter behavior; they do not establish real external durability, independent administration, or production security.

## Release gate

Do not describe external anchoring as implemented until a real independently administered store, signing-key boundary, least-privilege identities, immutable retention, atomic CAS, independent verifier, monitoring, recovery procedure, and provider-specific integration tests have all been reviewed and exercised.

Until then:
- local SHA-256 chain: implemented;
- local checkpoint export/verification: implemented;
- external anchor contract: specified by this document;
- real external publication and independent verification: not implemented;
- production audit assurance: not approved.
