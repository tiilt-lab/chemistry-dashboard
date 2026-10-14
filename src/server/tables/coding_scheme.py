from app import db
from datetime import datetime, timezone
import coding_schemes as _cs


class CodingScheme(db.Model):
    """An instructor-made coding scheme (coding_scheme.py): what the utterance
    coder codes for. Stored in the editor shape as JSON; sessions point at it
    with session.coding_scheme = "scheme:<id>". Goes with its owner."""
    __tablename__ = 'coding_scheme'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text)
    scheme = db.Column(db.Text, nullable=False)   # JSON, editor shape (coding_scheme.normalize)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    def __hash__(self):
        return hash(self.id)

    def __init__(self, owner_id, scheme):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.owner_id = owner_id
        self.created_at = now
        self.set_scheme(scheme)

    def set_scheme(self, scheme):
        import json
        self.name = scheme["name"]
        self.description = scheme.get("description") or ""
        self.scheme = json.dumps(scheme)
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def scheme_dict(self):
        return _cs.loads(self.scheme) or {"name": self.name, "description": self.description or "", "context": [], "dimensions": []}

    @property
    def ref(self):
        return _cs.SCHEME_PREFIX + str(self.id)

    def json(self, full=True):
        data = dict(id=self.id, ref=self.ref, owner_id=self.owner_id, name=self.name,
                    description=self.description or "", builtin=False,
                    created_at=str(self.created_at) + ' UTC', updated_at=str(self.updated_at) + ' UTC')
        scheme = self.scheme_dict()
        data['dimension_count'] = len(scheme.get('dimensions') or [])
        if full:
            data['context'] = scheme.get('context') or []
            data['dimensions'] = scheme.get('dimensions') or []
        return data
