# Database Design & Schema Specification

## 1. Storage Standards
- **Monetary Precision:** All monetary amounts (`expected_resale_value`, `parts_cost`, `labour_cost`, `packaging_cost`, `transportation_cost`, `sanitization_cost`, `refund_amount`) use PostgreSQL `NUMERIC(12, 2)` and Python `decimal.Decimal` with 2 decimal places to guarantee zero float drift.
- **Primary Keys:** UUID version 4 keys (`GUID` abstraction for PostgreSQL native UUID or CHAR(36) in SQLite).
- **Audit Columns:** Every model inherits `created_at` and `updated_at` timestamps in UTC (`TIMESTAMPTZ`).
- **Append-Only History:** Historical tracking events (`custody_events`), audit logs (`audit_events`), and assessment reports (`assessment_reports`) are immutable.

## 2. Table Summary

| Table Name | Primary Role | Key Foreign Keys |
| :--- | :--- | :--- |
| `organizations` | Multi-tenancy tenant entity | None |
| `users` | Authenticated operators and approvers | `organization_id` |
| `facilities` | Logistics hubs, warehouses, depots | `organization_id` |
| `return_requests` | Return intake master case | `created_by_user_id` |
| `return_items` | Individual equipment units | `return_request_id`, `manufacturer_org_id` |
| `pickup_assignments` | Return Agent field collection tasks | `return_item_id`, `agent_user_id` |
| `custody_events` | Immutable custody transfer audit | `return_item_id`, `actor_user_id` |
| `warehouse_receipts` | Warehouse scan intake & bin record | `return_item_id`, `facility_id` |
| `inspections` | Detailed technical condition test | `return_item_id`, `inspector_user_id` |
| `recovery_estimates` | Financial inputs & calculated NRV | `inspection_id` |
| `assessment_reports` | Versioned assessment snapshot & SLA | `return_item_id` |
| `partner_contracts` | Manufacturer contractual SLA terms | `manufacturer_org_id` |
| `authorization_policies`| Pre-authorization rules (Path A) | `manufacturer_org_id` |
| `approval_requests` | Grouped manufacturer approval request | `manufacturer_org_id` |
| `approval_request_items`| Individual item link in approval batch | `approval_request_id`, `return_item_id` |
| `authorization_decisions`| Atomic authorization record | `approval_request_item_id`, `decided_by_user_id` |
| `sanitization_records` | NIST 800-88 data erasure log | `return_item_id`, `technician_user_id` |
| `recovery_work_orders` | Execution tracking for repair/refurb | `return_item_id`, `facility_id` |
| `quality_checks` | Post-work QA diagnostics | `work_order_id`, `inspector_user_id` |
| `release_authorizations`| Final resale / disposition release | `return_item_id`, `verified_sanitization_id` |
| `refund_records` | Accounting customer refund ledger | `return_request_id` |
| `audit_events` | Immutable system audit log | `actor_user_id` |
