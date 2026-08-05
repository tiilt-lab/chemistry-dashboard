"""
BLINC Agent V3 - Ultra Intelligent Agent

A fundamentally redesigned agent that relies on model intelligence
rather than keyword matching. Key principles:

1. Use powerful models (GPT-4o/Claude) for reasoning
2. Trust the model with well-written tool descriptions
3. Self-reflective retrieval with document grading
4. Query rewriting when retrieval fails
5. Explicit "think" tool for complex reasoning
6. Graph-aware retrieval with community summaries

This agent does NOT use deterministic keyword routing.
"""

from .graph import create_agent_graph, get_compiled_graph
from .routes import agent_v3_bp

__all__ = ['create_agent_graph', 'get_compiled_graph', 'agent_v3_bp']
