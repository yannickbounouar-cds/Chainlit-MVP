import os
import chainlit as cl
from openai import AsyncAzureOpenAI
from mcp import ClientSession
import json

client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-01-01-preview",
    azure_endpoint="https://platform-core-hackathon-ndtibpy.openai.azure.com"
)

@cl.on_mcp_connect
def on_mcp_connect(connection, session: ClientSession):
    cl.user_session.set("mcp_session", session)

@cl.step(type="tool")
async def call_tool(tool_use):
    session = cl.user_session.get("mcp_session")
    return await session.call_tool(tool_use.name, tool_use.input)

@cl.on_message
async def main(message: cl.Message):
    session = cl.user_session.get("mcp_session")
    tools = []
    if session:
        result = await session.list_tools()
        tools = [
            {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
            for t in result.tools
        ]
    system_content = (
        "You are a helpful AI assistant.\n\nAvailable MCP tools:\n"
        f"{tools}\n\n"
        "If you want to call a tool, instead reply ONLY with a JSON object using double quotes for all keys and string values, and use true/false/null in lowercase (valid JSON only, no single quotes, no Python syntax). "
        "Example: {\"tool_name\": \"TOOL\", \"parameters\": {\"foo\": \"bar\"}}.\n"
        "If you do NOT want to call a tool, reply as a normal helpful assistant, NOT as a JSON object."
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": message.content}
    ]
    response = await client.chat.completions.create(
        model="openai-gpt4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
        stream=False
    )
    print(response)
    llm_reply = response.choices[0].message.content.strip()
    try:
        tool_call = json.loads(llm_reply)
    except Exception:
        tool_call = None
    # Only treat as a tool call if tool_name is a non-empty string
    if tool_call and tool_call.get("tool_name"):
        tool_name = tool_call["tool_name"]
        if tool_name:
            parameters = tool_call.get("parameters", {}) or {}
            await cl.Message(content=f"🔄 Calling tool `{tool_name}`...").send()
            tool_result = await call_tool(type('ToolUse', (), {"name": tool_name, "input": parameters})())
            await cl.Message(content=f"**Tool Result:**\n{tool_result}").send()
            return
    # Otherwise, just show the LLM reply
    await cl.Message(content=llm_reply).send()

if __name__ == "__main__":
    pass
