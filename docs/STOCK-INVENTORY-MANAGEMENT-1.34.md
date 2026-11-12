# PAPI STOCK & INVENTORY MANAGEMENT 1.34

Read-only stock projection from supplied opening balances and movement records. Supported movements: receipt, sale, return, adjustment_in, adjustment_out, reserve and release. Quantities are positive integers; timestamps require ISO 8601 timezone. Movement IDs are unique.

The engine calculates physical stock, reservations and available stock. Outbound movements cannot create negative stock; reservations cannot exceed physical stock. Invalid movements are rejected and reported.

Optional reorder points and target stock levels generate replenishment alerts and suggested quantities. These are planning signals only. No purchase order, supplier contact, sale fulfillment, stock mutation, external request or spending is performed.

Limitations: supplied records are not independently verified; stock is aggregated per SKU across locations rather than tracked at bin/location level. No expiry, batch/lot, serial-number or valuation accounting is included.
