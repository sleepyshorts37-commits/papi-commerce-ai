# PAPI KIDS server stack

This is a deployment template only. It has not been deployed and does not create a Cloudflare, Supabase or hosting account.

## Required server configuration

1. Copy \`.env.example\` to \`.env\` in this directory.
2. Use a dedicated PostgreSQL/Supabase database with migrations 013–024 applied.
3. Use a TLS PostgreSQL URL with \`sslmode=require\`.
4. Generate two different random secrets of at least 32 characters for upload and review.
5. Set a private persistent Docker volume; never expose \`/data/private\` over HTTP.
6. Set \`PAPI_KIDS_REVIEWER_ID\` to the accountable human reviewer.
7. Keep \`PAPI_KIDS_WORKER_ENABLED=false\` until the database, storage volume and backups are verified.

## Start the API

From this directory:

\`\`\`sh
docker compose up -d --build papi-kids-api
\`\`\`

Put the API behind an HTTPS reverse proxy. The Compose file exposes port 8000 only to the internal Docker network.

## Start the editorial worker

Only after confirming the private volume is shared with the API and the database schema is current:

\`\`\`sh
docker compose --profile worker up -d papi-kids-worker
\`\`\`

The worker processes structural editorial analysis only. Image/LLM generation remains separately disabled and requires the free-quota evidence and zero-spend authorization gate.

## Security and operations

- Upload and review secrets are separate and server-only.
- The API and worker run as a non-root user, read-only filesystem, dropped Linux capabilities and no-new-privileges.
- Persistent private assets use a named Docker volume.
- Configure encrypted off-host backups for the volume and database.
- Configure reverse-proxy rate limits, TLS renewal, monitoring and alerting before production.
- \`/healthz\` is a liveness endpoint, not a database readiness check.
- Do not publish or merge deployment changes without review and explicit authorization.

## Manual encrypted database backup

A separate one-shot runner is available under the Compose `backup` profile. It is disabled by default. Configure `PAPI_KIDS_BACKUP_ENABLED=true`, a private 0700 backup volume, `PAPI_KIDS_BACKUP_KEY_B64` (32 random bytes, Base64), and a key ID only on the server. Build and run manually with `docker compose --profile backup run --rm papi-kids-backup`. The runner uses TLS PostgreSQL, encrypts the pg_dump archive with AES-256-GCM, removes its plaintext staging file, and prints only non-sensitive file names. No schedule or offsite transfer is configured; copy encrypted artifacts to a separately secured offsite destination and verify the manifest.

## Optional offsite copy

A separate `offsite` Compose profile copies only encrypted `.pgdump.aesgcm` files and their JSON manifests using rclone, then runs a checksum verification. On success, it writes a private `offsite-verification.json` evidence report bound to each encrypted file's SHA-256, remote alias and verification timestamp; the health inventory accepts only matching evidence. It uses `rclone copy`, never `sync`, so it does not delete remote files. Keep the rclone configuration outside the repository. Mount it read-only and grant only the backup container's dedicated UID/GID 10001 access (for example, host group 10001 and mode 0640; no access for other users), through `PAPI_KIDS_RCLONE_CONFIG_FILE`. Set `PAPI_KIDS_OFFSITE_ENABLED=true` and a remote such as `drive:papi-kids-backups` only after configuring and testing that remote. Run manually with `docker compose --profile offsite run --rm papi-kids-offsite`. This is not scheduled automatically.

## Optional systemd schedules

Templates for a daily encrypted backup (02:00 UTC) and offsite copy/check (03:00 UTC) are in `systemd/`. They are not installed or enabled automatically. Edit the deployment path in both service units, copy the four unit files to `/etc/systemd/system`, run `systemctl daemon-reload`, test the manual Compose commands first, and only then enable the timers if desired. The backup/offsite environment flags remain independent fail-closed gates.

## Manuscript child-safety review

The editorial worker stores deterministic safety flags with the manuscript analysis. A separate `PAPI_KIDS_SAFETY_REVIEW_TOKEN` protects `POST /api/papi-kids/manuscripts/{upload_id}/safety-review`; the reviewer identity comes from server-side `PAPI_KIDS_REVIEWER_ID`. The decision is persisted in the private PostgreSQL audit table and in the book metadata, bound to the exact source SHA-256. Approving a flagged manuscript requires resolution notes. A changed manuscript invalidates the previous attestation. Do not reuse the illustration-review token.

## iPhone dashboard

The WSGI app serves the mobile dashboard at `/dashboard` (and `/`) over HTTPS. The page is generated server-side from non-secret settings `PAPI_KIDS_DASHBOARD_BOOK_ID`, `PAPI_KIDS_DASHBOARD_TITLE`, and `PAPI_KIDS_DASHBOARD_PAGE_COUNT`. It includes manuscript intake, status, illustration review, child-safety review, and library workflows. API actions remain protected by separate server-side tokens. Configure the reverse proxy to forward the HTTPS scheme correctly; plain HTTP dashboard requests are rejected.

## KDP listing metadata drafts

`POST /api/papi-kids/manuscripts/{upload_id}/kdp-metadata` saves a versioned listing draft in PostgreSQL. Use the separate server-side `PAPI_KIDS_METADATA_TOKEN`; the editor identity comes from `PAPI_KIDS_METADATA_EDITOR_ID`. Incomplete drafts are accepted and returned with explicit blockers so the owner can complete them later. Each version is append-only, SHA-256 tracked, and does not enable KDP upload or publication.

## Explicit KDP package build

The iPhone dashboard exposes a build button backed by `POST /api/papi-kids/manuscripts/{upload_id}/build-kdp-package`. It requires a separate `PAPI_KIDS_KDP_BUILD_TOKEN` and `PAPI_KIDS_KDP_BUILD_ENABLED=true`; the default is false. The service reads `kdp-build-config.json` from the manuscript's private storage directory (mode 0600). That server-side JSON profile contains only the interior, cover and optional ebook build arguments; it must never contain credentials. The build runs only after the owner confirms in the dashboard and only creates local files. PDF inspection, Kindle Previewer, release gate and manual KDP submission remain mandatory.

Package builds are recorded in the private PostgreSQL `kdp_package_builds` audit table and exposed in manuscript status. The package manifest hash is stored with each immutable version; a DB persistence failure removes the just-created package directory.

## Runtime readiness diagnostics

`GET /api/papi-kids/readiness` is protected by a separate `PAPI_KIDS_READINESS_TOKEN`. It checks storage permissions, database connectivity, required migrations, configured workflow tokens and provider credential presence. It never returns secret values and does not contact image providers or verify quota. A configured Cloudflare token does not prove a free quota is available.

## Human review of KDP package files

The owner can download the latest private PDF/EPUB using the authenticated `/api/papi-kids/manuscripts/{upload_id}/kdp-package/{interior|cover|ebook}` endpoint and record a hash-bound decision with `/kdp-package-review`. Configure the separate `PAPI_KIDS_KDP_REVIEW_TOKEN`. Reviews require notes and are stored append-only in PostgreSQL. The download service checks the current package hash and refuses path traversal, symlinks and changed files.

## Kindle Previewer attestation

When an EPUB is required, the owner must inspect the exact EPUB hash in Kindle Previewer and submit a separate attestation through `/api/papi-kids/manuscripts/{upload_id}/kindle-previewer-review`. The endpoint uses `PAPI_KIDS_KINDLE_PREVIEWER_TOKEN`, server-side `PAPI_KIDS_REVIEWER_ID`, an evidence SHA-256 and review notes. A new EPUB hash invalidates the previous attestation.

## Owner final release authorization

Configure `PAPI_KIDS_OWNER_RELEASE_TOKEN` and `PAPI_KIDS_RELEASE_OWNER_ID` on the server. The iPhone dashboard then permits an explicit, phrase-bound owner confirmation for the latest package. The server rechecks all current PDF/EPUB approvals, Kindle Previewer evidence when an EPUB exists, child-safety approval, commercial-use rights, listing metadata and zero-spend policy before persisting the authorization. This authorizes manual KDP submission only; automated upload and publication remain disabled.

## ZIP de soumission manuelle

Après confirmation finale du propriétaire, le tableau de bord iPhone propose un ZIP de soumission manuelle via `GET /api/papi-kids/manuscripts/{upload_id}/kdp-submission-bundle`, protégé par le jeton propriétaire distinct. Le service revalide le hash du manifeste, l'autorisation persistée, les revues et les hashes des fichiers avant de créer le ZIP en mémoire. Le ZIP comprend les PDFs, l'EPUB s'il existe, le manifeste, les métadonnées KDP normalisées, les attestations et les sommes SHA-256. Il n'est pas stocké sur le serveur et n'est jamais envoyé à Amazon.

## Suivi manuel de la soumission KDP

Après téléchargement du ZIP et soumission manuelle par le propriétaire, le tableau de bord peut consigner les étapes via `POST /api/papi-kids/manuscripts/{upload_id}/kdp-submission-status`. Les événements append-only sont liés au package autorisé, au propriétaire et à un SHA-256 de preuve. Les transitions sont contrôlées ; la déclaration de mise en ligne exige un ASIN et une URL Amazon HTTPS concordants. Ces informations sont déclaratives : PAPI KIDS ne consulte pas Amazon et ne vérifie pas indépendamment la disponibilité publique.
