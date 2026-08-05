# server/context_builder.py - Rich Context Assembly for Ultra RAG
"""
Context Builder: Creates rich, structured context for LLM insight generation.
Instead of 800-char truncated garbage, builds:
1. Full transcripts with speaker attribution
2. Concept map edges (challenges, supports, builds_on)
3. Interpreted metrics with qualitative labels
4. Temporal evolution narratives
5. Key moment extraction around argumentation points
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RichContext:
    """Structured context for LLM processing"""
    session_id: int
    session_name: str
    transcript_text: str
    metrics_section: str
    argumentation_moments: str
    evolution_narrative: str
    concept_structure: str
    full_context: str  # Combined ready-to-use context


class ContextBuilder:
    """
    Builds rich, query-relevant context for LLM insight generation.
    """

    def __init__(self):
        # Lazy imports to avoid circular dependencies
        pass

    def build_session_context(
        self,
        session_device_id: int,
        focus_area: str = 'general',
        max_transcript_chars: int = 4000,
        include_edges: bool = True
    ) -> RichContext:
        """
        Build comprehensive context for a session.

        Args:
            session_device_id: The session to build context for
            focus_area: 'argumentation', 'collaboration', 'evolution', 'speaker', 'general'
            max_transcript_chars: Maximum characters for transcript section
            include_edges: Whether to include concept map edges

        Returns:
            RichContext with all sections
        """
        from tables.session_device import SessionDevice
        from tables.session import Session
        from tables.transcript import Transcript
        from tables.concept_session import ConceptSession
        from tables.concept_node import ConceptNode
        from tables.concept_edge import ConceptEdge
        from tables.seven_cs_analysis import SevenCsAnalysis

        # Get session info
        session_device = SessionDevice.query.get(session_device_id)
        if not session_device:
            return None

        # Get session name via separate query
        session = Session.query.get(session_device.session_id)
        session_name = session.name if session else f"Session {session_device_id}"

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id
        ).order_by(Transcript.start_time).all()

        # Get concept map
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        nodes = []
        edges = []
        if concept_session:
            nodes = ConceptNode.query.filter_by(concept_session_id=concept_session.id).all()
            edges = ConceptEdge.query.filter_by(concept_session_id=concept_session.id).all()

        # Get 7C scores
        seven_cs_analysis = SevenCsAnalysis.query.filter_by(session_device_id=session_device_id).first()
        seven_cs = None
        if seven_cs_analysis and seven_cs_analysis.analysis_summary:
            # Extract scores from JSON structure
            summary = seven_cs_analysis.analysis_summary
            seven_cs = type('SevenCs', (), {
                'communication': summary.get('communication', {}).get('score', 0),
                'climate': summary.get('climate', {}).get('score', 0),
                'contribution': summary.get('contribution', {}).get('score', 0),
                'conflict': summary.get('conflict', {}).get('score', 0),
                'constructive': summary.get('constructive', {}).get('score', 0)
            })()

        # Build each section
        transcript_text = self._build_transcript_section(transcripts, max_transcript_chars)
        metrics_section = self._build_metrics_section(session_device_id, nodes, edges, seven_cs, focus_area)
        argumentation_moments = self._build_argumentation_moments(transcripts, nodes, edges) if focus_area in ['argumentation', 'general'] else ""
        evolution_narrative = self._build_evolution_narrative(transcripts) if focus_area in ['evolution', 'general'] else ""
        concept_structure = self._build_concept_structure(nodes, edges) if include_edges else ""

        # Combine into full context
        full_context = self._combine_context(
            session_id=session_device_id,
            session_name=session_name,
            transcript=transcript_text,
            metrics=metrics_section,
            argumentation=argumentation_moments,
            evolution=evolution_narrative,
            concepts=concept_structure,
            focus_area=focus_area
        )

        return RichContext(
            session_id=session_device_id,
            session_name=session_name,
            transcript_text=transcript_text,
            metrics_section=metrics_section,
            argumentation_moments=argumentation_moments,
            evolution_narrative=evolution_narrative,
            concept_structure=concept_structure,
            full_context=full_context
        )

    def _build_transcript_section(self, transcripts: List, max_chars: int) -> str:
        """Build transcript with speaker attribution"""
        if not transcripts:
            return "No transcript available."

        lines = []
        total_chars = 0

        for t in transcripts:
            # Transcript has speaker_tag (string) and speaker_id (int), but no speaker relationship
            speaker = t.speaker_tag or "Speaker"
            time_str = self._format_time(t.start_time)
            line = f"[{time_str}] {speaker}: {t.transcript}"

            if total_chars + len(line) > max_chars:
                lines.append("... [transcript truncated for length]")
                break

            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines)

    def _build_metrics_section(
        self,
        session_device_id: int,
        nodes: List,
        edges: List,
        seven_cs,
        focus_area: str
    ) -> str:
        """Build interpreted metrics section with qualitative labels"""
        sections = []

        # Argumentation metrics (always include for context)
        if edges:
            challenge_count = sum(1 for e in edges if e.edge_type == 'challenges')
            support_count = sum(1 for e in edges if e.edge_type == 'supports')
            builds_on_count = sum(1 for e in edges if e.edge_type == 'builds_on')
            elaborates_count = sum(1 for e in edges if e.edge_type == 'elaborates')

            debate_score = challenge_count + sum(1 for e in edges if e.edge_type == 'contrasts_with')
            reasoning_depth = builds_on_count + elaborates_count

            # Qualitative interpretation
            debate_label = self._interpret_score(debate_score, [(0, 'NONE'), (1, 'LOW'), (3, 'MODERATE'), (5, 'HIGH')])
            reasoning_label = self._interpret_score(reasoning_depth, [(0, 'NONE'), (2, 'BASIC'), (4, 'MODERATE'), (6, 'DEEP')])

            sections.append(f"""ARGUMENTATION METRICS:
- Debate Score: {debate_score} ({debate_label}) - Challenges + contrasts
- Reasoning Depth: {reasoning_depth} ({reasoning_label}) - Builds-on + elaborations
- Challenge Count: {challenge_count}
- Support Count: {support_count}
- Total Edges: {len(edges)}""")

        # Node types
        if nodes:
            question_count = sum(1 for n in nodes if n.node_type == 'question')
            problem_count = sum(1 for n in nodes if n.node_type == 'problem')
            solution_count = sum(1 for n in nodes if n.node_type == 'solution')
            idea_count = sum(1 for n in nodes if n.node_type == 'idea')

            sections.append(f"""CONCEPT TYPES:
- Questions: {question_count}
- Problems: {problem_count}
- Solutions: {solution_count}
- Ideas: {idea_count}""")

        # 7C Scores (collaboration focus)
        if seven_cs:
            comm_label = self._interpret_score(seven_cs.communication or 0, [(0, 'POOR'), (40, 'LOW'), (60, 'MODERATE'), (80, 'HIGH')])
            climate_label = self._interpret_score(seven_cs.climate or 0, [(0, 'POOR'), (40, 'LOW'), (60, 'MODERATE'), (80, 'HIGH')])
            contrib_label = self._interpret_score(seven_cs.contribution or 0, [(0, 'POOR'), (40, 'LOW'), (60, 'MODERATE'), (80, 'HIGH')])

            sections.append(f"""COLLABORATION QUALITY (7C Scores):
- Communication: {seven_cs.communication}/100 ({comm_label})
- Climate: {seven_cs.climate}/100 ({climate_label})
- Contribution Balance: {seven_cs.contribution}/100 ({contrib_label})
- Conflict Resolution: {seven_cs.conflict}/100
- Constructive Discourse: {seven_cs.constructive}/100""")

        return "\n\n".join(sections) if sections else "No metrics available."

    def _build_argumentation_moments(self, transcripts: List, nodes: List, edges: List) -> str:
        """Extract key argumentation moments with surrounding dialogue"""
        if not edges:
            return ""

        moments = []

        # Find challenge/support edges and their context
        for edge in edges:
            if edge.edge_type in ['challenges', 'supports', 'builds_on', 'contrasts_with']:
                source_node = next((n for n in nodes if n.id == edge.source_node_id), None)
                target_node = next((n for n in nodes if n.id == edge.target_node_id), None)

                if source_node and target_node:
                    edge_type_label = edge.edge_type.upper().replace('_', ' ')

                    # Get speaker info
                    source_speaker = source_node.speaker.alias if source_node.speaker else "Speaker"
                    target_speaker = target_node.speaker.alias if target_node.speaker else "Speaker"

                    moment = f"- {source_speaker} {edge_type_label} {target_speaker}'s point:\n"
                    moment += f"  Original: \"{target_node.text[:100]}...\"\n" if len(target_node.text or '') > 100 else f"  Original: \"{target_node.text}\"\n"
                    moment += f"  Response: \"{source_node.text[:100]}...\"" if len(source_node.text or '') > 100 else f"  Response: \"{source_node.text}\""

                    moments.append(moment)

        if not moments:
            return ""

        return "KEY ARGUMENTATION MOMENTS:\n" + "\n\n".join(moments[:5])  # Limit to 5 moments

    def _build_evolution_narrative(self, transcripts: List) -> str:
        """Build temporal evolution narrative"""
        if len(transcripts) < 4:
            return "Insufficient data for evolution analysis."

        # Split into halves
        mid = len(transcripts) // 2
        first_half = transcripts[:mid]
        second_half = transcripts[mid:]

        def avg_metric(chunks, attr):
            values = [getattr(c, attr) for c in chunks if getattr(c, attr) is not None]
            return sum(values) / len(values) if values else 0

        # Calculate evolution
        analytic_1 = avg_metric(first_half, 'analytic_thinking_value')
        analytic_2 = avg_metric(second_half, 'analytic_thinking_value')
        analytic_delta = analytic_2 - analytic_1

        tone_1 = avg_metric(first_half, 'emotional_tone_value')
        tone_2 = avg_metric(second_half, 'emotional_tone_value')
        tone_delta = tone_2 - tone_1

        certainty_1 = avg_metric(first_half, 'certainty_value')
        certainty_2 = avg_metric(second_half, 'certainty_value')
        certainty_delta = certainty_2 - certainty_1

        # Build narrative
        narratives = []

        if abs(analytic_delta) > 2:
            direction = "INCREASED" if analytic_delta > 0 else "DECREASED"
            narratives.append(f"Analytic thinking {direction} by {abs(analytic_delta):.1f} points over the discussion")

        if abs(tone_delta) > 2:
            direction = "became more positive" if tone_delta > 0 else "became more negative"
            narratives.append(f"Emotional tone {direction} ({tone_delta:+.1f} points)")

        if abs(certainty_delta) > 2:
            direction = "increased" if certainty_delta > 0 else "decreased"
            narratives.append(f"Certainty {direction} ({certainty_delta:+.1f} points)")

        if not narratives:
            return "EVOLUTION: Metrics remained relatively stable throughout the discussion."

        return "EVOLUTION OVER TIME:\n- " + "\n- ".join(narratives)

    def _build_concept_structure(self, nodes: List, edges: List) -> str:
        """Build concept map structure summary"""
        if not nodes:
            return ""

        # Group nodes by type
        by_type = {}
        for node in nodes:
            node_type = node.node_type or 'idea'
            if node_type not in by_type:
                by_type[node_type] = []
            speaker = node.speaker.alias if node.speaker else "Speaker"
            by_type[node_type].append(f"{speaker}: \"{node.text[:80]}...\"" if len(node.text or '') > 80 else f"{speaker}: \"{node.text}\"")

        sections = []
        for node_type, items in by_type.items():
            type_label = node_type.upper()
            sections.append(f"{type_label}S ({len(items)}):\n  " + "\n  ".join(items[:3]))  # Limit each type

        # Edge summary
        if edges:
            edge_counts = {}
            for edge in edges:
                edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1

            edge_summary = ", ".join([f"{t}: {c}" for t, c in sorted(edge_counts.items(), key=lambda x: -x[1])])
            sections.append(f"RELATIONSHIPS: {edge_summary}")

        return "CONCEPT STRUCTURE:\n" + "\n".join(sections)

    def _combine_context(
        self,
        session_id: int,
        session_name: str,
        transcript: str,
        metrics: str,
        argumentation: str,
        evolution: str,
        concepts: str,
        focus_area: str
    ) -> str:
        """Combine all sections into final context"""
        sections = [f"=== SESSION {session_id}: {session_name} ==="]

        # Order sections based on focus area
        if focus_area == 'argumentation':
            sections.extend([metrics, argumentation, concepts, transcript[:2000]])
        elif focus_area == 'collaboration':
            sections.extend([metrics, transcript[:2000], evolution])
        elif focus_area == 'evolution':
            sections.extend([evolution, metrics, transcript[:2000]])
        elif focus_area == 'speaker':
            sections.extend([transcript[:3000], metrics])
        else:
            sections.extend([metrics, transcript[:2000], argumentation, evolution])

        return "\n\n".join([s for s in sections if s])

    def build_contrastive_context(
        self,
        high_sessions: List[int],
        low_sessions: List[int],
        focus_area: str
    ) -> Tuple[str, str]:
        """Build context for contrastive analysis (high vs low metric sessions)"""
        high_contexts = []
        for sid in high_sessions[:3]:  # Limit to 3
            ctx = self.build_session_context(sid, focus_area, max_transcript_chars=2000)
            if ctx:
                high_contexts.append(ctx.full_context)

        low_contexts = []
        for sid in low_sessions[:3]:
            ctx = self.build_session_context(sid, focus_area, max_transcript_chars=2000)
            if ctx:
                low_contexts.append(ctx.full_context)

        high_combined = "\n\n---\n\n".join(high_contexts)
        low_combined = "\n\n---\n\n".join(low_contexts)

        return high_combined, low_combined

    def build_speaker_context(self, speaker_alias: str, max_sessions: int = 3) -> str:
        """Build comprehensive speaker context across sessions"""
        from tables.speaker import Speaker
        from tables.transcript import Transcript
        from tables.concept_node import ConceptNode

        speaker = Speaker.query.filter_by(alias=speaker_alias).first()
        if not speaker:
            return f"No speaker found with alias: {speaker_alias}"

        # Get speaker's transcripts
        transcripts = Transcript.query.filter_by(speaker_id=speaker.id).order_by(Transcript.id).limit(50).all()

        # Get speaker's concept contributions
        nodes = ConceptNode.query.filter_by(speaker_id=speaker.id).limit(30).all()

        # Aggregate metrics
        avg_clout = sum(t.clout_value or 0 for t in transcripts) / len(transcripts) if transcripts else 0
        avg_analytic = sum(t.analytic_thinking_value or 0 for t in transcripts) / len(transcripts) if transcripts else 0
        question_count = sum(1 for t in transcripts if t.question)
        total_words = sum(len((t.transcript or '').split()) for t in transcripts)

        # Get unique sessions
        session_ids = list(set(t.session_device_id for t in transcripts))

        # Build context
        sections = [f"=== SPEAKER PROFILE: {speaker_alias} ==="]

        sections.append(f"""OVERVIEW:
- Sessions participated: {len(session_ids)}
- Total contributions: {len(transcripts)} turns
- Total words: {total_words}
- Questions asked: {question_count}
- Concepts contributed: {len(nodes)}

SPEAKING STYLE METRICS:
- Average Clout: {avg_clout:.1f} (influence/confidence)
- Average Analytic: {avg_analytic:.1f} (analytical thinking)
- Question Ratio: {question_count/len(transcripts)*100:.1f}% of turns are questions""")

        # Sample quotes
        quotes = []
        for t in transcripts[:10]:
            if len(t.transcript or '') > 30:
                quotes.append(f"- \"{t.transcript[:150]}...\"" if len(t.transcript) > 150 else f"- \"{t.transcript}\"")

        if quotes:
            sections.append("SAMPLE QUOTES:\n" + "\n".join(quotes[:5]))

        # Concept contributions
        if nodes:
            node_samples = []
            for n in nodes[:5]:
                node_samples.append(f"- [{n.node_type}] \"{(n.text or '')[:100]}\"")
            sections.append("CONCEPT CONTRIBUTIONS:\n" + "\n".join(node_samples))

        return "\n\n".join(sections)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _interpret_score(self, value: float, thresholds: List[Tuple[float, str]]) -> str:
        """Interpret numeric score as qualitative label"""
        for threshold, label in reversed(thresholds):
            if value >= threshold:
                return label
        return thresholds[0][1]

    # =========================================================================
    # ARTIFACT DESCRIPTION FOR THREE-LAYER RESPONSE (GROUND layer)
    # =========================================================================

    def build_artifact_description(self, session_device_id: int) -> str:
        """
        Build a structured description of artifacts for the GROUND layer.

        This describes what users see in the UI:
        - Concept map structure (nodes, edges, relationships)
        - 7C collaboration scores with evidence
        - Key highlights that the LLM should reference

        Returns:
            Formatted string describing artifacts in LLM-readable format
        """
        from tables.session_device import SessionDevice
        from tables.session import Session
        from tables.concept_session import ConceptSession
        from tables.concept_node import ConceptNode
        from tables.concept_edge import ConceptEdge
        from tables.seven_cs_analysis import SevenCsAnalysis

        # Get session info
        session_device = SessionDevice.query.get(session_device_id)
        if not session_device:
            return f"No session found with ID {session_device_id}"

        session = Session.query.get(session_device.session_id)
        session_name = session.name if session else f"Session {session_device_id}"

        sections = [f"## ARTIFACTS FOR SESSION {session_device_id}: {session_name}"]
        sections.append("(These are what the user sees in the UI - reference them to create common ground)")

        # Get concept map data
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        nodes = []
        edges = []
        if concept_session:
            nodes = ConceptNode.query.filter_by(concept_session_id=concept_session.id).all()
            edges = ConceptEdge.query.filter_by(concept_session_id=concept_session.id).all()

        # Build concept map section
        concept_section = self._build_concept_map_artifact(nodes, edges)
        if concept_section:
            sections.append(concept_section)

        # Get 7C analysis
        seven_cs_analysis = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id
        ).first()

        seven_c_section = self._build_7c_artifact(seven_cs_analysis)
        if seven_c_section:
            sections.append(seven_c_section)

        # Add interpretation guidance
        interpretation = self._build_artifact_interpretation(nodes, edges, seven_cs_analysis)
        if interpretation:
            sections.append(interpretation)

        return "\n\n".join(sections)

    def _build_concept_map_artifact(self, nodes: List, edges: List) -> str:
        """Format concept map as artifact description"""
        if not nodes:
            return "### CONCEPT MAP\nNo concept map generated for this session."

        # Count node types
        node_type_counts = {}
        for node in nodes:
            ntype = node.node_type or 'idea'
            node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

        type_breakdown = ", ".join([f"{count} {t}s" for t, count in sorted(node_type_counts.items(), key=lambda x: -x[1])])

        # Count edge types
        edge_type_counts = {}
        for edge in edges:
            etype = edge.edge_type or 'related'
            edge_type_counts[etype] = edge_type_counts.get(etype, 0) + 1

        edge_breakdown = ", ".join([f"{count} {t}" for t, count in sorted(edge_type_counts.items(), key=lambda x: -x[1])])

        # Key relationships - the most important edges
        key_edges = self._format_key_edges(nodes, edges)

        return f"""### CONCEPT MAP (visible as interactive graph in UI)

**Structure:**
- Total nodes: {len(nodes)} ({type_breakdown})
- Total edges: {len(edges)} ({edge_breakdown if edge_breakdown else 'no relationships'})

**Key Relationships:**
{key_edges}"""

    def _format_key_edges(self, nodes: List, edges: List, max_edges: int = 5) -> str:
        """Format the most important edges (challenges, builds_on) as readable text"""
        if not edges:
            return "- No relationships extracted"

        # Priority order for edge types (most interesting first)
        priority = ['challenges', 'contrasts_with', 'builds_on', 'supports', 'elaborates', 'synthesizes']

        # Sort edges by priority
        def edge_priority(e):
            try:
                return priority.index(e.edge_type) if e.edge_type in priority else len(priority)
            except:
                return len(priority)

        sorted_edges = sorted(edges, key=edge_priority)[:max_edges]

        # Build node lookup
        node_map = {n.id: n for n in nodes}

        formatted = []
        for edge in sorted_edges:
            source = node_map.get(edge.source_node_id)
            target = node_map.get(edge.target_node_id)

            if source and target:
                source_speaker = source.speaker.alias if source.speaker else "Speaker"
                target_speaker = target.speaker.alias if target.speaker else "Speaker"

                edge_verb = {
                    'challenges': 'CHALLENGES',
                    'contrasts_with': 'CONTRASTS WITH',
                    'builds_on': 'BUILDS ON',
                    'supports': 'SUPPORTS',
                    'elaborates': 'ELABORATES',
                    'synthesizes': 'SYNTHESIZES'
                }.get(edge.edge_type, edge.edge_type.upper())

                source_text = (source.text[:60] + "...") if len(source.text or '') > 60 else source.text
                target_text = (target.text[:60] + "...") if len(target.text or '') > 60 else target.text

                formatted.append(f"- {source_speaker} {edge_verb} {target_speaker}: \"{source_text}\" → \"{target_text}\"")

        return "\n".join(formatted) if formatted else "- No significant relationships"

    def _build_7c_artifact(self, seven_cs_analysis) -> str:
        """Format 7C analysis as artifact description"""
        if not seven_cs_analysis or not seven_cs_analysis.analysis_summary:
            return "### 7C COLLABORATION ANALYSIS\nNo 7C analysis available for this session."

        summary = seven_cs_analysis.analysis_summary

        # Extract scores and evidence
        dimensions = ['communication', 'climate', 'contribution', 'conflict', 'constructive']

        scores_section = []
        evidence_section = []

        for dim in dimensions:
            if dim in summary:
                data = summary[dim]
                score = data.get('score', 0)
                explanation = data.get('explanation', '')
                evidence = data.get('evidence', [])

                # Qualitative label
                label = self._interpret_score(score, [(0, 'Poor'), (40, 'Below Average'), (60, 'Adequate'), (80, 'Good'), (90, 'Excellent')])
                scores_section.append(f"- {dim.capitalize()}: {score}/100 ({label})")

                # Add key evidence quotes (limit to 1-2 per dimension)
                if evidence:
                    top_evidence = evidence[:2]
                    for ev in top_evidence:
                        if isinstance(ev, dict):
                            quote = ev.get('text', ev.get('quote', ''))[:100]
                            if quote:
                                evidence_section.append(f"  [{dim}] \"{quote}...\"" if len(quote) == 100 else f"  [{dim}] \"{quote}\"")
                        elif isinstance(ev, str):
                            evidence_section.append(f"  [{dim}] \"{ev[:100]}...\"" if len(ev) > 100 else f"  [{dim}] \"{ev}\"")

        return f"""### 7C COLLABORATION SCORES (visible as bar chart in UI)

**Scores:**
{chr(10).join(scores_section)}

**Key Evidence Quotes:**
{chr(10).join(evidence_section[:6]) if evidence_section else "  No specific evidence quotes available"}"""

    def _build_artifact_interpretation(self, nodes: List, edges: List, seven_cs_analysis) -> str:
        """Build interpretation guidance - what do these artifacts suggest?"""
        insights = []

        # Argumentation strength
        if edges:
            challenge_count = sum(1 for e in edges if e.edge_type == 'challenges')
            builds_on_count = sum(1 for e in edges if e.edge_type == 'builds_on')

            if challenge_count >= 3:
                insights.append(f"Strong argumentation: {challenge_count} challenge edges indicate active debate")
            elif challenge_count == 0:
                insights.append("No challenges in concept map - discussion may lack critical engagement")

            if builds_on_count >= 3:
                insights.append(f"Good idea development: {builds_on_count} builds_on edges show cumulative thinking")

        # 7C highlights
        if seven_cs_analysis and seven_cs_analysis.analysis_summary:
            summary = seven_cs_analysis.analysis_summary

            # Find highest and lowest scores
            scores = {dim: summary.get(dim, {}).get('score', 0) for dim in ['communication', 'climate', 'contribution', 'conflict', 'constructive']}

            if scores:
                highest = max(scores.items(), key=lambda x: x[1])
                lowest = min(scores.items(), key=lambda x: x[1])

                if highest[1] >= 80:
                    insights.append(f"Strength: {highest[0].capitalize()} ({highest[1]}/100)")
                if lowest[1] <= 50:
                    insights.append(f"Area for growth: {lowest[0].capitalize()} ({lowest[1]}/100)")

        if not insights:
            return ""

        return f"""### WHAT ARTIFACTS SUGGEST
{chr(10).join('- ' + i for i in insights)}"""

    def build_multi_session_artifacts(self, session_ids: List[int]) -> str:
        """Build artifact descriptions for multiple sessions (for comparison queries)"""
        if not session_ids:
            return "No sessions to describe."

        descriptions = []
        for sid in session_ids[:5]:  # Limit to 5 sessions
            desc = self.build_artifact_description(sid)
            descriptions.append(desc)

        return "\n\n---\n\n".join(descriptions)
