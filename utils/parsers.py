import re
from typing import Optional

def extract_order_id(text: str) -> Optional[str]:
    """Extracts ORD-XXXX pattern from text."""
    if not text: return None
    match = re.search(r"ORD-\d+", text.upper())
    return match.group(0) if match else None

def extract_email(text: str) -> Optional[str]:
    """Extracts email pattern from text."""
    if not text: return None
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text.lower())
    return match.group(0) if match else None

def extract_product_id(text: str) -> Optional[str]:
    """Extracts PRD-XXXX pattern from text."""
    if not text: return None
    match = re.search(r"PRD-\d+", text.upper())
    return match.group(0) if match else None
