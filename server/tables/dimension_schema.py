from app import db
from datetime import datetime
import json


class DimensionSchema(db.Model):
    __tablename__ = 'dimension_schema'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schema_name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    # Array of {key, name, description, indicators[], scoring_criteria, color}
    dimensions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, schema_name, dimensions, is_default=False):
        self.schema_name = schema_name
        self.dimensions = dimensions
        self.is_default = is_default

    def get_dimension_dict(self):
        """Convert dimensions array to dict keyed by dimension key."""
        result = {}
        for dim in (self.dimensions or []):
            key = dim.get('key', '')
            result[key] = {
                'name': dim.get('name', key.title()),
                'description': dim.get('description', ''),
                'indicators': dim.get('indicators', []),
                'scoring_criteria': dim.get('scoring_criteria', ''),
                'color': dim.get('color', 'rgba(150, 150, 150, 0.35)')
            }
        return result

    def json(self):
        return dict(
            id=self.id,
            schema_name=self.schema_name,
            is_default=self.is_default,
            dimensions=self.dimensions,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None
        )
