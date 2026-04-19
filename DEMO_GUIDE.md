# Demo Guide (5-Minute Walkthrough)

## Script

### 0:00 - Opening
> "This is not a chatbot. This is an autonomous decision-making agent that processes 20 real support tickets — concurrently — and takes irreversible actions like refunds and cancellations, safely."

### 0:30 - Run the Agent
```bash
# Terminal 1: Background worker
python main.py

# Terminal 2: GUI Dashboard
python dashboard.py
```
Open `http://localhost:5000` to show the beautiful Web UI:
- Live progress as 20 tickets process concurrently
- Color-coded results table
- Metrics panel displaying zero DLQ and 100% refund precision.

### 1:00 - Show TKT-008 (Damaged Lamp → Auto Refund) via UI Modal
> "Watch the full chain on the web viewer: KB lookup → customer verify → order fetch → eligibility check → refund issued → reply sent. That's 6 tool calls, fully autonomous, with every step logged in real-time."

Key audit fields to highlight:
- `tools_called`: 6 tools in sequence
- `refund_amount`: $44.99
- `why_chosen`: "Refund approved: eligible, within window"

### 1:30 - Show TKT-018 (Fraud Attempt → Caught)
> "This customer claims to be a premium member with instant refund rights. Our system verifies: actual tier is 'standard'. No such policy exists. Classification: FRAUD. Action: escalate to fraud team. Zero dollars lost."

Key audit fields:
- `classification`: FRAUD
- `unsafe_action_blocked`: true
- `customer_tier`: standard (not premium)

### 2:00 - Show TKT-011 (High-Value Watch → Escalated)
> "This $249.99 order exceeds our $200 auto-refund threshold. The system escalates with a structured summary including customer tier, order value, and a recommended action for the manager."

### 2:30 - Open audit_log.json
> "Every ticket gets a full decision trace. Here's the reasoning chain, the policy checks, the tools called, and — critically — the 'why_not_other_actions' explaining why alternatives were rejected."

### 3:30 - Show Metrics Summary
```
Successfully Resolved: 10-12
Escalated to Human: 7-9
Clarification: 1
Failed / DLQ: 0
Refund Precision: 100%
Unsafe Actions Blocked: 5-7
```

### 4:00 - Closing
> "Every decision is explainable, safe, and auditable. The agent knows what it doesn't know — and escalates rather than guessing. That's the difference between a demo and a production system."

### 4:30 - Ready for Q&A

---

## Judge Q&A Preparation

**Q: Why is this agentic, not just rule-based?**
> A: Multi-step tool chains with dynamic branching. The agent decides which tools to call based on classification and policy state, not a fixed script. It handles uncertainty through escalation, not failure.

**Q: What happens if a tool fails?**
> A: Retry with exponential backoff (2 attempts). If still failing: send_reply → outbound queue. KB → cached policy. Eligibility → escalate. get_order → enrichment snapshot. Result: 0 DLQ across 20 tickets.

**Q: How do you prevent wrong refunds?**
> A: 5-point guardrail system. Order must exist > eligibility must be true > not already refunded > amount under $200 > not flagged as fraud. All 5 must pass or we escalate.

**Q: How does confidence scoring work?**
> A: Weighted by entity presence (40%), tool success (30%), policy clarity (30%). If customer and order found with clear intent, confidence is high. If missing both, confidence drops below threshold and we ask for clarification.

**Q: What's your concurrency strategy?**
> A: asyncio.gather on all 20 tickets. Each ticket runs its own tool chain independently. Simulated tool latency (100-500ms per call) makes sequential processing take ~30s. Concurrent: ~5-10s.

**Q: Did AI tools write this code?**
> A: Yes, AI-assisted development was used for code generation and iteration. Every line was reviewed, understood, and can be explained. The architecture decisions — safety-first, escalation-over-guessing, deterministic-first classification — are deliberate engineering choices.
