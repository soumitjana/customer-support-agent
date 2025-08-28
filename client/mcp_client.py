# client/mcp_client.py
from services.llm_service import LLMService
import json
from utils.abilities import COMMON_FUNCTIONS

class MCPClient:
    def __init__(self, server):
        self.server = server
        if server == "atlas":
            provider, model = self._detect_available_provider()
            self.llm = LLMService(provider=provider, model=model)
        
        else:
            self.llm = None  # Common server stays mocked

        self.ABILITY_PROMPTS = {
            "extract_entities": """
Extract product, action, and error keywords from state['query'].
Inputs:
- query: string
- email: string (optional)
Output:
- JSON { "software": str|None, "action": str|None, "error": str|None, "email_valid": bool }
Update state with extracted_* keys.
""",

            "enrich_records": """
Enrich the current ticket state with metadata.
Inputs: state JSON
Outputs: Return JSON object with fields:
- sla: SLA tier (Gold, Silver, Bronze) inferred from priority
- previous_tickets: integer (mock value if unknown)
- avg_resolution_time: string (e.g. "4h", "1d")
""",

            "clarify_question": """
If the query lacks details, generate ONE concise clarification
question in natural, empathetic language. Output: plain string.
""",

            "extract_answer": """
Listen for the user’s reply to a clarification question. 
Return a short, structured answer string only (no extra commentary).
""",

            "knowledge_base_search": """
Search for solutions in the knowledge base.
Inputs: state['query'] (customer's issue description).
If a KB exists, return:
{"found": true, "article_title": "...", "article_excerpt": "..."}
Else: {"found": false}
""",

            "escalation_decision": """
Decide whether to escalate to a human.
Inputs: state JSON, including solution_evaluation score (0–100).
Rule:
- If score < 90 → escalate = true
- Else → escalate = false
Output: {"escalate": true/false}
""",

            "update_ticket": """
Update the ticket fields in the state.
Inputs: state JSON
Allowed fields:
- status (open, pending, resolved)
- priority (low, medium, high)
- notes (string)
Output: JSON object with updated fields.
""",

            "close_ticket": """
You are responsible for closing tickets, but only if they meet strict conditions.

Inputs:
- state['ticket_id'] (integer)
- state['status'] (string)
- state['solution_evaluation'] (optional)

Rules:
1. If status == 'resolved':
    - Return JSON exactly in this format:
      {"ticket_id": <id>, "status": "closed", "resolution_notes": "<short summary>"}
    - The resolution_notes should mention the solution_evaluation score if available.
2. If status != 'resolved':
    - Do NOT attempt closure.
    - Instead return JSON exactly in this format:
      {"skipped": true, "reason": "Ticket not resolved yet"}
""",

            "execute_api_calls": """
Execute external CRM or order system API calls as needed.
Inputs: JSON with customer and ticket context.
Outputs: Return ONLY a JSON object:
{"success": true/false, "api": "<name>", "details": "<short description>"}
Do NOT return code snippets or tool calls.
""",

            "trigger_notifications": """
Send notification(s) to the customer.
Inputs:
- customer_name
- email
- ticket_id
- notification_type (created, updated, closed)
Output: Return ONLY a JSON object:
{"success": true/false, "notification_id": "<id>"}
Do NOT return code or tool invocations.
""",
        }

        self.ABILITY_TYPES = {
            "extract_entities": "json",
            "enrich_records": "json",
            "clarify_question": "string",
            "extract_answer": "string",
            "knowledge_base_search": "json",
            "escalation_decision": "json",
            "update_ticket": "json",
            "close_ticket": "json",
            "execute_api_calls": "json",
            "trigger_notifications": "json",
        }

    def _detect_available_provider(self):
        """Detect available LLM provider based on environment variables"""
        import os
        if os.environ.get('GEMINI_API_KEY'):
            return "gemini", "gemini-2.0-flash-exp"
        elif os.environ.get('OPENAI_API_KEY'):
            return "openai", "gpt-4o-mini"
        else:
            print("Warning: No API keys found. Using Gemini with mock responses.")
            return "gemini", "gemini-2.0-flash-exp"

    def safe_run_ability(self, ability_name, llm_output, expected_type="json"):
        if expected_type == "json":
            
            try:
                parsed = json.loads(llm_output)
                if isinstance(parsed, dict) and parsed.get("skipped") is True:
                    print(f"[INFO] Ability {ability_name} skipped: {parsed.get('reason', 'no reason provided')}")
                return parsed
            
            except Exception:
                if "{" in llm_output and "}" in llm_output:
                    try:
                        snippet = llm_output[llm_output.index("{"): llm_output.rindex("}")+1]
                        parsed = json.loads(snippet)
                        if isinstance(parsed, dict) and parsed.get("skipped") is True:
                            print(f"[INFO] Ability {ability_name} skipped: {parsed.get('reason', 'no reason provided')}")
                        
                        return parsed
                    
                    except Exception:
                        pass
                
                return {"error": f"Malformed output from {ability_name}", "raw": llm_output}
        
        elif expected_type == "string":
            return str(llm_output).strip()
        
        else:
            return {"error": f"Unsupported expected_type {expected_type}"}

    def call(self, ability, state):
        if self.server == "common":
            print(f"[MCP-COMMON] Running {ability}")
            func = COMMON_FUNCTIONS.get(ability)
            if func is None:
                state[ability] = f"{ability}_result"
                return state
            try:
                result = func(state.copy())
                if not isinstance(result, dict):
                    state[ability] = f"{ability}_result"
                    return state
                state.update(result)
                return state
            except Exception as e:
                state[ability] = f"{ability}_result"
                state.setdefault("errors", []).append(
                    {"ability": ability, "server": "COMMON", "error": str(e)}
                )
                return state

        if self.server == "atlas":
            print(f"[MCP-ATLAS] Running {ability}")
            try:
                prompt = self.ABILITY_PROMPTS.get(ability, f"Run ability {ability} with state: {state}")
                content = f"{prompt}\n\nState: {json.dumps(state)}"
                response = self.llm.complete([{"role": "user", "content": content}])
                parsed = self.safe_run_ability(
                    ability, response["content"], self.ABILITY_TYPES.get(ability, "json")
                )
                state[ability] = parsed
            except Exception as e:
                # Log error
                state.setdefault("errors", []).append(
                    {"ability": ability, "server": "ATLAS", "error": str(e)}
                )
                # Fallback mocks
                if ability == "extract_entities":
                    mock_output = '{"software": "App", "action": "login", "error": "crash", "email_valid": true}'
                elif ability == "enrich_records":
                    mock_output = '{"sla": "Gold", "previous_tickets": 2, "avg_resolution_time": "4h"}'
                elif ability == "clarify_question":
                    mock_output = "Could you provide more details about the issue?"
                elif ability == "extract_answer":
                    mock_output = "Windows 11"
                elif ability == "knowledge_base_search":
                    mock_output = '{"found": false}'
                elif ability == "escalation_decision":
                    score = state.get("solution_evaluation", {}).get("score", 50)
                    escalate = score < 90
                    mock_output = f'{{"escalate": {str(escalate).lower()}}}'
                elif ability == "update_ticket":
                    mock_output = '{"status": "pending", "priority": "high", "notes": "Waiting on user info"}'
                elif ability == "close_ticket":
                    ticket_status = state.get("status", "open")
                    ticket_id = state.get("ticket_id", 123)
                    escalate = state.get("escalation_decision", {}).get("escalate", False)
                    if ticket_status == "resolved" and not escalate:
                        mock_output = json.dumps({
                            "ticket_id": ticket_id,
                            "status": "closed",
                            "resolution_notes": f"Issue resolved. Solution evaluation score: {state.get('solution_evaluation', {}).get('score')}"
                        })
                    elif escalate:
                        mock_output = '{"error": "Ticket escalated, cannot close automatically"}'
                    else:
                        mock_output = '{"error": "Ticket not yet resolved, cannot close"}'
                elif ability == "execute_api_calls":
                    mock_output = '{"success": false, "reason": "no action required"}'
                elif ability == "trigger_notifications":
                    mock_output = '{"success": true, "notification_id": "mock_id"}'
                else:
                    mock_output = f'{{"mock": "{ability} response"}}'
                parsed = self.safe_run_ability(
                    ability, mock_output, self.ABILITY_TYPES.get(ability, "json")
                )
                state[ability] = parsed
            return state

        elif self.server == "human":
            print(f"[HUMAN] Waiting for {ability}")
            state[ability] = "user_provided_extra_info"
            return state
