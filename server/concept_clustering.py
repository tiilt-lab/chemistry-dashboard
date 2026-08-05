from datetime import datetime
import logging
from app import db
from tables.concept_session import ConceptSession
from tables.concept_node import ConceptNode
from tables.concept_edge import ConceptEdge
from tables.concept_cluster import ConceptCluster

def create_time_based_clusters(session_device_id, time_window_minutes=3):
    """
    Create clusters based on time windows
    
    Args:
        session_device_id: ID of the session device
        time_window_minutes: Size of each time window in minutes
    
    Returns:
        List of created cluster IDs
    """
    try:
        # Get the concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()
        
        if not concept_session:
            logging.error(f"No concept session found for session_device_id={session_device_id}")
            return []
        
        # Get all nodes with timestamps, sorted by time
        nodes = ConceptNode.query.filter_by(
            concept_session_id=concept_session.id
        ).filter(
            ConceptNode.timestamp.isnot(None)
        ).order_by(ConceptNode.timestamp).all()
        
        if not nodes:
            logging.info(f"No nodes with timestamps for session {concept_session.id}")
            return []
        
        # Create time-based clusters
        clusters = []
        current_cluster_nodes = []
        cluster_start_time = nodes[0].timestamp
        cluster_order = 0
        time_window_seconds = time_window_minutes * 60
        
        for node in nodes:
            # Check if we should start a new cluster
            if node.timestamp - cluster_start_time > time_window_seconds and current_cluster_nodes:
                # Save current cluster
                cluster = ConceptCluster(
                    concept_session_id=concept_session.id,
                    cluster_name=f"Segment {cluster_order + 1} ({format_time(cluster_start_time)}-{format_time(node.timestamp)})",
                    start_time=cluster_start_time,
                    end_time=current_cluster_nodes[-1].timestamp,
                    cluster_order=cluster_order
                )
                db.session.add(cluster)
                db.session.flush()  # Get the ID
                
                # Add nodes to cluster
                for cluster_node in current_cluster_nodes:
                    cluster.nodes.append(cluster_node)
                cluster.node_count = len(current_cluster_nodes)
                
                clusters.append(cluster)
                
                # Start new cluster
                cluster_order += 1
                current_cluster_nodes = [node]
                cluster_start_time = node.timestamp
            else:
                current_cluster_nodes.append(node)
        
        # Save final cluster
        if current_cluster_nodes:
            cluster = ConceptCluster(
                concept_session_id=concept_session.id,
                cluster_name=f"Segment {cluster_order + 1} ({format_time(cluster_start_time)}-{format_time(current_cluster_nodes[-1].timestamp)})",
                start_time=cluster_start_time,
                end_time=current_cluster_nodes[-1].timestamp,
                cluster_order=cluster_order
            )
            db.session.add(cluster)
            db.session.flush()
            
            for cluster_node in current_cluster_nodes:
                cluster.nodes.append(cluster_node)
            cluster.node_count = len(current_cluster_nodes)
            
            clusters.append(cluster)
        
        # Commit all changes
        db.session.commit()
        
        logging.info(f"Created {len(clusters)} time-based clusters for session {concept_session.id}")
        return [c.id for c in clusters]
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to create time-based clusters: {e}", exc_info=True)
        return []

def format_time(timestamp):
    """Format timestamp to MM:SS"""
    minutes = int(timestamp // 60)
    seconds = int(timestamp % 60)
    return f"{minutes:02d}:{seconds:02d}"