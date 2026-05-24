from app import db
from datetime import datetime
from utility import verify_characters
from sqlalchemy.dialects.mysql import LONGTEXT
import hashlib
import os
import binascii
import random
import string
import re

class SessionSynthesizedReport(db.Model):
    __tablename__ = 'session_synthesized_report'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id',ondelete="CASCADE"), nullable=False)
    synthesized_feedback = db.Column(LONGTEXT, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False) 

    session_device = db.relationship("SessionDevice", back_populates="sessionSynthesizedReports")

   
    def __hash__(self):
        return hash(self.id)

    def __init__(self, session_id, session_device_id,synthesized_feedback):
        self.session_id = session_id
        self.session_device_id = session_device_id
        self.synthesized_feedback = synthesized_feedback
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            session_id=self.session_id,
            session_device_id=self.session_device_id,
            synthesized_feedback=self.synthesized_feedback,
            creation_date=str(self.creation_date) + ' UTC'
        )

    @staticmethod
    def verify_fields(name=None):
        message = None
        # Not implemented
        return message == None, message
