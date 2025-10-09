from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize OpenAI client
#client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
api_key = os.getenv("OPENAI_API_KEY")
client = None
if api_key:
    client = OpenAI(api_key=api_key)
else:
    print("OPENAI_API_KEY not set. LLM routes will be disabled.")

# Create Blueprint for LLM routes
llm_bp = Blueprint('llm', __name__)

def prepare_context_data(data):
    """Prepare and limit data for token management"""
    metrics = data.get('metrics', {})
    transcripts = data.get('transcripts', [])
    session_info = data.get('sessionInfo', {})
    time_range = data.get('timeRange', {})
    
    # (Optional) truncate transcripts
    # limited_transcripts = transcripts[-30:] if len(transcripts) > 30 else transcripts
    
    return {
        'metrics': metrics,
        'transcripts': transcripts,
        'sessionInfo': session_info,
        'timeRange': time_range
    }

def generate_prompt(task_type, data):
    """Generate appropriate prompt based on task type"""
    
    if task_type == 'summary':
        metrics = data.get('metrics', {})
        transcripts = data.get('transcripts', [])
        session_info = data.get('sessionInfo', {})
        time_range = data.get('timeRange', {})
        
        # Limit transcript text to avoid token limits
        transcript_list = transcripts[:10] if len(transcripts) > 10 else transcripts
        transcript_text = '\n'.join([
            f"[{t.get('speaker', 'Speaker')} at {t.get('start_time', 0)}s]: {t.get('transcript', '')}"
            for t in transcript_list
        ])
        
        return f"""Analyze this discussion session and provide a concise summary:

Session: {session_info.get('name', 'Current Session')}
Time Range: {time_range.get('start', 0)} to {time_range.get('end', 'end')} seconds

Metrics:
- Emotional Tone: {metrics.get('emotional', 'N/A')}% (>50 = positive)
- Analytic Thinking: {metrics.get('analytic', 'N/A')}% (>50 = analytic)
- Clout: {metrics.get('clout', 'N/A')}% (higher = more confident)
- Authenticity: {metrics.get('authenticity', 'N/A')}% (higher = more authentic)
- Certainty: {metrics.get('certainty', 'N/A')}% (higher = more certain)

Recent Transcript Excerpts:
{transcript_text}

Please consider these aspects:
1. Overall communication style assessment;
2. Key discussion themes;
3. Notable patterns in the conversation;
4. Suggestions for potential improvement.

Keep the response under 200 words."""

    elif task_type == 'metrics':
        metrics = data.get('metrics', {})
        return f"""Interpret these communication metrics and explain what they reveal about the discussion:

- Emotional Tone: {metrics.get('emotional', 'N/A')}%
- Analytic Thinking: {metrics.get('analytic', 'N/A')}%
- Clout: {metrics.get('clout', 'N/A')}%
- Authenticity: {metrics.get('authenticity', 'N/A')}%
- Certainty: {metrics.get('certainty', 'N/A')}%

Provide specific insights about:
1. The overall communication dynamics
2. Potential strengths and areas for improvement
3. What these patterns suggest about group dynamics

Keep response under 150 words."""

    elif task_type == 'themes':
        transcripts = data.get('transcripts', [])
        # Limit transcript text
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
        # Default to summary
        return generate_prompt('summary', data)

@llm_bp.route('/api/v1/llm/analyze', methods=['POST'])
def analyze():
    """Main endpoint for LLM analysis"""
    if client is None:
        return jsonify({"success": False,
                        "error": "LLM disabled (no OPENAI_API_KEY)"}), 503
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
        
        # Call OpenAI API with latest syntax
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" for better quality
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
        print(f"LLM API Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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