# PAPI Agent Supervisor contract

## Data sources
Worker assignment terminal states, assignment start/finish timestamps, worker registry and heartbeat timestamps. Evaluations retain source period and sample count.

## Score semantics
Reliability is successful terminal assignments divided by terminal assignments. Completion reports terminal outcomes in the sampled population. Timeliness uses average elapsed runtime against a 60-minute reference. Always display sample size and methodology version.

## Alert semantics
- failure_rate: critical review at 3+ terminal assignments and reliability below 70%.
- low_score: warning at 3+ terminal assignments and overall score below 60.
- stale_heartbeat: warning when an idle/active worker misses its observation window.

## Human control
Alerts are recommendations. Human acknowledgement and resolution are auditable. A separate approved workflow is required for pause, disablement or permission changes.

## Access
All supervisor tables deny public/anon/authenticated access. RPC execution is granted only to service_role.
