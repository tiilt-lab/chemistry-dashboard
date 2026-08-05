"""
BLINC Agentic RAG System

This module implements an agentic query system for classroom discussion analysis.
It provides:
- Tool-based retrieval from multiple artifact types
- ReAct agent for simple queries
- Plan-Execute agent for complex queries
- Conversation state management
- Grounded response generation with citations
- Conversational UX with meta-intent classification, clarification, and fallback

Key Components:
- orchestrator: Main entry point, routes queries
- classifier: Determines query intent and complexity
- react_agent: Simple query handler with thought-action-observation loop
- plan_agent: Complex query handler with planning and execution
- state: Conversation state management
- grounding: Citation extraction and validation
- meta_intent: Pre-classifier for small talk, help, out-of-scope
- clarification: Smart clarification prompts for ambiguous queries
- fallback: Tiered fallback handling for errors
- tools/: All 17 agent tools
"""

__version__ = "1.1.0"

# Main entry point
from .orchestrator import AgentOrchestrator, get_orchestrator, OrchestratorResponse

# Query classification
from .classifier import (
    QueryClassifier,
    Classification,
    QueryIntent,
    QueryComplexity,
    ExtractedEntities,
    ReferenceResolver
)

# Agents
from .react_agent import ReActAgent, AgentResponse, AgentStep, AgentAction
from .plan_agent import PlanExecuteAgent, PlanAgentResponse, ExecutionPlan, PlanStep

# State management
from .state import ConversationState, ConversationStateManager

# Grounding
from .grounding import (
    GroundingValidator,
    GroundedResponse,
    Citation,
    CitationFormatter,
    ResponseFormatter
)

# Conversational UX
from .meta_intent import MetaIntentClassifier, MetaIntent, MetaClassification
from .clarification import (
    ClarificationEngine,
    ClarificationRequest,
    ClarificationType,
    PendingClarification
)
from .fallback import TieredFallbackHandler, FallbackResponse, FallbackTier, ErrorClassifier

__all__ = [
    # Main entry point
    'AgentOrchestrator',
    'get_orchestrator',
    'OrchestratorResponse',

    # Classification
    'QueryClassifier',
    'Classification',
    'QueryIntent',
    'QueryComplexity',
    'ExtractedEntities',
    'ReferenceResolver',

    # Agents
    'ReActAgent',
    'AgentResponse',
    'AgentStep',
    'AgentAction',
    'PlanExecuteAgent',
    'PlanAgentResponse',
    'ExecutionPlan',
    'PlanStep',

    # State
    'ConversationState',
    'ConversationStateManager',

    # Grounding
    'GroundingValidator',
    'GroundedResponse',
    'Citation',
    'CitationFormatter',
    'ResponseFormatter',

    # Conversational UX
    'MetaIntentClassifier',
    'MetaIntent',
    'MetaClassification',
    'ClarificationEngine',
    'ClarificationRequest',
    'ClarificationType',
    'PendingClarification',
    'TieredFallbackHandler',
    'FallbackResponse',
    'FallbackTier',
    'ErrorClassifier',
]
