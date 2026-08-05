from app import db
from datetime import datetime
import json


class DimensionScoreEdit(db.Model):
    __tablename__ = 'dimension_score_edit'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('seven_cs_analysis.id', ondelete='CASCADE'), nullable=False)
    dimension_key = db.Column(db.String(50), nullable=False)
    field_edited = db.Column(db.String(20), nullable=False)  # "score", "explanation", or "evidence"
    original_value = db.Column(db.Text)  # JSON-encoded original
    edited_value = db.Column(db.Text)    # JSON-encoded new value
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    analysis = db.relationship("SevenCsAnalysis", backref="edits")

    def __init__(self, analysis_id, dimension_key, field_edited, original_value, edited_value):
        self.analysis_id = analysis_id
        self.dimension_key = dimension_key
        self.field_edited = field_edited
        self.original_value = json.dumps(original_value) if not isinstance(original_value, str) else original_value
        self.edited_value = json.dumps(edited_value) if not isinstance(edited_value, str) else edited_value

    def json(self):
        return dict(
            id=self.id,
            analysis_id=self.analysis_id,
            dimension_key=self.dimension_key,
            field_edited=self.field_edited,
            original_value=json.loads(self.original_value) if self.original_value else None,
            edited_value=json.loads(self.edited_value) if self.edited_value else None,
            created_at=self.created_at.isoformat() if self.created_at else None
        )
