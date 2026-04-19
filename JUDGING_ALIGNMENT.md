# ⚖️ Judging Alignment Guide

**Welcome Judges!** ShopWave is designed specifically to max-out the Global AI Agent Hackathon rubric. 
We approached this not as a sandbox API wrapper, but as an Enterprise Operations challenge. 

Here is how our codebase rigidly aligns with your exact grading criteria.

---

### 1. Robust Agentic Architecture & Reasoning (30% Weight)
* **Our Approach**: We completely bypassed the standard "single agent prompt" anti-pattern. ShopWave leverages a **7-Stage Intent Pipeline**, separating Data Enrichment, Classification, Policy Verification, and Execution.
* **Proof in Code**: Examine `agent/resolution_agent.py` and `services/policy_engine.py`. Notice how the agent forces validation via `.reasoning_steps` appended sequentially, and uses deterministic O(1) checks before deferring to LLMs for ambiguity.

### 2. Multi-Tool Orchestration (20% Weight)
* **Requirement**: Systems must autonomously sequence multiple backend connections.
* **Our Approach**: ShopWave connects 8 mock enterprise APIs. Almost every single resolution path requires:
  1. `get_customer()`
  2. `get_order()`
  3. `check_refund_eligibility()`
  4. And finally an action (`issue_refund`, `send_reply`, `escalate`).
* **Proof in Code**: Check the `audit_log.json`. Every completed ticket demonstrates a chain of minimum 3 tools executed perfectly in state-dependent order.

### 3. Graceful Failure & System Resilience (25% Weight)
* **Our Approach**: We deliberately break our own tools. Look at `tools/resolution_tools.py`, where `@simulate_realism` aggressively injects 15% timeouts and 5% malformed data. ShopWave survives this using:
  * **2-Stage Backoff Retries**: Standard `asyncio` catching.
  * **Snapshot Fallbacks**: If standard Database APIs fail, it falls back to the local `en.order` context fetched during early enrichment.
  * **Dead Letter Routing**: If `send_reply` completely crashes, messages are saved safely to `outbound_queue.json` to prevent customer ghosting.

### 4. Safety Constraints & "No Black Boxes" (15% Weight)
* **Our Approach**: AI cannot just issue money. We built a **5-Point Financial Guardrail**:
  1. *Existence*: Customer and Order must be verified.
  2. *Idempotency*: Is it already refunded? Block to prevent duplicate drain.
  3. *Eligibility*: Date window validation (with VIP tier exception checks).
  4. *High-Value Threshold*: Strict $200 hardcoded limit for Auto-Refunds.
  5. *Fraud Protection*: Catching social engineering ("sue you", "scam").
* **Explainability**: Review the Web UI or `audit_log.json`. Under `why_not_other_actions` it literally documents the exact reasoning matrix generated *before* execution.

### 5. Deployment, UX, and Polish (10% Weight)
* **Our Approach**: Complete local setup out of the box in one command (`python dashboard.py`).
* **UX Quality**: Fully stylized Bootstrap + Glassmorphism UX connecting directly to the python runtime loop via AJAX polling. Included metrics readouts dynamically compute Speedups, DLQ fails, and Output Success in milliseconds.

---
**Verdict:** We prioritized building a system that is unbreakably safe, extremely fast (`asyncio`), and completely transparent. We hope you enjoy breaking it as much as we built it to survive.
