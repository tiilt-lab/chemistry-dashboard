"""
LangGraph Agent V2 for BLINC

A modern LangGraph-based agent that integrates with the full RAG service capabilities.
Replaces the pattern-matching approach with LLM-driven classification and routing.
"""

from .graph import create_agent_graph, get_compiled_graph
from .state import AgentState

__all__ = [
    'create_agent_graph',
    'get_compiled_graph',
    'AgentState'
]
