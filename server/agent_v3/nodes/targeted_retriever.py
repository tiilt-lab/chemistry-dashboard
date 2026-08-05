"""
Targeted Retriever Node for BLINC Agent V3

PRAS Stage 3: Targeted Retrieval with Reflection

Executes retrieval plans for each sub-goal with:
1. Tool execution with targeted parameters
2. Sub-goal specific grading (not just query relevance)
3. Reflection loops to assess satisfaction
4. Adaptive retry on unsatisfied sub-goals
"""

import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..llm import get_reasoning_client, get_fast_client
from ..tools import ALL_TOOLS, COMBINED_TOOLS
from ..state import SubGoalResult

logger = logging.getLogger(__name__)

# PRAS retrieval cache - avoids duplicate tool calls within a conversation
# Key: (conversation_id, tool_name, params_hash)
_pras_cache: Dict[str, Dict[str, Any]] = {}


def _get_pras_cache_key(conversation_id: str, tool_name: str, params: dict) -> str:
    """Generate a deterministic cache key for PRAS retrieval."""
    params_str = json.dumps(params, sort_keys=True, default=str)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:16]
    return f"pras:{conversation_id}:{tool_name}:{params_hash}"


def clear_pras_cache(conversation_id: str = None) -> int:
    """Clear PRAS cache. If conversation_id given, only clear that conversation."""
    global _pras_cache
    if conversation_id:
        prefix = f"pras:{conversation_id}:"
        keys_to_remove = [k for k in _pras_cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del _pras_cache[key]
        return len(keys_to_remove)
    else:
        count = len(_pras_cache)
        _pras_cache = {}
        return count

# Session name to ID mapping (shared with execute_tool)
SESSION_NAME_TO_ID = {
    'living in nyc': 18, 'nyc': 18, 'new york': 18,
    'is ai alive': 19, 'ai alive': 19, 'ai': 19,
    'nuclear fusion': 20, 'fusion': 20,
    'shaw interview': 21, 'shaw': 21,
    'collaboration literacy': 22, 'literacy': 22,
    'dinosaurs': 23, 'dinosaur': 23,
    'country music': 24, 'country': 24, 'music': 24,
    'abundance': 25
}


def _fetch_artifact_parallel(tool_name: str, session_id: int) -> Tuple[str, int, Any]:
    """
    Fetch a single artifact. Returns (tool_name, session_id, result).
    Designed to run in ThreadPoolExecutor for parallel artifact fetching.

    Each call creates its own MySQL connection (thread-safe).
    """
    try:
        if tool_name not in COMBINED_TOOLS:
            logger.error(f"Tool {tool_name} not found in COMBINED_TOOLS")
            return (tool_name, session_id, {'error': f'Tool {tool_name} not found'})

        result = COMBINED_TOOLS[tool_name](session_id=session_id)
        return (tool_name, session_id, result)
    except Exception as e:
        logger.error(f"Error fetching {tool_name} for session {session_id}: {e}")
        return (tool_name, session_id, {'error': str(e)})


REFLECTION_SYSTEM_PROMPT = """You are reflecting on evidence gathered for a specific sub-goal.

Your task is to assess whether the retrieved evidence addresses the sub-goal and what's missing.

Return JSON:
{
    "subgoal_satisfied": boolean,  // true if we have enough evidence
    "satisfaction_level": "full" | "partial" | "none",
    "indicators_found": ["list of indicators that were found"],
    "indicators_missing": ["list of indicators still needed"],
    "evidence_summary": "brief summary of what we found",
    "should_try_alternative": boolean,  // true if we should try another approach
    "suggested_next_step": "description of what to try next" | null
}

Guidelines:
1. "full" satisfaction = evidence clearly addresses the sub-goal
2. "partial" satisfaction = some evidence but gaps remain
3. "none" = retrieved content doesn't address the sub-goal
4. Only suggest alternatives if partial/none satisfaction
5. Consider whether secondary representations might help"""


def targeted_retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute next retrieval step with reflection.

    PRAS Stage 2: Targeted Retrieval (simplified from Stage 3)

    This node is called repeatedly until all sub-goals are processed.
    Now includes deterministic planning (previously a separate pras_plan node).

    CRITICAL: Handles discovery chaining - when search_for_sessions finds relevant
    sessions, this node automatically fetches their artifacts.

    Args:
        state: Current agent state with sub-goals

    Returns:
        State updates with retrieval results and reflection
    """
    from .representation_planner import get_next_retrieval_step, plan_retrieval

    # === DETERMINISTIC PLANNING ===
    # If retrieval_plans don't exist, create them now (was previously pras_plan node)
    plans_just_created = False
    if not state.get('retrieval_plans'):
        logger.info("[PRAS Stage 2] Creating deterministic retrieval plans")
        plan_updates = plan_retrieval(state)
        # Merge plan updates into state for this invocation
        state = {**state, **plan_updates}
        plans_just_created = True

    # Get next step to execute
    next_step = get_next_retrieval_step(state)

    if not next_step:
        # Check if we have discovered sessions that need artifact fetching
        discovered_sessions = state.get('_discovered_sessions', [])
        logger.info(f"[PRAS Stage 3] No more steps. Discovered sessions in state: {discovered_sessions}")

        if discovered_sessions:
            logger.info(f"[PRAS Stage 3] Fetching artifacts for {len(discovered_sessions)} discovered sessions: {discovered_sessions}")
            return _fetch_discovered_artifacts(state, discovered_sessions)

        logger.info("[PRAS Stage 3] All retrieval complete (no discovered sessions to fetch)")
        return {
            'pras_stage': 'retrieve_complete',
            'next_action': 'reason'  # Move to cross-rep reasoning
        }

    subgoal = next_step['subgoal']
    step = next_step['step']
    subgoal_id = next_step['subgoal_id']

    logger.info(f"[PRAS Stage 3] Executing step {next_step['step_index']+1}/{next_step['total_steps']} "
                f"for {subgoal_id}")

    # Check cache first to avoid duplicate tool calls
    conversation_id = state.get('conversation_id', 'default')
    tool_name = step.get('tool')
    params = _normalize_params(step.get('parameters', {}))
    cache_key = _get_pras_cache_key(conversation_id, tool_name, params)

    if cache_key in _pras_cache:
        tool_result = _pras_cache[cache_key]
        logger.info(f"  [Cache HIT] {tool_name} - returning cached result")
    else:
        # Execute the tool
        tool_result = _execute_retrieval_step(step)
        # Cache the result
        _pras_cache[cache_key] = tool_result
        logger.info(f"  [Cache MISS] {tool_name} - result cached")

    # === CRITICAL: Discovery chaining ===
    # If this was a search_for_sessions call, extract discovered sessions
    # and queue them for artifact fetching
    discovered_sessions = state.get('_discovered_sessions', [])
    if tool_name == 'search_for_sessions':
        sessions = tool_result.get('sessions', [])
        for s in sessions:
            sid = s.get('session_id')
            if sid and sid not in discovered_sessions:
                discovered_sessions.append(sid)
                logger.info(f"  [Discovery] Found session {sid}: {s.get('session_name', 'Unknown')}")

    # Grade results for sub-goal relevance
    grade_result = _grade_for_subgoal(tool_result, subgoal)

    # Reflect on results
    reflection = _reflect_on_results(subgoal, step, tool_result, grade_result, state)

    # Record step execution
    step_record = {
        'step': step,
        'tool_result': tool_result,
        'grade': grade_result,
        'reflection': reflection
    }

    # Update subgoal_results
    subgoal_results = state.get('subgoal_results', {}).copy()
    if subgoal_id not in subgoal_results:
        subgoal_results[subgoal_id] = SubGoalResult(
            subgoal_id=subgoal_id,
            steps_executed=[],
            satisfied=False,
            evidence_summary='',
            representations_used=[]
        )

    # Append step record
    subgoal_results[subgoal_id]['steps_executed'].append(step_record)

    # Update representations used
    reps_used = subgoal_results[subgoal_id]['representations_used']
    if step['representation'] not in reps_used:
        reps_used.append(step['representation'])
    subgoal_results[subgoal_id]['representations_used'] = reps_used

    # Update satisfaction based on reflection
    if reflection.get('subgoal_satisfied'):
        subgoal_results[subgoal_id]['satisfied'] = True
        subgoal_results[subgoal_id]['evidence_summary'] = reflection.get('evidence_summary', '')

    # Track in retrieval_reflections for transparency
    retrieval_reflections = state.get('retrieval_reflections', []).copy()
    retrieval_reflections.append({
        'subgoal_id': subgoal_id,
        'step': step['tool'],
        'satisfaction': reflection.get('satisfaction_level', 'unknown'),
        'indicators_found': reflection.get('indicators_found', [])
    })

    # Accumulate retrieval results (for compatibility with existing flow)
    retrieval_results = state.get('retrieval_results', []).copy()
    if tool_result.get('results'):
        retrieval_results.append(tool_result)

    # Track tools used (fix: PRAS path was not tracking this)
    tools_used = state.get('tools_used', []).copy()
    tool_name = step.get('tool')
    if tool_name and tool_name not in tools_used:
        tools_used.append(tool_name)

    # Determine next action
    next_action, next_subgoal_idx, next_step_idx = _determine_next_action(
        state, next_step, reflection, discovered_sessions
    )

    result = {
        'pras_stage': 'retrieve',
        'subgoal_results': subgoal_results,
        'retrieval_reflections': retrieval_reflections,
        'retrieval_results': retrieval_results,
        'tools_used': tools_used,  # Now tracked for PRAS path
        'current_subgoal_index': next_subgoal_idx,
        'current_retrieval_step': next_step_idx,
        'next_action': next_action,
        '_discovered_sessions': discovered_sessions,  # Track discovered sessions for chaining
        'thought_history': state.get('thought_history', []) + [
            f"Retrieved from {step['representation']} for {subgoal_id}: "
            f"{reflection.get('satisfaction_level', 'unknown')} satisfaction"
        ]
    }

    # Include retrieval_plans if they were just created (deterministic planning)
    if plans_just_created:
        result['retrieval_plans'] = state.get('retrieval_plans', {})

    return result


def _execute_retrieval_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single retrieval step."""
    tool_name = step.get('tool')
    params = step.get('parameters', {})

    # Normalize parameters
    params = _normalize_params(params)

    logger.info(f"  Executing {tool_name} with params: {params}")

    # Check COMBINED_TOOLS first (includes artifact tools), then ALL_TOOLS
    if tool_name in COMBINED_TOOLS:
        tool_fn = COMBINED_TOOLS[tool_name]
    elif tool_name in ALL_TOOLS:
        tool_fn = ALL_TOOLS[tool_name]
    else:
        logger.error(f"Unknown tool: {tool_name}")
        return {
            'tool_name': tool_name,
            'error': f"Unknown tool: {tool_name}",
            'results': [],
            'result_count': 0
        }

    try:
        result = tool_fn(**params)
        return result
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            'tool_name': tool_name,
            'error': str(e),
            'results': [],
            'result_count': 0
        }


def _normalize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize tool parameters."""
    normalized = params.copy()

    # Normalize session_id
    if 'session_id' in normalized:
        normalized['session_id'] = _normalize_session_id(normalized['session_id'])

    # Normalize session_ids list
    if 'session_ids' in normalized and isinstance(normalized['session_ids'], list):
        normalized['session_ids'] = [
            _normalize_session_id(sid) for sid in normalized['session_ids']
        ]

    return normalized


def _normalize_session_id(value):
    """Convert session name to ID if needed."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
        normalized = value.lower().strip()
        if normalized in SESSION_NAME_TO_ID:
            return SESSION_NAME_TO_ID[normalized]
        for name, sid in SESSION_NAME_TO_ID.items():
            if name in normalized or normalized in name:
                return sid
    return value


def _grade_for_subgoal(
    tool_result: Dict[str, Any],
    subgoal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Grade results specifically for sub-goal relevance.

    Different from query-level relevance - this checks if results
    address the specific indicators the sub-goal is looking for.

    Handles both legacy 'results' format and new specific tool formats:
    - get_transcript: returns 'utterances'
    - get_concept_map: returns 'nodes', 'edges'
    - get_7c_analysis: returns 'dimensions'
    """
    indicators = subgoal.get('indicators', [])

    # Extract results from different tool formats
    results = []

    # Legacy format
    if tool_result.get('results'):
        results = tool_result['results']

    # Specific tool formats
    elif tool_result.get('utterances'):
        # get_transcript format
        results = tool_result['utterances']
    elif tool_result.get('nodes'):
        # get_concept_map format
        results = tool_result['nodes']
    elif tool_result.get('dimensions'):
        # get_7c_analysis format - convert dimensions dict to list
        dims = tool_result['dimensions']
        if isinstance(dims, dict):
            results = [{'text': f"{k}: {v}"} for k, v in dims.items()]
        else:
            results = [dims]
    elif tool_result.get('sessions'):
        # search_for_sessions format
        results = tool_result['sessions']

    if not results:
        # Check if tool returned data but in a different structure
        if tool_result.get('is_relevant') or tool_result.get('result_count', 0) > 0:
            return {
                'is_relevant': True,
                'relevance_score': 0.5,
                'indicators_addressed': [],
                'reason': 'Tool returned data (specific format)'
            }
        return {
            'is_relevant': False,
            'relevance_score': 0.0,
            'indicators_addressed': [],
            'reason': 'No results returned'
        }

    # Quick heuristic grading - check for indicator keywords in results
    indicator_keywords = set()
    for ind in indicators:
        indicator_keywords.update(ind.lower().split())

    addressed = []
    total_relevance = 0.0

    for result in results:
        # Get text content from result
        text = ''
        if isinstance(result, dict):
            text = str(result.get('text', result.get('content', result.get('summary', result.get('transcript', result.get('label', ''))))))
            # Also check speaker field for speaker-related queries
            speaker = result.get('speaker', result.get('speaker_tag', result.get('attributed_to', '')))
            if speaker:
                text += ' ' + speaker
        elif isinstance(result, str):
            text = result

        text_lower = text.lower()

        # Check keyword overlap
        matching = [kw for kw in indicator_keywords if kw in text_lower]
        if matching:
            relevance = min(len(matching) / max(len(indicator_keywords), 1), 1.0)
            total_relevance += relevance
            for ind in indicators:
                ind_words = set(ind.lower().split())
                if any(w in text_lower for w in ind_words):
                    if ind not in addressed:
                        addressed.append(ind)

    avg_relevance = total_relevance / len(results) if results else 0.0

    return {
        'is_relevant': avg_relevance > 0.2 or len(addressed) > 0,
        'relevance_score': avg_relevance,
        'indicators_addressed': addressed,
        'reason': f"Found {len(addressed)}/{len(indicators)} indicators"
    }


def _reflect_on_results(
    subgoal: Dict[str, Any],
    step: Dict[str, Any],
    tool_result: Dict[str, Any],
    grade_result: Dict[str, Any],
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Reflect on retrieval results for the sub-goal.

    Uses heuristics for fast evaluation (LLM reflection was 4-5s overhead per step).
    The cross-rep reasoning stage will do deep analysis, so per-step LLM is wasteful.
    """
    # Determine result count from different tool formats
    result_count = 0
    has_data = False

    if tool_result.get('results'):
        result_count = len(tool_result['results'])
        has_data = result_count > 0
    elif tool_result.get('utterances'):
        result_count = len(tool_result['utterances'])
        has_data = result_count > 0
    elif tool_result.get('nodes'):
        result_count = len(tool_result['nodes'])
        has_data = result_count > 0
    elif tool_result.get('dimensions'):
        result_count = len(tool_result['dimensions']) if isinstance(tool_result['dimensions'], dict) else 1
        has_data = result_count > 0
    elif tool_result.get('sessions'):
        result_count = len(tool_result['sessions'])
        has_data = result_count > 0
    elif tool_result.get('result_count', 0) > 0:
        result_count = tool_result['result_count']
        has_data = True
    elif tool_result.get('is_relevant'):
        has_data = True
        result_count = 1

    # Fast path for errors or empty results
    if tool_result.get('error') or not has_data:
        secondary_reps = subgoal.get('secondary_representations') or ['transcript']
        return {
            'subgoal_satisfied': False,
            'satisfaction_level': 'none',
            'indicators_found': [],
            'indicators_missing': subgoal.get('indicators', []),
            'evidence_summary': 'No evidence retrieved',
            'should_try_alternative': True,
            'suggested_next_step': f"Try {secondary_reps[0]} representation"
        }

    # Heuristic-based reflection (saves ~4-5s per step vs LLM)
    # The cross-rep reasoning stage (Stage 4) will do the deep analysis
    indicators = subgoal.get('indicators', [])
    found = grade_result.get('indicators_addressed', [])
    missing = [i for i in indicators if i not in found]

    # Use result count and relevance as quality signals
    is_relevant = tool_result.get('is_relevant', result_count > 0)
    high_quality = result_count >= 3 and is_relevant

    # Determine satisfaction level
    if high_quality and len(found) >= len(indicators) * 0.7:
        satisfaction = 'full'
    elif result_count > 0 and (found or is_relevant):
        satisfaction = 'partial'
    else:
        satisfaction = 'none'

    return {
        'subgoal_satisfied': satisfaction == 'full',
        'satisfaction_level': satisfaction,
        'indicators_found': found,
        'indicators_missing': missing,
        'evidence_summary': f"Found {result_count} results, {len(found)}/{len(indicators)} indicators",
        'should_try_alternative': satisfaction != 'full',
        'suggested_next_step': None
    }


def _format_results_for_reflection(tool_result: Dict[str, Any]) -> str:
    """Format tool results for LLM reflection."""
    results = tool_result.get('results', [])
    if not results:
        return "No results"

    lines = []
    for i, r in enumerate(results[:5]):  # Limit to 5 for brevity
        if isinstance(r, dict):
            # Try different fields
            text = r.get('text', r.get('content', r.get('summary', '')))
            speaker = r.get('speaker', r.get('attributed_to', ''))
            prefix = f"[{speaker}] " if speaker else ""
            lines.append(f"{i+1}. {prefix}{text[:200]}...")
        else:
            lines.append(f"{i+1}. {str(r)[:200]}...")

    if len(results) > 5:
        lines.append(f"... and {len(results) - 5} more results")

    return "\n".join(lines)


def _determine_next_action(
    state: Dict[str, Any],
    current_step_info: Dict[str, Any],
    reflection: Dict[str, Any],
    discovered_sessions: List[int] = None
) -> tuple[str, int, int]:
    """
    Determine next action based on reflection.

    Returns:
        (next_action, next_subgoal_index, next_step_index)
    """
    subgoal_idx = current_step_info['subgoal_index']
    step_idx = current_step_info['step_index']
    total_steps = current_step_info['total_steps']
    total_subgoals = current_step_info['total_subgoals']

    satisfied = reflection.get('subgoal_satisfied', False)
    should_try_alt = reflection.get('should_try_alternative', False)

    # If satisfied or no alternative needed, move to next step or subgoal
    if satisfied or (step_idx + 1 >= total_steps):
        # Done with this subgoal, move to next
        if subgoal_idx + 1 >= total_subgoals:
            # All subgoals done - increment indices past end so get_next_retrieval_step returns None
            # The retriever will then check for discovered sessions and fetch artifacts
            return 'continue', total_subgoals, 0  # Past the end
        else:
            # Next subgoal
            return 'continue', subgoal_idx + 1, 0
    else:
        # Try next step in current subgoal
        return 'continue', subgoal_idx, step_idx + 1


def should_continue_retrieval(state: Dict[str, Any]) -> str:
    """
    Conditional edge: determine if retrieval should continue.

    Returns:
        "continue" - more retrieval needed
        "reason" - move to cross-rep reasoning
    """
    next_action = state.get('next_action', 'continue')

    if next_action == 'reason':
        return 'reason'

    # Check if all subgoals are done
    sub_goals = state.get('sub_goals', [])
    current_idx = state.get('current_subgoal_index', 0)

    if current_idx >= len(sub_goals):
        return 'reason'

    # Check iteration limits
    iteration = state.get('iteration_count', 0)
    max_iter = state.get('max_iterations', 8)
    if iteration >= max_iter:
        logger.warning(f"Retrieval hit max iterations ({max_iter})")
        return 'reason'

    return 'continue'


def _fetch_discovered_artifacts(state: Dict[str, Any], session_ids: List[int]) -> Dict[str, Any]:
    """
    Fetch artifacts for discovered sessions using specific tools.

    CRITICAL: This is the second stage of discovery chaining.
    After search_for_sessions finds relevant sessions, this function
    fetches complete artifacts from those sessions using specific tools
    (get_transcript, get_concept_map) instead of the monolithic get_artifacts.

    Uses ThreadPoolExecutor for PARALLEL execution of independent tool calls.

    Args:
        state: Current agent state
        session_ids: List of discovered session IDs

    Returns:
        State updates with fetched artifacts
    """
    logger.info(f"[Discovery Chaining] Fetching artifacts for sessions: {session_ids}")

    # Get existing state
    retrieval_results = state.get('retrieval_results', []).copy()
    tools_used = state.get('tools_used', []).copy()
    subgoal_results = state.get('subgoal_results', {}).copy()
    sub_goals = state.get('sub_goals', [])

    # Limit to first 2 sessions to avoid excessive fetching
    sessions_to_fetch = session_ids[:2]

    # Determine if we need 7C analysis
    sub_goal_reps = [sg.get('primary_representation') for sg in sub_goals]
    needs_7c = 'collaboration' in sub_goal_reps
    logger.info(f"  Sub-goal primary reps: {sub_goal_reps}, needs_7c: {needs_7c}")

    # Build list of all fetch tasks (tool_name, session_id)
    fetch_tasks = []
    for sid in sessions_to_fetch:
        fetch_tasks.append(('get_transcript', sid))
        fetch_tasks.append(('get_concept_map', sid))
        if needs_7c:
            fetch_tasks.append(('get_7c_analysis', sid))

    logger.info(f"  Executing {len(fetch_tasks)} fetch tasks in parallel")

    # Execute all fetches in parallel using ThreadPoolExecutor
    results_by_session: Dict[int, Dict[str, Any]] = {sid: {} for sid in sessions_to_fetch}

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_fetch_artifact_parallel, tool, sid): (tool, sid)
            for tool, sid in fetch_tasks
        }

        for future in as_completed(futures):
            tool_name, session_id, result = future.result()
            if result and not result.get('error'):
                results_by_session[session_id][tool_name] = result
                logger.info(f"    Got {tool_name} for session {session_id}")
            elif result and result.get('error'):
                logger.error(f"    Failed {tool_name} for session {session_id}: {result.get('error')}")

    # Process results and update state (preserving original order)
    session_focus = None

    for sid in sessions_to_fetch:
        session_results = results_by_session.get(sid, {})

        # Process transcript
        transcript_result = session_results.get('get_transcript')
        if transcript_result:
            retrieval_results.append(transcript_result)
            if 'get_transcript' not in tools_used:
                tools_used.append('get_transcript')

        # Process concept map
        concept_result = session_results.get('get_concept_map')
        if concept_result:
            retrieval_results.append(concept_result)
            if 'get_concept_map' not in tools_used:
                tools_used.append('get_concept_map')

        # Process 7C analysis
        collab_result = session_results.get('get_7c_analysis')
        if collab_result:
            retrieval_results.append(collab_result)
            if 'get_7c_analysis' not in tools_used:
                tools_used.append('get_7c_analysis')
            logger.info(f"    7C analysis for session {sid}: overall={collab_result.get('summary', {}).get('overall_score')}")

        # Update subgoal results with the actual content
        for sg in sub_goals:
            sg_id = sg.get('id')
            if sg_id in subgoal_results:
                # Add transcript step record
                if transcript_result:
                    step_record = {
                        'step': {
                            'representation': 'transcript',
                            'tool': 'get_transcript',
                            'parameters': {'session_id': sid}
                        },
                        'tool_result': transcript_result,
                        'grade': {'is_relevant': True, 'relevance_score': 0.8},
                        'reflection': {
                            'subgoal_satisfied': True,
                            'satisfaction_level': 'full',
                            'evidence_summary': f'Fetched transcript from session {sid}'
                        }
                    }
                    subgoal_results[sg_id]['steps_executed'].append(step_record)
                    subgoal_results[sg_id]['satisfied'] = True
                    if 'transcript' not in subgoal_results[sg_id].get('representations_used', []):
                        subgoal_results[sg_id]['representations_used'].append('transcript')

                # Add concept map to representations
                if concept_result:
                    if 'concept_map' not in subgoal_results[sg_id].get('representations_used', []):
                        subgoal_results[sg_id]['representations_used'].append('concept_map')

                # Add 7C analysis step record if we fetched it
                if collab_result:
                    collab_step = {
                        'step': {
                            'representation': 'collaboration',
                            'tool': 'get_7c_analysis',
                            'parameters': {'session_id': sid}
                        },
                        'tool_result': collab_result,
                        'grade': {'is_relevant': True, 'relevance_score': 0.9},
                        'reflection': {
                            'subgoal_satisfied': True,
                            'satisfaction_level': 'full',
                            'evidence_summary': f'7C analysis for session {sid}: overall score {collab_result.get("summary", {}).get("overall_score", "N/A")}'
                        }
                    }
                    subgoal_results[sg_id]['steps_executed'].append(collab_step)
                    if 'collaboration' not in subgoal_results[sg_id].get('representations_used', []):
                        subgoal_results[sg_id]['representations_used'].append('collaboration')

        # Set session focus to the first discovered session
        if not session_focus:
            session_focus = sid
            logger.info(f"  Setting session focus to {sid}")

    return {
        'pras_stage': 'retrieve_complete',
        'retrieval_results': retrieval_results,
        'tools_used': tools_used,
        'subgoal_results': subgoal_results,
        '_discovered_sessions': [],  # Clear after fetching
        'current_session_focus': session_focus,  # Set session focus
        'next_action': 'reason',
        'thought_history': state.get('thought_history', []) + [
            f"Fetched artifacts from {len(sessions_to_fetch)} discovered sessions: {sessions_to_fetch}"
        ]
    }
