from app import db
from sqlalchemy import UniqueConstraint
from utility import verify_characters
import uuid

class SessionDevice(db.Model):
    __tablename__ = 'session_device'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    processing_key = db.Column(db.String(64), nullable=True)
    name = db.Column(db.String(64))
    connected = db.Column(db.Boolean, nullable=False)
    removed = db.Column(db.Boolean, nullable=False, default=False) # If the device was removed from the session by the owner.
    button_pressed = db.Column(db.Boolean, nullable=False)
    embeddings = db.Column(db.String(64))
    
    speakers = db.relationship("Speaker", back_populates="session_device", cascade="all, delete",passive_deletes=True)

    UniqueConstraint('session_id', 'name', name='unique_session_name')

    KEY_MAX_LENGTH = 64
    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '

    def __hash__(self):
        return hash((self.session_device_id))

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
            embeddings=self.embeddings
        )

    @staticmethod
    def verify_fields(name=None):
        message = None
        if name != None:
            if len(name) > SessionDevice.NAME_MAX_LENGTH:
                message = 'Name must not exceed {0} characters.'.format(SessionDevice.NAME_MAX_LENGTH)
            if not verify_characters(name, SessionDevice.NAME_CHARS):
                message = 'Invalid characters in device name.'
        return message == None, message
