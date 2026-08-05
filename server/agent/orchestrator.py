"""
Agent Orchestrator

Main entry point for the agentic RAG system.
Routes queries to appropriate agents and manages conversation state.

Enhanced with conversational UX:
- Meta-intent classification (small talk, help, out-of-scope)
- Clarification prompts for ambiguous queries
- Tiered fallback handling
- Confidence communication
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .classifier import QueryClassifier, Classification, QueryComplexity, ReferenceResolver
from .react_agent import ReActAgent, AgentResponse
from .plan_agent import PlanExecuteAgent, PlanAgentResponse
from .grounding import GroundingValidator, GroundedResponse, ResponseFormatter
from .state import ConversationStateManager, ConversationState
from .meta_intent import MetaIntentClassifier, MetaIntent, MetaClassification
from .clarification import ClarificationEngine, ClarificationRequest, PendingClarification
from .fallback import TieredFallbackHandler, FallbackResponse, ErrorClassifier

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResponse:
    """Complete response from the orchestrator."""
    answer: str
    citations: List[Dict]
    confidence: float
    reasoning_trace: List[str]
    tools_used: List[str]
    follow_up_suggestions: List[str]
    conversation_id: str
    message_id: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    classification: Optional[Dict] = None
    execution_time_ms: float = 0.0
    # Conversational UX fields
    is_direct_response: bool = False  # True for small talk, help, out-of-scope
    needs_clarification: bool = False  # True when asking for clarification
    meta_intent: Optional[str] = None  # The detected meta-intent

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "answer": self.answer,
            "citations": self.citations,
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "tools_used": self.tools_used,
            "follow_up_suggestions": self.follow_up_suggestions,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "success": self.success,
            "error": self.error,
            "classification": self.classification,
            "execution_time_ms": self.execution_time_ms,
            "is_direct_response": self.is_direct_response,
            "needs_clarification": self.needs_clarification,
            "meta_intent": self.meta_intent
        }


class AgentOrchestrator:
    """
    Main orchestrator for the agentic RAG system.

    Responsibilities:
    1. Meta-intent classification (small talk, help, out-of-scope)
    2. Clarification handling for ambiguous queries
    3. Reference resolution using conversation context
    4. Query classification
    5. Route to ReAct or Plan-Execute agent
    6. Grounding validation with confidence communication
    7. Tiered fallback handling
    8. Conversation state management
    9. Response formatting
    """

    def __init__(self):
        """Initialize the orchestrator with all components."""
        # Core agent components
        self.classifier = QueryClassifier()
        self.react_agent = ReActAgent()
        self.plan_agent = PlanExecuteAgent()
        self.grounding_validator = GroundingValidator()
        self.state_manager = ConversationStateManager()
        self.reference_resolver = ReferenceResolver(self.state_manager)

        # Conversational UX components
        self.meta_classifier = MetaIntentClassifier()
        self.clarification_engine = ClarificationEngine()
        self.fallback_handler = TieredFallbackHandler()
        self.response_formatter = ResponseFormatter()

    def process_query(
        self,
        query: str,
        user_id: int,
        conversation_id: Optional[str] = None,
        session_device_id: Optional[int] = None
    ) -> OrchestratorResponse:
        """
        Process a user query through the agent system.

        Enhanced flow:
        1. Get/create conversation
        2. Meta-intent classification (small talk, help, out-of-scope)
        3. Handle direct responses or clarification responses
        4. Reference resolution
        5. Query classification
        6. Check for clarification needs
        7. Route to agent (ReAct or Plan-Execute)
        8. Grounding validation with confidence communication
        9. Update state and save messages
        10. Tiered fallback on errors

        Args:
            query: The user's question
            user_id: The authenticated user's ID
            conversation_id: Optional existing conversation ID
            session_device_id: Optional session context

        Returns:
            OrchestratorResponse with answer and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Get or create conversation
            if conversation_id:
                conversation = self._get_conversation(conversation_id)
                if not conversation:
                    conversation_id = self._create_conversation(
                        user_id, session_device_id, query
                    )
            else:
                conversation_id = self._create_conversation(
                    user_id, session_device_id, query
                )

            # Step 2: Meta-intent classification (conversational pre-processing)
            conversation_state = self.state_manager.get_state_as_dict(conversation_id)
            meta = self.meta_classifier.classify(query, conversation_state)
            logger.info(f"Meta-intent classified: {meta.intent.value} (confidence: {meta.confidence})")

            # Step 3: Handle non-domain queries immediately
            if meta.intent == MetaIntent.SMALL_TALK:
                return self._create_direct_response(
                    meta.suggested_response,
                    conversation_id,
                    start_time,
                    meta_intent=meta.intent.value,
                    suggestions=self.meta_classifier.get_starter_suggestions()
                )

            if meta.intent == MetaIntent.HELP_REQUEST:
                return self._create_direct_response(
                    meta.suggested_response,
                    conversation_id,
                    start_time,
                    meta_intent=meta.intent.value,
                    suggestions=self.meta_classifier.get_starter_suggestions()
                )

            if meta.intent == MetaIntent.OUT_OF_SCOPE:
                return self._create_direct_response(
                    meta.suggested_response,
                    conversation_id,
                    start_time,
                    meta_intent=meta.intent.value,
                    suggestions=self.meta_classifier.get_starter_suggestions()
                )

            # Step 4: Handle clarification responses
            if meta.intent == MetaIntent.CLARIFICATION_RESPONSE:
                return self._handle_clarification_response(
                    query, conversation_id, user_id, session_device_id, start_time
                )

            # Step 5: Handle ambiguous queries that need clarification
            if meta.intent == MetaIntent.IN_SCOPE_AMBIGUOUS:
                if meta.clarification_needed:
                    return self._request_clarification(
                        meta.clarification_needed,
                        query,
                        conversation_id,
                        start_time,
                        options=self.meta_classifier.get_starter_suggestions()
                    )

            # Step 6: Resolve references
            resolved_query, resolutions = self.reference_resolver.resolve(
                query, conversation_id
            )
            if resolutions:
                logger.debug(f"Resolved references: {resolutions}")

            # Step 7: Classify query for agent routing
            context = self._build_classification_context(
                conversation_id, session_device_id
            )
            classification = self.classifier.classify(resolved_query, context)
            logger.info(
                f"Query classified: intent={classification.intent.value}, "
                f"complexity={classification.complexity.value}"
            )

            # Step 8: Check if classification reveals need for clarification
            clarification = self.clarification_engine.check_needs_clarification(
                resolved_query, classification, conversation_state
            )
            if clarification:
                return self._request_clarification(
                    clarification.question,
                    query,
                    conversation_id,
                    start_time,
                    clarification_type=clarification.clarification_type.value,
                    options=clarification.options
                )

            # Step 9: Route to appropriate agent
            session_context = self._build_session_context(
                session_device_id, classification, conversation_id
            )

            if classification.complexity == QueryComplexity.SIMPLE:
                response = self._run_react_agent(
                    resolved_query, classification, session_context
                )
            else:
                response = self._run_plan_agent(
                    resolved_query, classification, session_context
                )

            # Step 10: Validate grounding
            tool_results = self._extract_tool_results(response)
            reasoning_trace = self._extract_reasoning_trace(response)

            logger.debug(f"Extracted {len(tool_results)} tool results")
            for i, tr in enumerate(tool_results):
                logger.debug(f"Tool result {i}: {tr.get('tool_name', 'unknown')}, success={tr.get('success')}")

            grounded = self.grounding_validator.validate_response(
                response.answer if hasattr(response, 'answer') else str(response),
                tool_results,
                reasoning_trace
            )

            logger.info(f"Grounding: confidence={grounded.confidence}, citations={len(grounded.citations)}")

            # Step 11: Check post-retrieval clarification needs
            # Lowered threshold from 0.3 to 0.2 to be more forgiving of vague queries
            if grounded.confidence < 0.2 and not grounded.citations:
                post_clarification = self.clarification_engine.check_post_retrieval_clarification(
                    query, [], grounded.confidence
                )
                if post_clarification:
                    return self._request_clarification(
                        post_clarification.question,
                        query,
                        conversation_id,
                        start_time,
                        clarification_type=post_clarification.clarification_type.value,
                        options=post_clarification.options
                    )

            # Step 12: Format response with confidence communication
            formatted_grounded = ResponseFormatter.format_response_with_confidence(grounded)

            # Step 13: Update conversation state
            self._update_conversation_state(
                conversation_id,
                classification,
                response,
                session_device_id
            )

            # Step 14: Reset failures on success
            self.state_manager.reset_failures(conversation_id)

            # Step 15: Save messages to database
            message_id = self._save_messages(
                conversation_id,
                query,
                formatted_grounded,
                response
            )

            execution_time = (time.time() - start_time) * 1000

            return OrchestratorResponse(
                answer=formatted_grounded.answer,
                citations=[c.to_dict() for c in formatted_grounded.citations],
                confidence=formatted_grounded.confidence,
                reasoning_trace=formatted_grounded.reasoning_trace,
                tools_used=response.tools_used if hasattr(response, 'tools_used') else [],
                follow_up_suggestions=formatted_grounded.follow_up_suggestions,
                conversation_id=conversation_id,
                message_id=message_id,
                success=True,
                classification=classification.to_dict(),
                execution_time_ms=execution_time,
                meta_intent=meta.intent.value
            )

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            execution_time = (time.time() - start_time) * 1000

            # Use tiered fallback handling
            return self._handle_error_with_fallback(
                e, query, conversation_id, user_id, session_device_id, execution_time
            )

    def _get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get existing conversation from database."""
        try:
            import database as db_helper
            return db_helper.get_agent_conversations(conversation_id=conversation_id)
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None

    def _create_conversation(
        self,
        user_id: int,
        session_device_id: Optional[int],
        first_query: str
    ) -> str:
        """Create a new conversation."""
        try:
            import database as db_helper

            # Generate title from first query
            title = first_query[:50] + "..." if len(first_query) > 50 else first_query

            conversation = db_helper.create_agent_conversation(
                user_id=user_id,
                session_device_id=session_device_id,
                title=title
            )
            return conversation.id
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return str(uuid.uuid4())

    def _build_classification_context(
        self,
        conversation_id: str,
        session_device_id: Optional[int]
    ) -> Dict:
        """Build context for classification."""
        context = {}

        # Get conversation state
        state = self.state_manager.get_state(conversation_id)
        if state:
            context['previous_session'] = state.current_session_focus
            context['previous_speaker'] = state.current_speaker_focus
            context['referenced_artifacts'] = state.referenced_artifacts

        # Add session context
        if session_device_id:
            context['current_session'] = session_device_id

        return context

    def _build_session_context(
        self,
        session_device_id: Optional[int],
        classification: Classification,
        conversation_id: Optional[str] = None
    ) -> Dict:
        """Build session context for agents including conversation state."""
        context = {}

        if session_device_id:
            context['session_device_id'] = session_device_id

        # Add resolved entities (with defensive None check)
        if classification and classification.entities:
            if classification.entities.session_device_ids:
                context['resolved_sessions'] = classification.entities.session_device_ids

        # Add session focus from conversation state (important for multi-turn)
        if conversation_id:
            state = self.state_manager.get_state(conversation_id)
            if state and state.current_session_focus:
                context['previous_session_focus'] = state.current_session_focus
                # If no explicit session, use the previous focus
                if not session_device_id and not context.get('resolved_sessions'):
                    context['session_device_id'] = state.current_session_focus
                    context['resolved_sessions'] = [state.current_session_focus]

        return context

    def _run_react_agent(
        self,
        query: str,
        classification: Classification,
        session_context: Dict
    ) -> AgentResponse:
        """Run the ReAct agent."""
        return self.react_agent.run(query, classification, session_context)

    def _run_plan_agent(
        self,
        query: str,
        classification: Classification,
        session_context: Dict
    ) -> PlanAgentResponse:
        """Run the Plan-Execute agent."""
        return self.plan_agent.run(query, classification, session_context)

    def _extract_tool_results(self, response) -> List[Dict]:
        """Extract tool results from agent response."""
        results = []

        if hasattr(response, 'steps'):
            # ReAct agent
            for step in response.steps:
                if hasattr(step, 'observation_data') and step.observation_data:
                    results.append({
                        'success': True,
                        'data': step.observation_data,
                        'tool_name': step.action.tool_name if step.action else ''
                    })
        elif hasattr(response, 'results'):
            # Plan-Execute agent
            for step_num, result in response.results.items():
                if hasattr(result, 'data'):
                    results.append({
                        'success': result.success,
                        'data': result.data,
                        'tool_name': ''
                    })

        return results

    def _extract_reasoning_trace(self, response) -> List[str]:
        """Extract reasoning trace from agent response."""
        trace = []

        if hasattr(response, 'steps'):
            # ReAct agent
            for step in response.steps:
                if hasattr(step, 'thought') and step.thought:
                    trace.append(f"Thought: {step.thought}")
                if hasattr(step, 'action') and step.action:
                    trace.append(f"Action: {step.action.tool_name}")
        elif hasattr(response, 'plan'):
            # Plan-Execute agent
            trace.append(f"Plan: {response.plan.reasoning}")
            for step in response.plan.steps:
                trace.append(f"Step {step.step}: {step.tool} - {step.purpose}")

        return trace

    def _update_conversation_state(
        self,
        conversation_id: str,
        classification: Classification,
        response,
        session_device_id: Optional[int]
    ):
        """Update conversation state based on the interaction."""
        state = self.state_manager.get_or_create_state(conversation_id)

        # Track all session IDs mentioned for comparisons
        all_session_ids = []

        # Update session focus - check multiple sources
        if session_device_id:
            state.set_session_focus(session_device_id)  # Use method to track history
            all_session_ids.append(session_device_id)
        elif classification and classification.entities and classification.entities.session_device_ids:
            for sid in classification.entities.session_device_ids:
                state.set_session_focus(sid)  # This tracks history
                all_session_ids.append(sid)
        else:
            # Try to extract session_device_id from tool results
            tool_results = self._extract_tool_results(response)
            for result in tool_results:
                data = result.get('data') or {}
                # Check direct session_device_id in result
                if data.get('session_device_id'):
                    sid = data['session_device_id']
                    state.set_session_focus(sid)
                    all_session_ids.append(sid)
                    break
                # Check in results array
                results_array = data.get('results', [])
                if results_array and isinstance(results_array, list):
                    for r in results_array[:1]:  # Check first result
                        if isinstance(r, dict) and r.get('session_device_id'):
                            sid = r['session_device_id']
                            state.set_session_focus(sid)
                            all_session_ids.append(sid)
                            break
                    if state.current_session_focus:
                        break
                # Check session_device_ids array
                session_ids = data.get('session_device_ids', [])
                if session_ids:
                    for sid in session_ids:
                        state.set_session_focus(sid)
                        all_session_ids.append(sid)
                    break

        # Check if compare_sessions was used and save compared sessions
        tools_used = getattr(response, 'tools_used', []) if response else []
        if 'compare_sessions' in tools_used and len(all_session_ids) >= 2:
            state.set_compared_sessions(list(set(all_session_ids)))
        elif classification and classification.entities and len(classification.entities.session_device_ids) >= 2:
            # If multiple sessions in classification, save as compared
            state.set_compared_sessions(classification.entities.session_device_ids)

        # Update speaker focus
        if classification and classification.entities and classification.entities.speakers:
            # Would need to resolve speaker name to ID
            pass

        # Update referenced artifacts
        if classification and classification.required_artifacts:
            state.referenced_artifacts.extend(classification.required_artifacts)
            state.referenced_artifacts = list(set(state.referenced_artifacts))[-10:]

        # Save state
        self.state_manager.save_state(conversation_id, state)

    def _save_messages(
        self,
        conversation_id: str,
        query: str,
        grounded: GroundedResponse,
        response
    ) -> Optional[int]:
        """Save user and assistant messages to database."""
        try:
            import database as db_helper

            # Save user message
            db_helper.add_agent_message(
                conversation_id=conversation_id,
                role='user',
                content=query
            )

            # Save assistant message
            assistant_msg = db_helper.add_agent_message(
                conversation_id=conversation_id,
                role='assistant',
                content=grounded.answer,
                citations=[c.to_dict() for c in grounded.citations],
                tools_used=response.tools_used if hasattr(response, 'tools_used') else [],
                reasoning_trace=grounded.reasoning_trace,
                confidence=grounded.confidence
            )

            return assistant_msg.id if assistant_msg else None

        except Exception as e:
            logger.error(f"Error saving messages: {e}")
            return None

    def _try_legacy_fallback(
        self,
        query: str,
        session_device_id: Optional[int]
    ) -> Optional[str]:
        """Try to use legacy RAG as fallback."""
        try:
            from rag_query_parser import QueryParser

            parser = QueryParser()
            result = parser.parse_and_execute(
                query,
                user_session_devices=[session_device_id] if session_device_id else None
            )

            if result.get('success') and result.get('results'):
                return result.get('answer') or result.get('results', [{}])[0].get('text', '')

        except Exception as e:
            logger.error(f"Legacy fallback failed: {e}")

        return None

    # =========================================================================
    # Conversational UX Helper Methods
    # =========================================================================

    def _create_direct_response(
        self,
        message: str,
        conversation_id: str,
        start_time: float,
        meta_intent: str = None,
        suggestions: List[str] = None
    ) -> OrchestratorResponse:
        """
        Create a direct response without agent processing.

        Used for small talk, help requests, and out-of-scope queries.
        """
        execution_time = (time.time() - start_time) * 1000

        return OrchestratorResponse(
            answer=message,
            citations=[],
            confidence=1.0,
            reasoning_trace=["Direct response (no retrieval needed)"],
            tools_used=[],
            follow_up_suggestions=suggestions or [],
            conversation_id=conversation_id,
            success=True,
            execution_time_ms=execution_time,
            is_direct_response=True,
            meta_intent=meta_intent
        )

    def _request_clarification(
        self,
        question: str,
        original_query: str,
        conversation_id: str,
        start_time: float,
        clarification_type: str = None,
        options: List[str] = None
    ) -> OrchestratorResponse:
        """
        Request clarification from the user.

        Stores pending clarification in conversation state for later resolution.
        """
        execution_time = (time.time() - start_time) * 1000

        # Store pending clarification in state
        pending_data = {
            "original_query": original_query,
            "clarification_type": clarification_type,
            "options": options or [],
            "expires_at": time.time() + 300  # 5 minute expiry
        }
        self.state_manager.set_pending_clarification(conversation_id, pending_data)

        return OrchestratorResponse(
            answer=question,
            citations=[],
            confidence=1.0,
            reasoning_trace=["Clarification requested"],
            tools_used=[],
            follow_up_suggestions=options or [],
            conversation_id=conversation_id,
            success=True,
            execution_time_ms=execution_time,
            needs_clarification=True,
            classification={"needs_clarification": True, "type": clarification_type}
        )

    def _handle_clarification_response(
        self,
        response: str,
        conversation_id: str,
        user_id: int,
        session_device_id: Optional[int],
        start_time: float
    ) -> OrchestratorResponse:
        """
        Handle a user's response to a clarification question.

        Resolves the clarification and re-processes the modified query.
        """
        # Get pending clarification
        pending_data = self.state_manager.get_pending_clarification(conversation_id)

        if not pending_data:
            # No pending clarification - treat as new query
            logger.debug("No pending clarification found, treating as new query")
            # Clear the flag and process normally
            self.state_manager.clear_pending_clarification(conversation_id)
            # Recursively process (without the CLARIFICATION_RESPONSE meta-intent)
            return self._process_as_new_query(
                response, user_id, conversation_id, session_device_id
            )

        # Resolve the clarification
        pending = PendingClarification.from_dict(pending_data)
        resolution = self.clarification_engine.resolve_clarification_response(
            response, pending
        )

        # Clear pending clarification
        self.state_manager.clear_pending_clarification(conversation_id)

        if resolution.get('action') == 'await_rephrase':
            # User wants to rephrase
            return self._create_direct_response(
                resolution.get('message', "Please ask your question in a different way."),
                conversation_id,
                start_time,
                suggestions=self.meta_classifier.get_starter_suggestions()
            )

        if resolution.get('action') == 'proceed_anyway':
            # User wants to see results anyway - reprocess original query
            return self._process_as_new_query(
                pending.original_query, user_id, conversation_id, session_device_id
            )

        if resolution.get('action') == 'use_selection':
            # User selected an option - process modified query
            modified_query = resolution.get('modified_query', pending.original_query)
            return self._process_as_new_query(
                modified_query, user_id, conversation_id, session_device_id
            )

        if resolution.get('action') == 'new_query_with_context':
            # User provided a new query with context
            return self._process_as_new_query(
                resolution.get('new_query', response), user_id, conversation_id, session_device_id
            )

        # Default: process response as new query
        return self._process_as_new_query(
            response, user_id, conversation_id, session_device_id
        )

    def _process_as_new_query(
        self,
        query: str,
        user_id: int,
        conversation_id: str,
        session_device_id: Optional[int]
    ) -> OrchestratorResponse:
        """
        Process a query after clearing clarification state.

        This prevents infinite loops by not re-triggering clarification response handling.
        """
        # Temporarily clear any pending clarification to prevent loop
        self.state_manager.clear_pending_clarification(conversation_id)

        # Re-process the query
        return self.process_query(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            session_device_id=session_device_id
        )

    def _handle_error_with_fallback(
        self,
        error: Exception,
        query: str,
        conversation_id: Optional[str],
        user_id: int,
        session_device_id: Optional[int],
        execution_time: float
    ) -> OrchestratorResponse:
        """
        Handle errors with tiered fallback strategy.

        Tier 1: Ask for rephrasing
        Tier 2: Show capability menu
        Tier 3: Offer example questions
        """
        conv_id = conversation_id or str(uuid.uuid4())

        # Classify the error
        error_type = ErrorClassifier.classify_error(error)

        # Try legacy fallback first
        fallback_response = self._try_legacy_fallback(query, session_device_id)
        if fallback_response:
            # Reset failures since we got a result
            if conversation_id:
                self.state_manager.reset_failures(conversation_id)

            return OrchestratorResponse(
                answer=fallback_response,
                citations=[],
                confidence=0.5,
                reasoning_trace=["Fallback to legacy RAG"],
                tools_used=[],
                follow_up_suggestions=[],
                conversation_id=conv_id,
                success=True,
                error="Used fallback",
                execution_time_ms=execution_time
            )

        # Get tiered fallback response
        fallback = self.fallback_handler.get_fallback(
            conv_id,
            error_type=error_type,
            original_query=query
        )

        # Update failure count in state
        if conversation_id:
            self.state_manager.increment_failure(conversation_id)

        return OrchestratorResponse(
            answer=fallback.message,
            citations=[],
            confidence=0.0,
            reasoning_trace=[f"Error: {str(error)}", f"Fallback tier: {fallback.tier.value}"],
            tools_used=[],
            follow_up_suggestions=fallback.suggestions,
            conversation_id=conv_id,
            success=False,
            error=str(error),
            execution_time_ms=execution_time
        )

    def get_welcome_message(self) -> Dict:
        """
        Get welcome message for new conversations.

        Returns a structured message for the frontend to display.
        """
        return {
            "message": (
                "Hello! I'm your Discussion Analysis Assistant. "
                "I can help you explore classroom transcripts, concept maps, "
                "collaboration metrics, and speaker patterns.\n\n"
                "What would you like to know about your discussions?"
            ),
            "suggestions": self.meta_classifier.get_starter_suggestions()
        }

    def get_conversation_history(
        self,
        conversation_id: str,
        user_id: int
    ) -> Optional[List[Dict]]:
        """Get conversation history for a user."""
        try:
            import database as db_helper

            # Verify ownership
            conversation = db_helper.get_agent_conversations(conversation_id=conversation_id)
            if not conversation or conversation.user_id != user_id:
                return None

            messages = db_helper.get_agent_messages(conversation_id)
            return [
                {
                    'id': m.id,
                    'role': m.role,
                    'content': m.content,
                    'citations': m.citations,
                    'tools_used': m.tools_used,
                    'confidence': m.confidence,
                    'created_at': m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ]

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return None

    def list_conversations(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """List user's conversations."""
        try:
            import database as db_helper

            conversations = db_helper.get_agent_conversations(
                user_id=user_id,
                limit=limit
            )

            return [
                {
                    'id': c.id,
                    'title': c.title,
                    'session_device_id': c.session_device_id,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                    'last_active': c.last_active.isoformat() if c.last_active else None
                }
                for c in conversations
            ]

        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []

    def delete_conversation(
        self,
        conversation_id: str,
        user_id: int
    ) -> bool:
        """Delete a conversation."""
        try:
            import database as db_helper

            # Verify ownership
            conversation = db_helper.get_agent_conversations(conversation_id=conversation_id)
            if not conversation or conversation.user_id != user_id:
                return False

            db_helper.delete_agent_conversation(conversation_id)

            # Clear state
            self.state_manager.clear_state(conversation_id)

            return True

        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False


# Global orchestrator instance
_global_orchestrator = None


def get_orchestrator() -> AgentOrchestrator:
    """Get the global orchestrator instance."""
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = AgentOrchestrator()
    return _global_orchestrator
