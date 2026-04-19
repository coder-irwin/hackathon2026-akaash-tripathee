# ShopWave Architecture

## System Overview
The ShopWave Resolution Engine is a **7-stage autonomous pipeline** that decouples context enrichment, classification, policy validation, and tool execution into modular, testable layers.

## Pipeline Diagram

```mermaid
flowchart TD
    A["Ticket Input (20 JSON tickets)"] --> B["Stage 1: Context Enrichment"]
    B --> B1["Email -> Customer (O(1) lookup)"]
    B --> B2["Order ID -> Order (regex + lookup)"]
    B --> B3["Order -> Product (FK join)"]
    B --> B4["Email fallback: infer most recent order"]
    
    B1 & B2 & B3 & B4 --> C["Stage 2: Hybrid Classification"]
    C --> C1["Deterministic Rules (85%+ coverage)"]
    C --> C2["GPT-4o-mini Fallback (edge cases)"]
    C --> C3["Fraud / SE Detection (keyword patterns)"]
    
    C1 & C2 & C3 --> D["Stage 3: Policy Validation"]
    D --> D1["Return Window Check (date math)"]
    D --> D2["Tier Override (VIP leniency)"]
    D --> D3["High-Value Gate ($200 threshold)"]
    D --> D4["Idempotency (refund_status check)"]
    
    D1 & D2 & D3 & D4 --> E["Stage 4: Confidence Gate"]
    E -->|"conf > 0.65"| F["Stage 5: Safe Action Router"]
    E -->|"conf < 0.65"| H["Clarification / Escalation"]
    
    F --> F1["Transactional: Refund/Return/Cancel"]
    F --> F2["Informational: Tracking/Policy"]
    F --> F3["Safety: Fraud/Warranty -> Escalate"]
    
    F1 & F2 & F3 --> G["Stage 6: Tool Execution Layer"]
    G --> G1["get_order, get_customer, get_product"]
    G --> G2["check_refund_eligibility"]
    G --> G3["issue_refund, cancel_order"]
    G --> G4["send_reply, escalate"]
    
    G1 & G2 & G3 & G4 --> I["Stage 7: Audit Logger"]
    I --> I1["audit_log.json (per-ticket trace)"]
    I --> I2["outbound_queue.json (failed replies)"]
    
    H --> I
```

## Module Documentation

### `services/data_service.py`
- **Purpose**: O(1) indexed data access layer
- **Inputs**: JSON files from `data/` directory
- **Outputs**: Customer, Order, Product, Ticket objects
- **Key Decision**: Pre-indexed by email and order_id at load time for constant-time lookups

### `services/context_enrichment.py`
- **Purpose**: Resolve identity, order, and product context for each ticket
- **Inputs**: Raw Ticket
- **Outputs**: EnrichedTicket with full context
- **Key Decision**: When no order_id in ticket, infers most recent order from customer email

### `services/classifier.py`
- **Purpose**: Hybrid deterministic + LLM classification
- **Inputs**: Ticket text + enrichment context
- **Outputs**: ClassificationOutput (primary_class, tags, risk, confidence)
- **Key Decision**: Fraud detection keywords checked FIRST to override any other classification

### `services/policy_engine.py`
- **Purpose**: State-based eligibility validation
- **Inputs**: EnrichedTicket
- **Outputs**: PolicyValidation (eligible/blocked actions, reasons)
- **Key Decision**: VIP tier always gets extended return window regardless of deadline

### `agent/resolution_agent.py`
- **Purpose**: Core reasoning loop with per-intent handlers
- **Inputs**: List of EnrichedTickets
- **Outputs**: List of AuditLogEntry
- **Key Decision**: Every financial action requires ALL 5 guardrails to pass. Fallback to escalation on any failure.

### `tools/resolution_tools.py`
- **Purpose**: Mock implementations of 8 tools with realistic failure simulation
- **Inputs**: Tool-specific parameters
- **Outputs**: Tool-specific responses
- **Key Decision**: 15% timeout rate, 5% malformed data rate for realism

## Resilience Architecture

| Failure | Detection | Fallback |
|---|---|---|
| Tool Timeout | asyncio.TimeoutError after retry | Cache/snapshot/escalate |
| Malformed Data | Error key in response | Use enrichment snapshot |
| Send Reply Fail | 2 retries exhausted | outbound_queue.json |
| KB Timeout | Retry fails | Hardcoded POLICY_FALLBACK dict |
| Eligibility Timeout | Cannot verify | Escalate (never guess) |
| Invalid Order ID | get_order returns null | Block refund, ask for ID |
