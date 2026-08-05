"""
Cross-Representation Reasoner Node for BLINC Agent V3

PRAS Stage 4: Cross-Representation Reasoning

After all sub-goals are retrieved, reasons across representations to:
1. Detect convergence - multiple reps support same conclusion
2. Detect tension - reps conflict or show different views
3. Weight evidence - which rep is most authoritative
4. Identify gaps - what couldn't be answered
"""

import logging
from typing import Dict, Any, List, Optional

from ..llm import get_fast_client
from ..state import CrossRepAnalysis, ConvergencePoint, TensionPoint

logger = logging.getLogger(__name__)


CROSS_REP_SYSTEM_PROMPT = """You are an expert at interpreting educational evidence from multiple perspectives.

You have evidence from multiple data representations: transcripts (what was said), concept maps (how ideas connect), and collaboration metrics (7C scores). Your task is to analyze what story these different views tell together.

## Your Interpretive Role

Don't just mechanically list convergence/tension - INTERPRET what the evidence means:
- What patterns emerge when you look across representations?
- What does a high 7C score combined with sparse concept map connections suggest?
- When transcript shows hesitation but concept map shows creative leaps, what's happening?

## Epistemic Hierarchy (weight evidence accordingly)

1. TRANSCRIPT (primary) - What was actually said - ground truth
2. CONCEPT_MAP (derived) - Extracted structure of ideas - shows reasoning patterns
3. COLLABORATION (interpreted) - 7C scores - quantifies interaction quality
4. SPEAKER_PROFILE (aggregated) - Patterns across sessions
5. SESSION_OVERVIEW (summary) - High-level context

## Analysis Guidelines

**When representations CONVERGE:**
- This strengthens claims - explain WHY they align
- Example: "The high communication score (85/100) is evident in the transcript where participants frequently build on each other's ideas..."

**When representations show TENSION:**
- This often reveals interesting nuances, not errors
- Interpret what the tension means
- Example: "The concept map shows deep causal reasoning, but contribution score is low (20/100) - this suggests one person drove the intellectual work"

**About GAPS:**
- Be honest about what you couldn't find
- But also reason about whether the gap matters for answering the query

## Response Format

Return JSON:
{
    "convergence_points": [
        {
            "claim": "Your interpretive finding, not just a data summary",
            "supporting_reps": ["transcript", "concept_map"],
            "evidence": [
                {"rep": "transcript", "finding": "specific evidence"},
                {"rep": "concept_map", "finding": "specific evidence"}
            ],
            "confidence": "high" | "medium" | "low"
        }
    ],
    "tension_points": [
        {
            "aspect": "What aspect shows tension",
            "rep1": {"name": "transcript", "finding": "what it suggests"},
            "rep2": {"name": "7c", "finding": "what it suggests"},
            "interpretation": "Your analysis of what this tension reveals"
        }
    ],
    "gaps": [
        {
            "aspect": "What couldn't be answered",
            "reason": "Why",
            "could_help": "What might help"
        }
    ],
    "overall_confidence": 0.0-1.0,
    "confidence_rationale": "Your reasoning about confidence - be specific"
}

**IMPORTANT**: Your convergence and tension interpretations should include ANALYTICAL INSIGHTS, not just structural observations. Tell us what the patterns MEAN for understanding the collaboration or discussion."""


def reason_across_representations(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reason across representations after retrieval.

    PRAS Stage 4: Cross-Representation Reasoning

    Args:
        state: Current agent state with subgoal results

    Returns:
        State updates with cross-rep analysis
    """
    query = state.get('current_query', state.get('original_query', ''))
    subgoal_results = state.get('subgoal_results', {})
    sub_goals = state.get('sub_goals', [])

    logger.info(f"[PRAS Stage 4] Cross-rep reasoning for {len(subgoal_results)} sub-goals")

    if not subgoal_results:
        logger.warning("No subgoal results to reason over")
        return {
            'pras_stage': 'reason',
            'cross_rep_analysis': CrossRepAnalysis(
                convergence_points=[],
                tension_points=[],
                gaps=[{'aspect': 'All', 'reason': 'No evidence retrieved'}],
                overall_confidence=0.0,
                confidence_rationale='No evidence available'
            ),
            'next_action': 'synthesize'
        }

    # Get all representations used
    all_reps = set()
    for result in subgoal_results.values():
        all_reps.update(result.get('representations_used', []))

    # === FAST PATH: Skip LLM for simpler queries ===
    # Use heuristic analysis when:
    # - 1-3 representations used
    # - 1-3 sub-goals total
    # - At least 50% of sub-goals satisfied
    satisfied_count = sum(1 for r in subgoal_results.values() if r.get('satisfied', False))
    satisfaction_ratio = satisfied_count / len(subgoal_results) if subgoal_results else 0
    is_simple = len(all_reps) <= 3 and len(subgoal_results) <= 3 and satisfaction_ratio >= 0.5

    logger.info(f"[PRAS Stage 4] Fast path check: {len(all_reps)} reps, {len(subgoal_results)} subgoals, {satisfied_count}/{len(subgoal_results)} satisfied ({satisfaction_ratio:.0%})")

    if is_simple:
        logger.info(f"[PRAS Stage 4] FAST PATH: {len(all_reps)} reps, {satisfaction_ratio:.0%} satisfied - skipping LLM")
        cross_rep_analysis = _fast_heuristic_analysis(subgoal_results, all_reps)
        return {
            'pras_stage': 'reason',
            'cross_rep_analysis': cross_rep_analysis,
            'representations_used': list(all_reps),
            'next_action': 'synthesize',
            'thought_history': state.get('thought_history', []) + [
                f"Cross-rep analysis (fast path): {len(all_reps)} representations, all satisfied"
            ]
        }

    # Format evidence for LLM (full path - complex queries)
    evidence_text = _format_evidence_for_reasoning(sub_goals, subgoal_results)

    logger.info(f"  Representations used: {list(all_reps)}")

    # Call LLM for cross-rep reasoning
    # Use fast model (GPT-4o-mini) - convergence/tension detection doesn't need full reasoning power
    try:
        llm = get_fast_client()

        user_prompt = f"""Query: {query}

Evidence gathered from {len(all_reps)} representation types across {len(subgoal_results)} sub-goals:

{evidence_text}

Analyze the evidence for:
1. Where do multiple representations converge on the same conclusion?
2. Where do representations show tension or conflict?
3. What aspects couldn't be fully answered?
4. What's your overall confidence in answering the query?"""

        result = llm.json_chat(
            system=CROSS_REP_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.1,
            max_tokens=2000
        )

        if result:
            cross_rep_analysis = _parse_cross_rep_result(result)
        else:
            cross_rep_analysis = _fallback_analysis(subgoal_results)

    except Exception as e:
        logger.error(f"Cross-rep reasoning error: {e}")
        cross_rep_analysis = _fallback_analysis(subgoal_results)

    logger.info(f"  Convergence points: {len(cross_rep_analysis.get('convergence_points', []))}")
    logger.info(f"  Tension points: {len(cross_rep_analysis.get('tension_points', []))}")
    logger.info(f"  Gaps: {len(cross_rep_analysis.get('gaps', []))}")
    logger.info(f"  Overall confidence: {cross_rep_analysis.get('overall_confidence', 0.0):.2f}")

    return {
        'pras_stage': 'reason',
        'cross_rep_analysis': cross_rep_analysis,
        'representations_used': list(all_reps),
        'next_action': 'synthesize',
        'thought_history': state.get('thought_history', []) + [
            f"Cross-rep analysis: {len(cross_rep_analysis.get('convergence_points', []))} convergence, "
            f"{len(cross_rep_analysis.get('tension_points', []))} tensions, "
            f"confidence {cross_rep_analysis.get('overall_confidence', 0.0):.0%}"
        ]
    }


def _format_evidence_for_reasoning(
    sub_goals: List[Dict],
    subgoal_results: Dict[str, Dict]
) -> str:
    """Format all evidence for cross-rep reasoning LLM."""
    sections = []

    for sg in sub_goals:
        sg_id = sg.get('id')
        result = subgoal_results.get(sg_id, {})

        section = [f"## Sub-goal: {sg.get('description')}"]
        section.append(f"Looking for: {', '.join(sg.get('indicators', []))}")
        section.append(f"Satisfied: {'Yes' if result.get('satisfied') else 'No'}")
        section.append(f"Representations used: {', '.join(result.get('representations_used', []))}")

        # Add evidence from each step
        steps = result.get('steps_executed', [])
        for i, step in enumerate(steps):
            step_info = step.get('step', {})
            tool_result = step.get('tool_result', {})
            reflection = step.get('reflection', {})

            section.append(f"\n### From {step_info.get('representation', 'unknown')} ({step_info.get('tool')}):")

            # Add key findings
            # Handle all tool response formats:
            # 1. Legacy 'results' format (search tools)
            # 2. Specific tool formats (get_transcript, get_concept_map, get_7c_analysis)
            # 3. Legacy 'artifacts' format (get_artifacts - deprecated)
            results_to_show = []

            # CRITICAL: Get session_id from tool_result for attribution
            session_id = tool_result.get('session_id')
            session_name = tool_result.get('session_name', f'Session {session_id}' if session_id else 'Unknown')

            if tool_result.get('results'):
                # Legacy search results format
                for r in tool_result['results'][:10]:
                    if isinstance(r, dict):
                        r['_session_id'] = session_id
                        r['_session_name'] = session_name
                    results_to_show.append(r)

            elif tool_result.get('utterances'):
                # get_transcript tool format - direct utterances
                for u in tool_result['utterances']:
                    results_to_show.append({
                        'speaker': u.get('speaker', u.get('speaker_tag', '')),
                        'text': u.get('text', u.get('transcript', '')),
                        '_session_id': session_id,
                        '_session_name': session_name
                    })

            elif tool_result.get('nodes'):
                # get_concept_map tool format - direct nodes
                # FIRST: Include graph statistics from summary (for question density, idea distribution queries)
                summary = tool_result.get('summary', {})
                if summary:
                    node_types = summary.get('node_types', {})
                    speaker_contribs = summary.get('speaker_contributions', {})
                    total_nodes = summary.get('total_nodes', 0)

                    # Format node type counts
                    if node_types:
                        type_str = ', '.join([f"{t}: {c}" for t, c in node_types.items()])
                        results_to_show.append({
                            'text': f"[GRAPH STATS] Total nodes: {total_nodes}, Node types: {type_str}",
                            '_session_id': session_id,
                            '_session_name': session_name
                        })

                    # Format speaker contributions
                    for speaker, data in speaker_contribs.items():
                        by_type = data.get('by_type', {})
                        type_breakdown = ', '.join([f"{t}: {c}" for t, c in by_type.items()])
                        results_to_show.append({
                            'text': f"[SPEAKER CONTRIBUTION] {speaker}: {data.get('total', 0)} total ({type_breakdown})",
                            '_session_id': session_id,
                            '_session_name': session_name
                        })

                # THEN: Include individual nodes
                for n in tool_result['nodes'][:15]:
                    results_to_show.append({
                        'text': f"[{n.get('type', n.get('node_type', 'concept'))}] {n.get('label', '')} (by {n.get('attributed_to', 'unknown')})",
                        '_session_id': session_id,
                        '_session_name': session_name
                    })

            elif tool_result.get('dimensions'):
                # get_7c_analysis tool format - collaboration dimensions
                dims = tool_result['dimensions']
                if isinstance(dims, dict):
                    for dim_name, dim_data in dims.items():
                        if not isinstance(dim_data, dict):
                            continue
                        score = dim_data.get('score', 0)
                        explanation = dim_data.get('explanation', '')
                        coded_segments = dim_data.get('coded_segments', [])

                        # Add score + explanation
                        results_to_show.append({
                            'text': f"[7C {dim_name}] Score: {score}/100 - {explanation[:150]}",
                            '_session_id': session_id,
                            '_session_name': session_name
                        })

                        # Add coded segments (specific evidence)
                        for seg in coded_segments[:3]:  # Limit to 3 per dimension
                            if isinstance(seg, str) and seg.strip():
                                results_to_show.append({
                                    'text': f"[7C {dim_name} evidence]: {seg[:200]}",
                                    '_session_id': session_id,
                                    '_session_name': session_name
                                })

            elif tool_result.get('sessions'):
                # search_for_sessions tool format
                for s in tool_result['sessions'][:5]:
                    summary = s.get('summary', '')
                    summary_text = str(summary)[:100] if summary else ''
                    results_to_show.append({
                        'text': f"Session {s.get('session_id')}: {s.get('session_name', '')} - {summary_text}",
                        '_session_id': s.get('session_id'),
                        '_session_name': s.get('session_name', '')
                    })

            elif tool_result.get('tool_name') == 'compare_sessions' and tool_result.get('results'):
                # compare_sessions tool format - extract comparison data
                for comparison in tool_result['results'][:3]:
                    if isinstance(comparison, dict):
                        sessions_compared = comparison.get('sessions_compared', [])
                        summary = comparison.get('summary', {})
                        collab_scores = summary.get('collaboration_scores', {})

                        # Format each compared session
                        for sess in comparison.get('session_details', [])[:5]:
                            sess_id = sess.get('session_device_id')
                            sess_name = sess.get('session_name', '')
                            collab = sess.get('collaboration', {})
                            overall = collab.get('overall_score', collab_scores.get(sess_id, 'N/A'))
                            themes = ', '.join(sess.get('main_themes', [])[:3]) if sess.get('main_themes') else ''

                            results_to_show.append({
                                'text': f"Session {sess_id} ({sess_name}): Collaboration={overall}/100, Themes: {themes}",
                                '_session_id': sess_id,
                                '_session_name': sess_name
                            })

            elif tool_result.get('artifacts'):
                # Legacy get_artifacts format (deprecated but supported)
                artifacts = tool_result['artifacts']
                if 'transcript' in artifacts:
                    transcript = artifacts['transcript']
                    for u in transcript.get('utterances', []):
                        results_to_show.append({
                            'speaker': u.get('speaker', ''),
                            'text': u.get('text', ''),
                            '_session_id': session_id,
                            '_session_name': session_name
                        })
                if 'concept_map' in artifacts:
                    concept_map = artifacts['concept_map']
                    for n in concept_map.get('nodes', [])[:15]:
                        results_to_show.append({
                            'text': f"[{n.get('type', 'concept')}] {n.get('label', '')} (by {n.get('attributed_to', 'unknown')})",
                            '_session_id': session_id,
                            '_session_name': session_name
                        })

            for j, r in enumerate(results_to_show):
                if isinstance(r, dict):
                    # Safely extract text - ensure it's a string before slicing
                    raw_text = r.get('text', r.get('content', r.get('summary', '')))
                    text = str(raw_text)[:200] if raw_text else ''
                    speaker = r.get('speaker', '')
                    # Include session info for proper attribution
                    sess_id = r.get('_session_id')
                    sess_name = r.get('_session_name', '')
                    session_label = f"Session {sess_id}" if sess_id else ""

                    if speaker and session_label:
                        section.append(f"  - [{session_label}, {speaker}]: {text}")
                    elif speaker:
                        section.append(f"  - [{speaker}]: {text}")
                    elif session_label:
                        section.append(f"  - [{session_label}]: {text}")
                    else:
                        section.append(f"  - {text}")
                else:
                    section.append(f"  - {str(r)[:200]}")

            # Add reflection summary
            if reflection:
                section.append(f"  Satisfaction: {reflection.get('satisfaction_level', 'unknown')}")
                if reflection.get('indicators_found'):
                    section.append(f"  Indicators found: {reflection.get('indicators_found')}")

        sections.append('\n'.join(section))

    return '\n\n'.join(sections)


def _parse_cross_rep_result(result: Dict) -> CrossRepAnalysis:
    """Parse LLM result into CrossRepAnalysis."""
    convergence_points: List[ConvergencePoint] = []
    for cp in result.get('convergence_points', []):
        convergence_points.append(ConvergencePoint(
            claim=cp.get('claim', ''),
            supporting_reps=cp.get('supporting_reps', []),
            evidence=cp.get('evidence', []),
            confidence=cp.get('confidence', 'medium')
        ))

    tension_points: List[TensionPoint] = []
    for tp in result.get('tension_points', []):
        tension_points.append(TensionPoint(
            aspect=tp.get('aspect', ''),
            rep1=tp.get('rep1', {}),
            rep2=tp.get('rep2', {}),
            interpretation=tp.get('interpretation', '')
        ))

    gaps = result.get('gaps', [])
    overall_confidence = float(result.get('overall_confidence', 0.5))
    confidence_rationale = result.get('confidence_rationale', '')

    return CrossRepAnalysis(
        convergence_points=convergence_points,
        tension_points=tension_points,
        gaps=gaps,
        overall_confidence=overall_confidence,
        confidence_rationale=confidence_rationale
    )


def _fast_heuristic_analysis(
    subgoal_results: Dict[str, Dict],
    all_reps: set
) -> CrossRepAnalysis:
    """
    Fast heuristic analysis for simple queries (no LLM call).

    Used when:
    - 1-2 representations only
    - All sub-goals satisfied

    This saves ~3-4 seconds per query vs full LLM analysis.
    """
    reps_list = list(all_reps)

    # Build convergence point based on available evidence
    convergence_points = []
    if len(reps_list) >= 1:
        # Find evidence from steps
        evidence = []
        for result in subgoal_results.values():
            for step in result.get('steps_executed', []):
                step_info = step.get('step', {})
                reflection = step.get('reflection', {})
                rep = step_info.get('representation', 'unknown')
                summary = reflection.get('evidence_summary', '')
                if summary:
                    evidence.append({'rep': rep, 'finding': summary})

        convergence_points.append(ConvergencePoint(
            claim="Evidence supports the query",
            supporting_reps=reps_list,
            evidence=evidence[:3],  # Limit to top 3
            confidence='high' if len(reps_list) > 1 else 'medium'
        ))

    # Calculate confidence from satisfaction
    satisfied_count = sum(1 for r in subgoal_results.values() if r.get('satisfied'))
    total_count = len(subgoal_results)
    confidence = 0.8 if satisfied_count == total_count else satisfied_count / total_count

    return CrossRepAnalysis(
        convergence_points=convergence_points,
        tension_points=[],  # No tension detection in fast path
        gaps=[],  # No gaps in fast path (all satisfied)
        overall_confidence=confidence,
        confidence_rationale=f"Fast path: {satisfied_count}/{total_count} sub-goals satisfied, {len(reps_list)} representations"
    )


def _fallback_analysis(subgoal_results: Dict[str, Dict]) -> CrossRepAnalysis:
    """Fallback analysis when LLM fails."""
    # Check which reps have results
    reps_with_results = set()
    satisfied_count = 0
    total_count = len(subgoal_results)

    for result in subgoal_results.values():
        reps_with_results.update(result.get('representations_used', []))
        if result.get('satisfied'):
            satisfied_count += 1

    # Basic convergence if multiple reps used
    convergence_points = []
    if len(reps_with_results) > 1:
        convergence_points.append(ConvergencePoint(
            claim="Evidence gathered from multiple representations",
            supporting_reps=list(reps_with_results),
            evidence=[],
            confidence='medium'
        ))

    # Calculate confidence based on satisfaction
    confidence = satisfied_count / total_count if total_count > 0 else 0.0

    return CrossRepAnalysis(
        convergence_points=convergence_points,
        tension_points=[],
        gaps=[{'aspect': 'Details', 'reason': 'LLM analysis unavailable'}],
        overall_confidence=confidence,
        confidence_rationale=f"{satisfied_count}/{total_count} sub-goals satisfied"
    )


def extract_key_claims(cross_rep_analysis: CrossRepAnalysis) -> List[Dict[str, Any]]:
    """
    Extract key claims from cross-rep analysis for synthesis.

    Helper function used by grounded_synthesizer.
    """
    claims = []

    # Add convergence claims
    for cp in cross_rep_analysis.get('convergence_points', []):
        claims.append({
            'claim': cp.get('claim', ''),
            'type': 'convergence',
            'confidence': cp.get('confidence', 'medium'),
            'grounding': [
                {
                    'rep': e.get('rep', ''),
                    'evidence': e.get('finding', '')
                }
                for e in cp.get('evidence', [])
            ]
        })

    # Add tension acknowledgments
    for tp in cross_rep_analysis.get('tension_points', []):
        claims.append({
            'claim': f"Tension in {tp.get('aspect', 'analysis')}",
            'type': 'tension',
            'confidence': 'noted',
            'interpretation': tp.get('interpretation', ''),
            'rep1': tp.get('rep1', {}),
            'rep2': tp.get('rep2', {})
        })

    return claims
