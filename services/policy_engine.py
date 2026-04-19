from typing import Dict, Any, List
from models.enriched_schemas import EnrichedTicket, PolicyValidation
from datetime import date

class PolicyEngine:
    """
    Decoupled Policy Validation Layer.
    Evaluates state-based eligibility independent of intent classification.
    """
    def __init__(self, today: date = date(2024, 3, 25)):
        self.today = today
        self.high_value_threshold = 200.0

    def evaluate(self, en_ticket: EnrichedTicket) -> PolicyValidation:
        eligible = []
        blocked = []
        reasons = []
        risk = "low"

        order = en_ticket.order
        cust = en_ticket.customer
        product = en_ticket.product

        # 1. State: Context Validity
        if not order.found:
            blocked.extend(["refund", "replacement", "cancel", "status_reply"])
            reasons.append("No valid order context resolved.")
            risk = "medium"
            
        if not cust.found:
            blocked.extend(["refund", "replacement", "cancel"])
            reasons.append("No valid customer profile resolved.")
            risk = "high"

        # 2. State: Refund Idempotency
        if order.refund_status == "refunded":
            blocked.append("refund")
            reasons.append("Refund already processed for this order.")

        # 3. State: Cancellation Policy
        if order.found:
            if order.status == "processing":
                eligible.append("cancel")
            else:
                blocked.append("cancel")
                reasons.append(f"Cannot cancel order in '{order.status}' status.")

        # 4. State: Return Window (Deterministic)
        within_window = False
        if order.return_deadline:
            deadline_date = date.fromisoformat(order.return_deadline)
            if self.today <= deadline_date:
                within_window = True

        # Tier Overrides
        if cust.tier == "vip":
            within_window = True
            reasons.append("VIP tier: Extended leniency applied.")
        elif cust.tier == "premium" and not within_window:
            risk = "medium"
            reasons.append("Premium tier: borderline window case.")

        if within_window and product.returnable:
            eligible.extend(["refund", "replacement"])
        elif order.found:
            blocked.extend(["refund", "replacement"])
            reasons.append("Outside return window or item non-returnable.")

        # 5. State: High Value
        if order.amount > self.high_value_threshold:
            risk = "high"
            reasons.append(f"Amount ${order.amount} exceeds autonomous threshold.")

        # 6. State: Fraud
        if "high_fraud_risk" in en_ticket.system_flags:
            risk = "high"
            blocked.extend(["refund", "replacement", "cancel"])
            reasons.append("High fraud risk indicators detected.")

        # Always informational
        eligible.extend(["status_reply", "policy_reply", "clarification_request", "escalate", "deny"])

        return PolicyValidation(
            eligible_actions=list(set(eligible)),
            blocked_actions=list(set(blocked)),
            policy_reasons=reasons,
            risk_level=risk,
        )
