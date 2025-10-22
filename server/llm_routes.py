import json  
import logging 
import sys
import os

# Add the audio_processing directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'audio_processing'))

from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = None
if api_key:
    client = OpenAI(api_key=api_key)
    logging.info("OpenAI client initialized successfully")
else:
    logging.warning("OPENAI_API_KEY not set. LLM routes will be disabled.")

# Create Blueprint for LLM routes
llm_bp = Blueprint('llm', __name__)

def get_all_node_types():
    """Get all possible node types across all schemas"""
    return ['question', 'idea', 'elaboration', 'example', 'uncertainty',
            'problem', 'cause', 'solution', 'constraint', 'evaluation',
            'goal', 'task', 'resource', 'timeline', 'dependency',
            'observation', 'hypothesis', 'data', 'interpretation', 'conclusion',
            'evidence', 'counterpoint', 'synthesis', 'implication',
            'concept', 'statement', 'reference', 'aside', 'clarification',
            'challenge', 'assumption', 'metaphor', 'speculation',
            'milestone', 'risk', 'action', 'decision_point',
            'anecdote', 'trade_off', 'workaround']

def get_all_edge_types():
    """Get all possible edge types across all schemas"""
    return ['explores', 'relates_to', 'contrasts_with', 'builds_on',
            'causes', 'solves', 'constrains', 'evaluates',
            'requires', 'precedes', 'enables', 'blocks',
            'supports', 'contradicts', 'derives_from', 'leads_to',
            'questions', 'exemplifies', 'elaborates', 'clarifies',
            'challenges', 'synthesizes', 'applies', 'contextualizes',
            'answers', 'agrees_with', 'disagrees_with',
            'mitigates', 'worsens', 'alternatives_to',
            'depends_on', 'contributes_to', 'delays',
            'qualifies', 'follows', 'refers_to']

def prepare_context_data(data):
    """Prepare and limit data for token management"""
    metrics = data.get('metrics', {})
    transcripts = data.get('transcripts', [])
    session_info = data.get('sessionInfo', {})
    time_range = data.get('timeRange', {})
    
    return {
        'metrics': metrics,
        'transcripts': transcripts,
        'sessionInfo': session_info,
        'timeRange': time_range
    }

def generate_prompt(task_type, data):
    """Generate appropriate prompt based on task type"""

    time_range = data.get('timeRange', {})
    time_context = ""
    time_instruction = ""
    
    if not time_range.get('isFullRange', True):
        start_sec = time_range.get('start', 0)
        end_sec = time_range.get('end', 0)
        total_sec = time_range.get('totalLength', 0)
        
        # Convert to minutes:seconds format
        start_min, start_s = divmod(int(start_sec), 60)
        end_min, end_s = divmod(int(end_sec), 60)
        
        # Calculate percentage
        percentage = 0
        if total_sec > 0:
            percentage = round(((end_sec - start_sec) / total_sec) * 100)
        
        time_context = f"\nSelected time range: {start_min}:{start_s:02d} to {end_min}:{end_s:02d} ({percentage}% of session)\n"
        time_instruction = f"NOTE: You are analyzing only a portion of the session from {start_min}:{start_s:02d} to {end_min}:{end_s:02d}. Mention this information at the start of your response."
    
    if task_type == 'summary':
        metrics = data.get('metrics', {})
        transcripts = data.get('transcripts', [])
        session_info = data.get('sessionInfo', {})
        
        # Limit transcript text to avoid token limits
        transcript_list = transcripts[:10] if len(transcripts) > 10 else transcripts
        transcript_text = '\n'.join([
            f"[{t.get('speaker', 'Speaker')} at {t.get('start_time', 0)}s]: {t.get('transcript', '')}"
            for t in transcript_list
        ])
        
        return f"""Analyze this discussion session and provide a concise summary:

Session: {session_info.get('name', 'Current Session')}{time_context}{time_instruction}

Metrics:
- Emotional Tone: {metrics.get('emotional', 'N/A')}% (>50 = positive)
- Analytic Thinking: {metrics.get('analytic', 'N/A')}% (>50 = analytic)
- Clout: {metrics.get('clout', 'N/A')}% (higher = more confident)
- Authenticity: {metrics.get('authenticity', 'N/A')}% (higher = more authentic)
- Certainty: {metrics.get('certainty', 'N/A')}% (higher = more certain)

Recent Transcript Excerpts:
{transcript_text}

Please consider these aspects:
1. Overall communication style assessment
2. Key discussion themes
3. Notable patterns in the conversation
4. Suggestions for potential improvement

Keep the response under 200 words."""

    elif task_type == 'metrics':
        metrics = data.get('metrics', {})
        return f"""{time_context}Interpret these communication metrics and explain what they reveal about the discussion:

- Emotional Tone: {metrics.get('emotional', 'N/A')}%
- Analytic Thinking: {metrics.get('analytic', 'N/A')}%
- Clout: {metrics.get('clout', 'N/A')}%
- Authenticity: {metrics.get('authenticity', 'N/A')}%
- Certainty: {metrics.get('certainty', 'N/A')}%

Provide specific insights about:
1. The overall communication dynamics
2. Potential strengths and areas for improvement
3. What these patterns suggest about group dynamics

Keep response under 200 words."""

    elif task_type == 'themes':
        transcripts = data.get('transcripts', [])
        transcript_list = transcripts[:15] if len(transcripts) > 15 else transcripts
        transcript_text = '\n'.join([t.get('transcript', '') for t in transcript_list])
        
        return f"""Extract and categorize the main themes from this discussion:

Transcript Excerpts:
{transcript_text}

Identify:
1. Main topics discussed
2. Recurring themes
3. Points of agreement/disagreement
4. Action items or decisions (if any)

Format as a bulleted list."""

    elif task_type == 'comparison':
        multi_sessions = data.get('multiSessions', [])
        if not multi_sessions or len(multi_sessions) < 2:
            return 'Not enough sessions to compare.'
        
        session_text = '\n'.join([
            f"""Session {i+1}: {session.get('name', 'Unknown')}
- Emotional: {session.get('metrics', {}).get('emotional', 'N/A')}%
- Analytic: {session.get('metrics', {}).get('analytic', 'N/A')}%
- Clout: {session.get('metrics', {}).get('clout', 'N/A')}%
- Authenticity: {session.get('metrics', {}).get('authenticity', 'N/A')}%
- Certainty: {session.get('metrics', {}).get('certainty', 'N/A')}%"""
            for i, session in enumerate(multi_sessions)
        ])
        
        return f"""Compare these discussion sessions:

{session_text}

Identify:
1. Key differences between sessions
2. Trends or patterns across sessions
3. Which session had the most effective communication and why

Keep response under 200 words."""
    
    else:
        return generate_prompt('summary', data)

@llm_bp.route('/api/v1/llm/analyze', methods=['POST'])
def analyze():
    """Main endpoint for LLM analysis"""
    if client is None:
        return jsonify({"success": False, "error": "LLM disabled (no OPENAI_API_KEY)"}), 503
    
    try:
        request_data = request.get_json()
        task_type = request_data.get('taskType', 'summary')
        data = request_data.get('data', {})
        
        # Prepare data
        prepared_data = prepare_context_data(data)
        
        # Add multiSessions if present
        if 'multiSessions' in data:
            prepared_data['multiSessions'] = data['multiSessions']
        
        # Generate prompt
        prompt = generate_prompt(task_type, prepared_data)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert communication analyst helping teams improve their discussions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'result': result,
            'usage': {
                'total_tokens': response.usage.total_tokens,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens
            }
        })
        
    except Exception as e:
        logging.error(f"LLM API Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_bp.route('/api/v1/llm/extract_concepts', methods=['POST'])
def extract_concepts():
    """Extract concepts and relationships from discussion segments"""
    if client is None:
        logging.error("LLM client not initialized - no OPENAI_API_KEY")
        return jsonify({
            "new_nodes": [],
            "new_edges": [],
            "discourse_type": "exploratory",
            "error": "LLM disabled - no API key configured"
        }), 200  # Return 200 with empty data to prevent breaking the flow
    
    try:
        request_data = request.get_json()
        context = request_data.get('context', {})
        
        # Log incoming request
        logging.info(f"Concept extraction request received with {len(context.get('speaker_segments', {}))} speakers")
        
        # Build transcript with ALL details
        speaker_text = ""
        for speaker, segments in context.get('speaker_segments', {}).items():
            speaker_text += f"\nSpeaker {speaker}: {' '.join(segments)}"
        
        # Include recent concepts
        recent_concepts_text = ""
        if context.get('recent_concepts'):
            concepts_list = [f"{c.get('text')} ({c.get('type')})" for c in context['recent_concepts']]
            recent_concepts_text = f"\nPrevious concepts: {', '.join(concepts_list)}"
        
        # Check if we have content to process
        if not speaker_text.strip():
            logging.warning("No transcript text to process for concept extraction")
            return jsonify({
                "new_nodes": [],
                "new_edges": [],
                "discourse_type": "exploratory"
            }), 200
        
        prompt = f"""Extract a comprehensive knowledge graph from this discussion. Be thorough - capture EVERY meaningful idea.

Discussion:{speaker_text}
{recent_concepts_text}

EXTRACTION RULES:
1. Extract AT LEAST one concept for every 2-3 sentences spoken
2. Include ALL of: main ideas, sub-points, examples, questions, clarifications
3. Keep concept text concise but complete (3-15 words is fine)
4. Don't oversummarize - "multimodal learning analytics for collaboration" is better than just "analytics"
5. Extract concepts even if they seem minor - better to have too many than too few
6. **speaker**: The speaker ID (e.g., 1, 2, "Unknown") who said the concept. This ID comes from the "Speaker {{ID}}" prefix.

CONCEPT TYPES to extract:
- Core ideas and claims (type: "idea")
- Questions asked (type: "question") - preserve the question form
- Examples given (type: "example") - label as "e.g., [example]"
- Problems identified (type: "problem")
- Solutions proposed (type: "solution")
- Goals stated (type: "goal")
- Uncertainties expressed (type: "uncertainty")
- Elaborations (type: "elaboration")
- Actions needed (type: "action")

RELATIONSHIPS (connect everything relevant):
- builds_on - when ideas develop
- elaborates - adding detail
- exemplifies - examples of concepts
- questions - questioning ideas
- challenges - disagreements
- supports - agreement/evidence
- enables - one thing allows another
- requires - dependencies

Extract generously. If someone says "We need better tools for analyzing student collaboration, maybe something with video", extract:
- "need better collaboration analysis tools" (type: "problem")
- "video-based analysis possibility" (type: "solution")
- "student collaboration analysis" (type: "goal")

Return JSON:
{{
    "new_nodes": [
        {{"text": "concept phrase (3-15 words ok)", "type": "type", "speaker": 1}}
    ],
    "new_edges": [
        {{"source": index, "target": index, "type": "relationship_type"}}
    ],
    "discourse_type": "exploratory|problem_solving|analytical|mixed"
}}"""
        
        logging.info("Calling OpenAI API for concept extraction...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """You are a thorough knowledge extractor. Your goal is to capture the richness of human discussion.
                    Extract MORE concepts rather than fewer. Include minor points, asides, and elaborations.
                    Every meaningful utterance should produce at least one concept.
                    Don't oversummarize - preserve the specific ideas being discussed."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,  # Slightly higher for more extraction
            max_tokens=2000  # More tokens for richer extraction
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Log for monitoring
        logging.info(f"Extracted {len(result.get('new_nodes', []))} concepts from {len(speaker_text.split())} words")

        # Handle different response formats from LLM
        nodes = result.get("new_nodes") or result.get("concepts") or []
        edges = result.get("new_edges") or result.get("relationships") or []
        
        # Validate and clean the extracted data
        valid_nodes = []
        for node in nodes:
            if node.get('text'):  # Must have text at minimum
                valid_nodes.append({
                    'text': node.get('text', ''),
                    'type': node.get('type', 'concept'),
                    'speaker': node.get('speaker', 'Unknown')
                })
        
        valid_edges = []
        for edge in edges:
            if 'source' in edge and 'target' in edge:
                valid_edges.append({
                    'source': edge['source'],
                    'target': edge['target'],
                    'type': edge.get('type', 'relates_to')
                })
        
        logging.info(f"Returning {len(valid_nodes)} valid nodes and {len(valid_edges)} valid edges")
        
        return jsonify({
            "new_nodes": valid_nodes,
            "new_edges": valid_edges,
            "discourse_type": result.get('discourse_type', 'exploratory'),
            "discourse_features": result.get('discourse_features', [])
        })
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response as JSON: {e}")
        return jsonify({
            "new_nodes": [],
            "new_edges": [],
            "discourse_type": "exploratory",
            "error": "Failed to parse LLM response"
        }), 200
        
    except Exception as e:
        logging.error(f"Concept extraction error: {str(e)}", exc_info=True)
        return jsonify({
            "new_nodes": [],
            "new_edges": [],
            "discourse_type": "exploratory",
            "error": str(e)
        }), 200

@llm_bp.route('/api/v1/llm/usage', methods=['GET'])
def get_usage():
    """Get usage statistics (placeholder for now)"""
    return jsonify({
        'success': True,
        'usage': {
            'requests_today': 10,
            'tokens_used': 5000,
            'estimated_cost': 0.10
        }
    })

@llm_bp.route('/api/v1/llm/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify LLM service is running"""
    if client is None:
        return jsonify({
            'status': 'disabled',
            'message': 'LLM service disabled - no API key configured'
        }), 503
    
    return jsonify({
        'status': 'healthy',
        'message': 'LLM service is operational'
    }), 200