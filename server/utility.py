# File for generic helper functions.
from flask import escape, jsonify
from collections import Counter
import re
import logging

logger = logging.getLogger('utility.funcs')
def string_to_bool(value):
    if not value:
        return None
    return value.lower() in ['true', '1', 't', 'y', 'yes']

def sanitize(value):
    if not value:
        return None
    if isinstance(value, (list,)):
        return [str(sanitize(v)) for v in value]
    else:
        return str(escape(value))

def get_client_ip(request):
    return request.remote_addr

def json_response(payload={}, status=200):
    resp = jsonify(payload)
    resp.status_code = status
    return resp

def verify_characters(value, chars):
    if re.search(r'^[{0}]+\Z'.format(chars), value):
        return True
    return False

def batch_video_metrics(videoMetrics, windowsize, fwrite, speaker, session_device):
    """
    Accumulate video metrics over specified window size.
    """
    
    start = 0
    end = windowsize 
    newwindowstarted = False  
    facial_emotion = []
    object_on_focus = []
    attention_level = [] 
    l = 0
    n=len(videoMetrics)
    while l < n:
        v= videoMetrics[l]
        if not newwindowstarted:
            start = v.time_stamp
            end = start + windowsize

        if v.time_stamp >= start and v.time_stamp < end:
            facial_emotion.append(str(v.facial_emotion))
            object_on_focus.append(str(v.object_on_focus))
            attention_level.append(int(v.attention_level))  
            newwindowstarted = True
            l += 1
        else:
            # Accumulate metrics for the window
            if facial_emotion:
                most_common_emotion = Counter(facial_emotion).most_common(1)[0][0]
            else:
                most_common_emotion = None
            if object_on_focus:
                most_common_object = Counter(object_on_focus).most_common(1)[0][0]
            else:
                most_common_object = None
            if attention_level:
                avg_attention = sum(attention_level) // len(attention_level)
            else:
                avg_attention = None

            fwrite.writerow({'Device ID':session_device.id,
                    'Device Name':session_device.name,
                    'Time Range':str(start)+'-'+str(end),
                    'Facial Emotion': most_common_emotion,
                    'Object Focus On': most_common_object,
                    'Attention Level': avg_attention,
                    'Speaker Tag': speaker.alias
                    })

            # Reset for next window
            facial_emotion = []
            object_on_focus = []
            attention_level = []
            newwindowstarted = False 
def batch_transcript_metrics(transcriptSpeakerMetric, windowsize, fwrite, speaker, session_device,keywords):
    """
    Accumulate video metrics over specified window size.
    """
    
    start = 0
    end = windowsize 
    newwindowstarted = False  
    analytic = []
    authenticity = []
    certainty = [] 
    clout = []
    emotionaL_tone = []
    participation_score = []
    internal_cohesion = []
    responsivity = []
    social_impact = []
    newness = []
    communication_density = []
    word_count = []
    words_per_window = []

    l = 0
    n=len(transcriptSpeakerMetric)
    while l < n:
        t, sm = transcriptSpeakerMetric[l]
        
        if not newwindowstarted:
            start = t.start_time
            end = start + windowsize

        if t.start_time >= start and t.start_time < end:
            analytic.append(int(t.analytic_thinking_value))
            authenticity.append(int(t.authenticity_value))
            certainty.append(int(t.certainty_value))  
            clout.append(int(t.clout_value)),
            emotionaL_tone.append(int(t.emotional_tone_value)),
            participation_score.append(int(float(sm.participation_score)*100)),
            internal_cohesion.append(int(float(sm.internal_cohesion)*100)),
            responsivity.append(int(float(sm.responsivity)*100)),
            social_impact.append(int(float(sm.social_impact)*100)),
            newness.append(int(float(sm.newness)*100)), 
            communication_density.append(int(float(sm.communication_density)*100)),
            word_count.append(int(t.word_count)),
            words_per_window.append(str(t.transcript)),

            newwindowstarted = True
            l += 1
        else:
            # Accumulate metrics for the window
            if analytic:
                analytic_thinking_val = sum(analytic)//len(analytic)
            else:
                analytic_thinking_val = 0
            if authenticity:
                authenticity_val = sum(authenticity)//len(authenticity)
            else:
                authenticity_val = 0
            if certainty:
                certainty_val = sum(certainty)//len(certainty)
            else:
                certainty_val = 0
            if clout:
                clout_val = sum(clout)//len(clout)
            else:
                clout_val = 0
            if emotionaL_tone:  
                emotional_tone_val = sum(emotionaL_tone)//len(emotionaL_tone)
            else:
                emotional_tone_val = 0
            if participation_score:
                participation_score_val = sum(participation_score)//len(participation_score)
            else:
                participation_score_val = 0
            if internal_cohesion:
                internal_cohesion_val = sum(internal_cohesion)//len(internal_cohesion)
            else:
                internal_cohesion_val = 0
            if responsivity:
                responsivity_val = sum(responsivity)//len(responsivity)
            else:
                responsivity_val = 0
            if social_impact:
                social_impact_val = sum(social_impact)//len(social_impact)
            else:
                social_impact_val = 0
            if newness:
                newness_val = sum(newness)//len(newness)
            else:
                newness_val = 0
            if communication_density:
                communication_density_val = sum(communication_density)//len(communication_density)
            else:
                communication_density_val = 0
            if word_count:
                word_count_val = sum(word_count)
            else:
                word_count_val = 0
            if words_per_window:
                transcript_val = ' '.join(words_per_window)
            else:
                transcript_val = '' 
            

            transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
            fwrite.writerow({'Device ID':session_device.id,
                    'Device Name':session_device.name,
                    'Time Range': str(start)+'-'+str(end),
                    'Transcript':transcript_val,
                    'Keywords': ', '.join([keyword.keyword for keyword in transcript_keywords]),
                    'Keywords Detected': ', '.join([keyword.word for keyword in transcript_keywords]),
                    'Similarity': ', '.join([str(round((1-keyword.similarity)*100,3)) for keyword in transcript_keywords]),
                    'Analytic Thinking': analytic_thinking_val,
                    'Authenticity': authenticity_val,
                    'Certainty': certainty_val,
                    'Clout': clout_val,
                    'Emotional Tone': emotional_tone_val,
                    'participation_score': participation_score_val,
                    'internal_cohesion':  internal_cohesion_val,
                    'responsivity':  responsivity_val,
                    'social_impact':  social_impact_val,
                    'newness':  newness_val, 
                    'communication_density': communication_density_val,
                    'Word Count': word_count_val,
                    'Speaker Tag': t.speaker_tag,
                    'Speaker ID': int(t.speaker_id),
                    'Topic ID': int(t.topic_id)
                    })

            # Reset for next window
            analytic = []
            authenticity = []
            certainty = [] 
            clout = []
            emotionaL_tone = []
            participation_score = []
            internal_cohesion = []
            responsivity = []
            social_impact = []
            newness = []
            communication_density = []
            word_count = []
            words_per_window = []
            newwindowstarted = False            