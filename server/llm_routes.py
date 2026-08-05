import json  
import logging 
import sys
import os

import database

# Add the audio_processing directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'audio_processing'))

from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = None
if api_key:
    client = OpenAI(api_key=api_key)
    logging.info("OpenAI client initialized successfully")
else:
    logging.warning("OPENAI_API_KEY not set. LLM routes will be disabled.")

llm_bp = Blueprint('llm', __name__)

def get_all_node_types():
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
        
        logging.info(f"Concept extraction request received with {len(context.get('speaker_segments', {}))} speakers")
        
        speaker_text = ""
        for speaker, segments in context.get('speaker_segments', {}).items():
            speaker_text += f"\nSpeaker {speaker}: {' '.join(segments)}"
        
        recent_concepts_text = ""
        if context.get('recent_concepts'):
            concepts_list = [f"{c.get('text')} ({c.get('type')})" for c in context['recent_concepts']]
            recent_concepts_text = f"\n\n**ALREADY EXTRACTED CONCEPTS (DO NOT EXTRACT THESE AGAIN):**\n{', '.join(concepts_list)}\n\n**IMPORTANT:** The above concepts are provided for context only. You may create edges TO them, but DO NOT extract them as new nodes."
        
        if not speaker_text.strip():
            logging.warning("No transcript text to process for concept extraction")
            return jsonify({
                "new_nodes": [],
                "new_edges": [],
                "discourse_type": "exploratory"
            }), 200
        
        prompt = f"""Extract a comprehensive knowledge graph from this discussion. Be thorough - capture EVERY meaningful idea FROM THE NEW DISCUSSION ONLY.

NEW DISCUSSION TO PROCESS:{speaker_text}
{recent_concepts_text}

EXTRACTION RULES:
1. Extract concepts ONLY from the "NEW DISCUSSION TO PROCESS" section above;
2. DO NOT re-extract any concepts listed in "ALREADY EXTRACTED CONCEPTS" section;
3. Extract AT LEAST one concept for every 2-3 sentences in the NEW discussion;
4. Include ALL of: main ideas, sub-points, examples, questions, clarifications from NEW discussion;
5. Keep concept text concise but complete (3-15 words is fine);
6. Don't oversummarize - "multimodal learning analytics" is better than just "analytics";
7. **speaker**: The speaker ID (e.g., 1, 2, "Unknown") who said the concept. This ID comes from the "Speaker {{ID}}" prefix.

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
- "video-based tools" (type: "solution")
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
                    CRITICAL RULE: Only extract NEW concepts from the NEW DISCUSSION section. Never re-extract concepts that are listed as ALREADY EXTRACTED.
                    Extract MORE concepts rather than fewer. Include minor points, asides, and elaborations.
                    Every meaningful utterance should produce at least one concept.
                    Don't oversummarize - preserve the specific ideas being discussed.
                    You may create edges/relationships TO already extracted concepts, but DO NOT create new nodes for them."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4, 
            max_tokens=2000 
        )
        
        result = json.loads(response.choices[0].message.content)
        
        logging.info(f"Extracted {len(result.get('new_nodes', []))} concepts from {len(speaker_text.split())} words")

        nodes = result.get("new_nodes") or result.get("concepts") or []
        edges = result.get("new_edges") or result.get("relationships") or []
        
        valid_nodes = []
        for node in nodes:
            if node.get('text'): 
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
    if client is None:
        return jsonify({
            'status': 'disabled',
            'message': 'LLM service disabled - no API key configured'
        }), 503
    
    return jsonify({
        'status': 'healthy',
        'message': 'LLM service is operational'
    }), 200



@llm_bp.route('/api/v1/llm/create_clusters', methods=['POST'])
def create_clusters():
    """Create semantic clusters from concepts using GPT-4o"""
    try:
        data = request.get_json()
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        
        if not nodes:
            return jsonify({'error': 'No nodes provided'}), 400
        
        # Build the prompt
        prompt = f"""Analyze these concepts from a discussion and create 2-5 semantic clusters.

Concepts:
{json.dumps(nodes, indent=2)}

Relationships:
{json.dumps(edges, indent=2)}

Group related concepts into clusters based on:
1. Topic coherence - concepts about the same subject
2. Logical flow - concepts that form arguments or explanations
3. Problem-solution relationships
4. Goal-action relationships

Return a JSON object with a "clusters" array. Each cluster must have:
- "name": descriptive title (max 50 chars)
- "summary": 1-2 sentence description
- "node_ids": array of concept node IDs in this cluster
- "theme": main theme type

IMPORTANT: Every node ID must appear in exactly one cluster."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at analyzing discussion concepts and organizing them into meaningful thematic clusters."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate and return
        if 'clusters' in result:
            return jsonify({'clusters': result['clusters']}), 200
        else:
            return jsonify({'clusters': result}), 200
            
    except Exception as e:
        logger.error(f"Cluster creation failed: {e}")
        return jsonify({'error': str(e)}), 500




@llm_bp.route('/api/v1/test-llm', methods=['GET'])
def test_route():
    return jsonify({"message": "LLM routes are working"}), 200