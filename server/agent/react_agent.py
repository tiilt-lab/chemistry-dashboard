"""
ReAct Agent

Implements a thought-action-observation loop for simple queries.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from dotenv import load_dotenv
load_dotenv()

import openai

from .tools import get_tool_registry, ToolResult
from .classifier import Classification, QueryIntent

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    """Represents an action the agent takes."""
    tool_name: str
    tool_input: Dict[str, Any]
    thought: str


@dataclass
class AgentStep:
    """A single step in the agent's reasoning."""
    thought: str
    action: Optional[AgentAction] = None
    observation: Optional[str] = None
    observation_data: Optional[Any] = None


@dataclass
class AgentResponse:
    """Complete response from the agent."""
    answer: str
    steps: List[AgentStep]
    tools_used: List[str]
    success: bool
    error: Optional[str] = None
    citations: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "answer": self.answer,
            "steps": [
                {
                    "thought": s.thought,
                    "action": {
                        "tool": s.action.tool_name,
                        "input": s.action.tool_input
                    } if s.action else None,
                    "observation": s.observation
                }
                for s in self.steps
            ],
            "tools_used": self.tools_used,
            "success": self.success,
            "error": self.error,
            "citations": self.citations
        }


class ReActAgent:
    """
    ReAct agent for simple queries.

    Uses a thought-action-observation loop to gather information
    and answer questions about classroom discussions.
    """

    DEFAULT_MAX_ITERATIONS = 3
    GRAPH_MAX_ITERATIONS = 5  # More iterations for graph traversal

    def __init__(self):
        """Initialize the agent."""
        self._client = None
        self.registry = get_tool_registry()
        self._load_prompts()

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = openai.OpenAI()
        return self._client

    def _load_prompts(self):
        """Load prompt templates."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'prompts'
        )

        # Load system prompt
        system_path = os.path.join(prompts_dir, 'react_system.txt')
        try:
            with open(system_path, 'r') as f:
                self.system_template = f.read()
        except FileNotFoundError:
            self.system_template = self._get_default_system_prompt()

        # Load thought prompt
        thought_path = os.path.join(prompts_dir, 'react_thought.txt')
        try:
            with open(thought_path, 'r') as f:
                self.thought_template = f.read()
        except FileNotFoundError:
            self.thought_template = self._get_default_thought_prompt()

    def _get_default_system_prompt(self) -> str:
        """Default system prompt if file not found."""
        return """You are an assistant that helps analyze classroom discussions.

Available tools:
{tool_descriptions}

Work in a loop:
1. Thought: What do you need to find out?
2. Action: Call a tool
3. Observation: Review the result
4. Repeat or Answer

Format:
Thought: [reasoning]
Action: [tool_name]
Action Input: {"param": "value"}

Or when ready:
Thought: I have enough information.
Final Answer: [your response]

{session_context}"""

    def _get_default_thought_prompt(self) -> str:
        """Default thought prompt if file not found."""
        return """Question: {query}

History:
{history}

Decide next step. Use 'Final Answer:' when ready to respond."""

    def run(
        self,
        query: str,
        classification: Classification,
        session_context: Optional[Dict] = None
    ) -> AgentResponse:
        """
        Run the ReAct loop to answer a query.

        Args:
            query: The user's question
            classification: Query classification result
            session_context: Optional context about current session

        Returns:
            AgentResponse with answer and reasoning trace
        """
        # Determine max iterations based on query type
        max_iterations = (
            self.GRAPH_MAX_ITERATIONS
            if classification.intent == QueryIntent.GRAPH_TRAVERSAL
            else self.DEFAULT_MAX_ITERATIONS
        )

        # Build system prompt with tool descriptions
        tool_descriptions = self.registry.get_tool_descriptions()
        context_str = self._format_session_context(session_context)

        system_prompt = self.system_template.format(
            tool_descriptions=tool_descriptions,
            session_context=context_str
        )

        # Initialize conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        steps: List[AgentStep] = []
        tools_used: List[str] = []

        for i in range(max_iterations):
            logger.debug(f"ReAct iteration {i + 1}/{max_iterations}")

            # Get next thought/action
            response = self._get_completion(messages)

            # Parse the response
            thought, action, final_answer = self._parse_response(response)

            if final_answer:
                # Agent is ready to answer
                step = AgentStep(thought=thought)
                steps.append(step)

                citations = self._extract_citations(steps)
                return AgentResponse(
                    answer=final_answer,
                    steps=steps,
                    tools_used=list(set(tools_used)),
                    success=True,
                    citations=citations
                )

            if action:
                # Execute the tool
                tools_used.append(action.tool_name)
                result = self.registry.execute_tool(
                    action.tool_name,
                    **action.tool_input
                )

                # Format observation
                observation = self._format_observation(result)
                observation_data = result.data if result.success else None

                step = AgentStep(
                    thought=thought,
                    action=action,
                    observation=observation,
                    observation_data=observation_data
                )
                steps.append(step)

                # Add to message history
                messages.append({
                    "role": "assistant",
                    "content": response
                })
                messages.append({
                    "role": "user",
                    "content": f"Observation: {observation}\n\nContinue reasoning or provide Final Answer."
                })
            else:
                # No action parsed, ask to continue
                step = AgentStep(thought=thought)
                steps.append(step)
                messages.append({
                    "role": "assistant",
                    "content": response
                })
                messages.append({
                    "role": "user",
                    "content": "Please specify an Action or provide a Final Answer."
                })

        # Max iterations reached - force an answer
        logger.warning(f"Max iterations ({max_iterations}) reached, forcing answer")
        final_answer = self._force_answer(query, steps, messages)

        citations = self._extract_citations(steps)
        return AgentResponse(
            answer=final_answer,
            steps=steps,
            tools_used=list(set(tools_used)),
            success=True,
            citations=citations
        )

    def _get_completion(self, messages: List[Dict]) -> str:
        """Get completion from the LLM."""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=2000
        )
        return response.choices[0].message.content

    def _parse_response(
        self,
        response: str
    ) -> Tuple[str, Optional[AgentAction], Optional[str]]:
        """
        Parse the agent's response into thought, action, or final answer.

        Returns:
            Tuple of (thought, action, final_answer)
        """
        thought = ""
        action = None
        final_answer = None

        # Extract thought
        thought_match = re.search(
            r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Check for final answer
        final_match = re.search(
            r'Final Answer:\s*(.+)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if final_match:
            final_answer = final_match.group(1).strip()
            return thought, None, final_answer

        # Extract action
        action_match = re.search(
            r'Action:\s*(\w+)',
            response,
            re.IGNORECASE
        )
        input_match = re.search(
            r'Action Input:\s*(\{.+?\})',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if action_match:
            tool_name = action_match.group(1).strip()

            # Parse action input
            tool_input = {}
            if input_match:
                try:
                    tool_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    # Try to extract key-value pairs
                    tool_input = self._parse_loose_json(input_match.group(1))

            action = AgentAction(
                tool_name=tool_name,
                tool_input=tool_input,
                thought=thought
            )

        return thought, action, final_answer

    def _parse_loose_json(self, text: str) -> Dict:
        """Attempt to parse loosely formatted JSON."""
        result = {}
        # Match patterns like "key": "value" or "key": value
        matches = re.findall(
            r'"?(\w+)"?\s*:\s*(?:"([^"]+)"|(\d+(?:\.\d+)?)|(\[[^\]]+\])|(\{[^\}]+\})|(true|false|null))',
            text,
            re.IGNORECASE
        )
        for match in matches:
            key = match[0]
            # Find the first non-empty value
            value = next((v for v in match[1:] if v), None)
            if value:
                # Convert types
                if value.lower() == 'true':
                    result[key] = True
                elif value.lower() == 'false':
                    result[key] = False
                elif value.lower() == 'null':
                    result[key] = None
                elif value.startswith('['):
                    try:
                        result[key] = json.loads(value)
                    except:
                        result[key] = value
                elif value.replace('.', '').isdigit():
                    result[key] = float(value) if '.' in value else int(value)
                else:
                    result[key] = value
        return result

    def _format_observation(self, result: ToolResult) -> str:
        """Format a tool result as an observation string."""
        if not result.success:
            return f"Error: {result.error}"

        # Truncate large results
        data_str = json.dumps(result.data, indent=2, default=str)
        if len(data_str) > 3000:
            # Summarize large results
            if isinstance(result.data, dict):
                summary = {}
                for k, v in result.data.items():
                    if isinstance(v, list) and len(v) > 3:
                        summary[k] = f"[{len(v)} items, showing first 3: {v[:3]}]"
                    elif isinstance(v, str) and len(v) > 200:
                        summary[k] = v[:200] + "..."
                    else:
                        summary[k] = v
                data_str = json.dumps(summary, indent=2, default=str)
            else:
                data_str = data_str[:3000] + "\n... (truncated)"

        return data_str

    def _format_session_context(self, context: Optional[Dict]) -> str:
        """Format session context for the prompt."""
        if not context:
            return "No specific session context."

        parts = []

        # Include resolved sessions (from session name resolution)
        if context.get('resolved_sessions'):
            session_ids = context['resolved_sessions']
            parts.append(f"Target session IDs (from query): {session_ids}")
            parts.append(f"IMPORTANT: Use these session_device_ids when calling tools: {session_ids}")

        if context.get('session_device_id'):
            parts.append(f"Current session ID: {context['session_device_id']}")
        if context.get('session_name'):
            parts.append(f"Session name: {context['session_name']}")
        if context.get('user_id'):
            parts.append(f"User ID: {context['user_id']}")
        if context.get('previous_session_focus'):
            parts.append(f"Previous session focus: {context['previous_session_focus']}")

        return "\n".join(parts) if parts else "No specific session context."

    def _force_answer(
        self,
        query: str,
        steps: List[AgentStep],
        messages: List[Dict]
    ) -> str:
        """Force the agent to provide an answer when max iterations reached."""
        # Gather all observations
        observations = [
            s.observation for s in steps
            if s.observation and not s.observation.startswith("Error:")
        ]

        if observations:
            context = "\n\n".join(observations)
            force_prompt = f"""Based on the information gathered:

{context}

Please provide your best answer to: {query}

Be honest if the information is incomplete."""
        else:
            force_prompt = f"""Unable to gather sufficient information.
Please provide what answer you can to: {query}
Or explain what information is missing."""

        messages.append({"role": "user", "content": force_prompt})
        response = self._get_completion(messages)

        # Try to extract answer from response
        final_match = re.search(
            r'Final Answer:\s*(.+)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if final_match:
            return final_match.group(1).strip()

        # Sanitize any leaked ReAct format from the response
        return self._sanitize_response(response.strip())

    def _sanitize_response(self, response: str) -> str:
        """
        Remove any leaked ReAct format (Thought/Action/Observation) from response.

        This prevents raw internal agent format from being shown to users.
        """
        # Remove Thought: lines
        response = re.sub(r'^Thought:\s*', '', response, flags=re.MULTILINE | re.IGNORECASE)

        # Remove Action: and Action Input: lines
        response = re.sub(r'^Action:\s*.+$', '', response, flags=re.MULTILINE | re.IGNORECASE)
        response = re.sub(r'^Action Input:\s*.+$', '', response, flags=re.MULTILINE | re.IGNORECASE)

        # Remove Observation: prefix (keep content)
        response = re.sub(r'^Observation:\s*', '', response, flags=re.MULTILINE | re.IGNORECASE)

        # Clean up multiple newlines
        response = re.sub(r'\n{3,}', '\n\n', response)

        # If response is mostly empty after sanitization, provide a fallback
        if len(response.strip()) < 20:
            return "I was unable to gather sufficient information to provide a complete answer. Could you please rephrase your question or provide more specific details?"

        return response.strip()

    def _extract_citations(self, steps: List[AgentStep]) -> List[Dict]:
        """Extract citations from the agent's observations."""
        citations = []

        for step in steps:
            if not step.observation_data:
                continue

            # Extract based on data structure
            data = step.observation_data
            if isinstance(data, dict):
                # Check for specific artifact types
                if 'session_device_id' in data:
                    citation = {
                        'type': 'session',
                        'session_device_id': data['session_device_id']
                    }

                    if 'nodes' in data:
                        citation['artifact_type'] = 'concept_map'
                        citation['node_count'] = data.get('node_count', 0)
                    elif 'dimensions' in data:
                        citation['artifact_type'] = 'seven_c'
                    elif 'transcripts' in data:
                        citation['artifact_type'] = 'transcript'
                        citation['excerpt'] = data['transcripts'][0].get('text', '')[:200] if data['transcripts'] else ''

                    citations.append(citation)

                # Handle search results
                if 'results' in data and isinstance(data['results'], list):
                    for result in data['results'][:3]:  # Top 3
                        if isinstance(result, dict):
                            citation = {'type': 'search_result'}
                            if 'session_device_id' in result:
                                citation['session_device_id'] = result['session_device_id']
                            if 'text' in result:
                                citation['excerpt'] = result['text'][:200]
                            if 'chunk_text' in result:
                                citation['excerpt'] = result['chunk_text'][:200]
                            if 'node_text' in result:
                                citation['excerpt'] = result['node_text'][:200]
                            citations.append(citation)

        return citations
