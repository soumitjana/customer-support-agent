# Langie — Customer Support Agent (LangGraph)

This repository contains a lightweight LangGraph-based customer support agent named "Langie". It demonstrates a staged workflow orchestration pattern where deterministic, non-deterministic, and human-in-the-loop abilities are composed to process customer support requests.

## Table of Contents

- Prerequisites
- Quick start
- Logical flow (stages)
- File responsibilities
- How the agent components interact
- Next phases
- Notes

## Prerequisites

- Python 3.11+ installed and available on PATH
- Basic familiarity with virtual environments and installing Python packages
- An API key for an LLM provider (OpenAI or Gemini) if you want Atlas abilities to call a live model

You will store the API key in a `.env` file at the project root (see Quick start).

## Quick start

1. Create a `.env` file in the project root and add one of the following keys depending on your provider:

   - For OpenAI:
     OPENAI_API_KEY=sk-... 

   - For Gemini:
     GEMINI_API_KEY=ya29....

2. Create and activate a virtual environment:

   python -m venv .venv
   .venv\Scripts\Activate

3. Install dependencies:

   pip install -r requirements.txt

4. Run the agent:

   python main.py

Notes:
- If no API key is provided, the code prints a warning and continues with mocked responses for Atlas abilities.
- On Windows PowerShell, use the provided activation command above; for other shells adapt accordingly.

## Logical flow (stages)

The orchestrator (`main.py`) runs a sequence of stages defined in `config.yaml`. Each stage contains one or more abilities. Abilities are small functional units that accept the current `state` and return a partial update. Stages in `config.yaml` represent the high-level pipeline:

- INTAKE — capture the incoming payload and initialize state containers
- UNDERSTAND — parse the request text and extract entities (LLM-powered when using Atlas)
- PREPARE — normalize fields, enrich records, and compute flags
- ASK — human-in-the-loop clarification when required
- WAIT — capture a human or upstream answer, store it
- RETRIEVE — knowledge base search (RAG target for next phase) and store data
- DECIDE — evaluate candidate solutions, decide if escalation is required
- UPDATE — update or close the ticket in the external system (mocked)
- CREATE — generate a customer-facing response
- DO — execute API calls or trigger notifications
- COMPLETE — output the final payload

The orchestrator iterates these stages and passes the evolving `state` between abilities. If an ability indicates escalation, the orchestrator routes to human intervention.

## File responsibilities

- `main.py` — The orchestration entrypoint. Loads the stage configuration, prompts the user for a simple initial payload, and runs the workflow loop which dispatches abilities by mode (auto vs human).

- `config.yaml` — The canonical skeleton of the agent's staged flow. Each stage lists abilities and the intended mode (deterministic, human, non-deterministic).

- `utils/abilities.py` — The canonical COMMON abilities registry and implementations. These are deterministic/state-centric helpers that transform or annotate the `state` object. Abilities return a single-key dict whose key is the ability name and whose value contains the result or updated sub-objects.

- `services/llm_service.py` — The LLM abstraction layer. Implements functions to call completions (sync and async), supports caching and provider selection (OpenAI, Anthropic, Gemini) and formats responses for the caller.

- `client/mcp_client.py` — The multi-control-plane client. Routes ability calls to either the `COMMON` functions (local deterministic behavior) or to `ATLAS` which uses the `LLMService` to invoke the model with ability-specific prompts. It also contains safe parsing of LLM outputs so outputs can be passed to the next stage.

- `client/human_client.py` — Human-in-the-loop helper that prompts a human operator for clarifications and customer replies. The orchestrator uses this for abilities marked as human.

## How components interact

1. `main.py` builds an initial `state` and reads `config.yaml` (the current project contains an inline config and a single `config.yaml` file which mirrors the stages).
2. For each ability, `main.py` consults the `ABILITIES` registry in `utils/abilities.py` to determine whether the ability is `auto` (run locally via `COMMON` functions) or `human` (use `human_client`) or `atlas` (LLM-backed via `mcp_client`).
3. `client/mcp_client.MCPClient` runs `COMMON` functions directly or sends an ability prompt to `services.llm_service.LLMService` when the server is `atlas`.
4. Atlas responses are parsed safely by `MCPClient.safe_run_ability`, which attempts JSON parsing and graceful degradation for malformed LLM outputs.
5. The orchestrator updates the `state` with each ability's output and continues. If `escalation_decision` indicates escalation, the orchestrator triggers human intervention.

## Next phases

- RAG (Retrieval-Augmented Generation) implementation for `knowledge_base_search` — integrate a document store (e.g., FAISS, Chroma, or a cloud vector DB), add an indexing pipeline, and wire retrieval into Atlas prompts so the LLM can ground answers in KB articles.
- Front-end UI with streaming messages — implement a small web UI (FastAPI/Flask + WebSockets or a React frontend) to stream model/human messages to operators and customers in real time.

## Notes and tips

- The repository is intentionally small and modular to make extending individual abilities straightforward.
- The ABILITIES registry in `utils/abilities.py` serves both as documentation and a dispatcher mapping ability names to server/mode settings.
- When adding a real LLM key, ensure you do not check the `.env` file or any secrets into source control.
- Add unit tests around `utils/abilities.py` behaviors and `client/mcp_client.safe_run_ability` to increase confidence before enabling live LLM calls.

This README reflects the current implementation and configuration in the repository. See `Lang_Graph_Agent.docx` for the original task description followed while implementing the agent.
