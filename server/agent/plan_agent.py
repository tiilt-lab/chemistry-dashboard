"""
Plan-Execute Agent

Implements a plan-then-execute strategy for complex queries.
"""

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set

from dotenv import load_dotenv
load_dotenv()

import openai

from .tools import get_tool_registry, ToolResult
from .classifier import Classification

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step: int
    tool: str
    params: Dict[str, Any]
    purpose: str
    depends_on: List[int] = field(default_factory=list)
    result: Optional[ToolResult] = None
    executed: bool = False


@dataclass
class ExecutionPlan:
    """Complete execution plan."""
    reasoning: str
    steps: List[PlanStep]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class PlanAgentResponse:
    """Complete response from the Plan-Execute agent."""
    answer: str
    plan: ExecutionPlan
    results: Dict[int, Any]  # step number -> result
    tools_used: List[str]
    success: bool
    error: Optional[str] = None
    citations: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "answer": self.answer,
            "plan": {
                "reasoning": self.plan.reasoning,
                "steps": [
                    {
                        "step": s.step,
                        "tool": s.tool,
                        "params": s.params,
                        "purpose": s.purpose,
                        "depends_on": s.depends_on,
                        "executed": s.executed
                    }
                    for s in self.plan.steps
                ]
            },
            "tools_used": self.tools_used,
            "success": self.success,
            "error": self.error,
            "citations": self.citations
        }


class PlanExecuteAgent:
    """
    Plan-Execute agent for complex queries.

    Generates an execution plan with dependencies, then executes
    steps (parallelizing independent steps) and synthesizes results.
    """

    MAX_PARALLEL_EXECUTIONS = 3
    MAX_STEPS = 12  # Increased from 8 for complex cross-session comparisons

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

        # Load plan generation prompt
        plan_path = os.path.join(prompts_dir, 'plan_generation.txt')
        try:
            with open(plan_path, 'r') as f:
                self.plan_template = f.read()
        except FileNotFoundError:
            self.plan_template = self._get_default_plan_prompt()

        # Load synthesis prompt
        synthesis_path = os.path.join(prompts_dir, 'synthesis.txt')
        try:
            with open(synthesis_path, 'r') as f:
                self.synthesis_template = f.read()
        except FileNotFoundError:
            self.synthesis_template = self._get_default_synthesis_prompt()

    def _get_default_plan_prompt(self) -> str:
        """Default plan prompt."""
        return """Plan steps to answer: {query}

Available tools: {tool_descriptions}

Return JSON with steps array. Each step has: step, tool, params, purpose, depends_on."""

    def _get_default_synthesis_prompt(self) -> str:
        """Default synthesis prompt."""
        return """Synthesize these results to answer: {query}

Plan: {plan}
Results: {results}

Provide a complete answer with citations."""

    def run(
        self,
        query: str,
        classification: Classification,
        session_context: Optional[Dict] = None
    ) -> PlanAgentResponse:
        """
        Run the Plan-Execute agent.

        Args:
            query: The user's question
            classification: Query classification result
            session_context: Optional context about current session

        Returns:
            PlanAgentResponse with answer and execution details
        """
        try:
            # Step 1: Generate plan
            plan = self._generate_plan(query, classification)

            if not plan.is_valid:
                return PlanAgentResponse(
                    answer=f"Unable to create a valid plan: {', '.join(plan.validation_errors)}",
                    plan=plan,
                    results={},
                    tools_used=[],
                    success=False,
                    error="Plan validation failed"
                )

            # Step 2: Execute plan
            results = self._execute_plan(plan, session_context)

            # Step 3: Synthesize results
            answer, citations = self._synthesize_results(query, plan, results)

            tools_used = list(set(s.tool for s in plan.steps if s.executed))

            return PlanAgentResponse(
                answer=answer,
                plan=plan,
                results=results,
                tools_used=tools_used,
                success=True,
                citations=citations
            )

        except Exception as e:
            logger.error(f"Plan-Execute agent failed: {e}")
            return PlanAgentResponse(
                answer=f"Error executing query: {str(e)}",
                plan=ExecutionPlan(reasoning="", steps=[], is_valid=False),
                results={},
                tools_used=[],
                success=False,
                error=str(e)
            )

    def _generate_plan(
        self,
        query: str,
        classification: Classification
    ) -> ExecutionPlan:
        """Generate an execution plan for the query."""
        tool_descriptions = self.registry.get_tool_descriptions()

        prompt = self.plan_template.format(
            query=query,
            tool_descriptions=tool_descriptions,
            intent=classification.intent.value,
            complexity=classification.complexity.value,
            artifacts=", ".join(classification.required_artifacts),
            entities=json.dumps(classification.entities.__dict__)
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a planning assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Parse plan steps
        steps = []
        for step_data in result.get("steps", []):
            step = PlanStep(
                step=step_data.get("step", len(steps) + 1),
                tool=step_data.get("tool", ""),
                params=step_data.get("params", {}),
                purpose=step_data.get("purpose", ""),
                depends_on=step_data.get("depends_on", [])
            )
            steps.append(step)

        plan = ExecutionPlan(
            reasoning=result.get("reasoning", ""),
            steps=steps
        )

        # Validate plan
        plan = self._validate_plan(plan)

        return plan

    def _validate_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Validate the execution plan."""
        errors = []

        if not plan.steps:
            errors.append("Plan has no steps")
            plan.is_valid = False
            plan.validation_errors = errors
            return plan

        if len(plan.steps) > self.MAX_STEPS:
            # Truncate plan instead of failing - take most important steps
            logger.warning(f"Plan has {len(plan.steps)} steps, truncating to {self.MAX_STEPS}")
            plan.steps = plan.steps[:self.MAX_STEPS]
            # Don't add error - allow plan to proceed with truncated steps

        # Check each step
        step_numbers = set()
        for step in plan.steps:
            # Check for duplicate step numbers
            if step.step in step_numbers:
                errors.append(f"Duplicate step number: {step.step}")
            step_numbers.add(step.step)

            # Check tool exists
            if not self.registry.get_tool(step.tool):
                errors.append(f"Unknown tool in step {step.step}: {step.tool}")

            # Check dependencies exist
            for dep in step.depends_on:
                if dep not in step_numbers and dep >= step.step:
                    if not any(s.step == dep for s in plan.steps):
                        errors.append(f"Step {step.step} depends on non-existent step {dep}")

        # Check for cycles
        if self._has_cycles(plan.steps):
            errors.append("Plan has circular dependencies")

        plan.is_valid = len(errors) == 0
        plan.validation_errors = errors

        return plan

    def _has_cycles(self, steps: List[PlanStep]) -> bool:
        """Check if the dependency graph has cycles."""
        # Build adjacency list
        graph = {s.step: set(s.depends_on) for s in steps}

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for step in steps:
            if step.step not in visited:
                if dfs(step.step):
                    return True

        return False

    def _execute_plan(
        self,
        plan: ExecutionPlan,
        context: Optional[Dict]
    ) -> Dict[int, Any]:
        """Execute the plan, parallelizing independent steps."""
        results = {}
        step_map = {s.step: s for s in plan.steps}

        # Track which steps are complete
        completed: Set[int] = set()

        while len(completed) < len(plan.steps):
            # Find steps ready to execute (all dependencies satisfied)
            ready_steps = [
                s for s in plan.steps
                if s.step not in completed
                and all(d in completed for d in s.depends_on)
            ]

            if not ready_steps:
                logger.error("No steps ready but plan not complete - possible cycle")
                break

            # Execute ready steps (parallel if multiple)
            if len(ready_steps) == 1:
                # Single step - execute directly
                step = ready_steps[0]
                result = self._execute_step(step, results)
                results[step.step] = result
                step.result = result
                step.executed = True
                completed.add(step.step)
            else:
                # Multiple independent steps - execute in parallel
                with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_EXECUTIONS) as executor:
                    futures = {
                        executor.submit(self._execute_step, step, results): step
                        for step in ready_steps
                    }

                    for future in as_completed(futures):
                        step = futures[future]
                        try:
                            result = future.result()
                            results[step.step] = result
                            step.result = result
                            step.executed = True
                            completed.add(step.step)
                        except Exception as e:
                            logger.error(f"Step {step.step} failed: {e}")
                            results[step.step] = ToolResult(
                                success=False,
                                data=None,
                                error=str(e)
                            )
                            completed.add(step.step)

        return results

    def _execute_step(
        self,
        step: PlanStep,
        previous_results: Dict[int, Any]
    ) -> ToolResult:
        """Execute a single plan step."""
        # Resolve variable references in params
        resolved_params = self._resolve_params(step.params, previous_results)

        logger.debug(f"Executing step {step.step}: {step.tool}({resolved_params})")

        return self.registry.execute_tool(step.tool, **resolved_params)

    def _resolve_params(
        self,
        params: Dict[str, Any],
        results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """Resolve variable references like $1.results[0].id in params."""
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$'):
                resolved[key] = self._resolve_reference(value, results)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, results)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_reference(v, results) if isinstance(v, str) and v.startswith('$') else v
                    for v in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_reference(self, ref: str, results: Dict[int, Any]) -> Any:
        """Resolve a single variable reference like $1.results[0].id."""
        if not ref.startswith('$'):
            return ref

        # Parse the reference
        match = re.match(r'\$(\d+)\.(.+)', ref)
        if not match:
            logger.warning(f"Invalid reference format: {ref}")
            return ref

        step_num = int(match.group(1))
        path = match.group(2)

        if step_num not in results:
            logger.warning(f"Reference to non-existent step: {step_num}")
            return ref

        result = results[step_num]
        if isinstance(result, ToolResult):
            result = result.data

        # Navigate the path
        try:
            current = result
            for part in self._parse_path(path):
                if isinstance(part, int):
                    current = current[part]
                elif isinstance(current, dict):
                    current = current[part]
                else:
                    current = getattr(current, part, None)
                    if current is None:
                        raise KeyError(part)
            return current
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to resolve {ref}: {e}")
            return ref

    def _parse_path(self, path: str) -> List:
        """Parse a path like 'results[0].id' into parts."""
        parts = []
        current = ""

        i = 0
        while i < len(path):
            char = path[i]
            if char == '.':
                if current:
                    parts.append(current)
                    current = ""
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ""
                # Find closing bracket
                j = path.index(']', i)
                index = int(path[i+1:j])
                parts.append(index)
                i = j
            else:
                current += char
            i += 1

        if current:
            parts.append(current)

        return parts

    def _synthesize_results(
        self,
        query: str,
        plan: ExecutionPlan,
        results: Dict[int, Any]
    ) -> tuple[str, List[Dict]]:
        """Synthesize results into a final answer."""
        # Format plan for prompt
        plan_str = json.dumps([
            {"step": s.step, "tool": s.tool, "purpose": s.purpose}
            for s in plan.steps
        ], indent=2)

        # Format results for prompt
        results_str = ""
        for step_num, result in results.items():
            step = next((s for s in plan.steps if s.step == step_num), None)
            if step:
                result_data = result.data if isinstance(result, ToolResult) else result
                results_str += f"\n### Step {step_num}: {step.tool}\n"
                results_str += f"Purpose: {step.purpose}\n"
                if isinstance(result, ToolResult) and result.success:
                    # Truncate large results
                    data_str = json.dumps(result_data, indent=2, default=str)
                    if len(data_str) > 2000:
                        data_str = self._summarize_result(result_data)
                    results_str += f"Result: {data_str}\n"
                elif isinstance(result, ToolResult):
                    results_str += f"Error: {result.error}\n"

        prompt = self.synthesis_template.format(
            query=query,
            plan=plan_str,
            results=results_str
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You synthesize information to answer questions. Be thorough but concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        answer = response.choices[0].message.content

        # Extract citations from results
        citations = self._extract_citations(results)

        return answer, citations

    def _summarize_result(self, data: Any) -> str:
        """Summarize large result data."""
        if isinstance(data, dict):
            summary = {}
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 5:
                    summary[k] = f"[{len(v)} items]"
                elif isinstance(v, str) and len(v) > 300:
                    summary[k] = v[:300] + "..."
                elif isinstance(v, dict) and len(str(v)) > 500:
                    summary[k] = "{...}"
                else:
                    summary[k] = v
            return json.dumps(summary, indent=2, default=str)
        elif isinstance(data, list) and len(data) > 5:
            return json.dumps(data[:5], indent=2, default=str) + f"\n... and {len(data) - 5} more items"
        else:
            return str(data)[:2000]

    def _extract_citations(self, results: Dict[int, Any]) -> List[Dict]:
        """Extract citations from all results."""
        citations = []

        for step_num, result in results.items():
            if not isinstance(result, ToolResult) or not result.success:
                continue

            data = result.data
            if not isinstance(data, dict):
                continue

            # Extract session citations
            if 'session_device_id' in data:
                citation = {
                    'type': 'artifact',
                    'session_device_id': data['session_device_id'],
                    'step': step_num
                }
                if 'nodes' in data:
                    citation['artifact_type'] = 'concept_map'
                elif 'dimensions' in data:
                    citation['artifact_type'] = 'seven_c'
                elif 'transcripts' in data:
                    citation['artifact_type'] = 'transcript'
                citations.append(citation)

            # Extract search result citations
            if 'results' in data and isinstance(data['results'], list):
                for i, item in enumerate(data['results'][:5]):
                    if isinstance(item, dict) and 'session_device_id' in item:
                        citations.append({
                            'type': 'search_result',
                            'session_device_id': item['session_device_id'],
                            'step': step_num,
                            'result_index': i
                        })

        return citations
