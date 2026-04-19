from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

class EnrichedCustomer(BaseModel):
    found: bool
    customer_id: Optional[str] = None
    name: Optional[str] = None
    tier: str = "standard"
    value_segment: str = "low"
    risk_level: str = "low"
    member_since: Optional[str] = None
    total_orders: int = 0
    total_spent: float = 0.0
    notes: Optional[str] = None

class EnrichedOrder(BaseModel):
    found: bool
    order_id: Optional[str] = None
    status: Optional[str] = None
    amount: float = 0.0
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    return_deadline: Optional[str] = None
    refund_status: Optional[str] = None
    quantity: int = 0
    notes: Optional[str] = None

class EnrichedProduct(BaseModel):
    found: bool
    product_id: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    price: float = 0.0
    warranty_months: int = 0
    return_window_days: int = 0
    returnable: bool = False

class ClassificationOutput(BaseModel):
    primary_class: str
    secondary_tags: List[str] = []
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    resolvability: str  # AUTO, CONDITIONAL_AUTO, NEED_MORE_INFO, DENY, ESCALATE
    confidence: float
    recommended_action: str
    reasoning_trace: List[str] = []

class PolicyValidation(BaseModel):
    eligible_actions: List[str] = []
    blocked_actions: List[str] = []
    policy_reasons: List[str] = []
    risk_level: str = "low"

class EnrichedTicket(BaseModel):
    model_config = ConfigDict(frozen=False)
    ticket_id: str
    subject: str
    body: str
    customer: EnrichedCustomer
    order: EnrichedOrder
    product: EnrichedProduct
    classification: ClassificationOutput
    policy: Optional[PolicyValidation] = None
    system_flags: List[str] = []
    metadata: Dict[str, Any] = {}

class AuditLogEntry(BaseModel):
    ticket_id: str
    timestamp: str
    customer_email: str
    customer_name: str = "Unknown"
    customer_tier: str = "unknown"
    classification: str
    confidence_score: float
    recommended_action: str
    tools_called: List[str] = []
    tool_results_summary: List[str] = []
    tool_failures: List[str] = []
    retries_used: int = 0
    fallbacks_used: List[str] = []
    reasoning_steps: List[str] = []
    policy_checks: List[str] = []
    risk_flags: List[str] = []
    why_chosen: str = ""
    why_not_other_actions: Dict[str, str] = {}
    final_outcome: str = ""
    final_action: str = ""
    refund_amount_if_any: float = 0.0
    escalated_bool: bool = False
    escalation_summary_if_any: Optional[str] = None
    latency_ms: int = 0
    success_bool: bool = False
    status: str = "pending"
    final_reply_preview: str = ""
    unsafe_action_blocked: bool = False
    unsafe_action_detail: str = ""
