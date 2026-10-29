# Business Rules & NRV Calculation Specification

## 1. Net Recovery Value (NRV) Formulas

All calculations are executed in Python `decimal.Decimal` with 2 decimal places and `ROUND_HALF_UP` quantization.

### 1.1 Repair & Resale
$$\text{NRV}_{\text{repair}} = \text{Resale Value} - (\text{Repair Parts} + \text{Repair Labour} + \text{Packaging} + \text{Transportation} + \text{Sanitization})$$

### 1.2 Refurbishment & Resale
$$\text{NRV}_{\text{refurb}} = \text{Resale Value} - (\text{Refurb Parts} + \text{Refurb Labour} + \text{Packaging} + \text{Transportation} + \text{Sanitization})$$

### 1.3 Resale As New (Guarded by Contract & Condition)
$$\text{NRV}_{\text{as\_new}} = \text{Resale Value} - (\text{Packaging} + \text{Transportation} + \text{Sanitization})$$
*Rule:* Permitted only if the product is verified as having zero cosmetic or functional defects, pristine packaging, and the manufacturer agreement explicitly authorizes open-box resale.

### 1.4 Manufacturer Return
$$\text{Financial Value}_{\text{mfg\_return}} = \text{Applicable Return Credit} - \text{Remaining Shipping to Manufacturer}$$
*Rule:* Sunk costs (e.g. initial customer pickup) are tracked separately and not counted against remaining forward decisions. If no contractual return credit exists, credit is \$0.00.

### 1.5 Recycling & Disposition
$$\text{NRV}_{\text{recycle}} = \text{Materials Scrap Value} - (\text{Processing Fee} + \text{Transportation to Recycler})$$

### 1.6 Transportation Cost Rule
A single flat estimated transportation fee (configurable in `Settings.AVERAGE_TRANSPORTATION_COST`) incorporates expected fuel and electricity costs. Separate fuel surcharges are strictly prohibited to prevent double-counting.

---

## 2. Safety Hazard Blocker
If `has_safety_hazard == True` (e.g., swollen lithium battery, electrical short, cracked CRT), standard resale and repair options are immediately marked ineligible by the decision engine. Only certified safe recycling or hazardous transport is authorized.

---

## 3. Five-Day SLA Non-Response Rule
1. Clock begins when an assessment report is finalized and published (`deadline_at = now + 120 hours`).
2. Reminders:
   - At 48 hours: 1st Friendly Reminder dispatched.
   - At 96 hours: 2nd Urgent Reminder dispatched.
3. At 120 hours (5 calendar/business days):
   - If partner contract flag `auto_return_on_timeout_authorized == True`: Item transitions to `OVERDUE` and initiates automatic return to manufacturer.
   - If partner contract flag is `False`: Item transitions to `ESCALATED` and remains `ON_HOLD`. Silence is never interpreted as consent to repair, refurbish, or sell.
4. Idempotency: Repeating worker executions will not send duplicate notifications or create duplicate work orders.

---

## 4. Device Data Sanitization Gate
1. Complies with NIST SP 800-88 Rev. 1 (Clear, Purge, Destroy, or Cryptographic Erase).
2. Devices storing personal customer data cannot be released for secondary market or outlet resale without a verified `PASSED` sanitization certificate.
3. Factory resets are strictly prohibited as proof of data sanitization.
4. If sanitization fails or media is unreadable, the product is placed on secure hold for physical degaussing or destruction.
