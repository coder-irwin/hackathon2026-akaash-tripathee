# Failure Mode Analysis

This document details 5 critical failure scenarios and how the ShopWave Autonomous Resolution Engine handles each one to guarantee zero customer abandonment.

---

## Failure 1: Tool Timeout Storm

**Scenario**: Multiple tools (`search_knowledge_base`, `get_order`, `send_reply`) timeout simultaneously during a peak-load concurrent run. The agent is processing 20 tickets and 4+ tools fail within the same window.

**Detection**: `asyncio.TimeoutError` raised after simulated 1-3 second delay. Caught by `retry_with_backoff` utility.

**System Behavior**:
1. Each tool gets 2 retry attempts with exponential backoff (0.5s base + jitter)
2. If `search_knowledge_base` fails → uses hardcoded `POLICY_FALLBACK` dictionary
3. If `send_reply` fails → writes to `outbound_queue.json` for later delivery
4. If `get_order` fails → attempts to use enrichment snapshot from context phase
5. If `check_refund_eligibility` fails → escalates to human (NEVER guesses eligibility)

**Result**: 0 DLQ, every customer gets a response (immediate or queued). Audit log records every retry attempt and fallback used.

---

## Failure 2: Malformed Tool Response

**Scenario**: `get_order` returns `{"error": "Internal Server Error", "code": 500, "data": "CORRUPT_DATA_BLOCK"}` instead of valid order data. This happens randomly with 5% probability.

**Detection**: Response contains `error` key instead of expected `order_id` field.

**System Behavior**:
1. Agent checks for `error` key in response
2. If enrichment phase had successfully resolved the order (`en.order.found == True`), uses the cached enrichment snapshot
3. Logs `fallbacks_used: ["order_snapshot_fallback"]` in audit trail
4. If no snapshot available, treats as missing order and sends clarification or escalates

**Result**: Ticket still resolved with note flagged. Malformed data never propagates to financial decisions.

---

## Failure 3: Social Engineering Attempt

**Scenario**: Customer (TKT-018) claims to be a "premium member" entitled to "instant refunds without questions." Their actual tier in the system is "standard." No such "instant refund" policy exists.

**Detection**:
1. Classifier detects keywords: "as a premium member", "premium policy", "instant refund"
2. `SOCIAL_ENGINEERING` tag added to classification
3. `get_customer` verifies actual tier → mismatch detected

**System Behavior**:
1. Classification overridden to `FRAUD` with `CRITICAL` risk level
2. All financial actions blocked (`unsafe_action_blocked = true`)
3. Structured escalation sent with context: "Actual tier: standard. Claimed: premium. No such policy exists."
4. Customer gets polite response: "I've forwarded your request to our specialist team."

**Result**: No refund issued. Human fraud team alerted with full context for investigation.

---

## Failure 4: Duplicate Refund Request

**Scenario**: Customer (TKT-009) asks about a refund for ORD-1009. This order was already refunded on 2024-03-02. Customer hasn't seen the money yet and wants confirmation.

**Detection**: `order.refund_status == "refunded"` checked before any financial action.

**System Behavior**:
1. Agent fetches order data → sees `refund_status: "refunded"`
2. Idempotency guard triggers → blocks any new `issue_refund` call
3. Logs `unsafe_action_blocked = true`, `unsafe_action_detail = "Blocked duplicate refund"`
4. Sends status confirmation: "Your refund has been processed. Please allow 5-7 business days."

**Result**: Customer informed of existing refund status. No duplicate financial transaction executed.

---

## Failure 5: Invalid Order ID with Legal Threat

**Scenario**: Customer (TKT-017) demands refund for ORD-9999 (doesn't exist in system) and threatens legal action ("My lawyer will be in touch").

**Detection**:
1. `extract_order_id` finds ORD-9999 in ticket text
2. `get_order(ORD-9999)` returns `None` → `invalid_order_id` flag added
3. Classifier detects "lawyer" → `THREAT_LANGUAGE` tag
4. Combined: invalid order + threat → `FRAUD` classification

**System Behavior**:
1. `FRAUD` classification triggers → all financial actions blocked
2. `unsafe_action_blocked = true`
3. Structured escalation with context: "Order ORD-9999 does not exist. Threat language detected."
4. Professional response sent without acknowledging the threat

**Result**: No refund issued for non-existent order. No system compromise. Fraud team alerted.
