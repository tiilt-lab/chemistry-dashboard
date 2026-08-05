from app import db
from datetime import datetime

class ConceptEdge(db.Model):
    __tablename__ = 'concept_edge'
    id = db.Column(db.String(100), primary_key=True)
    concept_session_id = db.Column(db.Integer, db.ForeignKey('concept_session.id', ondelete="CASCADE"), nullable=False)
    source_node_id = db.Column(db.String(100), db.ForeignKey('concept_node.id', ondelete="CASCADE"), nullable=False)
    target_node_id = db.Column(db.String(100), db.ForeignKey('concept_node.id', ondelete="CASCADE"), nullable=False)
    edge_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - simplified without overlaps parameter
    concept_session = db.relationship("ConceptSession", back_populates="edges")

    def __init__(self, id, concept_session_id, source_node_id, target_node_id, edge_type):
        self.id = id
        self.concept_session_id = concept_session_id
        self.source_node_id = source_node_id
        self.target_node_id = target_node_id
        self.edge_type = edge_type
        self.created_at = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            source=self.source_node_id,
            target=self.target_node_id,
            type=self.edge_type
        )