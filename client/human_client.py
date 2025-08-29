#client/human_client.py
def human_intervention(ability: str, state: dict) -> dict:
    """
    Handler for human-in-the-loop (HITL) abilities.
    Prompts the user for input and returns the result as a dict.
    """
    if ability == "clarify_question":
        prompt = "Could you please clarify your question to the customer?"
        print(f"[QUESTION TO SUPPORT TEAM] {prompt}")
        user_input = input(">>> ")
        state["clarify_question_input"] = user_input
        return {ability: user_input}
    elif ability == "extract_answer":
        prompt = state.get("clarify_question_input", "Can you share more details about your issue?")
        print(f"[QUESTION TO CUSTOMER] {prompt}")
        user_input = input(">>> ")
        return {ability: user_input}
    else:
        prompt = f"Could you help with the following request: {ability}?"
        print(prompt)
        user_input = input(">>> ")
        return {ability: user_input}
