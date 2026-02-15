import argparse
import json
import os
import string
import sys

from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=base_url)

    chat = client.chat.completions.create(
        model="anthropic/claude-haiku-4.5",
        messages=[{"role": "user", "content": args.p}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "Read and return the contents of a file from disk",
                    "parameters": {
                        "type":"object",
                        "properties": {
                          "file_path": {
                            "type": "string",
                            "description": "The absolute or relative path to a file"
                           },  
                        },
                        "required": ["file_path"]
                    },
                }
            }
        ]
    )

    # This checks if the result contains a tool_calls array if so execute the tool
    chat_message = chat.choices[0].messages

    if tool_calls in chat_message:
        extract_tool = chat_message.tool_calls
        tool_function = extract_tool[0].get("function")
        parse_function_name = tool_function.get("name")
        if parse_function_name == "ReadFile":
            #Grab the arguments for the read tool call, which is a file path
            parse_arguments = json.loads(tool_function.get("arguments"))
            file_path = parse_arguments.get("file_path")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(content)






    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # TODO: Uncomment the following line to pass the first stage
    print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
