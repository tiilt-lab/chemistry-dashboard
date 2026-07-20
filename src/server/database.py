from app import db
import re
from sqlalchemy import and_, desc
from sqlalchemy.sql.expression import func
from datetime import datetime
import random
import passcode_words
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
from tables.student import Student
from tables.api_client import APIClient
from tables.folder import Folder
from tables.topic_model import TopicModel
from tables.speaker import Speaker
from tables.speaker_transcript_metrics import SpeakerTranscriptMetrics
from tables.speaker_video_metrics import SpeakerVideoMetrics
from tables.llm_feedback_report import LLMFeedbackReport
from tables.llm_question_answer import LLMQuestionAnswer
from tables.rater import Rater
from tables.session_synthesized_report import SessionSynthesizedReport
from tables.rating import Rating
from tables.survey_response import SurveyResponse

# Saves changes made to database (models)
def save_changes():
    db.session.commit()

def close_session():
    db.session.remove()

# -------------------------
# Speakers
# -------------------------

def get_speakers(session_id=None, session_device_id=None, id = None):
    query = db.session.query(Speaker)
    if session_id != None:
        query = query.join(SessionDevice).filter(SessionDevice.session_id == session_id)
    if session_device_id != None:
        query = query.filter(Speaker.session_device_id == session_device_id)    
    if id != None:
        return query.filter(Speaker.id == id).first()
    
    return query.all()

def get_speaker_tags(session_device_id=None):
    query = db.session.query(Transcript).filter(session_device_id=session_device_id).distinct(Transcript.speaker_tag)
    return query.count()

def update_speaker(speaker_id, alias = None):
    speaker = get_speakers(id = speaker_id)
    if speaker:
        if alias:
            speaker.alias = alias
        db.session.commit()
        return speaker
    return None

# Roster with participation stats. A student is linked to a session when a
# speaker in it carries their username as alias (the fingerprint-enrollment
# flow sets this). owner_id=None -> all students, zero-session ones included
# (admin view); owner_id set -> only students seen in that user's sessions,
# with stats scoped to those sessions.
def get_students_overview(owner_id=None):
    query = db.session.query(
        Student,
        func.count(func.distinct(Session.id)),
        func.max(Session.creation_date),
    ).outerjoin(Speaker, Speaker.alias == Student.username) \
     .outerjoin(SessionDevice, Speaker.session_device_id == SessionDevice.id) \
     .outerjoin(Session, SessionDevice.session_id == Session.id)
    if owner_id is not None:
        # Filtering on the joined table makes this effectively an inner join:
        # exactly the "only their students" semantics we want.
        query = query.filter(Session.owner_id == owner_id)
    query = query.group_by(Student.id)
    return query.all()

# Every (session, group) a student appeared in, newest first; owner_id
# scopes to that user's sessions (same linkage as get_students_overview).
def get_student_activity(username, owner_id=None):
    query = db.session.query(Session, SessionDevice) \
        .join(SessionDevice, SessionDevice.session_id == Session.id) \
        .join(Speaker, Speaker.session_device_id == SessionDevice.id) \
        .filter(Speaker.alias == username)
    if owner_id is not None:
        query = query.filter(Session.owner_id == owner_id)
    query = query.distinct().order_by(Session.creation_date.desc())
    return query.all()

def get_student_llm_report_count(username, owner_id=None):
    query = db.session.query(func.count(LLMFeedbackReport.id)) \
        .filter(LLMFeedbackReport.speaker_username == username)
    if owner_id is not None:
        query = query.join(Session, LLMFeedbackReport.session_id == Session.id) \
            .filter(Session.owner_id == owner_id)
    return query.scalar() or 0

def create_speaker(session_device_id, alias=''):
    session_device = get_session_devices(id=session_device_id)
    if not session_device:
        return None
    if not alias:
        # Friendly per-device default ("Speaker 3"), not the global row id.
        existing = get_speakers(session_device_id=session_device_id)
        alias = 'Speaker {0}'.format(len(existing) + 1)
    speaker = Speaker(session_device_id, alias)
    db.session.add(speaker)
    db.session.commit()
    return speaker

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
    if session_id != None:
        query = query.join(Transcript, SpeakerTranscriptMetrics.transcript_id == Transcript.id) \
                     .join(SessionDevice, Transcript.session_device_id == SessionDevice.id) \
                     .filter(SessionDevice.session_id == session_id)
    return query.all()

def add_speaker_transcript_metrics(speaker_id, transcript_id, participation_score, internal_cohesion, responsivity, social_impact, newness, communication_density):
    metrics = SpeakerTranscriptMetrics(speaker_id, transcript_id, participation_score, internal_cohesion, responsivity, social_impact, newness, communication_density)
    # try:
    db.session.add(metrics)
    db.session.commit()
    # finally:
    #     close_session()
    return metrics

# -------------------------
# Video Metrics
# -------------------------

def get_speaker_video_metrics(id = None, student_username=None, session_id=None, session_device_id=None):
    query = db.session.query(SpeakerVideoMetrics).order_by(SpeakerVideoMetrics.time_stamp.asc())
    if session_id != None:
        query = query.join(SessionDevice).filter(SessionDevice.session_id == session_id)
    if id != None:
        return query.filter(SpeakerVideoMetrics.id == id).first()
    if student_username != None:
        query = query.filter(SpeakerVideoMetrics.student_username == student_username)
    if session_device_id != None:
        query = query.filter(SpeakerVideoMetrics.session_device_id == session_device_id)
    return query.all()

def get_speaker_video_metrics_by_session_alias(session_id=None, student_username=None,device_id=None):
    query = db.session.query(SpeakerVideoMetrics).order_by(SpeakerVideoMetrics.time_stamp.asc()) 
    if session_id != None:
        query = query.join(SessionDevice).filter(SpeakerVideoMetrics.session_device_id == SessionDevice.id)
        query = query.filter(SessionDevice.session_id == session_id) 

    if student_username != None:
        query = query.filter(SpeakerVideoMetrics.student_username == student_username)

    if device_id != None:
        query = query.filter(SpeakerVideoMetrics.session_device_id == device_id)

    return query.all()

def add_speaker_video_metrics(session_device_id,student_username, time_stamp, facial_emotion,attention_level,object_on_focus):
    metrics = SpeakerVideoMetrics(session_device_id,student_username, time_stamp, facial_emotion,attention_level,object_on_focus)
    # try:
    db.session.add(metrics)
    db.session.commit()
    # finally:
    #     close_session()
    return metrics

# -------------------------
# Get Speaker, Video and Transcript Metrics by session  
#-------------------------
#  transcript_id=None
def get_all_transcript_metrics_by_session(id = None, student_username=None, session_id=None, session_device_id=None, start_time=0, end_time=-1, speaker_id = -1):
    query = db.session.query(Transcript,SpeakerTranscriptMetrics)
    query = query.join(SpeakerTranscriptMetrics).filter((Transcript.id == SpeakerTranscriptMetrics.transcript_id) &
                                                        (Transcript.speaker_id == SpeakerTranscriptMetrics.speaker_id))

    if session_device_id != None:
        query = query.filter(Transcript.session_device_id == session_device_id) 

    if speaker_id != -1:
        query = query.filter(Transcript.speaker_id == speaker_id)
    else:        
        query = query.filter(Transcript.speaker_id != -1)
        query = query.distinct().order_by(Transcript.speaker_tag.asc())
    query = query.order_by(Transcript.start_time.asc())
    return query.all()

def get_all_transcript_metrics_by_session_by_timeline(id = None, student_username=None, session_id=None, session_device_id=None):
    query = db.session.query(Transcript,SpeakerTranscriptMetrics)
    query = query.join(SpeakerTranscriptMetrics).filter((Transcript.id == SpeakerTranscriptMetrics.transcript_id) &
                                                        (Transcript.speaker_id == SpeakerTranscriptMetrics.speaker_id))

    if session_device_id != None:
        query = query.filter(Transcript.session_device_id == session_device_id) 
     
    query = query.filter(Transcript.speaker_id != -1)
    query = query.order_by(Transcript.start_time.asc())
    return query.all()

def get_all_metrics_by_session(id = None, student_username=None, session_id=None, session_device_id=None, start_time=0, end_time=-1, speaker_id = -1):
    query = db.session.query(Transcript,SpeakerTranscriptMetrics,SpeakerVideoMetrics)
    query = query.join(SpeakerTranscriptMetrics, (Transcript.id == SpeakerTranscriptMetrics.transcript_id) &
                                                        (Transcript.speaker_id == SpeakerTranscriptMetrics.speaker_id))
    query = query.join(SpeakerVideoMetrics,(Transcript.start_time == SpeakerVideoMetrics.time_stamp)&
                       (Transcript.speaker_tag == SpeakerVideoMetrics.student_username))

    if session_device_id != None:
        query = query.filter(Transcript.session_device_id == session_device_id) 

    query = query.distinct()
    query = query.order_by(Transcript.speaker_tag.asc(),Transcript.start_time.asc())
    return query.all()

def get_video_metrics_by_session(id = None, student_username=None, session_id=None, session_device_id=None, start_time=0, end_time=-1, speaker_id = -1):
    query = db.session.query(SpeakerVideoMetrics)

    if session_device_id != None:
        query = query.filter(SpeakerVideoMetrics.session_device_id == session_device_id) 
    query = query.distinct().order_by(SpeakerVideoMetrics.student_username.asc())
    query = query.order_by(SpeakerVideoMetrics.time_stamp.asc())
    return query.all()
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

def delete_topic_model(topic_model_id):
  db.session.query(TopicModel).filter(TopicModel.id == topic_model_id).delete(synchronize_session='fetch')
  db.session.commit()
  return True

# -------------------------
# Keyword (Session keywords)
# -------------------------

# -------------------------
# KeywordUsage
# -------------------------

def add_keyword_usage(transcript_id, word, keyword, similarity):
    keyword = KeywordUsage(transcript_id, word, keyword, similarity)
    # try:
    db.session.add(keyword)
    db.session.commit()
    # finally:
    #     close_session()   
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

def get_Session_by_alias(alias=None):
    query = db.session.query(Session)
    query = query.join(SessionDevice).filter(SessionDevice.session_id == Session.id)
    query = query.join(Speaker).filter(Speaker.session_device_id == SessionDevice.id)

    if alias != None:
        query = query.filter(Speaker.alias == alias) 

    query = query.distinct().order_by(Session.creation_date.desc())
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

    sub_query2 = db.session.query(SpeakerVideoMetrics.id).\
        filter(SpeakerVideoMetrics.session_device_id == SessionDevice.id).\
        filter(SessionDevice.session_id == session_id).subquery()
        
    db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id.in_(sub_query)).delete(synchronize_session='fetch')
    db.session.query(Keyword).filter(Keyword.session_id == session_id).delete()
    db.session.query(Transcript).filter(Transcript.id.in_(sub_query)).delete(synchronize_session='fetch')
    db.session.query(SpeakerVideoMetrics).filter(SpeakerVideoMetrics.id.in_(sub_query2)).delete(synchronize_session='fetch')
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

def set_session_analysis_config(session_id, owner_id, keyword_list_id=None, topic_model_id=None):
    # Keywords/topic model are analysis-time settings: the posthoc queue reads
    # the session's keywords fresh for every run, so they can be chosen or
    # changed after creation (pass -1 to clear).
    session = get_sessions(id=session_id)
    if not session:
        return None
    if keyword_list_id is not None:
        db.session.query(Keyword).filter(Keyword.session_id == session_id).delete()
        if keyword_list_id != -1:
            for keyword_list_item in get_keyword_list_items(keyword_list_id, owner_id=owner_id):
                db.session.add(Keyword(session.id, keyword_list_item.keyword))
    if topic_model_id is not None:
        session.topic_model_id = None if topic_model_id == -1 else topic_model_id
    db.session.commit()
    return session

def generate_session_passcode(session_id):
    # Memorable single-word passcodes (see passcode_words.py); falls back to
    # word+digits if every word is in use by an active session.
    session = get_sessions(id=session_id)
    passcode = None
    for _ in range(60):
        candidate = random.choice(passcode_words.WORDS)
        if not get_sessions(active=True, passcode=candidate):
            passcode = candidate
            break
    while passcode is None:
        candidate = random.choice(passcode_words.WORDS) + str(random.randint(10, 99))
        if not get_sessions(active=True, passcode=candidate):
            passcode = candidate
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

def get_Session_device_by_alias(session_id=None,alias=None):
    query = db.session.query(SessionDevice)
    query = query.join(Speaker).filter(Speaker.session_device_id == SessionDevice.id)
    if session_id!=None:
        query = query.filter(SessionDevice.session_id == session_id)
    if alias != None:
        query = query.filter(Speaker.alias == alias) 
    # query = query.filter(SessionDevice.connected == False)
    query = query.distinct()
    return query.all()


def delete_session_device(session_device_id):
    db.session.query(KeywordUsage).filter(KeywordUsage.transcript_id == Transcript.id).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.query(Transcript).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.query(SpeakerVideoMetrics).filter(SpeakerVideoMetrics.session_device_id == session_device_id).delete(synchronize_session='fetch')
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

# -------------------------
# Transcript
# -------------------------

def add_transcript(session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id ,tag, speaker_id, voice_features=None):
    transcript = Transcript(session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, tag, speaker_id, voice_features=voice_features)
    # try:
    db.session.add(transcript)
    db.session.commit()
    # finally:
    #     close_session()
    return transcript

def update_transcript_features_batch(session_device_id, updates):
    # Overwrite the five E&T feature values on existing transcript rows (used
    # by the post-hoc style recomputation). Rows are matched by id AND device
    # so a stray id can't touch another pod's data. Returns rows updated.
    keys = ('emotional_tone_value', 'analytic_thinking_value', 'clout_value',
            'authenticity_value', 'certainty_value')
    count = 0
    for update in updates:
        row = db.session.query(Transcript).filter(
            Transcript.id == update.get('id'),
            Transcript.session_device_id == session_device_id).first()
        if row is None:
            continue
        features = update.get('features') or {}
        for key in keys:
            value = features.get(key)
            if value is not None:
                setattr(row, key, int(round(float(value))))
        count += 1
    db.session.commit()
    return count


def set_speaker_tag(transcript, tag):
    transcript.speaker_tag = tag
    db.session.commit()
    return True

def get_transcripts(session_id=None, session_device_id=None, start_time=0, end_time=-1, speaker_id = -1):
    query = db.session.query(Transcript).order_by(Transcript.start_time.asc())
    if session_id != None:
        # Join is required: filtering on SessionDevice without it produces a
        # cartesian product (every transcript x every device in the session).
        query = query.join(SessionDevice, Transcript.session_device_id == SessionDevice.id)
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

def get_transcripts_by_session_alias(session_id=None, speaker_tag=None,device_id = None):
    query = db.session.query(Transcript).order_by(Transcript.start_time.asc()) 
    if session_id != None:
        query = query.join(SessionDevice).filter(Transcript.session_device_id == SessionDevice.id)
        query = query.filter(SessionDevice.session_id == session_id) 

    # Plain filters — the argless .join() this used to chain crashes on
    # SQLAlchemy 2 (join() requires a target) and never added anything.
    if speaker_tag != None:
        query = query.filter(Transcript.speaker_tag == speaker_tag)

    if device_id != None:
        query = query.filter(Transcript.session_device_id == device_id)

    return query.all()



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
# Rater
# -------------------------

def get_raters(id=None,sessionid=None,sessiondeviceid=None,speakerid=None,speakertag=None,raterid=None,type=None,evaluationcategory=None,completed=None):
    query = db.session.query(Rater)
    if id != None:
        return query.filter(Rater.id == id).first()
    if sessionid != None:
        query = query.filter(Rater.sessionid == sessionid)
    if sessiondeviceid != None:
        query = query.filter(Rater.sessiondeviceid == sessiondeviceid)
    if speakerid != None:
        query = query.filter(Rater.speakerid == speakerid)
    if speakertag != None:
        query = query.filter(Rater.speakertag == speakertag)  
    if raterid != None:
        query = query.filter(Rater.raterid == raterid)
    if type != None:
        query = query.filter(Rater.type == type)        
    if evaluationcategory != None:
        query = query.filter(Rater.evaluation_category == evaluationcategory)
    if completed != None:
        query = query.filter(Rater.completed == completed)    
    return query.all()

def add_rater(sessionid, sessiondeviceid, speakerid, speakertag, raterid, type,evaluationcategory):
    rater = Rater(sessionid, sessiondeviceid, speakerid, speakertag, raterid, type,evaluationcategory,0)
    db.session.add(rater)
    db.session.commit()
    return True, rater  

def update_rater(id,sessionid=None,sessiondeviceid=None,speakerid=None,speakertag=None,raterid=None,type=None,evaluationcategory=None,completed=None):
    rater = get_raters(id=id)
    if rater:
        db_change = False
        if sessionid:
            rater.sessionid = sessionid
            db_change = True
        if sessiondeviceid:
            rater.sessiondeviceid = sessiondeviceid
            db_change = True  
        if speakerid:
            rater.speakerid = speakerid
            db_change = True
        if speakertag:
            rater.speakertag = speakertag
            db_change = True
        if raterid:
            rater.raterid = raterid
            db_change = True
        if type:
            rater.type = type
            db_change = True  
        if evaluationcategory:
            rater.evaluation_category = evaluationcategory
            db_change = True  
        if completed:
            rater.completed = completed
            db_change = True      
        
        if db_change:
            db.session.commit()
        return True, rater
    return False, None

def delete_rater(id):
    rater = get_raters(id=id)
    if rater:
        db.session.delete(rater)
        db.session.commit()
        return rater
    else:
        return None

# -------------------------
# Rating
# -------------------------

def get_ratings(id=None,sessionid=None,sessiondeviceid=None,speakertag=None,raterid=None,evaluationcategory=None):
    query = db.session.query(Rating)
    if id != None:
        return query.filter(Rating.id == id).first()
    if sessionid != None:
        query = query.filter(Rating.sessionid == sessionid)
    if sessiondeviceid != None:
        query = query.filter(Rating.sessiondeviceid == sessiondeviceid)
    if speakertag != None:
        query = query.filter(Rating.speakertag == speakertag)  
    if raterid != None:
        query = query.filter(Rating.raterid == raterid)      
    if evaluationcategory != None:
        query = query.filter(Rating.evaluation_category == evaluationcategory)
    return query.all()

def add_rating(sessionid, sessiondeviceid, speakertag, raterid,evaluationcategory,response):
    rating = Rating(sessionid, sessiondeviceid, speakertag, raterid,evaluationcategory,response)
    db.session.add(rating)
    db.session.commit()
    return True, rating  

def update_rating(id,sessionid=None,sessiondeviceid=None,speakertag=None,raterid=None,evaluationcategory=None,response=None):
    rating = get_ratings(id=id)
    if rating:
        db_change = False
        if sessionid:
            rating.sessionid = sessionid
            db_change = True
        if sessiondeviceid:
            rating.sessiondeviceid = sessiondeviceid
            db_change = True  
        if speakertag:
            rating.speakertag = speakertag
            db_change = True
        if raterid:
            rating.raterid = raterid
            db_change = True 
        if evaluationcategory:
            rating.evaluation_category = evaluationcategory
            db_change = True  
        if response:
            rating.response = response
            db_change = True      
        
        if db_change:
            db.session.commit()
        return True, rating
    return False, None

# -------------------------
# Survey Response
# -------------------------

def get_survey_reponse(id=None,sessionid=None,sessiondeviceid=None,username=None):
    query = db.session.query(SurveyResponse)
    if id != None:
        return query.filter(SurveyResponse.id == id).first()
    if sessionid != None:
        query = query.filter(SurveyResponse.sessionid == sessionid)
    if sessiondeviceid != None:
        query = query.filter(SurveyResponse.sessiondeviceid == sessiondeviceid)
    if username != None:
        query = query.filter(SurveyResponse.username == username)  
    return query.all()

def add_survey_reponse(sessionid, sessiondeviceid, username,response):
    survey = SurveyResponse(sessionid, sessiondeviceid, username,response)
    db.session.add(survey)
    db.session.commit()
    return True, survey  

def update_survey_reponse(id,sessionid=None,sessiondeviceid=None,username=None,response=None):
    survey = get_survey_reponse(id=id)
    if survey:
        db_change = False
        if sessionid:
            survey.sessionid = sessionid
            db_change = True
        if sessiondeviceid:
            survey.sessiondeviceid = sessiondeviceid
            db_change = True  
        if username:
            survey.username = username
            db_change = True
        if response:
            survey.response = response
            db_change = True      
        
        if db_change:
            db.session.commit()
        return True, survey
    return False, None

# -------------------------
# Student
# -------------------------

def get_students(id=None, username=None):
    query = db.session.query(Student)
    if id != None:
        return query.filter(Student.id == id).first()
    if username != None:
        return query.filter(Student.username == username).first()
    return query.all()

def add_student(lastname, firstname, username):
    matched_student = get_students(username=username)
    if matched_student:
        return False, matched_student
    biometric_captured="no"
    student = Student(lastname, firstname, username,biometric_captured)
    db.session.add(student)
    db.session.commit()
    return True, student

def sync_student(lastname, firstname, username,biometric_captured):
    matched_student = get_students(username=username)
    if matched_student:
        return False, matched_student
    student = Student(lastname, firstname, username,biometric_captured)
    db.session.add(student)
    db.session.commit()
    return True, student

# Merge one student profile into another: every username-keyed reference
# (session speakers, video metrics, LLM reports/answers, survey responses)
# moves to the target, then the duplicate row is deleted. Returns per-table
# moved counts, or None if either id is missing or they're the same row.
def merge_students(duplicate_id, target_id):
    duplicate = get_students(id=duplicate_id)
    target = get_students(id=target_id)
    if not duplicate or not target or duplicate.id == target.id:
        return None
    moved = {}
    moved['speakers'] = db.session.query(Speaker) \
        .filter(Speaker.alias == duplicate.username) \
        .update({'alias': target.username})
    moved['video_metrics'] = db.session.query(SpeakerVideoMetrics) \
        .filter(SpeakerVideoMetrics.student_username == duplicate.username) \
        .update({'student_username': target.username})
    moved['llm_reports'] = db.session.query(LLMFeedbackReport) \
        .filter(LLMFeedbackReport.speaker_username == duplicate.username) \
        .update({'speaker_username': target.username})
    moved['llm_answers'] = db.session.query(LLMQuestionAnswer) \
        .filter(LLMQuestionAnswer.speaker_username == duplicate.username) \
        .update({'speaker_username': target.username})
    moved['surveys'] = db.session.query(SurveyResponse) \
        .filter(SurveyResponse.username == duplicate.username) \
        .update({'username': target.username})
    if duplicate.biometric_captured == 'yes' and target.biometric_captured != 'yes':
        target.biometric_captured = 'yes'
    moved['duplicate_username'] = duplicate.username
    db.session.delete(duplicate)
    db.session.commit()
    return moved

def delete_student(id):
    student = get_students(id=id)
    if student:
        db.session.delete(student)
        db.session.commit()
        return student
    else:
        return None


def update_student(id, lastname=None, firstname=None,biometric_captured=None):
    student = get_students(id=id)
    if student:
        if lastname:
            student.name = lastname
        if firstname:
            student.firstname = firstname
        if biometric_captured:
            student.biometric_captured = biometric_captured    
        db.session.commit()
        return True,student
    return False, None

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

# -------------------------
# LLM Data
# -------------------------

def get_speaker_session_device_llm_report(id=None,username=None, sessionId=None, sessionDeviceId = None):
    query = db.session.query(LLMFeedbackReport)
    if id != None:
        return query.filter(LLMFeedbackReport.id == id).first()
    if sessionId != None:
        query =query.filter(LLMFeedbackReport.session_id == sessionId)
    if sessionDeviceId != None:
        query =query.filter(LLMFeedbackReport.session_device_id == sessionDeviceId)
    if username != None:
        return query.filter(LLMFeedbackReport.speaker_username == username).first()
    return query.all()

def add_speaker_session_device_llm_report(username, sessionId, sessionDeviceId,feedback_analysis):
    matched_feedback_analysis = get_speaker_session_device_llm_report(username=username, sessionId=sessionId, sessionDeviceId = sessionDeviceId)
    if matched_feedback_analysis:
        return False, matched_feedback_analysis
    feedback = LLMFeedbackReport(sessionId, sessionDeviceId, username,feedback_analysis)
    db.session.add(feedback)
    db.session.commit()
    return True, feedback

def update_speaker_session_device_llm_report(id, username=None, sessionId=None, sessionDeviceId=None,feedback_analysis=None):
    feedback = get_speaker_session_device_llm_report(id=id)
    if feedback:
        db_change = False
        if sessionId:
            feedback.session_id = sessionId
            db_change = True
        if sessionDeviceId:
            feedback.session_device_id = sessionDeviceId
            db_change = True
        if username:
            feedback.speaker_username = username 
            db_change = True  
        if feedback_analysis:
            feedback.feedback_analysis = feedback_analysis 
            db_change = True   
        
        if db_change:
            db.session.commit()

        return True,feedback
    return False, None

def get_speaker_session_device_llm_question_answer(id=None,username=None, sessionId=None, sessionDeviceId = None,default_question_id=None):
    query = db.session.query(LLMQuestionAnswer)
    if id != None:
        return query.filter(LLMQuestionAnswer.id == id).first()
    if sessionId != None:
        query = query.filter(LLMQuestionAnswer.session_id == sessionId)
    if sessionDeviceId != None:
        query = query.filter(LLMQuestionAnswer.session_device_id == sessionDeviceId)
    if username != None:
        query = query.filter(LLMQuestionAnswer.speaker_username == username)
    if default_question_id != None:
        return query.filter(LLMQuestionAnswer.default_question_id == default_question_id).first() 
    return query.all()

def add_speaker_session_device_llm_question_answer(username, sessionId, sessionDeviceId,default_question_id,question,answer):
    matched_response = get_speaker_session_device_llm_question_answer(username=username, sessionId=sessionId, sessionDeviceId = sessionDeviceId,default_question_id=default_question_id)
    if matched_response:
        return False, matched_response
    response = LLMQuestionAnswer(sessionId, sessionDeviceId, username,default_question_id,question,answer)
    db.session.add(response)
    db.session.commit()
    return True, response

def update_speaker_session_device_llm_question_answer(id, username=None, sessionId=None, sessionDeviceId=None,default_question_id=None,question=None,answer=None):
    response = get_speaker_session_device_llm_question_answer(id=id)
    if response:
        db_change = False
        if sessionId:
            response.session_id = sessionId
            db_change = True
        if sessionDeviceId:
            response.session_device_id = sessionDeviceId
            db_change = True
        if username:
            response.speaker_username = username 
            db_change = True  
        if default_question_id:
            response.default_question_id = default_question_id 
            db_change = True 
        if question:
            response.question = question 
            db_change = True 
        if answer:
            response.answer = answer 
            db_change = True           
        
        if db_change:
            db.session.commit()

        return True,response
    return False, None


# -------------------------
# Session Synthesized Data for Reflective Dashboard
# -------------------------

def get_synthesized_feedback_report(id=None, sessionId=None, sessionDeviceId = None):
    query = db.session.query(SessionSynthesizedReport)
    if id != None:
        return query.filter(SessionSynthesizedReport.id == id).first()
    if sessionId != None:
        query =query.filter(SessionSynthesizedReport.session_id == sessionId)
    if sessionDeviceId != None:
        query =query.filter(SessionSynthesizedReport.session_device_id == sessionDeviceId)
    return query.all()

def add_synthesized_feedback_report(sessionId, sessionDeviceId,synthesized_feedback):
    matched_synthesized_feedback = get_synthesized_feedback_report(sessionId=sessionId, sessionDeviceId = sessionDeviceId)
    if matched_synthesized_feedback:
        return False, matched_synthesized_feedback
    feedback = SessionSynthesizedReport(sessionId, sessionDeviceId, synthesized_feedback)
    db.session.add(feedback)
    db.session.commit()
    return True, feedback

def update_synthesized_feedback_report(id, sessionId=None, sessionDeviceId=None,synthesized_feedback=None):
    feedback = get_synthesized_feedback_report(id=id)
    if feedback:
        db_change = False
        if sessionId:
            feedback.session_id = sessionId
            db_change = True
        if sessionDeviceId:
            feedback.session_device_id = sessionDeviceId
            db_change = True
        if synthesized_feedback:
            feedback.synthesized_feedback = synthesized_feedback 
            db_change = True   
        
        if db_change:
            db.session.commit()

        return True,feedback
    return False, None
   


def get_session_ids_with_video(owner_id=None):
    # One query returning the set of session ids that have any video metrics,
    # so the sessions list can flag video without a per-session query.
    query = db.session.query(SessionDevice.session_id) \
        .join(SpeakerVideoMetrics, SpeakerVideoMetrics.session_device_id == SessionDevice.id)
    if owner_id is not None:
        query = query.join(Session, SessionDevice.session_id == Session.id) \
            .filter(Session.owner_id == owner_id)
    return set(row[0] for row in query.distinct().all())


def get_session_ids_with_posthoc(owner_id=None):
    # Set of session ids where any device has had a post-hoc re-analysis run,
    # so the sessions list can flag it without a per-session query. Degrades to
    # empty if the posthoc_analyzed_date column has not been migrated in yet, so
    # the sessions list never breaks on an un-migrated database.
    try:
        query = db.session.query(SessionDevice.session_id) \
            .filter(SessionDevice.posthoc_analyzed_date.isnot(None))
        if owner_id is not None:
            query = query.join(Session, SessionDevice.session_id == Session.id) \
                .filter(Session.owner_id == owner_id)
        return set(row[0] for row in query.distinct().all())
    except Exception as e:
        logging.warning('posthoc flag query failed (migration pending?): %s', e)
        db.session.rollback()
        return set()


def get_session_device_counts(owner_id=None):
    # {session_id: pod_count} in one query, so the sessions list can show pod
    # counts without a per-session query (mirrors get_session_ids_with_video).
    query = db.session.query(SessionDevice.session_id, func.count(SessionDevice.id))
    if owner_id is not None:
        query = query.join(Session, SessionDevice.session_id == Session.id) \
            .filter(Session.owner_id == owner_id)
    query = query.group_by(SessionDevice.session_id)
    return {row[0]: row[1] for row in query.all()}


def get_pod_durations(session_id):
    # {session_device_id: duration_seconds} for one session. session_device has
    # no timestamps of its own, and transcript.start_time is offset from the
    # SESSION start (not the pod's own start), so a pod's duration is the span
    # of its speech activity: last-utterance-end minus first-utterance-start,
    # i.e. MAX(start_time + length) - MIN(start_time).
    rows = db.session.query(
        Transcript.session_device_id,
        func.max(Transcript.start_time + Transcript.length)
        - func.min(Transcript.start_time)) \
        .join(SessionDevice, Transcript.session_device_id == SessionDevice.id) \
        .filter(SessionDevice.session_id == session_id) \
        .group_by(Transcript.session_device_id).all()
    return {row[0]: int(row[1]) for row in rows if row[1] is not None}


def get_pod_speaker_counts(session_id):
    # {session_device_id: participant_count} for one session's pods.
    rows = db.session.query(Speaker.session_device_id, func.count(Speaker.id)) \
        .join(SessionDevice, Speaker.session_device_id == SessionDevice.id) \
        .filter(SessionDevice.session_id == session_id) \
        .group_by(Speaker.session_device_id).all()
    return {row[0]: row[1] for row in rows}


def get_session_participant_counts(owner_id=None):
    # {session_id: total participants across the session's pods}, one query, so
    # the sessions list can show participant totals (mirrors the video/posthoc
    # flag helpers).
    query = db.session.query(SessionDevice.session_id, func.count(Speaker.id)) \
        .join(Speaker, Speaker.session_device_id == SessionDevice.id)
    if owner_id is not None:
        query = query.join(Session, SessionDevice.session_id == Session.id) \
            .filter(Session.owner_id == owner_id)
    query = query.group_by(SessionDevice.session_id)
    return {row[0]: row[1] for row in query.all()}


def get_pod_video_presence(session_id):
    # Set of session_device_ids in a session that have any video metrics, so the
    # pod list can flag pods that captured no data at all.
    rows = db.session.query(SpeakerVideoMetrics.session_device_id) \
        .join(SessionDevice, SpeakerVideoMetrics.session_device_id == SessionDevice.id) \
        .filter(SessionDevice.session_id == session_id).distinct().all()
    return set(r[0] for r in rows)


def get_student_longitudinal(username):
    # A student's trajectory across every session they took part in: per-session
    # speaking share (transcript) + average attention (video), chronologically,
    # so the UI can show growth/engagement over a term.
    devices = db.session.query(
        SessionDevice.id, SessionDevice.session_id, Session.name, Session.creation_date) \
        .join(Speaker, Speaker.session_device_id == SessionDevice.id) \
        .join(Session, SessionDevice.session_id == Session.id) \
        .filter(Speaker.alias == username) \
        .order_by(Session.creation_date).all()
    out = []
    for did, sid, sname, sdate in devices:
        their_sec = db.session.query(func.sum(Transcript.length)).filter(
            Transcript.session_device_id == did,
            Transcript.speaker_tag == username).scalar() or 0
        total_sec = db.session.query(func.sum(Transcript.length)).filter(
            Transcript.session_device_id == did,
            Transcript.speaker_tag.isnot(None)).scalar() or 0
        avg_attn = db.session.query(func.avg(SpeakerVideoMetrics.attention_level)).filter(
            SpeakerVideoMetrics.session_device_id == did,
            SpeakerVideoMetrics.student_username == username).scalar()
        # Tier-1 countable metrics for THIS student in this session, so the
        # panel can trend more than talk time: questions asked and their
        # openness, computed from the same transcript rows the dynamics
        # panel uses.
        their_utts = db.session.query(
            Transcript.question, Transcript.transcript).filter(
            Transcript.session_device_id == did,
            Transcript.speaker_tag == username).all()
        from analytics import classify_question
        questions = sum(1 for q, _t in their_utts if q)
        open_qs = sum(1 for q, t in their_utts
                      if q and classify_question(t) == 'open')
        out.append({
            'session_id': sid,
            'session_name': sname,
            'date': str(sdate) if sdate else None,
            'speaking_share': round(their_sec / total_sec, 3) if total_sec else 0,
            'speaking_seconds': int(their_sec),
            'avg_attention': round(float(avg_attn), 2) if avg_attn is not None else None,
            'questions': questions,
            'open_questions': open_qs,
        })
    return out


def get_conversation_dynamics(session_device_id):
    # DB wrapper: fetch a pod's ordered diarized utterances, then compute.
    from analytics import compute_conversation_dynamics
    rows = db.session.query(
        Transcript.speaker_tag, Transcript.start_time, Transcript.length) \
        .filter(Transcript.session_device_id == session_device_id,
                Transcript.speaker_tag.isnot(None)) \
        .order_by(Transcript.start_time).all()
    return compute_conversation_dynamics(rows)


def get_talk_metrics(session_device_id):
    # Tier-1 talk metrics (equity timeline, silences, handoffs/interruptions,
    # questions & wait time). Unlike the dynamics network this keeps
    # unattributed utterances — hiding them would overstate equity.
    from analytics import compute_talk_metrics
    rows = db.session.query(
        Transcript.speaker_tag, Transcript.start_time, Transcript.length,
        Transcript.question, Transcript.transcript) \
        .filter(Transcript.session_device_id == session_device_id) \
        .order_by(Transcript.start_time).all()
    enrolled = [s.alias for s in get_speakers(session_device_id=session_device_id)
                if s.alias]
    return compute_talk_metrics(rows, enrolled=enrolled)


def get_pod_duration(session_device_id):
    # Single-pod activity span (same derivation as get_pod_durations).
    from sqlalchemy import text
    row = db.session.execute(text("""SELECT MAX(start_time + length) - MIN(start_time)
        FROM transcript WHERE session_device_id = :d"""), {"d": session_device_id}).scalar()
    return int(row) if row is not None else None


def delete_pod_analysis(session_device_id, scope='audio'):
    # Wipe a pod's previous analysis before a full re-run so results REPLACE
    # instead of accumulating (re-runs were stacking duplicate transcripts).
    from sqlalchemy import text
    if scope == 'video':
        db.session.execute(text("DELETE FROM speaker_video_metrics WHERE session_device_id=:d"), {"d": session_device_id})
    else:
        # keyword_usage has no ON DELETE CASCADE; children with CASCADE
        # (speaker_transcript_metrics, seven_cs_coded_segment) follow the parent.
        db.session.execute(text("""DELETE ku FROM keyword_usage ku
            JOIN transcript t ON ku.transcript_id = t.id
            WHERE t.session_device_id = :d"""), {"d": session_device_id})
        db.session.execute(text("DELETE FROM transcript WHERE session_device_id=:d"), {"d": session_device_id})
    db.session.commit()


def get_session_ids_for_devices(device_ids):
    # {session_id} owning any of the given session_device ids (for the
    # "analysis running" flag on the sessions list).
    if not device_ids:
        return set()
    rows = db.session.query(SessionDevice.session_id) \
        .filter(SessionDevice.id.in_(list(device_ids))).distinct().all()
    return {r[0] for r in rows}


def clear_session_device_posthoc(session_device_id):
    # Un-stamp a pod whose "completion" produced no output (e.g. the ASR
    # crashed): leaving the date set makes the failure look Analyzed and
    # excludes the pod from survey-based retries.
    device = get_session_devices(id=session_device_id)
    if device is None:
        return False
    device.posthoc_analyzed_date = None
    db.session.commit()
    return True


def mark_session_device_posthoc(session_device_id, models=None):
    device = get_session_devices(id=session_device_id)
    if device is None:
        return False
    device.posthoc_analyzed_date = datetime.utcnow()
    if models is not None:
        # Persist the per-run model provenance blob. Guard so a missing column
        # (pre-migration) or bad value never blocks the completion timestamp.
        try:
            import json as _json
            device.posthoc_models = _json.dumps(models)
        except Exception as e:
            logging.warning("Could not persist posthoc_models: %s", e)
    db.session.commit()
    return True
