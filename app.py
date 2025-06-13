import os
import chainlit as cl
from openai import AsyncAzureOpenAI
from mcp import ClientSession
import json
import asyncio

client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-01-01-preview",
    azure_endpoint="https://platform-core-hackathon-ndtibpy.openai.azure.com"
)

@cl.on_chat_start
async def start():
    """Initialize conversation history"""
    cl.user_session.set("conversation_history", [])
    await cl.Message("👋 Hello! I'm your AI assistant with access to various tools. How can I help you today?").send()

@cl.on_mcp_connect
async def on_mcp_connect(connection, session: ClientSession):
    """Handle connection to multiple MCP servers"""
    # Store sessions by connection name
    mcp_sessions = cl.user_session.get("mcp_sessions", {})
    mcp_sessions[connection.name] = session
    cl.user_session.set("mcp_sessions", mcp_sessions)
    
    await cl.Message(f"✅ Connected to MCP server: **{connection.name}**").send()

    try:
        result = await session.list_tools()
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
                "server": connection.name
            }
            for t in result.tools
        ]

        # Store tools by server
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection.name] = tools
        cl.user_session.set("mcp_tools", mcp_tools)
        
        tools_info = {tool["name"]: f"{tool['description']} (from {connection.name})" for tool in tools}
        await cl.Message(
            f"🔧 Found **{len(tools)}** tools from **{connection.name}**:\n" + 
            "\n".join([f"• **{name}**: {desc}" for name, desc in tools_info.items()])
        ).send()
        
    except Exception as e:
        await cl.Message(f"❌ Error listing tools from {connection.name}: {str(e)}").send()

@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session: ClientSession):
    """Handle disconnection from MCP servers"""
    # Remove session
    mcp_sessions = cl.user_session.get("mcp_sessions", {})
    if name in mcp_sessions:
        del mcp_sessions[name]
        cl.user_session.set("mcp_sessions", mcp_sessions)

    # Remove tools
    mcp_tools = cl.user_session.get("mcp_tools", {})
    if name in mcp_tools:
        del mcp_tools[name]
        cl.user_session.set("mcp_tools", mcp_tools)

    await cl.Message(f"❌ Disconnected from MCP server: **{name}**").send()

def find_tool_server(tool_name: str) -> tuple[str, ClientSession]:
    """Find which MCP server provides a specific tool"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_sessions = cl.user_session.get("mcp_sessions", {})
    
    for server_name, tools in mcp_tools.items():
        for tool in tools:
            if tool["name"] == tool_name:
                if server_name in mcp_sessions:
                    return server_name, mcp_sessions[server_name]
                else:
                    raise Exception(f"Tool '{tool_name}' found but server '{server_name}' is not connected")
    
    raise Exception(f"Tool '{tool_name}' not found in any connected MCP server")

@cl.step(type="tool")
async def call_tool(tool_use):
    """Execute tool on the appropriate MCP server"""
    try:
        # Find which server provides this tool
        server_name, session = find_tool_server(tool_use.name)
        
        print(f"[DEBUG] Calling tool '{tool_use.name}' on server '{server_name}'")
        
        # Execute tool with timeout
        result = await asyncio.wait_for(
            session.call_tool(tool_use.name, tool_use.input),
            timeout=30.0
        )
        
        print(f"[DEBUG] Tool '{tool_use.name}' completed successfully on '{server_name}'")
        return result
        
    except asyncio.TimeoutError:
        raise Exception(f"Tool '{tool_use.name}' execution timed out after 30 seconds")
    except Exception as e:
        raise Exception(f"Tool execution failed: {str(e)}")

def get_all_available_tools() -> list:
    """Get all tools from all connected MCP servers"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    all_tools = []
    
    for server_name, tools in mcp_tools.items():
        for tool in tools:
            # Add server context to tool info
            tool_with_server = tool.copy()
            tool_with_server["display_name"] = f"{tool['name']} (via {server_name})"
            all_tools.append(tool_with_server)
    
    return all_tools

def add_to_conversation_history(role: str, content: str, tool_info: dict = None):
    """Add message to conversation history with optional tool information"""
    conversation_history = cl.user_session.get("conversation_history", [])
    
    message_entry = {
        "role": role,
        "content": content,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    if tool_info:
        message_entry["tool_info"] = tool_info
    
    conversation_history.append(message_entry)
    
    # Keep only last 20 messages to prevent context window overflow
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    cl.user_session.set("conversation_history", conversation_history)

def build_conversation_messages(current_message: str, all_tools: list) -> list:
    """Build complete conversation context for LLM"""
    conversation_history = cl.user_session.get("conversation_history", [])
    
    # Build system prompt with tools
    if all_tools:
        tools_list = "\n".join([
            f"- **{tool['name']}**: {tool['description']} (via {tool['server']})"
            for tool in all_tools
        ])
        system_content = (
            "You are a helpful AI assistant with access to multiple MCP tools and conversation memory.\n\n"
            f"**Available tools:**\n{tools_list}\n\n"
            "**IMPORTANT TOOL USAGE RULES:**\n"
            "- ALWAYS use a tool when the user asks for specific data, services, information that requires external APIs\n"
            "- ALWAYS use a tool when the user mentions tool names like 'gcnotify', 'news', etc.\n"
            "- ALWAYS use a tool when the user asks to 'get', 'fetch', 'retrieve', 'list', 'show' specific data\n"
            "- If you want to call a tool, reply ONLY with a JSON object using the exact tool name (without server suffix)\n"
            "- Use double quotes for all keys and string values, and use true/false/null in lowercase\n"
            "- Example: {\"tool_name\": \"EXACT_TOOL_NAME\", \"parameters\": {\"param\": \"value\"}}\n"
            "- If you do NOT want to call a tool, reply as a normal helpful assistant, NOT as a JSON object\n"
            "- You remember previous conversations and can reference them naturally\n"
            "- When in doubt about whether to use a tool, USE THE TOOL - it's better to provide real data\n\n"
            "**Examples of when to use tools:**\n"
            "- 'get gcnotify services' -> use gcnotify tool\n"
            "- 'show me the news' -> use news tool\n"
            "- 'list services' -> use appropriate service tool\n"
            "- 'what's happening in canada' -> use news tool"
        )
    else:
        system_content = (
            "You are a helpful AI assistant with conversation memory. "
            "Currently, no MCP tools are available. "
            "Answer questions using your general knowledge and remember previous conversations."
        )
    
    # Start with system message
    messages = [{"role": "system", "content": system_content}]
    
    # Add conversation history (convert to OpenAI format)
    for entry in conversation_history:
        # Skip tool info for OpenAI messages, but preserve the content
        messages.append({
            "role": entry["role"],
            "content": entry["content"]
        })
    
    # Add current user message
    messages.append({"role": "user", "content": current_message})
    
    return messages

@cl.on_message
async def main(message: cl.Message):
    """Main message handler with improved tool detection"""
    mcp_sessions = cl.user_session.get("mcp_sessions", {})
    all_tools = get_all_available_tools()
    
    # Add user message to conversation history
    add_to_conversation_history("user", message.content)
    
    # Show connection status for first message
    conversation_history = cl.user_session.get("conversation_history", [])
    if len(conversation_history) <= 1 and not mcp_sessions:
        await cl.Message("⚠️ No MCP servers connected. Some functionality may be limited.").send()
    elif len(conversation_history) <= 1 and mcp_sessions:
        connected_servers = list(mcp_sessions.keys())
        print(f"[DEBUG] Connected to {len(connected_servers)} MCP servers: {connected_servers}")
    
    # Enhanced tool detection - check for keywords that suggest tool usage
    user_message_lower = message.content.lower()
    tool_keywords = ['get', 'fetch', 'retrieve', 'list', 'show', 'find', 'search', 'gcnotify', 'news', 'services']
    contains_tool_keyword = any(keyword in user_message_lower for keyword in tool_keywords)
    
    # Build conversation context
    messages = build_conversation_messages(message.content, all_tools)
    
    # If we detect tool-related keywords and have tools available, be more explicit
    if contains_tool_keyword and all_tools:
        # Add an additional instruction to encourage tool usage
        messages.append({
            "role": "system", 
            "content": "The user's request seems to require external data. You should likely use one of the available tools to provide accurate, up-to-date information rather than guessing."
        })
    
    try:
        # First LLM call to determine if tool usage is needed
        response = await client.chat.completions.create(
            model="openai-gpt4o-mini",
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent tool usage
            max_tokens=1500,
            stream=False
        )
        
        llm_reply = response.choices[0].message.content.strip()
        print(f"[DEBUG] LLM response: {llm_reply[:200]}...")
        
        # Try to parse as tool call
        try:
            tool_call = json.loads(llm_reply)
            print(f"[DEBUG] Parsed tool call: {tool_call}")
        except Exception as e:
            print(f"[DEBUG] Not a tool call, parsing error: {e}")
            tool_call = None
        
        # Check if this is a valid tool call
        if tool_call and tool_call.get("tool_name") and all_tools:
            tool_name = tool_call["tool_name"]
            parameters = tool_call.get("parameters", {}) or {}
            
            try:
                # Find which server provides this tool
                server_name, _ = find_tool_server(tool_name)
                
                # Show tool execution message with server info
                await cl.Message(content=f"🔄 Calling **{tool_name}** via **{server_name}**...").send()
                
                print(f"[DEBUG] Executing tool: {tool_name} with parameters: {parameters}")
                
                # Execute the tool
                tool_result = await call_tool(type('ToolUse', (), {"name": tool_name, "input": parameters})())
                print(f"[DEBUG] Tool result type: {type(tool_result)}")
                
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
                
                print(f"[DEBUG] Extracted content length: {len(tool_content)}")
                
                # Build synthesis messages with conversation context
                synthesis_messages = [
                    {
                        "role": "system", 
                        "content": (
                            "You are a helpful AI assistant with conversation memory. A tool was executed to help answer the user's question. "
                            "Read the tool result and provide a natural, well-formatted response that directly addresses "
                            "the user's original question. Make the information clear, engaging, and easy to understand. "
                            "Format lists with proper bullet points or numbering when appropriate. "
                            "DO NOT DELETE ANY INFORMATION FROM THE TOOL RESULT. "
                            "Reference previous conversation context if relevant to provide better assistance."
                        )
                    }
                ]
                
                # Add relevant conversation history for context
                recent_history = cl.user_session.get("conversation_history", [])[-5:]  # Last 5 messages
                for entry in recent_history[:-1]:  # Exclude current message
                    synthesis_messages.append({
                        "role": entry["role"],
                        "content": entry["content"]
                    })
                
                # Add current context
                synthesis_messages.extend([
                    {"role": "user", "content": message.content},
                    {"role": "assistant", "content": f"I used the {tool_name} tool via {server_name}."},
                    {"role": "user", "content": f"Tool result: {tool_content}"},
                    {"role": "user", "content": "Please provide a natural, well-formatted response based on this result and our conversation history."}
                ])
                
                synthesis_response = await client.chat.completions.create(
                    model="openai-gpt4o-mini",
                    messages=synthesis_messages,
                    temperature=0.3,
                    max_tokens=2000,
                    stream=False
                )
                
                final_answer = synthesis_response.choices[0].message.content.strip()
                
                # Add assistant response to conversation history with tool info
                add_to_conversation_history("assistant", final_answer, {
                    "tool_used": tool_name,
                    "server": server_name,
                    "parameters": parameters
                })
                
                await cl.Message(content=final_answer).send()
                
            except Exception as e:
                # Handle tool execution errors gracefully
                print(f"[ERROR] Tool execution failed: {str(e)}")
                error_message = f"❌ Error using **{tool_name}**: {str(e)}\n\nLet me try to help you in another way."
                await cl.Message(content=error_message).send()
                
                # Fallback response with conversation context
                fallback_messages = build_conversation_messages(
                    f"The tool failed, please answer this question using your knowledge: {message.content}", 
                    []
                )
                fallback_messages[0]["content"] = "You are a helpful AI assistant with conversation memory. Answer the user's question using your general knowledge since tools are unavailable."
                
                fallback_response = await client.chat.completions.create(
                    model="openai-gpt4o-mini",
                    messages=fallback_messages,
                    temperature=0.7,
                    max_tokens=1500,
                    stream=False
                )
                
                fallback_answer = fallback_response.choices[0].message.content.strip()
                add_to_conversation_history("assistant", fallback_answer)
                await cl.Message(content=fallback_answer).send()
            
            return
        
        # If we detected tool keywords but LLM didn't use a tool, suggest it
        elif contains_tool_keyword and all_tools and not tool_call:
            print(f"[DEBUG] Tool keywords detected but no tool used. Suggesting tool usage.")
            suggestion_msg = f"It looks like you're asking for specific data. I have access to tools that can help. Would you like me to use the available tools to get you that information? Available tools: {', '.join([tool['name'] for tool in all_tools])}"
            add_to_conversation_history("assistant", suggestion_msg)
            await cl.Message(content=suggestion_msg).send()
            return
        
        elif tool_call and tool_call.get("tool_name") and not all_tools:
            response_msg = "🔧 I wanted to use a tool to help you, but no MCP servers are currently connected. Let me answer with my general knowledge and our conversation history."
            add_to_conversation_history("assistant", response_msg)
            await cl.Message(content=response_msg).send()
        
        # No tool call - show regular LLM response with conversation memory
        add_to_conversation_history("assistant", llm_reply)
        await cl.Message(content=llm_reply).send()
        
    except Exception as e:
        print(f"[ERROR] Main function error: {str(e)}")
        error_msg = f"❌ I encountered an error: {str(e)}"
        add_to_conversation_history("assistant", error_msg)
        await cl.Message(content=error_msg).send()

if __name__ == "__main__":
    pass
