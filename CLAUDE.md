# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a [CodeCrafters](https://codecrafters.io) challenge to build a Claude Code-like AI coding assistant. It implements an LLM-powered agent loop using the OpenAI-compatible API via OpenRouter, with tool-calling support.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the program:**
```bash
./your_program.sh -p "Your prompt here"
# or directly:
uv run --project . -m app.main -p "Your prompt here"
```

**Submit to CodeCrafters:**
```bash
codecrafters submit
```

## Environment

Requires a `.env` file with:
- `OPENROUTER_API_KEY` — API key for [OpenRouter](https://openrouter.ai/api/v1)

## Architecture

All logic lives in `app/main.py`. The flow is:

1. Parse `-p` prompt from CLI via `argparse`
2. Instantiate OpenAI client pointed at OpenRouter, using `anthropic/claude-haiku-4-5` model
3. Define tools as JSON Schema objects (currently: `ReadFile`)
4. Send prompt + tools to the LLM via `chat.completions`
5. If the response contains `tool_calls`, execute the requested tool and print the result
6. Print the LLM's final message content

This is a single-turn agent loop — it does not yet loop back with tool results for multi-turn interaction.

## Adding New Tools

Tools follow the OpenAI function-calling schema:
```python
{
    "type": "function",
    "function": {
        "name": "ToolName",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": { ... },
            "required": [...]
        }
    }
}
```

Add the definition to the `tools` list and handle the tool name in the tool dispatch block after the initial LLM call.
