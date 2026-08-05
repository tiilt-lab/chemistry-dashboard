"""
Session Narrator for Graph RAG V2

Generates narrative summaries of entire sessions.
These capture the arc, key insights, and unique contributions.
"""

import logging
from typing import Dict, Any, List

from openai import OpenAI

logger = logging.getLogger(__name__)


SESSION_NARRATIVE_PROMPT = """Create a narrative summary of this collaborative discussion session.

## Session Information
Name: {session_name}
Duration: {duration}
Participants: {participants}
Discourse Type: {discourse_type}

## Main Themes
{themes}

## Key Concepts
{concepts}

## 7C Collaboration Scores (if available)
{seven_cs}

## Instructions

Write a 3-4 paragraph narrative that:
1. Opens with what the session was about and who participated
2. Describes the main themes and how the discussion evolved
3. Highlights key insights, conclusions, or interesting moments
4. Assesses the collaboration quality and group dynamics

Write in third person, past tense. Be specific and cite examples.
Focus on the intellectual content and group dynamics.

Maximum 400 words.
"""


class SessionNarrator:
    """
    Generates narrative summaries for entire sessions.

    These narratives are embedded to enable natural language
    questions like "What happened in the fusion session?"
    """

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the narrator.

        Args:
            model: OpenAI model to use (gpt-4o for quality)
        """
        self.model = model
        self.client = OpenAI()

    def generate_narrative(
        self,
        session_id: int,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a narrative summary for a session.

        Args:
            session_id: The session device ID
            session_data: Session information including:
                - session_name
                - duration
                - participants
                - themes/clusters
                - key_concepts
                - seven_cs (optional)

        Returns:
            Narrative summary with metadata
        """
        logger.info(f"Generating narrative for session {session_id}")

        # Format session data for prompt
        session_name = session_data.get('session_name', f'Session {session_id}')
        duration = self._format_duration(session_data.get('duration', 0))
        participants = ", ".join(session_data.get('participants', ['Unknown']))
        discourse_type = session_data.get('discourse_type', 'discussion')

        # Format themes
        themes = session_data.get('themes', [])
        themes_text = "\n".join(f"- {t}" for t in themes) if themes else "No themes identified"

        # Format key concepts
        concepts = session_data.get('key_concepts', [])
        concepts_text = self._format_concepts(concepts)

        # Format 7C scores
        seven_cs = session_data.get('seven_cs', {})
        seven_cs_text = self._format_seven_cs(seven_cs)

        try:
            prompt = SESSION_NARRATIVE_PROMPT.format(
                session_name=session_name,
                duration=duration,
                participants=participants,
                discourse_type=discourse_type,
                themes=themes_text,
                concepts=concepts_text,
                seven_cs=seven_cs_text
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=600
            )

            narrative = response.choices[0].message.content

            return {
                'session_device_id': session_id,
                'session_name': session_name,
                'narrative': narrative,
                'word_count': len(narrative.split()),
                'participants': session_data.get('participants', []),
                'themes': themes,
                'discourse_type': discourse_type,
                'duration': session_data.get('duration')
            }

        except Exception as e:
            logger.error(f"Narrative generation error: {e}")
            return self._fallback_narrative(session_id, session_data)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human readable form."""
        if not seconds:
            return "Unknown duration"

        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"

    def _format_concepts(self, concepts: List[Dict]) -> str:
        """Format key concepts for the prompt."""
        if not concepts:
            return "No key concepts identified"

        lines = []
        for c in concepts[:15]:  # Top 15
            text = c.get('text', str(c))[:100]
            ctype = c.get('node_type', 'concept')
            speaker = c.get('speaker', '')

            if speaker:
                lines.append(f"- [{ctype}] {text} ({speaker})")
            else:
                lines.append(f"- [{ctype}] {text}")

        return "\n".join(lines)

    def _format_seven_cs(self, seven_cs: Dict) -> str:
        """Format 7C scores for the prompt."""
        if not seven_cs:
            return "Not available"

        lines = []
        for dimension in ['climate', 'communication', 'contribution', 'conflict',
                         'context', 'constructive', 'compatibility']:
            if dimension in seven_cs:
                score = seven_cs[dimension]
                if isinstance(score, dict):
                    score = score.get('score', 0)
                lines.append(f"- {dimension.title()}: {score}/100")

        return "\n".join(lines) if lines else "Not available"

    def _fallback_narrative(
        self,
        session_id: int,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a basic narrative without LLM."""
        session_name = session_data.get('session_name', f'Session {session_id}')
        participants = session_data.get('participants', ['participants'])
        themes = session_data.get('themes', ['various topics'])

        narrative = (
            f"In the {session_name} session, {', '.join(participants)} engaged in a "
            f"discussion covering {', '.join(themes[:3])}. "
            f"The conversation explored multiple perspectives and generated various ideas "
            f"and questions related to the main topics."
        )

        return {
            'session_device_id': session_id,
            'session_name': session_name,
            'narrative': narrative,
            'word_count': len(narrative.split()),
            'participants': session_data.get('participants', []),
            'themes': themes,
            'fallback': True
        }
