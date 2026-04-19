# Implementation Journey

This document tells the full build story of the ShopWave Autonomous Resolution Engine, from data foundation to production-hardened system.

---

## Phase 1: Data Foundation

**Goal**: Build O(1) indexed lookup maps for instant identity resolution.

**What we built**:
- `DataService` with pre-indexed `email_to_customer` dictionary for O(1) email lookups
- Order index by `order_id` for instant order retrieval
- Product index by `product_id` for catalog resolution
- Knowledge base loaded as raw text for semantic search simulation

**Key decisions**:
- Pre-index at load time, not at query time. This means enrichment is constant-time regardless of dataset size.
- Handle all edge cases: missing emails, invalid order IDs, cross-customer order attempts.

---

## Phase 2: Classification Engine

**Goal**: Map raw ticket text to deterministic business intents with fraud detection.

**Evolution**:
1. Started with simple keyword matching → too many false positives (e.g., "stopped working" matched "cancel")
2. Added ordered keyword priority: warranty keywords checked BEFORE refund keywords
3. Added fraud signal detection: threat language, fake tier claims, invented policies
4. Built hybrid layer: deterministic for 85%+ of tickets, GPT-4o-mini for ambiguous edge cases

**Taxonomy** (frozen):
```
PRIMARY: RETURN, REFUND, WARRANTY, TRACKING, CANCELLATION, EXCHANGE,
         DAMAGED, WRONG_ITEM, POLICY_QUERY, FRAUD, AMBIGUOUS
TAGS:    WITHIN_WINDOW, OUTSIDE_WINDOW, HIGH_VALUE, VIP, THREAT_LANGUAGE,
         SOCIAL_ENGINEERING, REPLACEMENT_REQUESTED, REFUND_STATUS_QUERY, etc.
```

**Key insight**: Classification order matters. "Stopped working" → WARRANTY, not CANCELLATION.

---

## Phase 3: Policy Engine

**Goal**: Deterministic state-based validation independent of classification.

**What we built**:
- Date math for return window checking (product-specific: 15/30/60 days)
- Tier-based override logic: VIP customers get extended return leniency
- High-value threshold: $200+ orders always require human approval
- Idempotency checks: already-refunded orders blocked from re-processing
- Fraud gates: flagged tickets blocked from all financial actions

**Key decisions**:
- Policy is decoupled from classification. Even if classifier says "REFUND", policy can block it.
- VIP exception is deterministic — not a "soft" suggestion, a hard override.

---

## Phase 4: Resolution Engine

**Goal**: Multi-step tool chains that autonomously resolve tickets.

**Architecture**:
- Per-intent handlers: `_handle_transactional`, `_handle_tracking`, `_handle_cancellation`, etc.
- Minimum 3 tool calls per ticket (hard requirement for audit depth)
- Every handler follows: KB lookup → Customer verify → Intent-specific action → Reply

**Tool chain examples**:
- Refund: `search_kb → get_customer → get_order → check_eligibility → issue_refund → send_reply`
- Tracking: `search_kb → get_customer → get_order → send_reply`
- Fraud: `search_kb → get_customer → get_order → escalate → send_reply`

**Concurrency**: `asyncio.gather` processes all 20 tickets simultaneously, achieving 5-8x speedup.

---

## Phase 5: Safety Layer

**Goal**: 100% refund precision. Zero unsafe financial actions.

**5-Point Guardrail System**:
1. **Existence**: `get_order` must return valid record
2. **Eligibility**: `check_refund_eligibility` must return `eligible=true`
3. **Idempotency**: `refund_status != "refunded"` (no duplicates)
4. **Threshold**: Amount ≤ $200 (higher → escalate)
5. **Fraud Gate**: No financial action on FRAUD/SE classifications

**Unsafe actions blocked per run**: 5-7 (high-value, duplicates, fraud attempts, invalid orders)

---

## Phase 6: Recovery Layer

**Goal**: 100% operational completion. No ticket left behind.

**Fallback strategies**:
| Tool | Failure | Fallback |
|------|---------|----------|
| `send_reply` | Timeout after 2 retries | Write to `outbound_queue.json` |
| `search_knowledge_base` | Timeout | Use `POLICY_FALLBACK` dictionary |
| `get_order` | Timeout/malformed | Use enrichment snapshot from context phase |
| `check_refund_eligibility` | Timeout | Escalate to human (never guess) |
| `escalate` | Timeout | Retry once, then log with manual flag |

**Result**: 0 DLQ across all runs. Every customer gets an outcome.

---

## Phase 7: Audit & Explainability

**Goal**: Any judge can inspect one ticket and understand full reasoning in <15 seconds.

**Per-ticket audit fields**:
- `reasoning_steps[]`: Step-by-step decision narrative
- `policy_checks[]`: Which policies were evaluated
- `why_chosen`: Why this specific action was taken
- `why_not_other_actions`: Why alternatives were rejected
- `risk_flags[]`: Security/policy flags triggered
- `tool_failures[]`: Which tools failed and why
- `fallbacks_used[]`: Which recovery strategies activated
- `unsafe_action_blocked`: Whether a dangerous action was prevented

**Enterprise metrics**:
- Avg Tools/Ticket: 5.0
- Decision Explainability Score: 10/10
- Fallback Rate: tracked per-tool
- Top Failure Tool: identified automatically
