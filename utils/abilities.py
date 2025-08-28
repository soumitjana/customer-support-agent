ABILITIES = {
    # Stage 1: INTAKE
    "accept_payload": {"server": "COMMON", "mode": "auto"},

    # Stage 2: UNDERSTAND
    "parse_request_text": {"server": "COMMON", "mode": "auto"},
    "extract_entities": {"server": "ATLAS", "mode": "auto"},

    # Stage 3: PREPARE
    "normalize_fields": {"server": "COMMON", "mode": "auto"},
    "enrich_records": {"server": "ATLAS", "mode": "auto"},
    "add_flags_calculations": {"server": "COMMON", "mode": "auto"},

    # Stage 4: ASK
    "clarify_question": {"server": "ATLAS", "mode": "human"},

    # Stage 5: WAIT
    "extract_answer": {"server": "ATLAS", "mode": "human"},
    "store_answer": {"server": "COMMON", "mode": "auto"},

    # Stage 6: RETRIEVE
    "knowledge_base_search": {"server": "ATLAS", "mode": "auto"},
    "store_data": {"server": "COMMON", "mode": "auto"},

    # Stage 7: DECIDE
    "solution_evaluation": {"server": "COMMON", "mode": "auto"},
    "escalation_decision": {"server": "ATLAS", "mode": "auto"},
    "update_payload": {"server": "COMMON", "mode": "auto"},

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