# PAPI PROCUREMENT PLANNER 1.61

Indicative replenishment proposals from supplied product and supplier snapshots.

- Flags active products at/below reorder threshold.
- Suggests quantity to reach target stock, respecting minimum order quantity.
- Estimates XOF cost and lead time; ranks within configured budget.
- Excludes inactive products and suppliers not marked approved.

Safety: budget defaults to 0 XOF and is advisory only. No purchase orders, supplier contact, payment, stock mutation, external calls or integrations. Every proposal remains `awaiting_human_approval`. Supplier status, prices, stock and lead times are not independently authenticated. Personal contact fields are rejected.
