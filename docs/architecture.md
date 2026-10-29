# System Architecture: Sustainable Reverse Logistics

## 1. Architectural Style
The system is built as a **Modular Monolith** using **Python 3.10+**, **FastAPI**, **SQLAlchemy 2.0 (async)**, and **Streamlit**.

### Why Modular Monolith?
- **Transactional Consistency (ACID):** Post-consumer reverse logistics requires coordinated, atomic state changes across physical inventory, custody transfers, financial ledgers, and authorization decisions.
- **Strict Separation of Concerns:** Application domain logic (NRV calculator, policy matching, sanitization gate, state machines) resides in isolated domain modules, completely decoupled from HTTP transport and presentation layers.
- **Direct Future Extensibility:** The service layer provides a unified interface for both internal manual intake and future automated ecommerce webhooks.

## 2. Decoupled Multi-Tier Topology

```
+-----------------------------------------------------------+
|                   Streamlit Frontend                      |
| (Role-Specific Portals: Admin, Agent, Ops, Approver, CPA) |
+-----------------------------+-----------------------------+
                              | HTTP REST / JSON (Bearer JWT)
                              v
+-----------------------------------------------------------+
|                   FastAPI API Gateway                     |
|  (CORS, OpenTelemetry, Token Bucket Limiting, OpenAPI)    |
+-----------------------------+-----------------------------+
                              | Dependency Injection
                              v
+-----------------------------------------------------------+
|                Domain & Application Services              |
| - NRV & Economic Engine (Decimal arithmetic)              |
| - Pre-Authorization Policy Engine (Path A)                |
| - 6-Dimensional State Machine Validators                  |
| - Device Data Sanitization Gate (NIST 800-88 Purge Gate)  |
| - 5-Day SLA Non-Response Background Worker                |
+-----------------------------+-----------------------------+
                              | SQLAlchemy 2.0 Async ORM
                              v
+-----------------------------------------------------------+
|                PostgreSQL / SQLite Database               |
|  (Persistent Source of Truth, Row Locks, Audit Trail)     |
+-----------------------------------------------------------+
```

## 3. The 6-Dimensional State Model
Rather than a single status column, the entity lifecycle is divided into 6 orthogonal dimensions:
1. **Return Case Status:** `RETURN_REQUESTED`, `PICKUP_ASSIGNED`, `PICKED_UP`, `IN_TRANSIT`, `WAREHOUSE_RECEIVED`, `INSPECTION_IN_PROGRESS`, `ASSESSED`, `RECOVERY_IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `ON_HOLD`.
2. **Recovery Classification:** `REPAIR`, `REFURBISHMENT`, `RESALE_AS_NEW_ELIGIBLE`, `RETURN_TO_MANUFACTURER`, `RECYCLING`, `ON_HOLD`.
3. **Manufacturer Approval Status:** `NOT_REQUIRED_POLICY_AUTHORIZED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `OVERDUE`, `ESCALATED`.
4. **Physical Custody Location:** `WITH_RETURN_AGENT`, `IN_TRANSIT`, `WAREHOUSE`, `INSPECTION_FACILITY`, `REPAIR_FACILITY`, `WITH_CARRIER`, `DELIVERED_TO_MANUFACTURER`.
5. **Sanitization Status:** `NOT_STARTED`, `IN_PROGRESS`, `PASSED`, `FAILED`, `EXCEPTION_REVIEW`.
6. **Customer Refund Status:** `NOT_APPLICABLE`, `PENDING`, `INITIATED`, `PROCESSING`, `COMPLETED`, `FAILED`.
