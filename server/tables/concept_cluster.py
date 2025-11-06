from app import db
from datetime import datetime

class ConceptCluster(db.Model):
    __tablename__ = 'concept_cluster'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    concept_session_id = db.Column(db.Integer, db.ForeignKey('concept_session.id', ondelete='CASCADE'), nullable=False)
    cluster_name = db.Column(db.String(200))
    summary = db.Column(db.Text)
    start_time = db.Column(db.Float)  # in seconds from session start
    end_time = db.Column(db.Float)
    centroid_node_id = db.Column(db.String(100), db.ForeignKey('concept_node.id', ondelete='SET NULL'))
    node_count = db.Column(db.Integer, default=0)
    cluster_order = db.Column(db.Integer)  # for maintaining temporal sequence
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    concept_session = db.relationship("ConceptSession", backref="clusters")
    nodes = db.relationship("ConceptNode", secondary="cluster_node_mapping", backref="clusters")
    centroid_node = db.relationship("ConceptNode", foreign_keys=[centroid_node_id])
    
    def __init__(self, concept_session_id, cluster_name, summary=None, start_time=None, end_time=None, cluster_order=0):
        self.concept_session_id = concept_session_id
        self.cluster_name = cluster_name
        self.summary = summary
        self.start_time = start_time
        self.end_time = end_time
        self.cluster_order = cluster_order
        self.created_at = datetime.utcnow()
    
    def json(self):
        return dict(
            id=self.id,
            name=self.cluster_name,
            summary=self.summary,
            start_time=self.start_time,
            end_time=self.end_time,
            node_count=self.node_count,
            order=self.cluster_order,
            nodes=[node.json() for node in self.nodes] if self.nodes else [],
            centroid_node_id=self.centroid_node_id
        )