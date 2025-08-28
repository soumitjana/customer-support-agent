# mcp_client.py
from services.llm_service import LLMService

class MCPClient:
    def __init__(self, server):
        self.server = server
        if server == "atlas":
            # For Atlas we use real external LLM
            self.llm = LLMService(provider="openai", model="gpt-4o-mini")
        else:
            self.llm = None  # Common server stays mocked

        ABILITY_PROMPTS = {
            "extract_entities": "Extract product, account, and dates from this query.",
            "enrich_records": "Add SLA and historical ticket info.",
            "clarify_question": "Ask a clarification question for missing details.",
            "extract_answer": "Wait and capture concise response",
            "knowledge_base_search": "Lookup knowledge base or FAQ",
            "escalation_decision": "Assign to human agent if score <90",
            "update_ticket": " Modify status, fields, priority of ticket",
            "close_ticket": "Mark issue resolved",
            "execute_api_calls": "Trigger CRM/order system actions",
            "trigger_notifications": "Send notifications to users"
        }


    def call(self, ability, state):
        if self.server == "common":
            print(f"[MCP-COMMON] Running {ability}")
            state[ability] = f"{ability}_result"
            return state

        elif self.server == "atlas":
            print(f"[MCP-ATLAS] Running {ability}")
            # Example: turn ability + state into a structured LLM prompt
            messages = [
                {"role": "system", "content": f"You are executing ability: {ability}"},
                {"role": "user", "content": f"Here is the current state: {state}"}
            ]
            response = self.llm.complete(messages)
            state[ability] = response["content"]
            return state

        elif self.server == "human":
            print(f"[HUMAN] Waiting for {ability}")
            state[ability] = "user_provided_extra_info"
            return state
