import logging
import json
import requests
from collections import deque
from datetime import datetime
import numpy as np
from .discourse_schemas import DISCOURSE_SCHEMAS, get_all_node_types, get_all_edge_types

class ConceptExtractor:
    def __init__(self, config, llm_endpoint='http://127.0.0.1:5000/api/v1/llm/extract_concepts'):
        self.config = config
        self.llm_endpoint = llm_endpoint
        self.concept_graph = {
            "nodes": [],
            "edges": [],
            "discourse_type": "exploratory",
            "session_id": f"{config.sessionId}:{config.deviceId}"
        }
        self.transcript_buffer = deque(maxlen=25) 
        self.node_id_counter = 0
        self.last_process_time = 0
        self.processing_interval = 8  # Process every 8 seconds
        self.first_extraction = True  # Track for faster first extraction
        
        # Keep conversation memory
        self.conversation_summary = []  
        self.speaker_profiles = {}  
        self.topic_evolution = []  
        self.pending_questions = [] 
        
    def should_process(self, current_time):
        """Check if enough time has passed to process again"""
        time_diff = current_time - self.last_process_time
        
        # First extraction at 8 seconds for quick feedback
        if self.first_extraction and time_diff >= 8:
            threshold = 8
        # Adaptive threshold updated for new buffer size
        elif len(self.transcript_buffer) > 20: 
            threshold = 8  # Process more frequently 
        else:
            threshold = self.processing_interval
            
        logging.info(f"ConceptExtractor: current_time={current_time}, last_process={self.last_process_time}, diff={time_diff}, threshold={threshold}")
        
        if time_diff >= threshold:
            self.last_process_time = current_time
            if self.first_extraction:
                self.first_extraction = False
            return True
        return False
    
    def add_transcript(self, transcript_text, speaker_id, start_time, end_time):
        """Add transcript to buffer and potentially trigger processing"""
        # Add to buffer
        self.transcript_buffer.append({
            "text": transcript_text,
            "speaker_id": speaker_id,
            "start_time": start_time,
            "end_time": end_time
        })
        
        # Track speaker patterns
        if speaker_id not in self.speaker_profiles:
            self.speaker_profiles[speaker_id] = {
                "utterance_count": 0,
                "total_words": 0,
                "topics_introduced": [],
                "questions_asked": 0
            }
        
        self.speaker_profiles[speaker_id]["utterance_count"] += 1
        self.speaker_profiles[speaker_id]["total_words"] += len(transcript_text.split())
        
        # Check for questions in transcript
        if '?' in transcript_text:
            self.speaker_profiles[speaker_id]["questions_asked"] += 1
            self.pending_questions.append({
                "question": transcript_text,
                "speaker": speaker_id,
                "time": start_time
            })
        
        should_proc = self.should_process(end_time)
        logging.info(f"ConceptExtractor: should_process({end_time}) = {should_proc}")
        
        if should_proc:
            logging.info("ConceptExtractor: Processing buffer now")
            return self.process_buffer()
        return None
    
    def process_buffer(self):
        """Process accumulated transcripts to extract concepts"""
        logging.info(f"ConceptExtractor: process_buffer called, buffer length: {len(self.transcript_buffer)}")
        
        if not self.transcript_buffer:
            logging.info("ConceptExtractor: Buffer empty, nothing to process")
            return None
        
        logging.info(f"ConceptExtractor: Processing {len(self.transcript_buffer)} transcripts")
        
        try:
            context = self._prepare_context()
            logging.info(f"ConceptExtractor: Prepared context with {len(context.get('speaker_segments', {}))} speakers")
            logging.info(f"ConceptExtractor: Including {len(context.get('recent_concepts', []))} recent concepts")
            
            # Call LLM to extract concepts
            logging.info("ConceptExtractor: Calling LLM extraction...")
            extraction_result = self._call_llm_extraction(context)
            logging.info(f"ConceptExtractor: LLM extraction returned: {extraction_result is not None}")
            
            if extraction_result:
                nodes_before = len(self.concept_graph["nodes"])
                edges_before = len(self.concept_graph["edges"])
                
                self._update_graph(extraction_result)
                
                new_nodes = self.concept_graph["nodes"][nodes_before:]
                new_edges = self.concept_graph["edges"][edges_before:]
                
                logging.info(f"ConceptExtractor: Added {len(new_nodes)} nodes and {len(new_edges)} edges")
                
                self._update_conversation_memory(new_nodes)
                
                result = {
                    "type": "incremental",
                    "nodes": new_nodes,
                    "edges": new_edges,
                    "discourse_type": extraction_result.get("discourse_type", "exploratory"),
                    "discourse_features": extraction_result.get("discourse_features", []),
                    "timestamp": self.last_process_time
                }
                return result
            else:
                logging.warning("ConceptExtractor: LLM returned None")
        except Exception as e:
            logging.error(f"ConceptExtractor: Exception in process_buffer: {str(e)}", exc_info=True)
            
        return None
    
    def _prepare_context(self):
        """Prepare enriched context from transcript buffer and conversation history"""
        # Group by speaker with temporal ordering preserved
        speaker_segments = {}
        temporal_segments = []  # Keep temporal order
        
        for segment in self.transcript_buffer:
            speaker = segment['speaker_id'] if segment['speaker_id'] != -1 else 'Unknown'
            
            if speaker not in speaker_segments:
                speaker_segments[speaker] = []
            speaker_segments[speaker].append(segment['text'])
            
            temporal_segments.append({
                "speaker": speaker,
                "text": segment['text'],
                "time": segment['start_time']
            })
        
        recent_concepts = self.concept_graph['nodes'][-20:] if len(self.concept_graph['nodes']) > 20 else self.concept_graph['nodes']
        
        # Include pending questions that might be answered
        recent_questions = self.pending_questions[-5:] if len(self.pending_questions) > 5 else self.pending_questions
        
        # Prepare speaker statistics
        speaker_stats = {}
        for speaker_id, profile in self.speaker_profiles.items():
            speaker_stats[str(speaker_id)] = {
                "utterances": profile["utterance_count"],
                "questions": profile["questions_asked"]
            }
        
        return {
            "speaker_segments": speaker_segments,
            "temporal_segments": temporal_segments[-25:],  # Last 25 segments in time order
            "recent_concepts": recent_concepts,
            "current_discourse_type": self.concept_graph.get("discourse_type", "exploratory"),
            "conversation_summary": self.conversation_summary[-5:],  # Last 5 key points
            "pending_questions": recent_questions,
            "speaker_stats": speaker_stats,
            "total_nodes": len(self.concept_graph["nodes"]),
            "total_edges": len(self.concept_graph["edges"])
        }
    
    def _call_llm_extraction(self, context):
        """Call LLM endpoint to extract concepts with enriched context"""
        try:
            # Debug: Log what we're sending
            logging.info(f"ConceptExtractor: Calling LLM endpoint: {self.llm_endpoint}")
            logging.info(f"ConceptExtractor: Context has {len(context.get('speaker_segments', {}))} speakers")
            
            # Check if endpoint is reachable first
            import socket
            from urllib.parse import urlparse
            
            try:
                parsed_url = urlparse(self.llm_endpoint)
                hostname = parsed_url.hostname or 'server'
                port = parsed_url.port or 5000
                
                # Try to resolve the hostname
                socket.gethostbyname(hostname)
                logging.info(f"ConceptExtractor: Server '{hostname}' is resolvable")
            except socket.gaierror as e:
                logging.error(f"ConceptExtractor: Cannot resolve server hostname '{hostname}': {e}")
                logging.error("ConceptExtractor: Check if 'server' container is running and linked properly in docker-compose")
                return None
            
            # Make the request
            response = requests.post(
                self.llm_endpoint,
                json={
                    "context": context,
                    "schemas": DISCOURSE_SCHEMAS
                },
                timeout=15
            )
            
            logging.info(f"ConceptExtractor: LLM response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Debug: Log what we received
                nodes_count = len(result.get('new_nodes', []))
                edges_count = len(result.get('new_edges', []))
                logging.info(f"ConceptExtractor: LLM returned {nodes_count} nodes, {edges_count} edges")
                
                if nodes_count == 0:
                    logging.warning("ConceptExtractor: LLM returned no nodes. Context might be insufficient or LLM not configured properly")
                    logging.debug(f"ConceptExtractor: Full LLM response: {json.dumps(result)}")
                
                return result
            else:
                logging.error(f"ConceptExtractor: LLM extraction failed with status {response.status_code}")
                logging.error(f"ConceptExtractor: Response body: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"ConceptExtractor: LLM request timed out after 15 seconds")
            return None
        except requests.exceptions.ConnectionError as e:
            logging.error(f"ConceptExtractor: Cannot connect to LLM endpoint at {self.llm_endpoint}")
            logging.error(f"ConceptExtractor: Connection error: {e}")
            logging.error("ConceptExtractor: Check if the server container is running and the port 5000 is exposed")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"ConceptExtractor: Failed to call LLM endpoint: {e}")
            return None
        except Exception as e:
            logging.error(f"ConceptExtractor: Unexpected error in LLM extraction: {e}", exc_info=True)
            return None
    
    def _update_graph(self, extraction_result):
        """Update the concept graph with new extractions"""
        new_nodes = extraction_result.get("new_nodes", [])
        new_edges = extraction_result.get("new_edges", [])
        
        # Create index-to-ID mapping for THIS batch
        batch_index_to_id = {}
        
        # Add nodes and track mapping
        for i, node in enumerate(new_nodes):
            node_id = f"node_{self.concept_graph['session_id']}_{self.node_id_counter}"
            node["id"] = node_id
            node["timestamp"] = self.last_process_time
            batch_index_to_id[i] = node_id  # Map batch index to global ID
            self.concept_graph["nodes"].append(node)
            self.node_id_counter += 1
        
        # Fix edges using the mapping with validation
        valid_edges = []
        for edge in new_edges:
            source_id = edge.get("source")
            target_id = edge.get("target")

            # Map integer indices to actual node IDs
            if isinstance(source_id, int):
                if source_id in batch_index_to_id:
                    source_id = batch_index_to_id[source_id]
                else:
                    logging.warning(f"ConceptExtractor: Skipping edge with invalid source index: {edge}")
                    continue  # Skip this edge

            if isinstance(target_id, int):
                if target_id in batch_index_to_id:
                    target_id = batch_index_to_id[target_id]
                else:
                    logging.warning(f"ConceptExtractor: Skipping edge with invalid target index: {edge}")
                    continue  # Skip this edge

            edge["id"] = f"edge_{self.concept_graph['session_id']}_{len(self.concept_graph['edges']) + len(valid_edges)}"
            edge["source"] = source_id
            edge["target"] = target_id
            valid_edges.append(edge)

        self.concept_graph["edges"].extend(valid_edges)
        
        if "discourse_type" in extraction_result:
            self.concept_graph["discourse_type"] = extraction_result["discourse_type"]
    
    def _update_conversation_memory(self, new_nodes):
        """Update conversation memory with key concepts"""
        # Add significant concepts to summary (nodes with certain types)
        key_types = ['goal', 'problem', 'conclusion', 'action', 'synthesis']
        for node in new_nodes:
            if node.get('type') in key_types:
                self.conversation_summary.append({
                    "text": node['text'],
                    "type": node['type'],
                    "time": self.last_process_time
                })
        
        if len(self.conversation_summary) > 20:
            self.conversation_summary = self.conversation_summary[-20:]
            
        # Check if questions were answered
        if new_nodes:
            answered_indices = []
            for i, question in enumerate(self.pending_questions):
                # Simple heuristic: if a new node mentions key words from question
                question_words = set(question['question'].lower().split())
                for node in new_nodes:
                    node_words = set(node['text'].lower().split())
                    if len(question_words & node_words) > 2:  # At least 2 common words
                        answered_indices.append(i)
                        break
            
            # Remove answered questions
            for i in reversed(answered_indices):
                self.pending_questions.pop(i)
    
    def get_full_graph(self):
        """Get the complete concept graph with metadata"""
        return {
            **self.concept_graph,
            "metadata": {
                "total_utterances": sum(p["utterance_count"] for p in self.speaker_profiles.values()),
                "total_speakers": len(self.speaker_profiles),
                "pending_questions": len(self.pending_questions),
                "key_points": len(self.conversation_summary)
            }
        }