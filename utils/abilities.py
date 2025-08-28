# abilities.py
"""
Deterministic (COMMON / STATE) abilities for the workflow.

Design goals
------------
- Keep these functions **general** and **schema-driven**.
- Avoid brittle keyword checks or hardcoded domain mappings.
- Operate only on structured fields already present in `state`
  (e.g., anything produced by ATLAS abilities like extract_entities, enrich_records).
- Be side-effect free: take `state`, return a **partial update dict**.

Conventions
-----------
- Every function returns a dict with a **single top-level key** named exactly
  after the ability (so the workflow runner can `state.update(result)` safely).
- If a function needs to store or update shared sub-objects, it should do so under
  stable keys (e.g., `structured_request`, `decision`, `flags`, etc.).
"""

from typing import Any, Dict, List

# ---------------------------
# ABILITIES registry (server + mode)
# ---------------------------

ABILITIES: Dict[str, Dict[str, str]] = {
    # Stage 1: INTAKE (Payload Entry Only)
    "accept_payload": {"server": "COMMON", "mode": "auto"},

    # Stage 2: UNDERSTAND - Deterministic / ATLAS mix
    "parse_request_text": {"server": "COMMON", "mode": "auto"},
    "extract_entities": {"server": "ATLAS", "mode": "auto"},  # non-deterministic

    # Stage 3: PREPARE - Deterministic / ATLAS mix
    "normalize_fields": {"server": "COMMON", "mode": "auto"},
    "enrich_records": {"server": "ATLAS", "mode": "auto"},    # non-deterministic
    "add_flags_calculations": {"server": "COMMON", "mode": "auto"},

    # Stage 4: ASK - Human
    "clarify_question": {"server": "ATLAS", "mode": "human"},
    # Stage 5: WAIT - Deterministic capture
    "extract_answer": {"server": "ATLAS", "mode": "human"},
    "store_answer": {"server": "COMMON", "mode": "auto"},     # STATE mgmt

    # Stage 6: RETRIEVE
    "knowledge_base_search": {"server": "ATLAS", "mode": "auto"},  # non-deterministic
    "store_data": {"server": "COMMON", "mode": "auto"},            # STATE mgmt

    # Stage 7: DECIDE
    "solution_evaluation": {"server": "COMMON", "mode": "auto"},   # general scoring
    "escalation_decision": {"server": "ATLAS", "mode": "auto"},    # non-deterministic
    "update_payload": {"server": "COMMON", "mode": "auto"},        # STATE mgmt

    # Stage 8: UPDATE
    "update_ticket": {"server": "ATLAS", "mode": "auto"},
    "close_ticket": {"server": "ATLAS", "mode": "auto"},

    # Stage 9: CREATE
    "response_generation": {"server": "COMMON", "mode": "auto"},

    # Stage 10: DO
    "execute_api_calls": {"server": "ATLAS", "mode": "auto"},
    "trigger_notifications": {"server": "ATLAS", "mode": "auto"},

    # Stage 11: COMPLETE
    "output_payload": {"server": "COMMON", "mode": "auto"},
}

# ---------------------------
# Helpers
# ---------------------------

def _lower_or_none(val: Any) -> Any:
    return val.lower() if isinstance(val, str) else val

def _normalize_priority(p: Any) -> str:
    """
    Normalize priority to one of: 'low', 'medium', 'high'.
    If not mappable, return original as-is (but lowercased).
    """
    mapping = {
        "l": "low", "lo": "low", "low": "low",
        "m": "medium", "med": "medium", "medium": "medium", "normal": "medium",
        "h": "high", "hi": "high", "high": "high", "urgent": "high", "critical": "high"
    }
    if isinstance(p, str):
        key = p.strip().lower()
        return mapping.get(key, key)
    return p

def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))

def _append_list(state: Dict, key: str, value: Any) -> None:
    arr = list(state.get(key, []) or [])
    arr.append(value)
    state[key] = arr

# ---------------------------
# COMMON / STATE abilities
# ---------------------------

def accept_payload(state: Dict) -> Dict:
    """
    Pass-through capture. Useful place to initialize stable containers.
    """
    out = dict(state)  # shallow copy
    out.setdefault("structured_request", {})
    out.setdefault("flags", {})
    out.setdefault("decision", {})
    out.setdefault("history", [])
    return {"accept_payload": "accept_payload_result", **out}

def parse_request_text(state: Dict) -> Dict:
    """
    Make raw text query minimally structured without guessing semantics.
    """
    query = state.get("query", "")
    structured = dict(state.get("structured_request", {}))
    structured.setdefault("summary", query)
    structured.setdefault("language", "unknown")  
    structured.setdefault("length", len(query) if isinstance(query, str) else 0)
    return {"parse_request_text": "parse_request_text_result", "structured_request": structured}

def normalize_fields(state: Dict) -> Dict:
    """
    Normalize common primitives like priority/email casing in a general way.
    """
    normalized = {}
    # Priority normalization
    if "priority" in state:
        normalized["priority"] = _normalize_priority(state["priority"])

    if "email" in state and isinstance(state["email"], str):
        normalized["email"] = state["email"].strip().lower()

    return {"normalize_fields": "normalize_fields_result", **normalized}

def add_flags_calculations(state: Dict) -> Dict:
    """
    General flags & simple derived fields based on presence/absence of structured data,
    not on domain-specific keywords.
    """
    flags = dict(state.get("flags", {}))

    # Presence-based signals (general)
    flags["has_entities"] = bool(
        state.get("entities") or
        any(k.startswith("extracted_") for k in state.keys())
    )
    flags["has_kb_result"] = bool(state.get("knowledge_base_search"))
    flags["has_enrichment"] = bool(state.get("enrich_records"))
    flags["has_answer"] = bool(state.get("extract_answer"))

    # Risk signals (general heuristics)
    prio = _lower_or_none(state.get("priority"))
    if prio in {"high", "critical"}:
        flags["sla_risk"] = "elevated"
    elif prio in {"medium", "normal"}:
        flags["sla_risk"] = "moderate"
    elif prio in {"low"}:
        flags["sla_risk"] = "low"
    else:
        flags["sla_risk"] = "unknown"

    return {"add_flags_calculations": "add_flags_calculations_result", "flags": flags}

def store_answer(state: Dict) -> Dict:
    """
    Append the human-provided answer into a stable place.
    """
    updated = {}
    answers = list(state.get("answers", []))
    ans = state.get("extract_answer")
    if ans:
        answers.append({"text": ans})
        updated["answers"] = answers
    return {"store_answer": "store_answer_result", **updated}

def store_data(state: Dict) -> Dict:
    """
    Attach any retrieved info into a stable container.
    """
    updated = {}
    kb = state.get("knowledge_base_search")
    if kb is not None:
        retrieved = list(state.get("retrieved_data", []))
        retrieved.append({"source": "kb", "payload": kb})
        updated["retrieved_data"] = retrieved
    return {"store_data": "store_data_result", **updated}

def solution_evaluation(state: Dict) -> Dict:
    """
    GENERAL scoring
    Uses only presence/structure of fields and simple heuristics.
    """
    score = 50  # neutral baseline

    priority = _lower_or_none(state.get("priority"))
    if priority == "high":
        score += 15
    elif priority == "low":
        score -= 5

    # Entities present (from ATLAS or elsewhere)
    if state.get("entities") or any(k.startswith("extracted_") for k in state.keys()):
        score += 10

    # Knowledge base presence
    kb = state.get("knowledge_base_search")
    if isinstance(kb, dict) and kb.get("found") is True:
        score += 10
    elif kb is not None:
        score -= 5

    # Enrichment (historical context helps)
    previous_tickets = 0
    enr = state.get("enrich_records")
    if isinstance(enr, dict):
        previous_tickets = int(enr.get("previous_tickets", 0) or 0)

    if previous_tickets >= 3:
        score -= 10

    score = _clamp(score, 0, 100)
    return {"solution_evaluation": {"score": score}}

def update_payload(state: Dict) -> Dict:
    """
    Record decision outcomes in a stable container.
    - Reads solution_evaluation.score (COMMON)
    - Reads escalation_decision (ATLAS) if present
    """
    decision = dict(state.get("decision", {}))

    # Attach score if present
    score = None
    se = state.get("solution_evaluation")
    if isinstance(se, dict):
        score = se.get("score")
    elif isinstance(se, (int, float)):
        score = se
    if score is not None:
        decision["score"] = int(score)

    # Mirror escalate flag if ATLAS produced it
    esc = state.get("escalation_decision")
    if isinstance(esc, dict) and "escalate" in esc:
        decision["should_escalate"] = bool(esc["escalate"])
        if "reason" in esc:
            decision["escalation_reason"] = esc["reason"]

    # Lightweight status suggestion (non-binding)
    if decision.get("score", 0) >= 90 and not decision.get("should_escalate", False):
        decision.setdefault("next_status_hint", "resolved_candidate")
    elif decision.get("should_escalate", False):
        decision.setdefault("next_status_hint", "pending_handoff")
    else:
        decision.setdefault("next_status_hint", "in_progress")

    return {"update_payload": "update_payload_result", "decision": decision}

def response_generation(state: Dict) -> Dict:
    """
    Deterministic templated response using structured fields only.
    """
    customer = state.get("customer_name", "Customer")
    score = None
    se = state.get("solution_evaluation")
    if isinstance(se, dict):
        score = se.get("score")

    escalate = None
    esc = state.get("escalation_decision")
    if isinstance(esc, dict):
        escalate = esc.get("escalate")

    kb_hit = False
    kb = state.get("knowledge_base_search")
    if isinstance(kb, dict) and kb.get("found") is True:
        kb_hit = True

    lines: List[str] = []
    lines.append(f"Hi {customer},")
    lines.append("")
    lines.append("Thanks for reaching out. We’re reviewing your request and taking the next appropriate steps.")
    if score is not None:
        lines.append(f"- Current solution confidence score: {score}/100.")
    if kb_hit:
        lines.append("- We found some relevant guidance in our knowledge base and are applying it.")
    if escalate is True:
        lines.append("- We’re routing this to a specialist for a closer look.")
    else:
        lines.append("- We’re progressing your case internally and will follow up soon.")

    msg = "\n".join(lines)
    return {"response_generation": msg}

def output_payload(state: Dict) -> Dict:
    """
    Marker ability for pipeline end. No-op update.
    """
    return {"output_payload": "output_payload_result"}

# ---------------------------
# Export mapping for COMMON server dispatcher
# ---------------------------

COMMON_FUNCTIONS = {
    "accept_payload": accept_payload,
    "parse_request_text": parse_request_text,
    "normalize_fields": normalize_fields,
    "add_flags_calculations": add_flags_calculations,
    "store_answer": store_answer,
    "store_data": store_data,
    "solution_evaluation": solution_evaluation,
    "update_payload": update_payload,
    "response_generation": response_generation,
    "output_payload": output_payload,
}
