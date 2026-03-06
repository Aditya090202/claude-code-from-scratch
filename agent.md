# agent.md

This file provides guidance for AI agents working on this codebase.

## Project Purpose

Build a Claude Code-like AI coding assistant that uses an LLM (via OpenRouter) with tool-calling capabilities to execute coding tasks.

## Key Files

- `app/main.py` — Core agent loop and tool implementation
- `app/tools/` — Directory for tool implementations (currently empty stubs)
- `app/agent/` — Agent logic (loop, models, policy - currently empty stubs)

## Current Implementation

The main loop in `app/main.py`:
1. Parses `-p` argument for user prompt
2. Creates OpenAI client with OpenRouter
3. Sends prompt with 3 tools (ReadFile, WriteToFile, Bash)
4. Executes tool calls if LLM requests them
5. Returns final LLM response

## Working on This Codebase

- **Environment**: Requires `OPENROUTER_API_KEY` in `.env`
- **Run**: `./your_program.sh -p "prompt"` or `uv run -m app.main -p "prompt"`
- **Add tools**: Define in JSON Schema format in `main.py` tools list and handle in the tool dispatch block

## Extension Points

- Implement actual tool modules in `app/tools/`
- Add `ListDir` and `SearchFiles` tools (stubs exist but are empty)
- Implement multi-turn agent loop in `app/agent/loop.py`
- Add agent models in `app/agent/models.py`
- Add policy logic in `app/agent/policy.py`
