from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class Rater(db.Model):
    __tablename__ = 'rater'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sessionid = db.Column(db.Integer, nullable=False)
    sessiondeviceid = db.Column(db.Integer, nullable=False)
    speakerid = db.Column(db.Integer, nullable=False)
    speakertag = db.Column(db.String(30), nullable=False)
    raterid = db.Column(db.String(30), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    evaluation_category = db.Column(db.String(40), nullable=False)
    completed = db.Column(db.Integer, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)

    def __hash__(self):
        return hash(self.id)

    def __init__(self, sessionid, sessiondeviceid, speakerid, speakertag, raterid, type,evaluation_category,completed):
        self.sessionid = sessionid
        self.sessiondeviceid = sessiondeviceid
        self.speakerid = speakerid
        self.speakertag = speakertag
        self.raterid = raterid
        self.type = type
        self.evaluation_category = evaluation_category
        self.completed = completed
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            sessionid=self.sessionid,
            sessiondeviceid=self.sessiondeviceid,
            speakerid=self.speakerid,
            speakertag=self.speakertag,
            raterid=self.raterid,
            type=self.type,
            evaluation_category = self.evaluation_category,
            completed = self.completed,
            creation_date=str(self.creation_date) + ' UTC',
        )

   

    @staticmethod
    def verify_fields(email=None, role=None):
        message = None
       
