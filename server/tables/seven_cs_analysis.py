from app import db
from datetime import datetime
import json

class SevenCsAnalysis(db.Model):
    __tablename__ = 'seven_cs_analysis'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='CASCADE'), nullable=False)

    # Analysis results stored as JSON for flexibility
    # Structure: {"climate": {"score": 75, "explanation": "...", "evidence": [...]}, ...}
    # Keys present = active dimensions for this session. Absent = inactive.
    analysis_summary = db.Column(db.JSON)

    # AI-generated baseline (same structure as analysis_summary).
    # Set at generation time; never modified by user edits.
    # Used to compute edit diffs: if analysis_summary[dim] != ai_baseline[dim], it's been edited.
    ai_baseline = db.Column(db.JSON)

    # Analysis status
    analysis_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed

    # Optional custom schema (NULL = legacy hardcoded 7C)
    schema_id = db.Column(db.Integer, db.ForeignKey('dimension_schema.id', ondelete='SET NULL'), nullable=True)

    # Metadata
    total_segments_analyzed = db.Column(db.Integer)
    processing_time_seconds = db.Column(db.Float)
    llm_model_used = db.Column(db.String(50), default='gpt-4o')
    tokens_used = db.Column(db.Integer)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session_device = db.relationship("SessionDevice", backref="seven_cs_analyses")
    coded_segments = db.relationship("SevenCsCodedSegment", back_populates="analysis", cascade="all, delete-orphan")

    def __init__(self, session_device_id, analysis_status='pending', llm_model_used='gpt-4o', schema_id=None):
        self.session_device_id = session_device_id
        self.analysis_status = analysis_status
        self.llm_model_used = llm_model_used
        self.schema_id = schema_id
        self.analysis_summary = {}
        self.ai_baseline = {}

    def update_summary(self, summary_data, segments_analyzed, processing_time, tokens_used):
        """Update the analysis with results. Sets both analysis_summary and ai_baseline."""
        self.analysis_summary = summary_data
        self.ai_baseline = summary_data
        self.total_segments_analyzed = segments_analyzed
        self.processing_time_seconds = processing_time
        self.tokens_used = tokens_used
        self.analysis_status = 'completed'
        self.updated_at = datetime.utcnow()

    def get_dimension_counts(self):
        """Get counts of coded segments per dimension"""
        counts = {}
        for segment in self.coded_segments:
            if segment.dimension not in counts:
                counts[segment.dimension] = 0
            counts[segment.dimension] += 1
        return counts

    def json(self):
        return dict(
            id=self.id,
            session_device_id=self.session_device_id,
            analysis_summary=self.analysis_summary,
            analysis_status=self.analysis_status,
            total_segments_analyzed=self.total_segments_analyzed,
            processing_time_seconds=self.processing_time_seconds,
            llm_model_used=self.llm_model_used,
            tokens_used=self.tokens_used,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            dimension_counts=self.get_dimension_counts(),
            schema_id=self.schema_id,
            ai_baseline=self.ai_baseline
        )

    @staticmethod
    def verify_fields():
        return True, None