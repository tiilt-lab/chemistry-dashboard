from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class Rating(db.Model):
    __tablename__ = 'rating'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sessionid = db.Column(db.Integer, nullable=False)
    sessiondeviceid = db.Column(db.Integer, nullable=False)
    speakertag = db.Column(db.String(30), nullable=False)
    raterid = db.Column(db.String(30), nullable=False)
    evaluation_category = db.Column(db.String(40), nullable=False)
    response = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)

    def __hash__(self):
        return hash(self.id)

    def __init__(self, sessionid, sessiondeviceid, speakertag, raterid,evaluation_category,response):
        self.sessionid = sessionid
        self.sessiondeviceid = sessiondeviceid
        self.speakertag = speakertag
        self.raterid = raterid
        self.evaluation_category = evaluation_category
        self.response = response
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            sessionid=self.sessionid,
            sessiondeviceid=self.sessiondeviceid,
            speakertag=self.speakertag,
            raterid=self.raterid,
            evaluation_category = self.evaluation_category,
            response = self.response,
            creation_date=str(self.creation_date) + ' UTC',
        )

   

