"""
Grounded Synthesizer Node for BLINC Agent V3

PRAS Stage 5: Grounded Synthesis

Generates final answer with explicit grounding in evidence:
1. Structure answer around main claims
2. Ground every claim with typed citations
3. Acknowledge convergence explicitly
4. Acknowledge tensions when present
5. State limitations honestly

Enhancement: True Citation Grounding
- Each citation includes source_chunk_id for traceability
- Validation against actual retrieval results
"""

import hashlib
import logging
import re
from typing import Dict, Any, List, Optional

from ..llm import get_reasoning_client
from ..state import GroundedClaim, Citation, ArtifactRef, CitationPreview

logger = logging.getLogger(__name__)

# Citation ID counter for unique IDs
_citation_counter = 0


def _generate_source_chunk_id(cite_data: Dict, citation_type: str) -> str:
    """Generate a unique, deterministic ID for citation grounding."""
    key_parts = [
        str(cite_data.get('session_id', '')),
        str(cite_data.get('speaker', '')),
        str(cite_data.get('timestamp', '')),
        str(cite_data.get('quote_preview', cite_data.get('evidence', '')))[:100],
        citation_type
    ]
    key_string = '|'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()[:12]


def _validate_citation_against_retrieval(
    cite_data: Dict,
    citation_type: str,
    state: Dict
) -> bool:
    """
    Validate that a citation exists in the actual retrieval results.

    This ensures the paper claim 'artifact-grounded' is defensible.
    Handles all tool response formats.
    """
    session_id = cite_data.get('session_id')
    speaker = cite_data.get('speaker')
    dimension = cite_data.get('dimension')  # For 7C citations
    score = cite_data.get('score')  # For 7C citations

    # Get all retrieval results
    retrieval_results = state.get('retrieval_results', [])
    subgoal_results = state.get('subgoal_results', {})

    # Check in retrieval_results
    for result in retrieval_results:
        # Check top-level session_id (specific tools)
        result_session = result.get('session_id')
        if session_id and result_session == session_id:
            return True

        # Check legacy results format
        for item in result.get('results', []):
            if isinstance(item, dict):
                item_session = item.get('session_device_id', item.get('session_id'))
                item_speaker = item.get('speaker', item.get('speaker_alias', ''))

                if session_id and item_session == session_id:
                    if not speaker or speaker.lower() == item_speaker.lower():
                        return True

        # Check get_transcript format
        for u in result.get('utterances', []):
            if isinstance(u, dict):
                item_speaker = u.get('speaker', u.get('speaker_tag', ''))
                if result_session == session_id:
                    if not speaker or speaker.lower() == item_speaker.lower():
                        return True

        # Check get_concept_map format
        for n in result.get('nodes', []):
            if isinstance(n, dict):
                if result_session == session_id:
                    return True

        # Check search_for_sessions format
        for s in result.get('sessions', []):
            if isinstance(s, dict):
                if s.get('session_id') == session_id:
                    return True

    # Check in subgoal_results evidence
    for subgoal_id, sg_result in subgoal_results.items():
        for step in sg_result.get('steps_executed', []):
            tool_result = step.get('tool_result', {})
            tool_session = tool_result.get('session_id')

            # Check top-level session_id
            if session_id and tool_session == session_id:
                return True

            # Check legacy results format
            for item in tool_result.get('results', []):
                if isinstance(item, dict):
                    item_session = item.get('session_device_id', item.get('session_id'))
                    if session_id and item_session == session_id:
                        return True

            # Check utterances format
            if tool_result.get('utterances') and tool_session == session_id:
                return True

            # Check nodes format
            if tool_result.get('nodes') and tool_session == session_id:
                return True

            # Check 7C analysis format - validate dimension and score
            if citation_type == '7c' and dimension:
                # Check if this tool returned 7C data
                for item in tool_result.get('results', []):
                    if isinstance(item, dict):
                        dimensions = item.get('dimensions', {})
                        if dimension.lower() in dimensions:
                            dim_data = dimensions[dimension.lower()]
                            retrieved_score = dim_data.get('score')
                            # Validate if score matches (if provided) or dimension exists
                            if score is None or retrieved_score == score:
                                return True

    # Special handling for 7C citations without session_id
    # If we retrieved 7C data for ANY session and citation mentions a dimension, validate it
    if citation_type == '7c' and dimension and not session_id:
        for subgoal_id, sg_result in subgoal_results.items():
            for step in sg_result.get('steps_executed', []):
                tool_result = step.get('tool_result', {})
                tool_name = step.get('step', {}).get('tool', '')
                if 'collaboration' in tool_name or '7c' in tool_name.lower():
                    # 7C tool was used - validate the dimension exists
                    for item in tool_result.get('results', []):
                        if isinstance(item, dict):
                            dimensions = item.get('dimensions', {})
                            if dimension.lower() in dimensions:
                                return True

    return False


SYNTHESIS_SYSTEM_PROMPT = """You are an expert analyst of collaborative learning discussions.

Your task: Analyze the evidence and provide thoughtful, insightful answers.

## CRITICAL ACCURACY RULES

1. **Session IDs**: Only use session IDs that appear in the evidence. If evidence says "[David, Session 20]", that's Session 20 - don't guess or infer.

2. **Speaker-Session Match**: The "Speakers and Their Sessions" section shows who was in which session. NEVER claim a speaker said something in a session they didn't participate in.

## YOUR ROLE AS AN ANALYST

You're not just summarizing data - you're interpreting it. You should:
- **Reason about patterns**: What do the data suggest about collaboration quality, thinking styles, or group dynamics?
- **Connect dots**: How do transcripts, concept maps, and 7C scores tell a coherent story?
- **Offer interpretations**: Based on the evidence, what conclusions can you draw?
- **Share observations**: What's surprising, notable, or worth exploring further?

## WRITING STYLE

Write clean, readable prose like a thoughtful colleague sharing insights:
- Ground claims in specific evidence (quotes, scores, concept connections)
- Explain your reasoning: "The high communication score combined with Tucker's repeated questions suggests..."
- Be direct about what the data shows, but also share your analytical perspective
- Mention sources naturally (e.g., "David explained...", "In session 20...")

DON'T:
- Use bracketed citations like (Session 20, David) or [7C: Score] - references will be shown separately
- Just list data without interpretation
- Use robotic phrases or force artificial structure
- Hedge excessively - commit to conclusions the evidence supports
- Avoid giving your analysis or opinion when the data supports it

## WHAT TO INCLUDE

1. **Direct answer** - Your key finding and interpretation
2. **Evidence and reasoning** - How you reached your conclusion, with quotes and scores
3. **Analytical insights** - Patterns, connections, or implications you noticed
4. **Open questions** - What would be worth exploring further

## RESPONSE FORMAT

Return JSON:
{
    "answer": "Your full answer with analysis in natural markdown. Include your reasoning and interpretation, not just data. Mention sources naturally in prose (no bracketed citations).",
    "artifacts_referenced": [
        {
            "type": "transcript|concept_map|7c_analysis|speaker_profile",
            "session_id": 20,
            "speaker": "David",
            "key_content": "Brief description of what this artifact showed"
        }
    ],
    "confidence": 0.0 to 1.0,
    "follow_ups": ["Suggested next questions based on what you found"]
}

## INTERPRETING THE DATA

- **Transcripts**: Primary evidence - actual words spoken. Look for reasoning patterns, questions, elaborations.
- **Concept maps**: Show how ideas connect - hub concepts indicate key themes, causal chains show reasoning.
- **7C scores**: Collaboration quality (0-100). Each dimension includes:
  * Score (0-100)
  * Explanation of WHY that score was given
  * Coded segments - specific observed behaviors that justify the score
  When citing 7C data, DON'T just mention the score - explain what the evidence shows:
  * BAD: "The contribution score was 20/100"
  * GOOD: "The contribution score was just 20/100 because only Speaker 17 participated, with no input or responses from other participants"
  Interpret combinations: high communication + low conflict = collaborative exploration; high constructive + low contribution = one person driving.
- **Clusters**: Thematic groupings. Multiple speakers in same cluster = shared focus; isolated clusters = parallel thinking.

**Important**: Don't just report the data - analyze it. If 7C shows high context (90/100) and the concept map has deep causal chains, that suggests sophisticated reasoning. Say so."""


def synthesize_grounded_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final grounded response.

    PRAS Stage 5: Grounded Synthesis

    Args:
        state: Current agent state with all evidence

    Returns:
        State updates with final answer
    """
    query = state.get('current_query', state.get('original_query', ''))
    cross_rep_analysis = state.get('cross_rep_analysis', {})
    subgoal_results = state.get('subgoal_results', {})
    sub_goals = state.get('sub_goals', [])
    reps_used = state.get('representations_used', [])

    logger.info(f"[PRAS Stage 5] Synthesizing grounded response")

    # Format all inputs for synthesis
    synthesis_input = _format_synthesis_input(
        query, sub_goals, subgoal_results, cross_rep_analysis
    )

    try:
        llm = get_reasoning_client()

        result = llm.json_chat(
            system=SYNTHESIS_SYSTEM_PROMPT,
            user=synthesis_input,
            temperature=0.2,  # Slightly higher for natural language
            max_tokens=2500
        )

        if result:
            return _process_synthesis_result(result, state, reps_used)

    except Exception as e:
        logger.error(f"Synthesis error: {e}")

    # Fallback synthesis
    return _fallback_synthesis(query, subgoal_results, cross_rep_analysis, reps_used, state)


def _format_synthesis_input(
    query: str,
    sub_goals: List[Dict],
    subgoal_results: Dict[str, Dict],
    cross_rep_analysis: Dict
) -> str:
    """Format all evidence for synthesis LLM."""
    sections = [f"# Query\n{query}"]

    # CRITICAL: Extract and display all session IDs actually present in the data
    # This prevents the LLM from hallucinating session IDs from context
    sessions_found = set()
    speakers_found = {}  # speaker -> sessions they appear in

    for sg_id, result in subgoal_results.items():
        for step in result.get('steps_executed', []):
            tool_result = step.get('tool_result', {})

            # Get session_id from top-level for specific tools
            tool_session = tool_result.get('session_id')
            if tool_session and isinstance(tool_session, int):
                sessions_found.add(tool_session)

            # Handle legacy results format
            for r in tool_result.get('results', []):
                if isinstance(r, dict):
                    session = r.get('session_device_id') or r.get('session_id') or r.get('session') or tool_session
                    speaker = r.get('speaker', r.get('speaker_alias', ''))
                    if session and isinstance(session, int):
                        sessions_found.add(session)
                        if speaker:
                            if speaker not in speakers_found:
                                speakers_found[speaker] = set()
                            speakers_found[speaker].add(session)

            # Handle get_transcript format
            for u in tool_result.get('utterances', []):
                if isinstance(u, dict):
                    speaker = u.get('speaker', u.get('speaker_tag', ''))
                    if speaker and tool_session and isinstance(tool_session, int):
                        if speaker not in speakers_found:
                            speakers_found[speaker] = set()
                        speakers_found[speaker].add(tool_session)

            # Handle get_concept_map format
            for n in tool_result.get('nodes', []):
                if isinstance(n, dict):
                    attributed_to = n.get('attributed_to', '')
                    if attributed_to and tool_session and isinstance(tool_session, int):
                        if attributed_to not in speakers_found:
                            speakers_found[attributed_to] = set()
                        speakers_found[attributed_to].add(tool_session)

            # Handle search_for_sessions format
            for s in tool_result.get('sessions', []):
                if isinstance(s, dict):
                    sess_id = s.get('session_id')
                    if sess_id and isinstance(sess_id, int):
                        sessions_found.add(sess_id)

    if sessions_found:
        sections.append(f"\n# Sessions Found in Evidence: {sorted(sessions_found)}")
        sections.append("**IMPORTANT: Only cite sessions from this list. These are the ONLY valid session IDs.**")
        if speakers_found:
            speaker_info = [f"  - {s}: Sessions {sorted(list(sess))}" for s, sess in speakers_found.items()]
            sections.append("\n# Speakers and Their Sessions:")
            sections.extend(speaker_info)
            sections.append("\n**Use these exact session-speaker mappings when citing.**")

    # Sub-goal evidence
    sections.append("\n# Evidence by Sub-goal")
    logger.info(f"[Synthesis] sub_goals: {len(sub_goals)}, subgoal_results keys: {list(subgoal_results.keys())}")

    # CRITICAL: Iterate over subgoal_results keys, not sub_goals list
    # This handles cases where _plan_global_comparison creates a new subgoal (sg_compare_all)
    # that doesn't match the original decomposer sub_goals
    all_subgoal_ids = set([sg.get('id') for sg in sub_goals] + list(subgoal_results.keys()))

    for sg_id in all_subgoal_ids:
        result = subgoal_results.get(sg_id, {})
        steps_count = len(result.get('steps_executed', []))
        # Find matching sub_goal for description, or use sg_id as fallback
        matching_sg = next((sg for sg in sub_goals if sg.get('id') == sg_id), None)
        sg_description = matching_sg.get('description') if matching_sg else f"Subgoal: {sg_id}"
        logger.info(f"[Synthesis] Subgoal {sg_id}: steps_executed={steps_count}")

        sg_section = [f"\n## {sg_description}"]
        sg_section.append(f"Status: {'Satisfied' if result.get('satisfied') else 'Partially satisfied'}")
        sg_section.append(f"Evidence summary: {result.get('evidence_summary', 'See details below')}")

        # Key evidence from steps
        for step in result.get('steps_executed', [])[:3]:
            step_info = step.get('step', {})
            tool_result = step.get('tool_result', {})
            tool_name = step_info.get('tool', '')

            # CRITICAL: Get session_id from tool_result top level
            tool_session_id = tool_result.get('session_id')
            session_name = tool_result.get('session_name', f'Session {tool_session_id}' if tool_session_id else 'Unknown')

            # Handle compare_sessions results specially
            if tool_name == 'compare_sessions' and tool_result.get('results'):
                logger.info(f"[Synthesis] Processing compare_sessions results")
                comparison = tool_result['results'][0] if tool_result['results'] else {}
                summary = comparison.get('summary', {})
                collab_scores = summary.get('collaboration_scores', {})
                logger.info(f"[Synthesis] Collaboration scores: {collab_scores}")

                if collab_scores:
                    # Sort by score descending
                    sorted_scores = sorted(collab_scores.items(), key=lambda x: x[1], reverse=True)
                    sg_section.append(f"\n**COMPARISON RESULTS - Collaboration Scores (Ranked):**")
                    for rank, (sess_id, score) in enumerate(sorted_scores, 1):
                        sg_section.append(f"  {rank}. Session {sess_id}: {score}/100")

                    # Highlight the winner
                    if sorted_scores:
                        best_session, best_score = sorted_scores[0]
                        sg_section.append(f"\n**BEST SESSION: Session {best_session} with score {best_score}/100**")

                # Also add session themes
                themes = summary.get('themes', {})
                if themes:
                    sg_section.append("\n**Session Themes:**")
                    for sess_id, theme_list in themes.items():
                        if theme_list:
                            sg_section.append(f"  - Session {sess_id}: {', '.join(theme_list[:2])}")

            # Handle legacy results format (search tools)
            elif tool_result.get('results'):
                sg_section.append(f"\nFrom {step_info.get('representation')}:")
                for r in tool_result['results'][:5]:
                    if isinstance(r, dict):
                        text = r.get('text', r.get('content', r.get('transcript', '')))[:150]
                        speaker = r.get('speaker', r.get('speaker_alias', r.get('speaker_tag', '')))
                        session = r.get('session_device_id') or r.get('session_id') or r.get('session') or tool_session_id

                        if speaker and session:
                            sg_section.append(f"  - **SESSION {session}**, {speaker}: \"{text}\"")
                            sg_section.append(f"    (Cite as: Session {session}, {speaker})")
                        elif speaker:
                            sg_section.append(f"  - {speaker}: \"{text}\"")
                        elif session:
                            sg_section.append(f"  - **SESSION {session}**: \"{text}\"")
                        else:
                            sg_section.append(f"  - \"{text}\"")

            # Handle get_transcript format (specific tool)
            elif tool_result.get('utterances'):
                session = tool_session_id
                sg_section.append(f"\nFrom transcript (Session {session}):")
                for u in tool_result['utterances'][:8]:
                    if isinstance(u, dict):
                        speaker = u.get('speaker', u.get('speaker_tag', ''))
                        text = u.get('text', u.get('transcript', ''))[:150]
                        if speaker and session:
                            sg_section.append(f"  - **SESSION {session}**, {speaker}: \"{text}\"")
                            sg_section.append(f"    (Cite as: Session {session}, {speaker})")
                        elif speaker:
                            sg_section.append(f"  - {speaker}: \"{text}\"")

            # Handle get_concept_map format (specific tool)
            elif tool_result.get('nodes'):
                session = tool_session_id
                sg_section.append(f"\nFrom concept map (Session {session}):")

                # IMPORTANT: Include graph statistics summary FIRST
                summary = tool_result.get('summary', {})
                if summary:
                    node_types = summary.get('node_types', {})
                    speaker_contribs = summary.get('speaker_contributions', {})
                    total_nodes = summary.get('total_nodes', 0)

                    # Graph statistics
                    if node_types:
                        type_str = ', '.join([f"{k}: {v}" for k, v in node_types.items()])
                        sg_section.append(f"  **GRAPH STATS**: {total_nodes} total nodes - {type_str}")
                        # Calculate question density
                        if 'question' in node_types and total_nodes > 0:
                            density = round(100 * node_types['question'] / total_nodes, 1)
                            sg_section.append(f"    → Question density: {node_types['question']}/{total_nodes} = {density}%")

                    # Speaker contributions
                    if speaker_contribs:
                        sg_section.append(f"  **SPEAKER CONTRIBUTIONS**:")
                        for speaker, data in speaker_contribs.items():
                            total = data.get('total', 0)
                            by_type = data.get('by_type', {})
                            type_breakdown = ', '.join([f"{k}: {v}" for k, v in by_type.items()])
                            pct = round(100 * total / total_nodes, 1) if total_nodes > 0 else 0
                            sg_section.append(f"    - {speaker}: {total} nodes ({pct}%) - {type_breakdown}")

                # Then include individual nodes
                nodes = tool_result['nodes'][:8]
                if nodes:
                    sg_section.append(f"  Key concepts:")
                    for n in nodes:
                        if isinstance(n, dict):
                            label = n.get('label', '')[:100]
                            ntype = n.get('type', n.get('node_type', 'concept'))
                            attributed = n.get('attributed_to', 'unknown')
                            sg_section.append(f"  - [{ntype}] {label} (by {attributed}, Session {session})")

            # Handle get_7c_analysis format (specific tool)
            elif tool_result.get('dimensions'):
                session = tool_session_id
                dims = tool_result['dimensions']
                if isinstance(dims, dict):
                    sg_section.append(f"\n**7C Collaboration Analysis (Session {session}):**")
                    sg_section.append("IMPORTANT: Use these scores AND explanations to support your answer.")

                    for dim_name, dim_data in dims.items():
                        if not isinstance(dim_data, dict):
                            continue
                        score = dim_data.get('score', 0)
                        explanation = dim_data.get('explanation', '')[:300]  # Increased from 150
                        coded_segments = dim_data.get('coded_segments', [])

                        sg_section.append(f"\n  **{dim_name.upper()}**: {score}/100")
                        sg_section.append(f"    Why: {explanation}")

                        # Include coded segments as concrete evidence
                        if coded_segments:
                            sg_section.append(f"    Observed behaviors:")
                            for seg in coded_segments[:3]:  # Include up to 3 per dimension
                                if isinstance(seg, str) and seg.strip():
                                    sg_section.append(f"      • \"{seg[:200]}\"")

                    sg_section.append("\n  >> When discussing collaboration quality, CITE specific scores and explain WHY using the evidence above.")

            # Handle search_for_sessions format (discovery)
            elif tool_result.get('sessions'):
                sg_section.append(f"\nFrom session search:")
                for s in tool_result['sessions'][:5]:
                    if isinstance(s, dict):
                        sess_id = s.get('session_id')
                        sess_name = s.get('session_name', '')
                        summary = s.get('summary', '')[:100]
                        sg_section.append(f"  - **SESSION {sess_id}** ({sess_name}): {summary}")

            # Handle legacy artifacts format (from get_artifacts tool - deprecated)
            elif tool_result.get('artifacts'):
                session = tool_session_id or tool_result.get('session_id')
                artifacts = tool_result['artifacts']

                if 'transcript' in artifacts:
                    transcript = artifacts['transcript']
                    sg_section.append(f"\nFrom transcript (Session {session}):")
                    for u in transcript.get('utterances', [])[:5]:
                        speaker = u.get('speaker', '')
                        text = u.get('text', '')[:150]
                        if speaker and session:
                            sg_section.append(f"  - **SESSION {session}**, {speaker}: \"{text}\"")
                            sg_section.append(f"    (Cite as: Session {session}, {speaker})")

                if 'concept_map' in artifacts:
                    concept_map = artifacts['concept_map']
                    nodes = concept_map.get('nodes', [])[:5]
                    if nodes:
                        sg_section.append(f"\nFrom concept map (Session {session}):")
                        for n in nodes:
                            label = n.get('label', '')[:100]
                            ntype = n.get('type', 'concept')
                            attributed = n.get('attributed_to', 'unknown')
                            sg_section.append(f"  - [{ntype}] {label} (by {attributed}, Session {session})")

        sections.append('\n'.join(sg_section))

    # Cross-rep analysis
    sections.append("\n# Cross-Representation Analysis")

    conv_points = cross_rep_analysis.get('convergence_points', [])
    if conv_points:
        sections.append("\n## Convergence Points")
        for cp in conv_points:
            sections.append(f"- {cp.get('claim')} (confidence: {cp.get('confidence')})")
            sections.append(f"  Supported by: {', '.join(cp.get('supporting_reps', []))}")

    tension_points = cross_rep_analysis.get('tension_points', [])
    if tension_points:
        sections.append("\n## Tension Points")
        for tp in tension_points:
            sections.append(f"- {tp.get('aspect')}")
            sections.append(f"  {tp.get('rep1', {}).get('name')}: {tp.get('rep1', {}).get('finding')}")
            sections.append(f"  {tp.get('rep2', {}).get('name')}: {tp.get('rep2', {}).get('finding')}")
            sections.append(f"  Interpretation: {tp.get('interpretation')}")

    gaps = cross_rep_analysis.get('gaps', [])
    if gaps:
        sections.append("\n## Gaps")
        for gap in gaps:
            sections.append(f"- {gap.get('aspect')}: {gap.get('reason')}")

    confidence = cross_rep_analysis.get('overall_confidence', 0.5)
    rationale = cross_rep_analysis.get('confidence_rationale', '')
    sections.append(f"\n## Overall Confidence: {confidence:.0%}")
    sections.append(f"Rationale: {rationale}")

    sections.append("\n# Instructions")
    sections.append("Generate a well-grounded answer with explicit citations to the evidence above.")

    return '\n'.join(sections)


def _process_synthesis_result(
    result: Dict,
    state: Dict,
    reps_used: List[str]
) -> Dict[str, Any]:
    """Process LLM synthesis result into state updates."""
    answer = result.get('answer', '')
    follow_ups = result.get('follow_ups', [])

    # Handle new simplified format (artifacts_referenced) or old format (citations_used)
    artifacts_referenced = result.get('artifacts_referenced', [])
    llm_citations = result.get('citations_used', [])  # Old format fallback

    # Get confidence from LLM result or fall back to cross-rep analysis
    llm_confidence = result.get('confidence')
    if isinstance(llm_confidence, (int, float)):
        confidence = float(llm_confidence)
    else:
        cross_rep = state.get('cross_rep_analysis', {})
        confidence = cross_rep.get('overall_confidence', 0.5)

    # Build citations from artifacts_referenced (new format) or llm_citations (old format)
    if artifacts_referenced:
        citations = _build_citations_from_artifacts(artifacts_referenced, state)
    else:
        # Old format - handle main_claims
        main_claims = result.get('main_claims', [])
        citations = _build_structured_citations(
            llm_citations=llm_citations,
            main_claims=main_claims,
            answer=answer,
            state=state
        )

    # Simplified grounded claims (not forcing the old structure)
    grounded_claims = []

    # Build reasoning trace for transparency
    cross_rep = state.get('cross_rep_analysis', {})
    reasoning_trace = {
        'sub_goals_count': len(state.get('sub_goals', [])),
        'subgoals_satisfied': sum(
            1 for r in state.get('subgoal_results', {}).values()
            if r.get('satisfied')
        ),
        'representations_used': reps_used,
        'convergence_count': len(cross_rep.get('convergence_points', [])),
        'tension_count': len(cross_rep.get('tension_points', [])),
        'gap_count': len(cross_rep.get('gaps', []))
    }

    return {
        'pras_stage': 'synthesize',
        'final_answer': answer,
        'grounded_claims': grounded_claims,
        'citations': citations,
        'confidence': confidence,
        'representations_used': reps_used,
        'follow_ups': follow_ups,
        'reasoning_trace': reasoning_trace,
        'reflection': None,  # No longer forcing tensions/limitations
        'next_action': 'format',
        'thought_history': state.get('thought_history', []) + [
            f"Synthesized answer with {len(citations)} artifact references, "
            f"confidence {confidence:.0%}"
        ]
    }


def _build_citations_from_artifacts(
    artifacts: List[Dict],
    state: Dict
) -> List[Citation]:
    """Build Citation objects from the new artifacts_referenced format.

    Now includes validation against retrieval results for the 'validated' field.
    """
    citations = []

    for i, artifact in enumerate(artifacts):
        # Build cite_data for validation
        cite_data = {
            'session_id': artifact.get('session_id'),
            'speaker': artifact.get('speaker'),
            'evidence': artifact.get('key_content', '')
        }

        # Normalize citation type
        cite_type = _normalize_citation_type(artifact.get('type', 'transcript'))

        # Generate source chunk ID for traceability
        source_chunk_id = _generate_source_chunk_id(cite_data, cite_type)

        # Validate against actual retrieval results
        validated = _validate_citation_against_retrieval(cite_data, cite_type, state)

        if not validated:
            logger.debug(f"[Citation Grounding] Unvalidated artifact citation: Session {artifact.get('session_id')}")

        citation = {
            'id': f"cite-{i+1}",
            'citationType': cite_type,
            'inlineText': f"Session {artifact.get('session_id', '?')}",
            'referenceText': artifact.get('key_content', ''),
            'artifactRef': {
                'sessionId': artifact.get('session_id'),
                'speaker': artifact.get('speaker')
            },
            'preview': {
                'title': f"{cite_type} - Session {artifact.get('session_id', '?')}",
                'content': artifact.get('key_content', '')[:300],
                'metadata': {'speaker': artifact.get('speaker')}
            },
            # Grounding fields
            'sourceChunkId': source_chunk_id,
            'validated': validated
        }
        citations.append(citation)

    validated_count = sum(1 for c in citations if c.get('validated'))
    logger.info(f"[Citations] Built {len(citations)} citations, {validated_count} validated")
    return citations


# =============================================================================
# Citation Building Functions
# =============================================================================

def _build_structured_citations(
    llm_citations: List[Dict],
    main_claims: List[Dict],
    answer: str,
    state: Dict
) -> List[Citation]:
    """
    Build structured Citation objects from LLM output.

    Combines LLM-provided citation metadata with:
    1. Artifact references for popover fetching
    2. Preview content for quick display
    3. Unique citation IDs
    """
    global _citation_counter
    citations: List[Citation] = []
    seen_inline_texts = set()  # Deduplicate

    # First, try to use LLM-provided citations
    for cite_data in llm_citations:
        inline_text = cite_data.get('inline_text', '')
        if not inline_text or inline_text in seen_inline_texts:
            continue
        seen_inline_texts.add(inline_text)

        cite_type = cite_data.get('type', _infer_citation_type(inline_text))
        citation = _create_citation(
            inline_text=inline_text,
            citation_type=cite_type,
            cite_data=cite_data,
            state=state
        )
        if citation:
            citations.append(citation)

    # Also extract from grounding if LLM didn't provide citations_used
    if not llm_citations:
        for claim in main_claims:
            for grounding in claim.get('grounding', []):
                citation_text = grounding.get('citation', '')
                if citation_text and citation_text not in seen_inline_texts:
                    seen_inline_texts.add(citation_text)
                    cite_type = grounding.get('rep', _infer_citation_type(citation_text))
                    citation = _create_citation(
                        inline_text=citation_text,
                        citation_type=cite_type,
                        cite_data=grounding,
                        state=state
                    )
                    if citation:
                        citations.append(citation)

    # Parse any remaining citations from the answer text
    additional_citations = _extract_citations_from_answer(answer, seen_inline_texts, state)
    citations.extend(additional_citations)

    logger.info(f"[Citations] Built {len(citations)} structured citations")
    return citations


def _create_citation(
    inline_text: str,
    citation_type: str,
    cite_data: Dict,
    state: Dict
) -> Optional[Dict[str, Any]]:
    """
    Create a single Citation object with artifact ref, preview, and grounding.

    Enhancement: True Citation Grounding
    - Generates source_chunk_id for traceability
    - Validates against retrieval results
    """
    global _citation_counter
    _citation_counter += 1
    citation_id = f"cite-{_citation_counter}"

    # Normalize citation type
    cite_type = _normalize_citation_type(citation_type)

    # Build artifact reference
    artifact_ref = _build_artifact_ref(cite_type, cite_data)

    # Build preview content
    preview = _build_preview(cite_type, cite_data, state)

    # Generate reference text
    reference_text = _generate_reference_text(cite_type, cite_data, inline_text)

    # Generate source chunk ID for traceability
    source_chunk_id = _generate_source_chunk_id(cite_data, cite_type)

    # Validate against actual retrieval results
    validated = _validate_citation_against_retrieval(cite_data, cite_type, state)

    if not validated:
        logger.warning(f"[Citation Grounding] Unvalidated citation: {inline_text}")

    # Return dict with all fields including grounding
    return {
        'id': citation_id,
        'citation_type': cite_type,
        'inline_text': inline_text,
        'reference_text': reference_text,
        'artifact_ref': artifact_ref,
        'preview': preview,
        # Grounding fields for paper claim "artifact-grounded"
        'source_chunk_id': source_chunk_id,
        'validated': validated
    }


def _normalize_citation_type(cite_type: str) -> str:
    """Normalize citation type to one of: transcript, concept, 7c, cluster, session, speaker."""
    cite_type = cite_type.lower().strip()

    type_aliases = {
        'transcript': 'transcript',
        'transcripts': 'transcript',
        'quote': 'transcript',
        'concept': 'concept',
        'concept_map': 'concept',
        'concepts': 'concept',
        'edge': 'concept',
        '7c': '7c',
        'collaboration': '7c',
        'seven_c': '7c',
        'cluster': 'cluster',
        'community': 'cluster',
        'session': 'session',
        'overview': 'session',
        'session_overview': 'session',
        'speaker': 'speaker',
        'profile': 'speaker',
        'speaker_profile': 'speaker'
    }

    return type_aliases.get(cite_type, 'transcript')


def _infer_citation_type(inline_text: str) -> str:
    """Infer citation type from inline text pattern."""
    patterns = [
        (r'\(Session \d+,\s*[^)]+\)', 'transcript'),
        (r'\[Concept:\s*"[^"]+"\]', 'concept'),
        (r'\[Edge:\s*[^\]]+\]', 'concept'),
        (r'\[7C:\s*\w+\s*\d+/100\]', '7c'),
        (r'\[Cluster:\s*"[^"]+"\]', 'cluster'),
        (r'\[Session:\s*\d+\s+Overview\]', 'session'),
        (r'\[Speaker:\s*[^\]]+\]', 'speaker')
    ]

    for pattern, cite_type in patterns:
        if re.search(pattern, inline_text, re.IGNORECASE):
            return cite_type

    return 'transcript'  # Default


def _build_artifact_ref(cite_type: str, cite_data: Dict) -> ArtifactRef:
    """Build artifact reference for popover fetching."""
    ref = ArtifactRef()

    # Session ID
    session_id = cite_data.get('session_id')
    if session_id is not None:
        ref['session_id'] = int(session_id) if isinstance(session_id, (int, str)) else None

    # Speaker
    speaker = cite_data.get('speaker')
    if speaker:
        ref['speaker'] = str(speaker)

    # Type-specific refs
    if cite_type == 'concept':
        concept_text = cite_data.get('concept_text') or cite_data.get('evidence', '')
        if concept_text:
            ref['concept_id'] = concept_text[:50]  # Use text as ID for now

    elif cite_type == '7c':
        dimension = cite_data.get('dimension')
        if dimension:
            ref['dimension'] = dimension

    elif cite_type == 'cluster':
        cluster_name = cite_data.get('cluster_name') or cite_data.get('evidence', '')
        if cluster_name:
            ref['cluster_id'] = cluster_name

    # Timestamp
    timestamp = cite_data.get('timestamp')
    if timestamp is not None:
        try:
            ref['timestamp'] = float(timestamp)
        except (ValueError, TypeError):
            pass

    return ref


def _build_preview(cite_type: str, cite_data: Dict, state: Dict) -> CitationPreview:
    """Build preview content for popover display."""
    # Get evidence text for preview - ensure never None
    evidence = cite_data.get('evidence') or cite_data.get('quote_preview') or ''
    if evidence and len(evidence) > 300:
        evidence = evidence[:297] + '...'

    # Type-specific preview building
    if cite_type == 'transcript':
        speaker = cite_data.get('speaker', 'Unknown')
        session_id = cite_data.get('session_id', '?')
        title = f"{speaker} - Session {session_id}"
        metadata = {
            'wordCount': len(evidence.split()) if evidence else 0,
            'timestamp': cite_data.get('timestamp')
        }

    elif cite_type == 'concept':
        concept_text = cite_data.get('concept_text', evidence[:50])
        title = f"Concept: {concept_text}"
        metadata = {
            'conceptType': cite_data.get('concept_type', 'idea'),
            'speaker': cite_data.get('speaker'),
            'connections': cite_data.get('connections', 0)
        }

    elif cite_type == '7c':
        dimension = cite_data.get('dimension', 'Unknown')
        score = cite_data.get('score', 0)
        title = f"{dimension} - {score}/100"
        metadata = {
            'score': score,
            'dimension': dimension,
            'explanation': evidence[:200] if evidence else ''
        }

    elif cite_type == 'cluster':
        cluster_name = cite_data.get('cluster_name', evidence[:30])
        title = f"Cluster: {cluster_name}"
        metadata = {
            'clusterSize': cite_data.get('cluster_size', 0),
            'keyConcepts': cite_data.get('key_concepts', [])
        }

    elif cite_type == 'session':
        session_id = cite_data.get('session_id', '?')
        title = f"Session {session_id} Overview"
        metadata = {
            'participants': cite_data.get('participants', []),
            'duration': cite_data.get('duration')
        }

    elif cite_type == 'speaker':
        speaker = cite_data.get('speaker', 'Unknown')
        title = f"Speaker: {speaker}"
        metadata = {
            'sessionCount': cite_data.get('session_count', 0),
            'utteranceCount': cite_data.get('utterance_count', 0)
        }

    else:
        title = 'Reference'
        metadata = {}

    return CitationPreview(
        title=title,
        content=evidence,
        metadata=metadata
    )


def _generate_reference_text(cite_type: str, cite_data: Dict, inline_text: str) -> str:
    """Generate reference list text for a citation."""
    if cite_type == 'transcript':
        speaker = cite_data.get('speaker') or 'Unknown'
        evidence = cite_data.get('evidence') or cite_data.get('quote_preview') or ''
        if evidence:
            return f"{speaker}'s statement: \"{evidence[:80]}...\"" if len(evidence) > 80 else f"{speaker}'s statement: \"{evidence}\""
        return f"Quote from {speaker}"

    elif cite_type == 'concept':
        concept_text = cite_data.get('concept_text') or cite_data.get('evidence') or inline_text or 'Unknown concept'
        return f"Concept node: {concept_text[:60]}"

    elif cite_type == '7c':
        dimension = cite_data.get('dimension') or 'Unknown'
        score = cite_data.get('score') or 0
        return f"7C {dimension} dimension score: {score}/100"

    elif cite_type == 'cluster':
        cluster_name = cite_data.get('cluster_name') or cite_data.get('evidence') or inline_text or 'Unknown cluster'
        return f"Thematic cluster: {cluster_name}"

    elif cite_type == 'session':
        session_id = cite_data.get('session_id', '?')
        return f"Session {session_id} overview and summary"

    elif cite_type == 'speaker':
        speaker = cite_data.get('speaker', 'Unknown')
        return f"Speaker profile: {speaker}"

    return inline_text


def _extract_citations_from_answer(
    answer: str,
    seen_inline_texts: set,
    state: Dict
) -> List[Citation]:
    """Extract any citations from answer text that weren't in the structured output."""
    citations: List[Citation] = []

    # Citation patterns to extract
    patterns = [
        (r'\(Session (\d+),\s*([^)]+)\)', 'transcript', ['session_id', 'speaker']),
        (r'\[Concept:\s*"([^"]+)"\]', 'concept', ['concept_text']),
        (r'\[7C:\s*(\w+)\s*(\d+)/100\]', '7c', ['dimension', 'score']),
        (r'\[Cluster:\s*"([^"]+)"\]', 'cluster', ['cluster_name']),
        (r'\[Session:\s*(\d+)\s+Overview\]', 'session', ['session_id']),
        (r'\[Speaker:\s*([^\]]+)\]', 'speaker', ['speaker'])
    ]

    for pattern, cite_type, field_names in patterns:
        for match in re.finditer(pattern, answer, re.IGNORECASE):
            inline_text = match.group(0)
            if inline_text in seen_inline_texts:
                continue
            seen_inline_texts.add(inline_text)

            # Build cite_data from match groups
            cite_data = {}
            for i, field_name in enumerate(field_names, start=1):
                if i <= len(match.groups()):
                    value = match.group(i)
                    if field_name in ('session_id', 'score'):
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            pass
                    cite_data[field_name] = value

            citation = _create_citation(
                inline_text=inline_text,
                citation_type=cite_type,
                cite_data=cite_data,
                state=state
            )
            if citation:
                citations.append(citation)

    return citations


def _generate_reflection(
    tensions: List[Dict],
    limitations: List[str]
) -> str:
    """Generate a reflection note about the answer."""
    parts = []

    if tensions:
        parts.append(f"Acknowledged {len(tensions)} tension(s) in the evidence.")

    if limitations:
        parts.append(f"Noted {len(limitations)} limitation(s):")
        for lim in limitations[:3]:
            parts.append(f"  - {lim}")

    return ' '.join(parts) if parts else "Answer synthesized from available evidence."


def _fallback_synthesis(
    query: str,
    subgoal_results: Dict[str, Dict],
    cross_rep_analysis: Dict,
    reps_used: List[str],
    state: Dict
) -> Dict[str, Any]:
    """Fallback synthesis when LLM fails."""
    # Gather key findings
    findings = []
    for sg_id, result in subgoal_results.items():
        if result.get('evidence_summary'):
            findings.append(f"- {result['evidence_summary']}")
        for step in result.get('steps_executed', [])[:1]:
            reflection = step.get('reflection', {})
            if reflection.get('indicators_found'):
                findings.append(f"- Found: {', '.join(reflection['indicators_found'])}")

    # Build basic answer
    answer_parts = [f"Based on analysis of {len(reps_used)} representation types:"]
    if findings:
        answer_parts.extend(findings)
    else:
        answer_parts.append("Limited evidence was found for this query.")

    # Add gaps
    gaps = cross_rep_analysis.get('gaps', [])
    if gaps:
        answer_parts.append("\n**Limitations:**")
        for gap in gaps[:3]:
            answer_parts.append(f"- {gap.get('aspect', 'Some aspects')}: {gap.get('reason', 'insufficient evidence')}")

    answer = '\n'.join(answer_parts)

    return {
        'pras_stage': 'synthesize',
        'final_answer': answer,
        'grounded_claims': [],
        'citations': [],
        'confidence': cross_rep_analysis.get('overall_confidence', 0.3),
        'representations_used': reps_used,
        'follow_ups': [],
        'reasoning_trace': {'fallback': True},
        'reflection': 'Fallback synthesis used due to LLM error.',
        'next_action': 'format',
        'thought_history': state.get('thought_history', []) + [
            'Used fallback synthesis'
        ]
    }
