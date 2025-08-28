#main.py
from client.mcp_client import MCPClient
from client.human_client import human_intervention
from utils.abilities import ABILITIES



# Define the workflow config (stages and abilities)
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


# Input state
init_state = {
    "customer_name": "Alice",
    "email": "alice@example.com",
    "query": "My app crashes on login",
    "priority": "high",
    "ticket_id": 123
}

def mcp_call(server, ability, state):
    client = MCPClient(server.lower())
    return client.call(ability, state.copy())

def run_workflow(config, init_state):
    state = init_state.copy()
    for stage in config["stages"]:
        for ability in stage["abilities"]:
            ability_conf = ABILITIES[ability]
            if ability_conf["mode"] == "auto":
                result = mcp_call(ability_conf["server"], ability, state)
            elif ability_conf["mode"] == "human":
                result = human_intervention(ability, state)
            else:
                raise ValueError(f"Unknown mode for ability {ability}")
            
            # Error handling: check if ability returned an error
            if isinstance(result.get(ability), dict) and "error" in result[ability]:
                print(f"[ERROR] Ability {ability} failed: {result[ability]['error']}")
                state.update(result)  # Still update to preserve error info
                continue
            
            state.update(result)
            
            # Loop handling: conditional escalation
            if ability == "escalation_decision" and result.get(ability, {}).get("escalate", False):
                print("[ESCALATION] Escalating to human agent...")
               
    return state

final_state = run_workflow(config, init_state)
print("\nFinal Payload:", final_state)