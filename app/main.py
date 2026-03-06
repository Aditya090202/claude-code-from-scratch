import argparse
import json
import os
import string
import subprocess
import sys
import shlex
import re

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"rmdir",
    r"del\s+",
    r"format\s+",
    r"mkfs",
    r">\s*/dev/",
    r"dd\s+if=",
    r":\(\)\{",
    r"chmod\s+777",
    r"chown\s+-R",
    r"shutdown",
    r"reboot",
    r"halt",
    r"poweroff",
    r"pkill\s+-9",
    r"killall\s+-9",
]

DESTRUCTIVE_TOOLS = ["WriteToFile"]


class ToolPolicy:
    def __init__(self):
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """You are an AI coding assistant with access to tools. Follow these policies:

## Tool Use Guidelines

1. **ReadFile**: Use to inspect files before editing or to understand code structure
2. **WriteToFile**: Use to create or modify files - ALWAYS read first if the file might exist
3. **Bash**: Use to run commands, tests, git operations, or build scripts

## Safety Policy

- NEVER execute commands that could destroy data (rm -rf, format, etc.)
- NEVER execute commands you don't understand
- ALWAYS use ReadFile before WriteToFile on existing files
- Ask for confirmation before executing potentially dangerous commands

## Response Guidelines

- When you DON'T need tools, respond directly with your answer
- When you DO need tools, call them and then explain the results
- After using tools successfully, provide your final response and exit the tool use loop

When you are done and have the answer, exit the tool use loop (do not call more tools)."""

    def is_dangerous_command(self, command: str) -> bool:
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def requires_confirmation(self, tool_name: str, args: dict) -> bool:
        if tool_name == "WriteToFile":
            return True
        if tool_name == "Bash" and self.is_dangerous_command(args.get("command", "")):
            return True
        return False

    def should_use_tools(self, user_prompt: str) -> bool:
        action_keywords = [
            "create",
            "write",
            "edit",
            "modify",
            "delete",
            "remove",
            "run",
            "execute",
            "build",
            "test",
            "check",
            "find",
            "search",
            "list",
            "show",
            "display",
            "get",
            "read",
        ]
        prompt_lower = user_prompt.lower()
        return any(keyword in prompt_lower for keyword in action_keywords)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    policy = ToolPolicy()
    message_array = [
        {"role": "system", "content": policy.system_prompt},
        {"role": "user", "content": args.p},
    ]
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=message_array,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "ReadFile",
                        "description": "Read and return the contents of a file from disk",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "The absolute or relative path to a file",
                                },
                            },
                            "required": ["file_path"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "WriteToFile",
                        "description": "Write content to a file",
                        "parameters": {
                            "type": "object",
                            "required": ["file_path", "content"],
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "The relative path of the file",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The content of the file that you want to write to",
                                },
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "Bash",
                        "description": "Run commands in the shell",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "The command to execute in the shell",
                                }
                            },
                            "required": ["command"],
                        },
                    },
                },
            ],
        )

        # This checks if the result contains a tool_calls array if so execute the tool
        chat_message = chat.choices[0].message
        # Take the response of the LLM and store it in the messages array
        message_array.append(chat_message)

        if chat_message.tool_calls:
            extract_tool = chat_message.tool_calls
            tool_function = extract_tool[0].function
            tool_id = chat_message.tool_calls[0].id
            parse_function_name = tool_function.name

            parse_arguments = json.loads(tool_function.arguments)

            if policy.requires_confirmation(parse_function_name, parse_arguments):
                confirmation_msg = f"Confirm: Execute {parse_function_name} with {parse_arguments}? (yes/no)"
                message_array.append({"role": "user", "content": confirmation_msg})
                continue

            if parse_function_name == "ReadFile":
                # Grab the arguments for the read tool call, which is a file path
                parse_arguments = json.loads(tool_function.arguments)
                file_path = parse_arguments.get("file_path")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # take the result of your tool call and add it to the messages array
                message_array.append(
                    {"role": "tool", "tool_call_id": tool_id, "content": content}
                )
            if parse_function_name == "WriteToFile":
                parse_arguments = json.loads(tool_function.arguments)
                file_path = parse_arguments.get("file_path")
                content = parse_arguments.get("content")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                message_array.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": f"Wrote {len(content)} characters to {file_path}",
                    }
                )
            if parse_function_name == "Bash":
                parse_arguments = json.loads(tool_function.arguments)
                bash_command = parse_arguments.get("command")
                args = shlex.split(bash_command)
                result = subprocess.run(
                    args,
                    shell=False,
                    capture_output=True,
                    text=True,
                )
                if result.stderr:
                    message_array.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Error running the bash command: {result.stderr}",
                        }
                    )
                else:
                    message_array.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Output of the bash command {result.stdout}",
                        }
                    )
        else:
            break

    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # TODO: Uncomment the following line to pass the first stage
    print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
