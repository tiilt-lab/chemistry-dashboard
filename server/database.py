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
from tables.user import User
from tables.api_client import APIClient
from tables.folder import Folder
from tables.speaker import Speaker
from tables.speaker_transcript_metrics import SpeakerTranscriptMetrics
from tables.concept_session import ConceptSession
from tables.concept_node import ConceptNode
from tables.concept_edge import ConceptEdge
from tables.concept_cluster import ConceptCluster
from tables.cluster_node_mapping import cluster_node_mapping
from tables.seven_cs_analysis import SevenCsAnalysis
from tables.seven_cs_coded_segment import SevenCsCodedSegment
# Note: AgentConversation and AgentMessage are imported lazily in functions below

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

def create_session(user_id, keyword_list_id=None, topic_model_id=None, name="Unnamed", folder=None):
    # keyword_list_id and topic_model_id are deprecated but kept for API compatibility
    session = Session(user_id, name, folder, None)
    db.session.add(session)
    db.session.commit()
    return session, []  # Second element kept for API compatibility

def delete_session(session_id):
    session_to_delete = get_sessions(id=session_id, active=True)
    if session_to_delete:
        return False, "Cannot delete an active session"

    try:
        sub_query = db.session.query(Transcript.id).\
            filter(Transcript.session_device_id == SessionDevice.id).\
            filter(SessionDevice.session_id == session_id).subquery()

        # Get session devices for cleanup
        session_devices = db.session.query(SessionDevice).filter(SessionDevice.session_id == session_id).all()

        # Collect speaker aliases BEFORE deletion (for ChromaDB speaker re-indexing)
        speaker_aliases_to_update = set()
        try:
            for device in session_devices:
                speakers = Speaker.query.filter_by(session_device_id=device.id).all()
                for speaker in speakers:
                    if speaker.alias:
                        speaker_aliases_to_update.add(speaker.alias)
        except Exception as e:
            logging.warning(f"Could not collect speaker aliases for re-indexing: {e}")

        # Clean up RAG indexes for each session device
        try:
            from rag_service import RAGService
            rag_service = RAGService()
            for device in session_devices:
                rag_service.delete_session_index(device.id)
                logging.info(f"Cleaned up RAG index for session_device {device.id}")
        except Exception as e:
            logging.warning(f"Failed to clean up RAG indexes during session deletion: {e}")
            # Don't fail the deletion if RAG cleanup fails

        # Delete related data in correct order to avoid foreign key constraints
        db.session.query(Transcript).filter(Transcript.id.in_(sub_query)).delete(synchronize_session='fetch')

        # Delete SessionDevice and Session
        db.session.query(SessionDevice).filter(SessionDevice.session_id == session_id).delete()
        db.session.query(Session).filter(Session.id == session_id).delete()

        db.session.commit()

        # AFTER MySQL delete: Re-index or delete speakers from ChromaDB
        # Speakers are indexed cross-session, so we need to update their profiles
        if speaker_aliases_to_update:
            try:
                from rag_service import RAGService
                from speaker_serializer import SpeakerSerializer
                rag_service = RAGService()
                speaker_serializer = SpeakerSerializer()

                for alias in speaker_aliases_to_update:
                    # Check if speaker still exists in other sessions
                    remaining_speaker = Speaker.query.filter_by(alias=alias).first()
                    if remaining_speaker:
                        # Re-index with updated data (excluding deleted session)
                        speaker_data = speaker_serializer.serialize_speaker(alias)
                        if speaker_data:
                            rag_service.index_speaker(alias, speaker_data)
                            logging.info(f"Re-indexed speaker {alias} after session deletion")
                    else:
                        # Speaker no longer exists in any session - delete from ChromaDB
                        rag_service.delete_speaker_index(alias)
                        logging.info(f"Deleted speaker {alias} from ChromaDB (no longer in any session)")
            except Exception as e:
                logging.warning(f"Failed to update speaker indexes after session deletion: {e}")

        return True, "Session deleted successfully"
    except Exception as e:
        db.session.rollback()
        return False, str(e)

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

def disconnect_all_session_devices():
    query = db.session.query(SessionDevice).filter(SessionDevice.connected == True)
    for session_device in query.all():
        session_device.connected = False
    db.session.commit()
    return True

def set_session_device_status(session_device_id, status):
    session_device = get_session_devices(id=session_device_id)
    if session_device and session_device != status:
        session_device.connected = status
        db.session.commit()
        return True
    return False

def delete_session_device(session_device_id):
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
    db.session.query(Transcript).filter(Transcript.session_device_id == session_device_id).delete(synchronize_session='fetch')
    db.session.commit()


# -------------------------
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
        transcriptSubQuery = db.session.query(Transcript.id).filter(Transcript.session_device_id == SessionDevice.id).filter(SessionDevice.session_id == Session.id).filter(Session.owner_id == id).subquery()
        sessionSubQuery = db.session.query(Session.id).filter(Session.owner_id == id).subquery()
        db.session.query(Transcript).filter(Transcript.id.in_(transcriptSubQuery)).delete(synchronize_session='fetch')
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


# -------------------------
# Graph Traversal Functions (for Agentic RAG)
# -------------------------

def get_concept_nodes(session_device_id=None, concept_session_id=None, node_id=None,
                      node_type=None, speaker_id=None):
    """
    Get concept nodes with flexible filtering.

    Args:
        session_device_id: Filter by session device
        concept_session_id: Filter by concept session
        node_id: Get specific node by ID
        node_type: Filter by node type (question, idea, hypothesis, etc.)
        speaker_id: Filter by speaker

    Returns:
        List of ConceptNode objects or single node if node_id specified
    """
    query = db.session.query(ConceptNode)

    if node_id:
        return query.filter(ConceptNode.id == node_id).first()

    if concept_session_id:
        query = query.filter(ConceptNode.concept_session_id == concept_session_id)
    elif session_device_id:
        # Join through ConceptSession to get nodes for a session_device
        query = query.join(ConceptSession).filter(
            ConceptSession.session_device_id == session_device_id
        )

    if node_type:
        query = query.filter(ConceptNode.node_type == node_type)

    if speaker_id:
        query = query.filter(ConceptNode.speaker_id == speaker_id)

    return query.order_by(ConceptNode.timestamp).all()


def get_concept_edges(session_device_id=None, concept_session_id=None,
                      source_node_id=None, target_node_id=None, edge_type=None):
    """
    Get concept edges with flexible filtering.

    Args:
        session_device_id: Filter by session device
        concept_session_id: Filter by concept session
        source_node_id: Filter by source node
        target_node_id: Filter by target node
        edge_type: Filter by edge type (builds_on, challenges, etc.)

    Returns:
        List of ConceptEdge objects
    """
    query = db.session.query(ConceptEdge)

    if concept_session_id:
        query = query.filter(ConceptEdge.concept_session_id == concept_session_id)
    elif session_device_id:
        query = query.join(ConceptSession).filter(
            ConceptSession.session_device_id == session_device_id
        )

    if source_node_id:
        query = query.filter(ConceptEdge.source_node_id == source_node_id)

    if target_node_id:
        query = query.filter(ConceptEdge.target_node_id == target_node_id)

    if edge_type:
        query = query.filter(ConceptEdge.edge_type == edge_type)

    return query.all()


def get_node_neighbors(node_id, edge_types=None, direction='both'):
    """
    Get all concept nodes directly connected to a given node.

    Args:
        node_id: The center node ID
        edge_types: Optional list of edge types to filter (e.g., ['builds_on', 'challenges'])
        direction: 'incoming', 'outgoing', or 'both' (default)

    Returns:
        List of dicts with neighbor node info and edge details
    """
    results = []

    # Get outgoing edges (this node -> others)
    if direction in ['outgoing', 'both']:
        outgoing_query = db.session.query(ConceptEdge, ConceptNode).join(
            ConceptNode, ConceptEdge.target_node_id == ConceptNode.id
        ).filter(ConceptEdge.source_node_id == node_id)

        if edge_types:
            outgoing_query = outgoing_query.filter(ConceptEdge.edge_type.in_(edge_types))

        for edge, node in outgoing_query.all():
            results.append({
                'node': node.json(),
                'edge_type': edge.edge_type,
                'edge_id': edge.id,
                'direction': 'outgoing'
            })

    # Get incoming edges (others -> this node)
    if direction in ['incoming', 'both']:
        incoming_query = db.session.query(ConceptEdge, ConceptNode).join(
            ConceptNode, ConceptEdge.source_node_id == ConceptNode.id
        ).filter(ConceptEdge.target_node_id == node_id)

        if edge_types:
            incoming_query = incoming_query.filter(ConceptEdge.edge_type.in_(edge_types))

        for edge, node in incoming_query.all():
            results.append({
                'node': node.json(),
                'edge_type': edge.edge_type,
                'edge_id': edge.id,
                'direction': 'incoming'
            })

    return results


def get_concept_path(source_node_id, target_node_id, max_depth=4):
    """
    Find the shortest path between two concept nodes using BFS.

    Args:
        source_node_id: Starting node ID
        target_node_id: Target node ID
        max_depth: Maximum path length to search

    Returns:
        List of dicts representing the path, or None if no path found.
        Each dict contains: node_id, node_text, node_type, edge_type (to next)
    """
    from collections import deque

    if source_node_id == target_node_id:
        node = get_concept_nodes(node_id=source_node_id)
        if node:
            return [{'node': node.json(), 'edge_to_next': None}]
        return None

    # Get concept_session_id for both nodes to ensure they're in same session
    source_node = get_concept_nodes(node_id=source_node_id)
    target_node = get_concept_nodes(node_id=target_node_id)

    if not source_node or not target_node:
        return None

    if source_node.concept_session_id != target_node.concept_session_id:
        return None  # Nodes not in same session

    # Build adjacency list for the session
    edges = get_concept_edges(concept_session_id=source_node.concept_session_id)
    adj = {}
    for edge in edges:
        if edge.source_node_id not in adj:
            adj[edge.source_node_id] = []
        adj[edge.source_node_id].append((edge.target_node_id, edge.edge_type))
        # Also add reverse edges for undirected search
        if edge.target_node_id not in adj:
            adj[edge.target_node_id] = []
        adj[edge.target_node_id].append((edge.source_node_id, edge.edge_type))

    # BFS
    queue = deque([(source_node_id, [source_node_id], [])])  # (current, path, edge_types)
    visited = {source_node_id}

    while queue:
        current, path, edge_types = queue.popleft()

        if len(path) > max_depth:
            continue

        if current not in adj:
            continue

        for next_node_id, edge_type in adj[current]:
            if next_node_id in visited:
                continue

            new_path = path + [next_node_id]
            new_edge_types = edge_types + [edge_type]

            if next_node_id == target_node_id:
                # Found path - build result
                result = []
                nodes = {n.id: n for n in get_concept_nodes(
                    concept_session_id=source_node.concept_session_id
                )}
                for i, node_id in enumerate(new_path):
                    node = nodes.get(node_id)
                    result.append({
                        'node': node.json() if node else {'id': node_id},
                        'edge_to_next': new_edge_types[i] if i < len(new_edge_types) else None
                    })
                return result

            visited.add(next_node_id)
            queue.append((next_node_id, new_path, new_edge_types))

    return None  # No path found


def get_causal_chain(node_id, direction='forward', max_depth=5):
    """
    Extract causal/logical chains from a concept node.

    Follows edges of causal types: causes, leads_to, enables, solves, answers

    Args:
        node_id: Starting node ID
        direction: 'forward' (follow outgoing causal edges) or 'backward' (incoming)
        max_depth: Maximum chain length

    Returns:
        List of dicts representing the causal chain with nodes and edge types
    """
    CAUSAL_EDGE_TYPES = ['causes', 'leads_to', 'enables', 'solves', 'answers', 'results_in']

    start_node = get_concept_nodes(node_id=node_id)
    if not start_node:
        return []

    chain = [{'node': start_node.json(), 'edge_type': None}]
    visited = {node_id}
    current_id = node_id

    for _ in range(max_depth):
        # Get edges based on direction
        if direction == 'forward':
            edges = get_concept_edges(
                concept_session_id=start_node.concept_session_id,
                source_node_id=current_id
            )
            edges = [e for e in edges if e.edge_type in CAUSAL_EDGE_TYPES]
        else:
            edges = get_concept_edges(
                concept_session_id=start_node.concept_session_id,
                target_node_id=current_id
            )
            edges = [e for e in edges if e.edge_type in CAUSAL_EDGE_TYPES]

        if not edges:
            break

        # Take the first unvisited causal edge
        next_edge = None
        for edge in edges:
            next_id = edge.target_node_id if direction == 'forward' else edge.source_node_id
            if next_id not in visited:
                next_edge = edge
                break

        if not next_edge:
            break

        next_id = next_edge.target_node_id if direction == 'forward' else next_edge.source_node_id
        next_node = get_concept_nodes(node_id=next_id)

        if next_node:
            chain.append({
                'node': next_node.json(),
                'edge_type': next_edge.edge_type
            })
            visited.add(next_id)
            current_id = next_id
        else:
            break

    return chain


def get_cluster_subgraph(cluster_id, include_cross_cluster_edges=False):
    """
    Get all nodes and edges within a thematic cluster.

    Args:
        cluster_id: The cluster ID to extract
        include_cross_cluster_edges: Whether to include edges connecting to nodes outside the cluster

    Returns:
        Dict with 'cluster', 'nodes', 'edges', and 'internal_edges'
    """
    cluster = db.session.query(ConceptCluster).filter(
        ConceptCluster.id == cluster_id
    ).first()

    if not cluster:
        return None

    # Get nodes in cluster
    cluster_nodes = cluster.nodes or []
    node_ids = {n.id for n in cluster_nodes}

    # Get edges
    all_edges = get_concept_edges(concept_session_id=cluster.concept_session_id)

    internal_edges = []
    cross_cluster_edges = []

    for edge in all_edges:
        source_in = edge.source_node_id in node_ids
        target_in = edge.target_node_id in node_ids

        if source_in and target_in:
            internal_edges.append(edge.json())
        elif (source_in or target_in) and include_cross_cluster_edges:
            cross_cluster_edges.append(edge.json())

    result = {
        'cluster': cluster.json(),
        'nodes': [n.json() for n in cluster_nodes],
        'internal_edges': internal_edges,
        'node_count': len(cluster_nodes),
        'internal_edge_count': len(internal_edges)
    }

    if include_cross_cluster_edges:
        result['cross_cluster_edges'] = cross_cluster_edges

    return result


def get_speaker_contribution_graph(session_device_id, speaker_id):
    """
    Get the subgraph of concepts contributed by a specific speaker.

    Args:
        session_device_id: The session to analyze
        speaker_id: The speaker ID

    Returns:
        Dict with speaker's nodes, edges between them, and summary stats
    """
    # Get speaker's nodes
    speaker_nodes = get_concept_nodes(
        session_device_id=session_device_id,
        speaker_id=speaker_id
    )

    if not speaker_nodes:
        return {
            'speaker_id': speaker_id,
            'nodes': [],
            'edges': [],
            'node_count': 0,
            'edge_count': 0
        }

    node_ids = {n.id for n in speaker_nodes}

    # Get concept_session_id
    concept_session = db.session.query(ConceptSession).filter(
        ConceptSession.session_device_id == session_device_id
    ).first()

    if not concept_session:
        return {
            'speaker_id': speaker_id,
            'nodes': [n.json() for n in speaker_nodes],
            'edges': [],
            'node_count': len(speaker_nodes),
            'edge_count': 0
        }

    # Get edges where both source and target are speaker's nodes
    all_edges = get_concept_edges(concept_session_id=concept_session.id)
    speaker_edges = [
        e for e in all_edges
        if e.source_node_id in node_ids or e.target_node_id in node_ids
    ]

    # Categorize edges
    internal_edges = [e for e in speaker_edges
                      if e.source_node_id in node_ids and e.target_node_id in node_ids]
    outgoing_edges = [e for e in speaker_edges
                      if e.source_node_id in node_ids and e.target_node_id not in node_ids]
    incoming_edges = [e for e in speaker_edges
                      if e.source_node_id not in node_ids and e.target_node_id in node_ids]

    # Count node types
    from collections import Counter
    type_counts = Counter(n.node_type for n in speaker_nodes if n.node_type)

    return {
        'speaker_id': speaker_id,
        'nodes': [n.json() for n in speaker_nodes],
        'edges': [e.json() for e in speaker_edges],
        'internal_edges': [e.json() for e in internal_edges],
        'outgoing_edges': [e.json() for e in outgoing_edges],
        'incoming_edges': [e.json() for e in incoming_edges],
        'node_count': len(speaker_nodes),
        'edge_count': len(speaker_edges),
        'node_types': dict(type_counts)
    }


def trace_concept_to_source(node_id):
    """
    Find the transcript turns that generated a concept node.

    Uses the node's timestamp to find nearby transcripts.

    Args:
        node_id: The concept node ID

    Returns:
        Dict with the node, source transcripts, and context
    """
    node = get_concept_nodes(node_id=node_id)
    if not node:
        return None

    # Get concept session to find session_device_id
    concept_session = db.session.query(ConceptSession).filter(
        ConceptSession.id == node.concept_session_id
    ).first()

    if not concept_session:
        return {'node': node.json(), 'transcripts': [], 'context': []}

    session_device_id = concept_session.session_device_id

    # Find transcripts near the node's timestamp
    timestamp = node.timestamp or 0
    window = 30  # 30 second window

    transcripts = db.session.query(Transcript).filter(
        Transcript.session_device_id == session_device_id,
        Transcript.start_time >= timestamp - window,
        Transcript.start_time <= timestamp + window
    ).order_by(Transcript.start_time).all()

    # Try to find the best matching transcript
    best_match = None
    best_score = 0

    node_text_lower = node.text.lower() if node.text else ""

    for t in transcripts:
        t_text_lower = t.transcript.lower() if t.transcript else ""

        # Simple word overlap scoring
        node_words = set(node_text_lower.split())
        t_words = set(t_text_lower.split())
        overlap = len(node_words & t_words)

        if overlap > best_score:
            best_score = overlap
            best_match = t

    # Get context (surrounding transcripts)
    context_transcripts = db.session.query(Transcript).filter(
        Transcript.session_device_id == session_device_id,
        Transcript.start_time >= timestamp - 60,
        Transcript.start_time <= timestamp + 60
    ).order_by(Transcript.start_time).all()

    return {
        'node': node.json(),
        'best_match': {
            'id': best_match.id,
            'text': best_match.transcript,
            'speaker_tag': best_match.speaker_tag,
            'start_time': best_match.start_time,
            'speaker_id': best_match.speaker_id
        } if best_match else None,
        'transcripts': [{
            'id': t.id,
            'text': t.transcript,
            'speaker_tag': t.speaker_tag,
            'start_time': t.start_time,
            'speaker_id': t.speaker_id
        } for t in transcripts],
        'context': [{
            'id': t.id,
            'text': t.transcript,
            'speaker_tag': t.speaker_tag,
            'start_time': t.start_time
        } for t in context_transcripts]
    }


# -------------------------
# Agent Conversation Functions
# -------------------------

def create_agent_conversation(user_id, session_device_id=None, title=None, agent_version='v3'):
    """
    Create a new agent conversation.

    Args:
        user_id: The user ID
        session_device_id: Optional session device to focus on
        title: Optional conversation title
        agent_version: Agent version (v3, v4, v5, v6, baseline)

    Returns:
        The created AgentConversation object
    """
    from tables.agent_conversation import AgentConversation
    conversation = AgentConversation(
        user_id=user_id,
        session_device_id=session_device_id,
        title=title,
        agent_version=agent_version
    )
    db.session.add(conversation)
    db.session.commit()
    return conversation


def get_agent_conversations(user_id=None, conversation_id=None, agent_version=None, limit=50):
    """
    Get agent conversations.

    Args:
        user_id: Filter by user
        conversation_id: Get specific conversation
        agent_version: Filter by agent version (v3, v4, v5, v6, baseline)
        limit: Maximum number to return

    Returns:
        List of conversations or single conversation
    """
    from tables.agent_conversation import AgentConversation
    query = db.session.query(AgentConversation)

    if conversation_id:
        return query.filter(AgentConversation.id == conversation_id).first()

    if user_id:
        query = query.filter(AgentConversation.user_id == user_id)

    if agent_version:
        query = query.filter(AgentConversation.agent_version == agent_version)

    return query.order_by(desc(AgentConversation.last_active)).limit(limit).all()


def update_agent_conversation(conversation_id, title=None, session_device_id=None):
    """Update an agent conversation."""
    conversation = get_agent_conversations(conversation_id=conversation_id)
    if not conversation:
        return None

    if title is not None:
        conversation.title = title
    if session_device_id is not None:
        conversation.session_device_id = session_device_id

    conversation.touch()
    db.session.commit()
    return conversation


def delete_agent_conversation(conversation_id):
    """Delete an agent conversation and all its messages."""
    conversation = get_agent_conversations(conversation_id=conversation_id)
    if not conversation:
        return False

    db.session.delete(conversation)
    db.session.commit()
    return True


def add_agent_message(conversation_id, role, content, citations=None,
                      tools_used=None, reasoning_trace=None, confidence=None):
    """
    Add a message to an agent conversation.

    Args:
        conversation_id: The conversation UUID
        role: 'user' or 'assistant'
        content: Message text
        citations: Optional citation data (for assistant)
        tools_used: Optional list of tools used (for assistant)
        reasoning_trace: Optional reasoning steps (for assistant)
        confidence: Optional confidence score (for assistant)

    Returns:
        The created AgentMessage object
    """
    from tables.agent_message import AgentMessage

    # Update conversation's last_active
    conversation = get_agent_conversations(conversation_id=conversation_id)
    if not conversation:
        return None

    conversation.touch()

    # Auto-generate title from first user message
    if role == 'user' and not conversation.title:
        conversation.update_title_from_query(content)

    message = AgentMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations,
        tools_used=tools_used,
        reasoning_trace=reasoning_trace,
        confidence=confidence
    )
    db.session.add(message)
    db.session.commit()
    return message


def get_agent_messages(conversation_id, limit=100, offset=0):
    """
    Get messages for a conversation.

    Args:
        conversation_id: The conversation UUID
        limit: Maximum messages to return
        offset: Number of messages to skip

    Returns:
        List of AgentMessage objects in chronological order
    """
    from tables.agent_message import AgentMessage
    return db.session.query(AgentMessage).filter(
        AgentMessage.conversation_id == conversation_id
    ).order_by(AgentMessage.created_at).offset(offset).limit(limit).all()


def get_conversation_history_for_context(conversation_id, max_messages=10):
    """
    Get recent conversation history formatted for LLM context.

    Args:
        conversation_id: The conversation UUID
        max_messages: Maximum recent messages to include

    Returns:
        List of dicts with role and content
    """
    from tables.agent_message import AgentMessage
    messages = db.session.query(AgentMessage).filter(
        AgentMessage.conversation_id == conversation_id
    ).order_by(desc(AgentMessage.created_at)).limit(max_messages).all()

    # Reverse to chronological order
    messages = list(reversed(messages))

    return [{'role': m.role, 'content': m.content} for m in messages]
