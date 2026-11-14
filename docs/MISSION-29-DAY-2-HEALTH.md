# Day 2 — Health register

Added per-worker heartbeat register with source classification and monotonic last-seen timestamps. Trusted-backend RPC records heartbeats. Stale-worker detection creates deduplicated alerts for idle/active workers and never changes status.
