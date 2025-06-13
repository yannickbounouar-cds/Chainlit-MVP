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
    
    # First LLM call to determine if tool usage is needed
    response = await client.chat.completions.create(
        model="openai-gpt4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
        stream=False
    )
    
    llm_reply = response.choices[0].message.content.strip()
    
    try:
        tool_call = json.loads(llm_reply)
    except Exception:
        tool_call = None
    
    # Check if this is a tool call
    if tool_call and tool_call.get("tool_name"):
        tool_name = tool_call["tool_name"]
        if tool_name:
            parameters = tool_call.get("parameters", {}) or {}
            
            # Show tool execution message
            await cl.Message(content=f"🔄 Calling tool `{tool_name}`...").send()
            
            try:
                # Execute the tool
                tool_result = await call_tool(type('ToolUse', (), {"name": tool_name, "input": parameters})())
                
                # Extract clean content from tool result
                if hasattr(tool_result, 'content') and tool_result.content:
                    if isinstance(tool_result.content, list):
                        tool_content = "\n".join([
                            item.text if hasattr(item, 'text') else str(item) 
                            for item in tool_result.content
                        ])
                    else:
                        tool_content = str(tool_result.content)
                else:
                    tool_content = str(tool_result)
                
                # Create a new conversation with the tool result for the LLM to process
                synthesis_messages = [
                    {
                        "role": "system", 
                        "content": (
                            "You are a helpful AI assistant. A tool was just executed to help answer the user's question. "
                            "Please read the tool result and provide a natural, well-formatted response that directly addresses "
                            "the user's original question. Make the information clear, engaging, and easy to understand. "
                            "Format lists nicely with proper bullet points or numbering when appropriate."
                        )
                    },
                    {"role": "user", "content": f"Original question: {message.content}"},
                    {"role": "assistant", "content": f"I'll help you with that. Let me use the {tool_name} tool."},
                    {"role": "user", "content": f"Tool result: {tool_content}"},
                    {"role": "user", "content": "Please provide a natural, well-formatted response based on this tool result."}
                ]
                
                # Second LLM call to synthesize the tool result into a beautiful response
                synthesis_response = await client.chat.completions.create(
                    model="openai-gpt4o-mini",
                    messages=synthesis_messages,
                    temperature=0.3,  # Lower temperature for more focused responses
                    max_tokens=2000,
                    stream=False
                )
                
                final_answer = synthesis_response.choices[0].message.content.strip()
                await cl.Message(content=final_answer).send()
                
            except Exception as e:
                # Handle tool execution errors gracefully
                error_message = f"I encountered an error while using the {tool_name} tool: {str(e)}. Let me try to help you in another way."
                await cl.Message(content=error_message).send()
                
                # Fallback: provide a direct response without tools
                fallback_messages = [
                    {
                        "role": "system", 
                        "content": "You are a helpful AI assistant. Answer the user's question to the best of your ability without using external tools."
                    },
                    {"role": "user", "content": message.content}
                ]
                
                fallback_response = await client.chat.completions.create(
                    model="openai-gpt4o-mini",
                    messages=fallback_messages,
                    temperature=0.7,
                    max_tokens=1500,
                    stream=False
                )
                
                fallback_answer = fallback_response.choices[0].message.content.strip()
                await cl.Message(content=fallback_answer).send()
            
            return
    
    # If no tool call, just show the LLM reply
    await cl.Message(content=llm_reply).send()

if __name__ == "__main__":
    pass
