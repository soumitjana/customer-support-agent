def human_intervention(ability: str, state: dict) -> dict:
    """
    Handler for human-in-the-loop (HITL) abilities.
    Prompts the user for input and returns the result as a dict.
    """
    print(f"[HUMAN] Please provide input for ability: {ability}")
    user_input = input(">>> ")
    return {ability: user_input} 
