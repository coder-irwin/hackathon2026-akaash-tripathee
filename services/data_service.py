import json
from pathlib import Path
from typing import Dict, List, Optional
from models.schemas import Customer, Order, Product, Ticket

class DataService:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.customers: Dict[str, Customer] = {}
        self.email_to_customer: Dict[str, Customer] = {}
        self.orders: Dict[str, Order] = {}
        self.products: Dict[str, Product] = {}
        self.tickets: List[Ticket] = []
        self.knowledge_base: str = ""
        self.load_data()

    def load_data(self):
        # Load Customers
        with open(self.data_dir / "customers.json", "r") as f:
            customers_data = json.load(f)
            for c in customers_data:
                customer = Customer(**c)
                self.customers[customer.customer_id] = customer
                self.email_to_customer[customer.email.lower()] = customer

        # Load Products
        with open(self.data_dir / "products.json", "r") as f:
            products_data = json.load(f)
            for p in products_data:
                product = Product(**p)
                self.products[product.product_id] = product

        # Load Orders
        with open(self.data_dir / "orders.json", "r") as f:
            orders_data = json.load(f)
            for o in orders_data:
                order = Order(**o)
                self.orders[order.order_id] = order

        # Load Tickets
        with open(self.data_dir / "tickets.json", "r") as f:
            tickets_data = json.load(f)
            for t in tickets_data:
                self.tickets.append(Ticket(**t))

        # Load Knowledge Base
        with open(self.data_dir / "knowledge-base.md", "r") as f:
            self.knowledge_base = f.read()

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        return self.email_to_customer.get(email.lower())

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def search_knowledge_base(self, query: str) -> Dict[str, str]:
        """Enhanced search that returns specific policy snippets."""
        sections = self.knowledge_base.split("\n## ")
        matches = {}
        
        keywords = query.lower().split()
        for section in sections:
            header = section.split("\n")[0].strip()
            # If header is the main title
            if section.startswith("# "):
                header = section.split("\n")[0].replace("#", "").strip()

            if any(kw in section.lower() for kw in keywords):
                # Clean up section string
                content = "## " + section if not section.startswith("#") else section
                matches[header] = content
        
        if not matches:
            return {"default": "No specific policy found in knowledge base."}
        
        # Return top matches
        return dict(list(matches.items())[:3])
