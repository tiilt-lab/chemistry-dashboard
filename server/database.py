from app import db
import re
from sqlalchemy import or_, and_, desc
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func
import requests
from utility import sanitize
from datetime import datetime, timedelta
import random
import string
import logging

# Tables
from tables.device import Device
from tables.session import Session
from tables.session_device import SessionDevice
from tables.transcript import Transcript
from tables.keyword_usage import KeywordUsage
from tables.keyword_list_item import KeywordListItem
from tables.keyword_list import KeywordList
from tables.keyword import Keyword
from tables.user import User
from tables.api_client import APIClient
from tables.folder import Folder
from tables.topic_model import TopicModel
from tables.speaker import Speaker
from tables.speaker_transcript_metrics import SpeakerTranscriptMetrics

# Saves changes made to database (models)
def save_changes():
    db.session.commit()

def close_session():
    db.session.remove()

# -------------------------
# Speakers
# -------------------------

def get_speakers(session_device_id=None, id = None):
    query = db.session.query(Speaker)
    if id != None:
        return query.filter(Speaker.id == id).first()
    if session_device_id != None:
        query = query.filter(Speaker.session_device_id == session_device_id)
    return query.all()

def get_speaker_tags(session_device_id=None):
    query = db.session.query(Transcript).filter(session_device_id=session_device_id).distinct(Transcript.speaker_tag)
    return query.count()

def add_speaker(session_device_id, alias):
  speaker = Speaker(session_device_id, alias)
  db.session.add(speaker)
  db.session.commit()
  return speaker

def update_speaker(speaker_id, alias = None):
    speaker = get_speakers(id = speaker_id)
    if speaker:
        if alias:
            speaker.alias = alias
        db.session.commit()
        return speaker
    return None

def delete_speaker(speaker_id):
    db.session.query(Speaker).filter(Speaker.id == speaker_id).delete(synchronize_session='fetch')
    db.session.commit()
    return True

# -------------------------
# Speaker Transcript Metrics
# -------------------------

def get_speaker_transcript_metrics(id = None, speaker_id=None, transcript_id=None, session_device_id=None, session_id=None):
    query = db.session.query(SpeakerTranscriptMetrics)
    if id != None:
        return query.filter(SpeakerTranscriptMetrics.id == id).first()
    if speaker_id != None:
        query = query.filter(SpeakerTranscriptMetrics.speaker_id == speaker_id)
    if transcript_id != None:
        query = query.filter(SpeakerTranscriptMetrics.transcript_id == transcript_id)
    if session_device_id != None:
        query = query.join(Transcript, SpeakerTranscriptMetrics.transcript_id).filter(Transcript.session_device_id == session_device_id)
    return query.all()

def add_speaker_transcript_metrics(speaker_id, transcript_id, participation_score, internal_cohesion, responsivity, social_impact, newness, communication_density):
    metrics = SpeakerTranscriptMetrics(speaker_id, transcript_id, participation_score, internal_cohesion, responsivity, social_impact, newness, communication_density)
    db.session.add(metrics)
    db.session.commit()
    return metrics

def update_speaker_transcript_metrics(id, speaker_id=None, transcript_id=None, participation_score=None, internal_cohesion=None, responsivity=None, social_impact=None, newness=None, communication_density=None):
    metrics = get_speaker_transcript_metrics(id)

    if metrics:
        if speaker_id:
            metrics.speaker_id = speaker_id
        if transcript_id:
            metrics.transcript_id = transcript_id
        if participation_score:
            metrics.participation_score = participation_score
        if internal_cohesion:
            metrics.interal_cohesion = internal_cohesion
        if responsivity:
            metrics.responsivity = responsivity
        if social_impact:
            metrics.social_impact = social_impact
        if newness:
            metrics.newness = newness
        if communication_density:
            metrics.communcation_density = communication_density
        db.session.commit()
        return(metrics)

    return None

def delete_speaker_transcript_metrics(id = None, speaker_id = None, transcript_id = None):
    if id:
        db.session.query(SpeakerTranscriptMetrics).filter(SpeakerTranscriptMetrics.id == id).delete(synchronize_session='fetch')
    if speaker_id:
        if transcript_id:
            db.session.query(SpeakerTranscriptMetrics).filter(SpeakerTranscriptMetrics.speaker_id == speaker_id)\
              .filter(SpeakerTranscriptMetrics.transcript_id == transcript_id)\
                .delete(synchronize_session='fetch')
        else:
            db.session.query(SpeakerTranscriptMetrics).filter(SpeakerTranscriptMetrics.speaker_id == speaker_id)\
              .delete(synchronize_session='fetch')
    else:
        db.session.query(SpeakerTranscriptMetrics).filter(SpeakerTranscriptMetrics.transcript_id == transcript_id)\
          .delete(synchronize_session='fetch')
    db.session.commit()
    return True

# -------------------------
# Topic Models
# -------------------------

def get_topic_models(owner_id = None, id = None, name = None):
  query = db.session.query(TopicModel)
  if owner_id != None:
      query = query.filter(TopicModel.owner_id == owner_id)
  if id != None:
      return query.filter(TopicModel.id == id).first()
  if name != None:
      return query.filter(TopicModel.name == name).first()
  return query.all()


def add_topic_model(user_id, name, summary):
  topic_model = TopicModel(user_id, name, summary)
  db.session.add(topic_model)
  db.session.commit()
  return topic_model

def update_topic_model(topic_model_id, name=None, summary=None):
    topic_model = get_topic_models(id=topic_model_id)
    if topic_model:
        if name:
            topic_model.name = name
        if summary:
            topic_model.summary = summary
        db.session.commit()
        return topic_model
    return None

def delete_topic_model(topic_model_id):
  db.session.query(TopicModel).filter(TopicModel.id == topic_model_id).delete(synchronize_session='fetch')
  db.session.commit()
  return True

# -------------------------
# Keyword (Session keywords)
# -------------------------

def add_session_keyword(session_id, keyword):
    keyword = Keyword(session_id, keyword)
    db.session.add(keyword)
    db.session.commit()
    return keyword

def bulk_add_session_keyword(session_id, keywords):
    result = []
    for keyword in keywords:
        keyword = Keyword(session_id, keyword)
        db.session.add(keyword)
        result.append(keyword)
    db.session.commit()
    return result

def get_session_keywords(session_id):
    return db.session.query(Keyword).filter(Keyword.session_id == session_id).all()

# -------------------------
# KeywordUsage
# -------------------------

def add_keyword_usage(transcript_id, word, keyword, similarity):
    keyword = KeywordUsage(transcript_id, word, keyword, similarity)
    db.session.add(keyword)
    db.session.commit()
    return keyword

def get_keyword_usages(session_id=None, session_device_id=None, start_time=0, end_time=-1):
    query = db.session.query(KeywordUsage).\
        filter(Transcript.id == KeywordUsage.transcript_id)
    if session_id != None:
        query = query.filter(Transcript.id == KeywordUsage.transcript_id).\
            filter(Transcript.session_device_id == SessionDevice.id).\
            filter(SessionDevice.session_id == session_id)
    if session_device_id:
        query = query.filter(Transcript.session_device_id == session_device_id)
    if start_time > 0:
        query = query.filter(Transcript.start_time >= start_time)
    if end_time != -1 and end_time > start_time:
        query = query.filter(Transcript.start_time < end_time)
    return query.all()

def get_transcript_keyword_usages(transcript_id):
    return db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id == transcript_id)


# -------------------------
# KeywordLists
# -------------------------

def get_keyword_lists(id=None, name=None, owner_id=None):
    query = db.session.query(KeywordList)
    if owner_id != None:
        query = query.filter(KeywordList.owner_id == owner_id)
    if id != None:
        return query.filter(KeywordList.id == id).first()
    if name != None:
        return query.filter(KeywordList.name == name).first()
    return query.all()

def add_keyword_list(user_id):
    keyword_list = KeywordList(user_id)
    db.session.add(keyword_list)
    db.session.commit()
    return keyword_list

def update_keyword_list(keyword_list_id, name=None, keywords=None):
    keyword_list = get_keyword_lists(id=keyword_list_id)
    if keyword_list:
        if name != None:
            keyword_list.name = name
        if keywords != None:
            db.session.query(KeywordListItem).filter(KeywordListItem.keyword_list_id == keyword_list_id).delete()
            for keyword in keywords:
                add_keyword_list_item(keyword_list_id, keyword)
        db.session.commit()
        return keyword_list
    return None

def delete_keyword_list(keyword_list_id):
    db.session.query(KeywordListItem).filter(KeywordListItem.keyword_list_id == keyword_list_id).delete(synchronize_session='fetch')
    db.session.query(KeywordList).filter(KeywordList.id == keyword_list_id).delete(synchronize_session='fetch')
    db.session.commit()
    return True

# -------------------------
# KeywordListItems
# -------------------------

def get_keyword_list_item(keyword_list_id, keyword):
    return db.session.query(KeywordListItem).filter(and_(KeywordListItem.keyword_list_id == keyword_list_id, KeywordListItem.keyword == keyword)).first()

def get_keyword_list_items(keyword_list_id, owner_id=None):
    query = db.session.query(KeywordListItem).filter(KeywordListItem.keyword_list_id == keyword_list_id)
    if owner_id != None:
        query = query.filter(KeywordListItem.keyword_list_id == KeywordList.id).filter(KeywordList.owner_id == owner_id)
    return query.all()

def add_keyword_list_item(keyword_list_id, keyword):
    duplicate_keyword = get_keyword_list_item(keyword_list_id, keyword)
    if duplicate_keyword:
        return None
    else:
        keyword = KeywordListItem(keyword_list_id, keyword)
        db.session.add(keyword)
        db.session.commit()
        return keyword

def delete_keyword_list_item(keyword_list_id, keyword):
    keyword = db.session.query(KeywordListItem).filter(and_(KeywordListItem.keyword_list_id == keyword_list_id, KeywordListItem.keyword == keyword)).first()
    if keyword:
        db.session.delete(keyword)
        db.session.commit()
        return True
    return False

# -------------------------
# Devices
# -------------------------

def get_devices(id=None, ids=None, ip=None, mac_addr=None, archived=None, connected=None, in_use=None, is_pod=None):
    query = db.session.query(Device)
    if is_pod != None:
        query = query.filter(Device.is_pod == is_pod)
    if connected != None:
        query = query.filter(Device.connected == connected)
    if archived != None:
        query = query.filter(Device.archived == archived)
    if in_use != None:
        device_ids_in_session = [Device.id for Device in get_devices_in_session()]
        if in_use:
            query = query.filter(Device.id.in_(device_ids_in_session))
        else:
            query = query.filter(Device.id.notin_(device_ids_in_session))
    if ids != None:
        query = query.filter(Device.id.in_(ids))
    if ip != None:
        return query.filter(Device.ip_address == ip).first()
    if id != None:
        return query.filter(Device.id == id).first()
    if mac_addr != None:
        return query.filter(Device.mac_address == mac_addr).first()
    return query.all()

def get_device_active_session(device_id):
    return db.session.query(Session).\
        filter(Session.end_date == None).\
        filter(Session.id == SessionDevice.session_id).\
        filter(SessionDevice.device_id == device_id).first()

def get_device_active_session_device(device_id):
    return db.session.query(SessionDevice).\
        filter(Session.end_date == None).\
        filter(Session.id == SessionDevice.session_id).\
        filter(SessionDevice.removed == False).\
        filter(SessionDevice.device_id == device_id).first()

# Used for adding pods.
# Returns the added device, and a boolean indicating if the pod is new to the db.
def add_pod(mac_address):
    duplicate_pod = get_devices(mac_addr=mac_address)
    if duplicate_pod and not duplicate_pod.archived:
        return False, duplicate_pod
    elif duplicate_pod and duplicate_pod.archived:
        duplicate_pod.name = None
        duplicate_pod.archived = False
        db.session.commit()
        return True, duplicate_pod
    else:
        pod = Device(mac_address=mac_address, is_pod=True)
        db.session.add(pod)
        db.session.commit()
        return True, pod

def delete_device(device_id, full_delete=False):
    device = get_devices(id=device_id)
    if device:
        if not full_delete:
            device.archived = True
            db.session.commit()
        else:
            db.session.delete(device)
            db.session.commit()
        return True
    return False

def edit_device(deivce_id, name=None, connected=None):
    device = get_devices(id=deivce_id)
    if device:
        db_change = False
        if name != None and name != device.name:
            device.name = name
            db_change = True
        if connected != None and connected != device.connected:
            device.connected = connected
            db_change = True
        if db_change:
            db.session.commit()
    return device

def set_device_connected(device_id, connected):
    device = get_devices(id=device_id)
    device.connected = connected
    db.session.commit()

def get_devices_in_session():
    return db.session.query(Device).\
        filter(Device.id == SessionDevice.device_id).\
        filter(SessionDevice.connected == True).all()

def verify_devices_exist(device_ids):
    device_matches = db.session.query(Device.id).\
        filter(Device.id.in_(device_ids)).all()
    return len(device_matches) == len(device_ids)

def verify_devices_available(device_ids):
    devices_in_session = db.session.query(Device.id).\
        filter(Device.id.in_(device_ids)).\
        filter(Device.id == SessionDevice.device_id).\
        filter(Session.id == SessionDevice.session_id).\
        filter(Session.end_date == None).all()
    return len(devices_in_session) == 0

# -------------------------
# Sessions
# -------------------------

def get_sessions(id=None, owner_id=None, active=None, folder_ids=None, passcode=None, first=False):
    query = db.session.query(Session).order_by(Session.creation_date.desc())
    if owner_id != None:
        query = query.filter(Session.owner_id == owner_id)
    if active == True:
        query = query.filter(Session.end_date == None)
    if active == False:
        query = query.filter(Session.end_date != None)
    if passcode != None:
        query = query.filter(Session.passcode == passcode)
    if folder_ids != None:
        query = query.filter(Session.folder.in_(folder_ids))
    if id != None:
        return query.filter(Session.id == id).first()
    if first:
        return query.first()
    return query.all()

def create_session(user_id, keyword_list_id, topic_model_id, name="Unnamed", folder=None):
    # TODO get the topic model from the db and somehow add it to the discussion.
    session = Session(user_id, name, folder, topic_model_id)
    db.session.add(session)
    keyword_list_items = get_keyword_list_items(keyword_list_id, owner_id=user_id)
    keywords = []
    for keyword_list_item in keyword_list_items:
        keyword = Keyword(session.id, keyword_list_item.keyword)
        keywords.append(keyword)
        db.session.add(keyword)
    db.session.commit()
    return session, keywords

def delete_session(session_id):
    session_to_delete = get_sessions(id=session_id, active=True)
    if session_to_delete:
        return False
    
    sub_query = db.session.query(Transcript.id).\
        filter(Transcript.session_device_id == SessionDevice.id).\
        filter(SessionDevice.session_id == session_id).subquery()
        
    db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id.in_(sub_query)).delete(synchronize_session='fetch')
    db.session.query(Keyword).filter(Keyword.session_id == session_id).delete()
    db.session.query(Transcript).filter(Transcript.id.in_(sub_query)).delete(synchronize_session='fetch')
    db.session.query(SessionDevice).filter(SessionDevice.session_id == session_id).delete()
    db.session.query(Session).filter(Session.id == session_id).delete()
    db.session.commit()
    return True

def update_session(session_id, name=None, folder_id=None):
    session = get_sessions(id=session_id)
    if session:
        db_change = False
        if name and name != session.name:
            session.name = name
            db_change = True
        if folder_id:
            if folder_id == -1:
                session.folder = None
            else:
                session.folder = folder_id
            db_change = True
        if db_change:
            db.session.commit()
        return session
    return None

def generate_session_passcode(session_id):
    session = get_sessions(id=session_id)
    collision = True
    while collision:
        characters = re.sub('[AEIOU]', '', string.ascii_uppercase + string.digits)
        passcode = ''.join(random.choice(characters) for _ in range(4))
        sessions = get_sessions(active=True, passcode=passcode)
        if not sessions:
            collision = False
    session.passcode = passcode
    db.session.commit()
    return session

# -------------------------
# SessionDevice
# -------------------------

def get_session_devices(id=None, session_id=None, device_id=None, name=None, processing_key=None, connected=None, in_session=None, first=None):
    query = db.session.query(SessionDevice)
    if session_id != None:
        query = query.filter(SessionDevice.session_id == session_id)
    if device_id != None:
        query = query.filter(SessionDevice.device_id == device_id)
    if in_session != None:
        query = query.filter(SessionDevice.session_id == Session.id)
        if in_session:
            query = query.filter(Session.end_date == None)
        else:
            query = query.filter(Session.end_date != None)
    if name != None:
        query = query.filter(SessionDevice.name == name)
    if connected != None:
        query = query.filter(SessionDevice.connected == connected)
    if processing_key != None:
        return query.filter(SessionDevice.processing_key == processing_key).first()
    if id != None:
        return query.filter(SessionDevice.id == id).first()
    if first != None:
        return query.first()
    return query.all()

def set_session_device_status(session_device_id, status):
    session_device = get_session_devices(id=session_device_id)
    if session_device and session_device != status:
        session_device.connected = status
        db.session.commit()
        return True
    return False

def delete_session_device(session_device_id):
    db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id == Transcript.id).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.query(Transcript).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.query(SessionDevice).filter(SessionDevice.id == session_device_id).delete()
    db.session.commit()
    return True

def create_byod_session_device(passcode, name, collaborators):
    session = get_sessions(active=True, passcode=passcode, first=True)
    speakers = []
    if not session:
        return False, 'Session not found.', speakers
    duplicate = get_session_devices(session_id=session.id, name=name, first=True)
    if duplicate:
        if duplicate.connected: # User signed into a device already in use.
            return False, "Name already in use.", speakers
        else: # User signed back into existing device.
            duplicate.removed = False
            db.session.commit()
            return True, duplicate, get_speakers(session_device_id=duplicate.id)
    else: # New session device.
        session_device = SessionDevice(session.id, None, name)
        db.session.add(session_device)
        db.session.commit()
        session_device.create_key()
        db.session.commit()
        logging.info("Collaborators: {}".format(collaborators))
        for i in range(0, collaborators):
          speaker = Speaker(session_device.id,"")
          speakers.append(speaker)
          db.session.add(speaker)
          db.session.commit()
        return True, session_device, speakers

def create_session_device(session_id, name):
    session = get_sessions(id=session_id, active=True)
    if not session:
        return False, 'Session not found.'
    session_device = SessionDevice(session.id, None, name)
    db.session.add(session_device)
    db.session.commit()
    session_device.create_key()
    db.session.commit()
    return True, session_device

def create_pod_session_device(session_id, device_id):
    session = get_sessions(id=session_id, active=True)
    if not session:
        return False, 'Session not found.'
    pod = get_devices(id=device_id, connected=True, in_use=False, is_pod=True)
    if not pod:
        return False, 'Pod not found or is not available.'
    session_devices = get_session_devices(session_id=session_id, device_id=device_id)
    if session_devices:
        session_device = session_devices[0]
        if session_device.connected:
            return False, 'Device already added.'
        else:
            session_device.create_key()
            session_device.removed = False
            db.session.commit()
            return True, session_device
    session_device = SessionDevice(session.id, device_id, pod.get_name())
    db.session.add(session_device)
    db.session.commit()
    session_device.create_key()
    db.session.commit()
    return True, session_device

def setEmbeddingsFile(processing_key, embeddings):
    session_device = get_session_devices(processing_key=processing_key)
    session_device.embeddings = embeddings
    db.session.commit()
    return True




# -------------------------
# Transcript
# -------------------------

def add_transcript(session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id ,tag, speaker_id):
    transcript = Transcript(session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, tag, speaker_id)
    db.session.add(transcript)
    db.session.commit()
    return transcript

def set_speaker_tag(transcript, tag):
    transcript.speaker_tag = tag
    db.session.commit()
    return True

def get_transcripts(session_id=None, session_device_id=None, start_time=0, end_time=-1, speaker_id = -1):
    query = db.session.query(Transcript)
    if session_id != None:
        query = query.filter(SessionDevice.session_id == session_id)
    if session_device_id != None:
        query = query.filter(Transcript.session_device_id == session_device_id)
    if start_time > 0:
        query = query.filter(Transcript.start_time >= start_time)
    if end_time != -1 and end_time > start_time:
        query = query.filter(Transcript.start_time < end_time)
    if speaker_id != -1:
        query = query.filter(Transcript.speaker_id == speaker_id)
    return query.all()

def delete_device_transcripts(session_device_id):
    db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id == Transcript.id).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.query(Transcript).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.commit()

# -------------------------
# User
# -------------------------

def get_users(id=None, email=None, roles=None):
    query = db.session.query(User)
    if roles != None:
        query = query.filter(User.role.in_(roles))
    if id != None:
        return query.filter(User.id == id).first()
    if email != None:
        return query.filter(User.email == email).first()
    return query.all()

def add_user(email, role='user', password=None):
    matched_user = get_users(email=email)
    if matched_user:
        return False, "User already exists."
    user = User(email, role, password=password)
    db.session.add(user)
    db.session.commit()
    return True, user

def delete_user(id):
    user = get_users(id=id)
    if user:
        delete_api_client(user.id)
        keywordListItemSubQuery = db.session.query(KeywordList.id).filter(KeywordList.owner_id == id).subquery()
        transcriptSubQuery = db.session.query(Transcript.id).filter(Transcript.session_device_id == SessionDevice.id).filter(SessionDevice.session_id == Session.id).filter(Session.owner_id == id).subquery()
        sessionSubQuery = db.session.query(Session.id).filter(Session.owner_id == id).subquery()
        db.session.query(KeywordListItem).filter(KeywordListItem.keyword_list_id.in_(keywordListItemSubQuery)).delete(synchronize_session='fetch')
        db.session.query(KeywordList).filter(KeywordList.owner_id == id).delete()
        db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id.in_(transcriptSubQuery)).delete(synchronize_session='fetch')
        db.session.query(Transcript).filter(Transcript.id.in_(transcriptSubQuery)).delete(synchronize_session='fetch')
        db.session.query(Keyword).filter(Keyword.session_id.in_(sessionSubQuery)).delete(synchronize_session='fetch')
        db.session.query(SessionDevice).filter(SessionDevice.session_id.in_(sessionSubQuery)).delete(synchronize_session='fetch')
        db.session.query(Session).filter(Session.owner_id == id).delete()
        folder_ids = [folder.id for folder in db.session.query(Folder).filter(Folder.owner_id == id).all()]
        _delete_folder_bulk(folder_ids)
        db.session.delete(user)
        db.session.commit()
        return True
    else:
        return False

def update_user(user_id, data):
    user = get_users(id=user_id)
    if user:
        if data.get('role', None) in ['user', 'admin', 'super']:
            user.role = data['role']
        if data.get('locked', None) in [True, False]:
            user.locked = data['locked']
    db.session.commit()
    return user

# -------------------------
# API Client
# -------------------------

def get_api_clients(client_id=None, user_id=None):
    query = db.session.query(APIClient)
    if user_id != None:
        query = query.filter(APIClient.user_id == user_id)
    if client_id != None:
        return query.filter(APIClient.client_id == client_id).first()
    return query.all()

def create_api_client(user_id):
    delete_api_client(user_id=user_id)
    api_client = APIClient(user_id)
    client_secret = api_client.generate_secret()
    db.session.add(api_client)
    db.session.commit()
    return api_client, client_secret

def delete_api_client(user_id=None, client_id=None):
    if user_id != None:
        existing_clients = get_api_clients(user_id=user_id)
        if existing_clients:
            for client in existing_clients:
                db.session.delete(client)
            db.session.commit()
    elif client_id != None:
        existing_client = get_api_clients(client_id=client_id)
        if existing_client:
            db.session.delete(existing_client)
            db.session.commit()

# -------------------------
# Folders
# -------------------------

def get_folders(id=None, owner_id=None, parent=None, first=False):
    query = db.session.query(Folder)
    if id != None:
        query = query.filter(Folder.id == id)
    if owner_id != None:
        query = query.filter(Folder.owner_id == owner_id)
    if parent != None:
        query = query.filter(Folder.parent == parent)
    if first:
        return query.first()
    return query.all()

def add_folder(owner_id, name=None, parent=None):
    folder = Folder(owner_id=owner_id, name=name, parent=parent)
    db.session.add(folder)
    db.session.commit()
    return folder

def update_folder(folder_id, name=None, parent=None):
    folder = db.session.query(Folder).filter(Folder.id == folder_id).first()
    if name != None:
        folder.name = name
    # -1 means root folder, none means no change.
    if parent != None:
        if parent == -1:
            folder.parent = None
        else:
            folder.parent = parent
    db.session.commit()
    return folder

def is_child_folder(parent_id=None, child_id=None):
    parent_folder_dependant_ids = [session.id for session in get_dependents(parent_id)]
    return child_id in parent_folder_dependant_ids

def delete_folder(folder_id):
    passed_in_folder = get_folders(id=folder_id, first=True)
    folders_to_delete = get_dependents(folder_id)
    folders_to_delete.append(passed_in_folder)

    folder_ids = [folder.id for folder in folders_to_delete]
    sessions_to_delete = get_sessions(folder_ids=folder_ids)
    if len([session for session in sessions_to_delete if session.end_date == None]) > 0:
        return False, 'Cannot delete folder that contains an active discussion.'

    for session in sessions_to_delete:
        delete_session(session.id)
    _delete_folder_bulk(folder_ids)
    return True, 'Folder deleted successfully.'

def _delete_folder_bulk(folder_ids):
    db.session.query(Folder).filter(Folder.id.in_(folder_ids)).update({Folder.parent: None}, synchronize_session='fetch')
    db.session.commit()
    db.session.query(Folder).filter(Folder.id.in_(folder_ids)).delete(synchronize_session='fetch')
    db.session.commit()

def get_dependents(folder_id = None):
    dependents = []
    children = []
    current_children = get_folders(parent=folder_id)
    for child in current_children:
        children.insert(0, child)
    while children:
        current_child = children.pop(0)
        dependents.insert(0, current_child)
        folders = get_folders(parent=current_child.id)
        for folder in folders:
            children.insert(0,folder)
    return dependents
