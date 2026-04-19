from typing import Dict, Any, List
from .llm_classifier import LLMClassifier
from utils.scoring import calculate_confidence, determine_resolvability
from models.schemas import Ticket
from models.enriched_schemas import ClassificationOutput

class RuleClassifier:
    """
    Production Hybrid Classifier.
    Deterministic keyword rules → LLM fallback for ambiguous/edge cases.
    Frozen taxonomy with strict fraud detection.
    """
    def __init__(self):
        self.llm = LLMClassifier()

    async def classify_deterministic(self, ticket: Ticket, context: Dict[str, Any]) -> ClassificationOutput:
        text = f"{ticket.subject} {ticket.body}".lower()
        tags = []

        if context.get("customer_found") and context.get("order_found"):
            tags.append("IDENTITY_VERIFIED")
        if context.get("extracted_order_id"):
            tags.append("ORDER_ID_FOUND")

        # --- Fraud / Social Engineering Detection (HIGHEST PRIORITY) ---
        fraud_signals = ["lawsuit", "lawyer", "sue you", "legal action", "5 minutes",
                         "my brother works", "i know the ceo", "chargeback"]
        social_eng = ["as a premium member", "premium policy", "instant refund",
                      "premium members get", "vip policy says"]
        
        has_threat = any(s in text for s in fraud_signals)
        has_social_eng = any(s in text for s in social_eng)

        if has_threat:
            tags.append("THREAT_LANGUAGE")
        if has_social_eng:
            tags.append("SOCIAL_ENGINEERING")

        # --- Primary Intent Classification (ordered by specificity) ---
        primary = "AMBIGUOUS"
        action = "clarification_request"

        # Tracking (most specific keyword)
        if any(k in text for k in ["where is my", "tracking", "track my", "shipping status", "in transit"]):
            primary = "TRACKING"
            action = "status_reply"
        # Cancellation
        elif any(k in text for k in ["cancel my", "cancel it", "want to cancel", "cancel before"]):
            primary = "CANCELLATION"
            action = "cancel"
        # Warranty (check BEFORE refund to avoid collision)
        elif any(k in text for k in ["warranty", "defect", "stopped working", "stopped heating",
                                      "manufacturing defect"]):
            primary = "WARRANTY"
            action = "escalate"
        # Damaged on arrival
        elif any(k in text for k in ["damaged", "broken", "cracked", "came broken", "arrived damaged",
                                      "box also looked damaged"]):
            primary = "DAMAGED"
            action = "refund"
        # Wrong item
        elif any(k in text for k in ["wrong size", "wrong colour", "wrong color", "wrong item",
                                      "received size", "got the black", "mismatch"]):
            primary = "WRONG_ITEM"
            action = "refund"
        # Refund status query (before general refund)
        elif any(k in text for k in ["refund already", "refund status", "confirm it went through",
                                      "haven't seen the money"]):
            primary = "REFUND"
            action = "status_reply"
            tags.append("REFUND_STATUS_QUERY")
        # General refund
        elif any(k in text for k in ["refund", "money back"]):
            primary = "REFUND"
            action = "refund"
        # Return process query (asking how, not initiating)
        elif any(k in text for k in ["how do i return", "return instructions", "what's the process",
                                      "thinking about returning", "might want to return",
                                      "is it too late"]):
            primary = "RETURN"
            action = "policy_reply"
            tags.append("ASKING_PROCESS_ONLY")
        # General return
        elif any(k in text for k in ["return", "send it back", "return request"]):
            primary = "RETURN"
            action = "refund"
        # Policy query
        elif any(k in text for k in ["policy", "rules", "what is your", "general question",
                                      "do you offer"]):
            primary = "POLICY_QUERY"
            action = "policy_reply"
        # Exchange
        elif any(k in text for k in ["exchange", "swap", "replace", "replacement", "correct size"]):
            primary = "EXCHANGE"
            action = "escalate"

        # Override: Fraud signals take priority over everything
        if has_social_eng and primary in ["REFUND", "RETURN", "EXCHANGE"]:
            primary = "FRAUD"
            action = "escalate"
            tags.append("SOCIAL_ENGINEERING")

        # Override: threat language on non-existent orders
        if has_threat and not context.get("order_found"):
            primary = "FRAUD"
            action = "escalate"

        # Replacement requests → always escalate
        if any(k in text for k in ["want a replacement", "not a refund", "replacement not"]):
            tags.append("REPLACEMENT_REQUESTED")
            action = "escalate"

        # If no clear intent detected
        if primary == "AMBIGUOUS":
            if not context.get("extracted_order_id") and not context.get("customer_found"):
                primary = "AMBIGUOUS"
                action = "clarification_request"

        # Context-aware secondary tags
        if context.get("order_found"):
            order_status = context.get("order_status", "")
            if order_status == "processing":
                tags.append("PROCESSING_ORDER")
            elif order_status == "shipped":
                tags.append("SHIPPED_ORDER")
            elif order_status == "delivered":
                tags.append("DELIVERED_ORDER")

        # Confidence scoring
        base_score = 0.75 if primary not in ["AMBIGUOUS"] else 0.3
        if has_threat or has_social_eng:
            base_score = 0.9
        conf = calculate_confidence(base_score, context)

        risk = "LOW"
        if primary in ["REFUND", "RETURN", "CANCELLATION", "WRONG_ITEM", "DAMAGED", "EXCHANGE"]:
            risk = "MEDIUM"
        if primary == "FRAUD" or has_social_eng or has_threat:
            risk = "CRITICAL"
        if context.get("high_value"):
            risk = "HIGH"
            tags.append("HIGH_VALUE")

        res = determine_resolvability(primary, conf, risk, tags)

        return ClassificationOutput(
            primary_class=primary,
            secondary_tags=tags,
            risk_level=risk,
            resolvability=res,
            confidence=conf,
            recommended_action=action,
            reasoning_trace=[f"Deterministic classification: {primary}"]
        )

    async def classify_and_score(self, ticket: Ticket, context: Dict[str, Any]) -> ClassificationOutput:
        det = await self.classify_deterministic(ticket, context)

        # High-confidence deterministic results bypass LLM
        if det.confidence > 0.75 and det.primary_class not in ["AMBIGUOUS"]:
            return det

        # LLM fallback for edge cases
        try:
            llm = await self.llm.classify(ticket.subject, ticket.body, context)
        except Exception:
            return det

        final_tags = list(set(llm.get("secondary_tags", []) + det.secondary_tags))
        conf = calculate_confidence(llm.get("confidence", 0.6), context)

        mapped_primary = llm.get("primary_class", det.primary_class)
        if mapped_primary == "AMBIGUOUS" and det.primary_class != "AMBIGUOUS":
            mapped_primary = det.primary_class

        risk = llm.get("risk_level", det.risk_level)
        res = determine_resolvability(mapped_primary, conf, risk, final_tags)

        return ClassificationOutput(
            primary_class=mapped_primary,
            secondary_tags=final_tags,
            risk_level=risk,
            resolvability=res,
            confidence=conf,
            recommended_action=llm.get("recommended_action", det.recommended_action),
            reasoning_trace=(det.reasoning_trace + llm.get("reasoning_trace", []))
        )
