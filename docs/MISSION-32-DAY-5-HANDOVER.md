# Day 5 — Handover and limitations

Documented the explicit server-side adapter boundary and the fact that Supabase service_role is privileged. A deployment must authenticate agent requests before constructing sealed principals; never accept a caller-supplied actor string as proof of identity.

Local JSONL remains the default. Remote sync is opt-in through an injected SupabaseStore. The shared-memory reader applies visibility rules in SQL; chat visibility remains filtered by the trusted backend adapter. No remote project, deployment, worker, scheduler or autonomous agent was configured or activated. Final CI must pass on the exact branch head before closure.
