from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class SurveyResponse(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sessionid = db.Column(db.Integer, nullable=False)
    sessiondeviceid = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(30), nullable=False)
    response = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)

    def __hash__(self):
        return hash(self.id)

    def __init__(self, sessionid, sessiondeviceid, username,response):
        self.sessionid = sessionid
        self.sessiondeviceid = sessiondeviceid
        self.username = username
        self.response = response
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            sessionid=self.sessionid,
            sessiondeviceid=self.sessiondeviceid,
            username=self.username,
            response = self.response,
            creation_date=str(self.creation_date) + ' UTC',
        )

   

