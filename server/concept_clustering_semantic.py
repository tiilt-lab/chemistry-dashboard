import logging
import json
import requests
from typing import List, Dict
from app import db
from tables.concept_session import ConceptSession
from tables.concept_node import ConceptNode
from tables.concept_edge import ConceptEdge
from tables.concept_cluster import ConceptCluster

def create_semantic_clusters(session_device_id):
    """
    Create clusters using GPT-4o for semantic analysis
    """
    try:
        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()
        
        if not concept_session:
            logging.error(f"No concept session found for {session_device_id}")
            return []
        
        # Get all nodes and edges
        nodes = ConceptNode.query.filter_by(
            concept_session_id=concept_session.id
        ).all()
        
        edges = ConceptEdge.query.filter_by(
            concept_session_id=concept_session.id
        ).all()
        
        if not nodes:
            logging.info("No nodes to cluster")
            return []
        
        # Prepare data for GPT-4o
        nodes_data = [
            {
                'id': node.id,
                'text': node.text,
                'type': node.node_type,
                'timestamp': node.timestamp
            }
            for node in nodes
        ]
        
        edges_data = [
            {
                'source': edge.source_node_id,
                'target': edge.target_node_id,
                'type': edge.edge_type
            }
            for edge in edges
        ]
        
        # Call the new clustering endpoint
        response = requests.post(
            'http://localhost:5000/api/v1/llm/create_clusters',
            json={
                'nodes': nodes_data,
                'edges': edges_data
            },
            timeout=40
        )
        
        if response.status_code != 200:
            logging.error(f"LLM clustering failed: {response.text}")
            return []
            
        result = response.json()
        clusters_data = result.get('clusters', [])
        
        if not clusters_data:
            logging.error("No clusters returned from LLM")
            return []
        
        # Create cluster objects in database
        created_clusters = []
        for idx, cluster_info in enumerate(clusters_data):
            cluster = ConceptCluster(
                concept_session_id=concept_session.id,
                cluster_name=cluster_info['name'],
                summary=cluster_info.get('summary', ''),
                cluster_order=idx
            )
            db.session.add(cluster)
            db.session.flush()
            
            # Add nodes to cluster
            node_ids = cluster_info.get('node_ids', [])
            cluster_nodes = [n for n in nodes if n.id in node_ids]
            
            for node in cluster_nodes:
                cluster.nodes.append(node)
            
            cluster.node_count = len(cluster_nodes)
            
            # Set time range based on nodes
            if cluster_nodes:
                timestamps = [n.timestamp for n in cluster_nodes if n.timestamp]
                if timestamps:
                    cluster.start_time = min(timestamps)
                    cluster.end_time = max(timestamps)
            
            # Find centroid (most connected node)
            if node_ids and edges:
                edge_count = {}
                for edge in edges:
                    if edge.source_node_id in node_ids:
                        edge_count[edge.source_node_id] = edge_count.get(edge.source_node_id, 0) + 1
                    if edge.target_node_id in node_ids:
                        edge_count[edge.target_node_id] = edge_count.get(edge.target_node_id, 0) + 1
                
                if edge_count:
                    cluster.centroid_node_id = max(edge_count, key=edge_count.get)
            
            created_clusters.append(cluster)
        
        db.session.commit()
        logging.info(f"Created {len(created_clusters)} semantic clusters")
        return [c.id for c in created_clusters]
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to create semantic clusters: {e}", exc_info=True)
        return []