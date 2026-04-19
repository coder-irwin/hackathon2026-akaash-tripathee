from typing import List, Dict, Any, Optional
from datetime import date
from models.schemas import Ticket, Customer, Order, Product
from models.enriched_schemas import (
    EnrichedTicket, EnrichedCustomer, EnrichedOrder, EnrichedProduct, PolicyValidation
)
from utils.parsers import extract_order_id, extract_email
from services.data_service import DataService
from services.classifier import RuleClassifier
from services.policy_engine import PolicyEngine


class ContextEnrichmentEngine:
    """
    Full-pipeline context enrichment.
    Resolves identity → order → product → classification → policy in one pass.
    """
    def __init__(self, data_service: DataService):
        self.ds = data_service
        self.today = date(2024, 3, 25)
        self.class_engine = RuleClassifier()
        self.policy_engine = PolicyEngine(today=self.today)

    async def enrich_ticket(self, ticket: Ticket) -> EnrichedTicket:
        # 1. Identity Resolution
        email = extract_email(f"{ticket.subject} {ticket.body}") or ticket.customer_email
        customer_record = self.ds.get_customer_by_email(email)

        # 2. Order Resolution
        order_id = extract_order_id(f"{ticket.subject} {ticket.body}")
        order_record = None
        system_flags = []

        if order_id:
            order_record = self.ds.get_order(order_id)
            if not order_record:
                system_flags.append("invalid_order_id")
            elif customer_record and order_record.customer_id != customer_record.customer_id:
                order_record = None
                system_flags.append("order_customer_mismatch")

        # Email-based order inference when no order_id in ticket text
        if not order_record and customer_record:
            customer_orders = [
                o for o in self.ds.orders.values()
                if o.customer_id == customer_record.customer_id
            ]
            if customer_orders:
                order_record = sorted(customer_orders, key=lambda x: x.order_date, reverse=True)[0]
                system_flags.append("order_inferred_from_email")

        # 3. Product Resolution
        product_record = None
        if order_record:
            product_record = self.ds.get_product(order_record.product_id)

        # 4. Build classification context
        order_status = order_record.status if order_record else None
        classification_context = {
            "extracted_order_id": order_id,
            "customer_found": bool(customer_record),
            "order_found": bool(order_record),
            "product_found": bool(product_record),
            "order_status": order_status,
            "high_value": (order_record.amount > 200) if order_record else False,
        }

        # 5. Classification
        classification = await self.class_engine.classify_and_score(ticket, classification_context)

        # 6. Package enriched ticket
        resolved_order_id = order_id or (order_record.order_id if order_record else None)
        en_ticket = EnrichedTicket(
            ticket_id=ticket.ticket_id,
            subject=ticket.subject,
            body=ticket.body,
            customer=self._pack_customer(customer_record),
            order=self._pack_order(order_record),
            product=self._pack_product(product_record),
            classification=classification,
            system_flags=system_flags,
            metadata={
                "source_email": email,
                "extracted_order_id": order_id,
                "resolved_order_id": resolved_order_id,
            }
        )

        # 7. Policy validation
        en_ticket.policy = self.policy_engine.evaluate(en_ticket)

        return en_ticket

    def _pack_customer(self, c: Optional[Customer]) -> EnrichedCustomer:
        if not c:
            return EnrichedCustomer(found=False)
        return EnrichedCustomer(
            found=True,
            customer_id=c.customer_id,
            name=c.name,
            tier=c.tier,
            member_since=c.member_since.isoformat(),
            total_orders=c.total_orders,
            total_spent=c.total_spent,
            notes=c.notes,
        )

    def _pack_order(self, o: Optional[Order]) -> EnrichedOrder:
        if not o:
            return EnrichedOrder(found=False)
        return EnrichedOrder(
            found=True,
            order_id=o.order_id,
            status=o.status,
            amount=o.amount,
            order_date=o.order_date.isoformat(),
            delivery_date=o.delivery_date.isoformat() if o.delivery_date else None,
            return_deadline=o.return_deadline.isoformat() if o.return_deadline else None,
            refund_status=o.refund_status,
            notes=o.notes,
        )

    def _pack_product(self, p: Optional[Product]) -> EnrichedProduct:
        if not p:
            return EnrichedProduct(found=False)
        return EnrichedProduct(
            found=True,
            product_id=p.product_id,
            name=p.name,
            category=p.category,
            price=p.price,
            warranty_months=p.warranty_months,
            return_window_days=p.return_window_days,
            returnable=p.returnable,
        )
