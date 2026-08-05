"""
Nodes for BLINC Agent V3 LangGraph workflow.

Simplified architecture (4-stage PRAS, no ReAct fallback):
- decompose → retrieve → reason → synthesize

Each node is a function that takes state and returns updated state.
"""

from .input_processor import process_input
from .synthesize import synthesize
from .reflect import reflect
from .format_response import format_response
from .query_router import execute_fast_path
from .verify_claims import verify_claims, format_verification_for_response

# PRAS nodes (simplified 4-stage architecture)
from .query_decomposer import decompose_query, should_use_pras
from .targeted_retriever import targeted_retrieve, should_continue_retrieval
from .cross_rep_reasoner import reason_across_representations, extract_key_claims
from .grounded_synthesizer import synthesize_grounded_response

# NOTE: ReAct nodes removed (reason_and_act, execute_tool, grade_results, rewrite_query)
# NOTE: plan_retrieval now internal to targeted_retrieve (deterministic planning)

__all__ = [
    # Core nodes
    'process_input',
    'synthesize',
    'reflect',
    'format_response',
    'execute_fast_path',
    # Verification
    'verify_claims',
    'format_verification_for_response',
    # PRAS nodes (simplified 4-stage)
    'decompose_query',
    'should_use_pras',
    'targeted_retrieve',
    'should_continue_retrieval',
    'reason_across_representations',
    'extract_key_claims',
    'synthesize_grounded_response'
]
