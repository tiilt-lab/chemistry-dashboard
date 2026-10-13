from app import db
from utility import verify_characters
import uuid

class SessionDevice(db.Model):
    __tablename__ = 'session_device'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    processing_key = db.Column(db.String(64), nullable=True)
    name = db.Column(db.String(64))
    connected = db.Column(db.Boolean, nullable=False)
    removed = db.Column(db.Boolean, nullable=False, default=False) # If the device was removed from the session by the owner.
    button_pressed = db.Column(db.Boolean, nullable=False)
    embeddings = db.Column(db.String(64))
    # Set when a post-hoc re-analysis (audio/video/style) completes for this pod.
    posthoc_analyzed_date = db.Column(db.DateTime, nullable=True)
    # JSON blob of the model choices used by the last post-hoc run (asr,
    # embedder, diarizer, scorer, emotion, attention, object, face, head, ...),
    # for reproducibility/provenance. Nullable. NOTE: this is a mapped column,
    # so migration f1a2b3c4d5e6 MUST be applied before deploying this code — a
    # missing DB column raises on every SessionDevice query, it does not read as
    # None. The _posthoc_models_json guard only protects against bad JSON.
    posthoc_models = db.Column(db.Text, nullable=True)
    # Negotiation classes with one device per team (session.negotiation_paired):
    # the breakout group this device belongs to ("Table 3") and the side of the
    # case it records ("Pat" or "Sandy"), so its transcript, faces and gestures
    # all count for that team. NULL on every other session. Mapped columns:
    # migration 5d6e7f809102 must be applied before this code is deployed.
    negotiation_group = db.Column(db.String(32), nullable=True)
    negotiation_side = db.Column(db.String(16), nullable=True)

    speakers = db.relationship("Speaker", back_populates="session_device", cascade="all, delete",passive_deletes=True)
    llmfeedbackreports = db.relationship("LLMFeedbackReport", back_populates="session_device", cascade="all, delete",passive_deletes=True)
    llmquestionanswer = db.relationship("LLMQuestionAnswer", back_populates="session_device", cascade="all, delete",passive_deletes=True)
    sessionSynthesizedReports = db.relationship("SessionSynthesizedReport", back_populates="session_device", cascade="all, delete",passive_deletes=True)

    # No UNIQUE on (session_id, name): no deployment ever had one, and
    # create_byod_session_device converges concurrent same-name joins itself
    # (the model used to declare one; migration 1f2e3d4c5b6a records the live
    # schema). ux_sd_processing_key: looked up on every pod request and
    # callback; UNIQUE so a key can never resolve to two pods (f8ae4e72c79c).
    __table_args__ = (db.Index('ux_sd_processing_key', 'processing_key', unique=True),)

    KEY_MAX_LENGTH = 64
    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '
    NEGOTIATION_SIDES = ('Pat', 'Sandy')
    NEGOTIATION_GROUP_MAX_LENGTH = 32

    def __hash__(self):
        return hash(self.id)

    def __init__(self, session_id, device_id, name):
        self.session_id = session_id
        self.device_id = device_id
        self.name = name
        self.connected = False
        self.removed = False
        self.button_pressed = False
        self.embeddings =  None

    def create_key(self):
        self.processing_key = '{0}-{1}'.format(self.id, str(uuid.uuid4()))

    def json(self):
        return dict(
            id=self.id,
            session_id=self.session_id,
            device_id=self.device_id,
            name=self.name,
            connected=self.connected,
            removed=self.removed,
            button_pressed=self.button_pressed,
            embeddings=self.embeddings,
            posthoc_analyzed_date=str(self.posthoc_analyzed_date) + ' UTC' if self.posthoc_analyzed_date else None,
            posthoc_models=self._posthoc_models_json(),
            negotiation_group=self.negotiation_group,
            negotiation_side=self.negotiation_side
        )

    def _posthoc_models_json(self):
        # Defensive: column may be absent on un-migrated deployments, or hold a
        # bad value. Never let provenance break the pod's json().
        import json as _json
        raw = getattr(self, 'posthoc_models', None)
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def verify_fields(name=None):
        message = None
        if name is not None:
            if len(name) > SessionDevice.NAME_MAX_LENGTH:
                message = 'Name must not exceed {0} characters.'.format(SessionDevice.NAME_MAX_LENGTH)
            if not verify_characters(name, SessionDevice.NAME_CHARS):
                message = 'Invalid characters in device name.'
        return message is None, message

    @staticmethod
    def verify_negotiation(group=None, side=None):
        """(ok, message, clean group, clean side) for a paired-session role.
        Blank/None clears a field; the side is case-insensitive Pat/Sandy;
        the group is a short label with the device-name character set."""
        clean_group = (group or '').strip() if isinstance(group, str) or group is None else None
        if clean_group is None:
            return False, 'Group must be text.', None, None
        if len(clean_group) > SessionDevice.NEGOTIATION_GROUP_MAX_LENGTH:
            return False, 'Group must not exceed {0} characters.'.format(SessionDevice.NEGOTIATION_GROUP_MAX_LENGTH), None, None
        if clean_group and not verify_characters(clean_group, SessionDevice.NAME_CHARS):
            return False, 'Invalid characters in group.', None, None
        clean_side = None
        if side not in (None, ''):
            if not isinstance(side, str):
                return False, 'Side must be Pat or Sandy.', None, None
            clean_side = side.strip().capitalize()
            if clean_side not in SessionDevice.NEGOTIATION_SIDES:
                return False, 'Side must be Pat or Sandy.', None, None
        return True, None, clean_group or None, clean_side

    def negotiation_label(self):
        # "Table 3 · Pat" for the overview and the coding panel; None if unset.
        parts = [p for p in (self.negotiation_group, self.negotiation_side) if p]
        return ' \u00b7 '.join(parts) if parts else None
