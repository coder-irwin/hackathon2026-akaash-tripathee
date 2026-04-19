import asyncio
from typing import Optional, Dict, Any
from services.data_service import DataService
from utils.tool_utils import simulate_realism, logger
from datetime import datetime, date

class ResolutionTools:
    def __init__(self, data_service: DataService):
        self.ds = data_service
        self.refund_log = []

    @simulate_realism
    async def get_customer(self, email: str) -> Dict[str, Any]:
        customer = self.ds.get_customer_by_email(email)
        if not customer:
            return {"error": "Customer not found"}
        return customer.model_dump()

    @simulate_realism
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        order = self.ds.get_order(order_id)
        if not order:
            return {"error": "Order not found"}
        return order.model_dump()

    @simulate_realism
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        product = self.ds.get_product(product_id)
        if not product:
            return {"error": "Product not found"}
        return product.model_dump()

    @simulate_realism
    async def search_knowledge_base(self, query: str) -> str:
        return self.ds.search_knowledge_base(query)

    @simulate_realism
    async def check_refund_eligibility(self, order_id: str) -> Dict[str, Any]:
        order = self.ds.get_order(order_id)
        if not order:
            return {"eligible": False, "reason": "Order not found"}
        
        if order.refund_status:
            return {"eligible": False, "reason": f"Already {order.refund_status}"}
        
        product = self.ds.get_product(order.product_id)
        if not product:
            return {"eligible": False, "reason": "Product not found"}

        # Logic: 
        # 1. Within return window?
        # 2. Defective? (This tool only checks static rules, specific case defect is handled in reasoning)
        
        today = date(2024, 3, 25) # Assume current date for evaluation
        
        if order.return_deadline and today <= order.return_deadline:
            return {"eligible": True, "reason": "Within return window", "amount": order.amount}
        
        # Check tier exception
        customer = self.ds.customers.get(order.customer_id)
        if customer and customer.tier == "vip":
            return {"eligible": True, "reason": "VIP exception — approved for late return", "amount": order.amount}

        return {"eligible": False, "reason": "Outside return window", "amount": 0}

    @simulate_realism
    async def issue_refund(self, order_id: str, amount: float) -> Dict[str, Any]:
        order = self.ds.get_order(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}
        
        # Irreversible action
        order.refund_status = "refunded"
        self.refund_log.append({"order_id": order_id, "amount": amount, "timestamp": datetime.now().isoformat()})
        logger.info(f"REFUND ISSUED: Order {order_id} for ${amount}")
        return {"success": True, "transaction_id": f"REF-{order_id}-{int(datetime.now().timestamp())}"}

    @simulate_realism
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        order = self.ds.get_order(order_id)
        if not order:
            return {"success": False, "error": "Order not found"}
        order.status = "canceled"
        logger.info(f"CANCELED: Order {order_id}")
        return {"success": True, "status": "canceled"}

    @simulate_realism
    async def send_reply(self, ticket_id: str, message: str) -> Dict[str, Any]:
        logger.info(f"REPLY SENT to {ticket_id}: {message[:50]}...")
        return {"success": True, "status": "delivered"}

    @simulate_realism
    async def escalate(self, ticket_id: str, summary: str, priority: str) -> Dict[str, Any]:
        logger.info(f"ESCALATED {ticket_id} | Priority: {priority} | Summary: {summary}")
        return {"success": True, "escalation_id": f"ESC-{ticket_id}"}
