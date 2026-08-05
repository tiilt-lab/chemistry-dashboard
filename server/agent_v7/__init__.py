"""
BLINC Agent V7.2 - Pure ReAct Scaffolding Agent

A simplified agent architecture based on pure ReAct pattern:
- LLM decides what tools to call (no hardcoded routing)
- Tool guidance in system prompt for different query types
- Conversation memory for multi-turn context
- Scaffolded responses that point to specific evidence
- Artifact steering (user controls which tools to use)

Architecture:
- react_agent.py: Core ReAct loop - LLM decides tools
- prompts_v2.py: System prompt with tool selection guidance
- memory.py: Conversation context persistence
- tools_v2.py: Tool interface (wraps artifact_tools.py)
- steering.py: Extract and validate user steering preferences
- graph_v2.py: LangGraph wrapper for agent invocation
- routes_v2.py: Flask API endpoints
- tools/artifact_tools.py: Database queries (implementations)
- llm/: LLM client abstraction

Handler: V7_PURE_REACT
"""

# Core agent components (V7.2)
from .react_agent import ScaffoldingAgent, run_agent, AgentResponse

# Memory management
from .memory import ConversationMemory, get_memory, clear_memory

# Graph and routes (V7.2)
from .graph_v2 import create_agent_graph, get_graph, invoke_agent, reset_conversation
from .routes_v2 import agent_v7_bp

__all__ = [
    # Core agent
    'ScaffoldingAgent',
    'run_agent',
    'AgentResponse',
    # Memory
    'ConversationMemory',
    'get_memory',
    'clear_memory',
    # Graph/routes
    'create_agent_graph',
    'get_graph',
    'invoke_agent',
    'reset_conversation',
    'agent_v7_bp',
]
