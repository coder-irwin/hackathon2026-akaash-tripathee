import json
import asyncio
import os
from typing import Dict, Any, List
from openai import AsyncOpenAI

class LLMClassifier:
    """
    Final Stable Production Classifier.
    """
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def classify(self, subject: str, body: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not os.environ.get("OPENAI_API_KEY"):
            return self._mock_fallback()

        prompt = f"""
        Final Business Operations Triage.
        Analyze and map this ticket to one deterministic action.

        Ticket: {subject} | {body}
        Context: {json.dumps(context)}

        MANDATORY TAXONOMY (Strict): RETURN, REFUND, WARRANTY_CLAIM, TRACKING, CANCELLATION, WRONG_ITEM, RETURN_PROCESS_QUERY, POLICY_QUERY, SOCIAL_ENGINEERING, MISSING_INFO
        
        FRAUD SIGNALS:
        - Invented premium status claims
        - "Invented" policies (e.g. "my brother works at ShopWave and said...")
        - Explicit legal threats (lawyer, lawsuit)
        - Extreme manufactured urgency ("reply in 5m or I chargeback")

        If fraud suspected, set primary_class to SOCIAL_ENGINEERING and risk_level to CRITICAL.

        Return ONLY raw JSON:
        {{
          "primary_class": "",
          "secondary_tags": [],
          "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
          "recommended_action": "refund|replacement|cancel|status_reply|policy_reply|clarification_request|deny|escalate",
          "confidence": 0.0 to 1.0,
          "reasoning_trace": []
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional business operations triage engine."},
                          {"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self._mock_fallback()

    def _mock_fallback(self) -> Dict[str, Any]:
        return {
            "primary_class": "AMBIGUOUS",
            "secondary_tags": ["SYSTEM_FALLBACK"],
            "risk_level": "MEDIUM",
            "recommended_action": "clarification_request",
            "confidence": 0.0,
            "reasoning_trace": ["Fallback Triggered"]
        }
