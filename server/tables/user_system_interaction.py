from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class UserSystemInteraction(db.Model):
    __tablename__ = 'user_system_interaction'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sessionid = db.Column(db.Integer, nullable=False)
    sessiondeviceid = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(30), nullable=False)
    action = db.Column(db.Text, nullable=False)    
    creation_date = db.Column(db.DateTime, nullable=False)

    def __hash__(self):
        return hash(self.id)

    def __init__(self, sessionid, sessiondeviceid, username,action):
        self.sessionid = sessionid
        self.sessiondeviceid = sessiondeviceid
        self.username = username
        self.action = action
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            sessionid=self.sessionid,
            sessiondeviceid=self.sessiondeviceid,
            username=self.username,
            action = self.action,
            creation_date=str(self.creation_date) + ' UTC',
        )

   

    @staticmethod
    def verify_fields(email=None, role=None):
        message = None
       
