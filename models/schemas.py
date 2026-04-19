from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, date

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip: str

class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    phone: str
    tier: str
    member_since: date
    total_orders: int
    total_spent: float
    address: Address
    notes: Optional[str] = None

class Order(BaseModel):
    order_id: str
    customer_id: str
    product_id: str
    quantity: int
    amount: float
    status: str
    order_date: date
    delivery_date: Optional[date] = None
    return_deadline: Optional[date] = None
    refund_status: Optional[str] = None
    notes: Optional[str] = None

class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    warranty_months: int
    return_window_days: int
    returnable: bool
    notes: Optional[str] = None

class Ticket(BaseModel):
    ticket_id: str
    customer_email: str
    subject: str
    body: str
    source: str
    created_at: datetime
    tier: int
    expected_action: Optional[str] = None

class ReasoningStep(BaseModel):
    thought: str
    action: Optional[str] = None
    observation: Optional[Any] = None
    decision: Optional[str] = None

class ToolCall(BaseModel):
    tool: str
    parameters: dict
    output: Any
    duration: float = 0.0

# AuditLogEntry has been moved to enriched_schemas.py to support the high-fidelity pipeline.
