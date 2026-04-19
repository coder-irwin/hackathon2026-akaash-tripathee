from typing import Dict, Any, List

def calculate_confidence(
    intelligence_score: float, 
    context: Dict[str, Any]
) -> float:
    """
    Final Hardened Confidence Scorer.
    Eliminates 'brevity penalty' for short clear tickets.
    """
    # 1. Base Intelligence
    final_score = intelligence_score * 0.55
    
    # 2. Context Verification (Max 0.45)
    if context.get("order_found"): final_score += 0.2
    if context.get("customer_found"): final_score += 0.15
    if context.get("product_found"): final_score += 0.1
    
    # 3. Request Integrity
    if context.get("has_clear_verb"): final_score += 0.1
    
    # 4. Strict Penalties (Only for contradictions)
    if context.get("contradiction_detected"): final_score -= 0.4
    
    return min(max(final_score, 0.0), 1.0)

def determine_resolvability(primary_class: str, confidence: float, risk_level: str, tags: List[str]) -> str:
    """
    Action-First Resolvability Mapper.
    Prioritizes resolution over identity for low-risk intents.
    """
    if risk_level == "CRITICAL" or "SOCIAL_ENGINEERING" in tags:
        return "ESCALATE"
        
    # Informational Queries
    if primary_class in ["POLICY_QUERY", "TRACKING"]:
        return "AUTO" if confidence > 0.4 else "NEED_MORE_INFO"

    # Transactional
    if primary_class == "AMBIGUOUS" and confidence < 0.4:
        return "NEED_MORE_INFO"

    if "OUTSIDE_WINDOW" in tags and primary_class in ["REFUND", "RETURN", "EXCHANGE"]:
        return "DENY"
        
    if primary_class in ["REFUND", "RETURN", "CANCELLATION", "DAMAGED", "WRONG_ITEM"]:
        # If we have identity verified or even just an order ID, we enable conditional auto
        if "IDENTITY_VERIFIED" in tags or "ORDER_ID_FOUND" in tags:
            return "CONDITIONAL_AUTO"
        return "NEED_MORE_INFO"
        
    return "AUTO"
