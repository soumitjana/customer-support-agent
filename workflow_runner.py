# workflow_runner.py
from client.mcp_client import MCPClient
from client.human_client import human_intervention
from utils.abilities import ABILITIES

def mcp_call(server, ability, state):
    client = MCPClient(server.lower())
    return client.call(ability, state.copy())

def run_customer_support_workflow(customer_name, email, query, human_inputs=None):
    """
    Runs the customer support workflow with optional human inputs for web interface.
    """
    # Same config as main.py
    config = {
        "stages": [
            {"name": "INTAKE", "abilities": ["accept_payload"]},
            {"name": "UNDERSTAND", "abilities": ["parse_request_text", "extract_entities"]},
            {"name": "PREPARE", "abilities": ["normalize_fields", "enrich_records", "add_flags_calculations"]},
            {"name": "ASK", "abilities": ["clarify_question"]},
            {"name": "WAIT", "abilities": ["extract_answer", "store_answer"]},
            {"name": "RETRIEVE", "abilities": ["knowledge_base_search", "store_data"]},
            {"name": "DECIDE", "abilities": ["solution_evaluation", "escalation_decision", "update_payload"]},
            {"name": "UPDATE", "abilities": ["update_ticket", "close_ticket"]},
            {"name": "CREATE", "abilities": ["response_generation"]},
            {"name": "DO", "abilities": ["execute_api_calls", "trigger_notifications"]},
            {"name": "COMPLETE", "abilities": ["output_payload"]},
        ]
    }

    init_state = {
        "customer_name": customer_name,
        "email": email,
        "query": query,
        "priority": "high",
        "ticket_id": 123
    }

    state = init_state.copy()
    human_input_index = 0

    for stage in config["stages"]:
        for ability in stage["abilities"]:
            ability_conf = ABILITIES[ability]
            
            if ability_conf["mode"] == "auto":
                result = mcp_call(ability_conf["server"], ability, state)
            elif ability_conf["mode"] == "human":
                # Use provided human input if available
                if human_inputs and human_input_index < len(human_inputs):
                    result = {ability: human_inputs[human_input_index]}
                    human_input_index += 1
                else:
                    # Return state to indicate human input needed
                    state["_human_input_needed"] = ability
                    return state
            else:
                raise ValueError(f"Unknown mode for ability {ability}")
            
            # Error handling
            if isinstance(result.get(ability), dict) and "error" in result[ability]:
                print(f"[ERROR] Ability {ability} failed: {result[ability]['error']}")
                state.update(result)
                continue
            
            state.update(result)
            
            # Escalation handling
            if ability == "escalation_decision" and result.get(ability, {}).get("escalate", False):
                print("[ESCALATION] Escalating to human agent...")
    
    return state
