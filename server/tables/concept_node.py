from app import db
from datetime import datetime

class ConceptNode(db.Model):
    __tablename__ = 'concept_node'
    id = db.Column(db.String(100), primary_key=True)
    concept_session_id = db.Column(db.Integer, db.ForeignKey('concept_session.id', ondelete="CASCADE"), nullable=False)
    text = db.Column(db.Text)
    node_type = db.Column(db.String(50))
    speaker_id = db.Column(db.Integer, db.ForeignKey('speaker.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship - simplified without the edge relationships
    concept_session = db.relationship("ConceptSession", back_populates="nodes")
    speaker = db.relationship("Speaker", backref="concept_nodes")

    def __init__(self, id, concept_session_id, text, node_type, speaker_id=None, timestamp=None):
        self.id = id
        self.concept_session_id = concept_session_id
        self.text = text
        self.node_type = node_type
        self.speaker_id = speaker_id
        self.timestamp = timestamp
        self.created_at = datetime.utcnow()

    def json(self):
        # Get speaker alias if speaker exists
        speaker_alias = None
        if self.speaker_id and self.speaker:
            speaker_alias = self.speaker.get_alias()
        elif self.speaker_id:
            speaker_alias = f"Speaker {self.speaker_id}"

        return dict(
            id=self.id,
            text=self.text,
            type=self.node_type,  # Return as 'type' for frontend compatibility
            speaker_id=self.speaker_id,
            speaker_alias=speaker_alias,  # Include speaker alias
            timestamp=self.timestamp
        )