# PAPI PROCUREMENT & SUPPLIER MANAGEMENT 1.33

Read-only analysis of supplier/product observations explicitly supplied by an authorized user. No live supplier discovery, source-page fetching, supplier contact, purchase order, negotiation, payment or spending is performed.

Required fields: supplier_id, supplier_name, product_key, product_name, market, currency (XOF), unit_price_xof, minimum_order_quantity, observed_at (ISO 8601 with timezone), source_ref (public HTTPS URL).

Landed unit cost is calculated only when unit price, shipping total and allocation units, taxes, packaging and other fees are supplied. Shipping is allocated with ceiling division. Missing components produce an unknown cost, never an assumed zero.

Optional operational evidence includes lead time, stock status, payment terms, completed/on-time orders, inspected/defective units and documented disputes. Rates require supplied valid numerators and denominators. No subjective reliability score is fabricated.

Only current observations with complete landed costs are ranked, within the same product and market, by estimated landed cost then lead time. Source URLs and evidence are not independently authenticated. Stale observations remain visible but are excluded from ranking.

All amounts are non-negative integer XOF. No supplier contact details or personal data are collected. Purchase proposals and purchase orders are not generated in this phase. Procurement decisions remain manual and require owner approval.
