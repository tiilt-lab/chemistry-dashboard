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


def batch_video_metrics(videoMetrics, windowsize, fwrite, speaker, session_device,format='csv'):
    """
    Accumulate video metrics over specified window size.
    """
    accumulated_metrics = []
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
            if format=='csv':
                fwrite.writerow({'Device ID':session_device.id,
                        'Device Name':session_device.name,
                        'Time Range (s)':str(start)+'-'+str(end),
                        'Facial Emotion': most_common_emotion,
                        'Object Focus On': most_common_object,
                        'Attention Level': avg_attention,
                        'Speaker Tag': speaker.alias
                        })
            else:
                accumulated_metrics.append([session_device.id,session_device.name,[start,end],most_common_emotion,
                                            most_common_object,avg_attention,speaker.alias,speaker.id])

            # Reset for next window
            facial_emotion = []
            object_on_focus = []
            attention_level = []
            newwindowstarted = False 

    if format!='csv':
        return accumulated_metrics

def batch_transcript_metrics(transcriptSpeakerMetric, windowsize, fwrite, speaker, session_device,keywords,format='csv'):
    """
    Accumulate video metrics over specified window size.
    """
    accumulated_metrics = []
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
    keywords_window = []
    keywords_detected_window = []
    similarity_window = []

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
            transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
            keywords_window.append(', '.join([keyword.keyword for keyword in transcript_keywords]))
            keywords_detected_window.append(', '.join([keyword.word for keyword in transcript_keywords]))
            similarity_window.append(', '.join([str(round((1-keyword.similarity)*100,3)) for keyword in transcript_keywords]))

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
            if keywords_detected_window:
                keywords_detected_val = ' '.join(keywords_detected_window)
            else:
                keywords_detected_val = ''
            if similarity_window:
                similarity_val = ' '.join(similarity_window)
            else:
                similarity_val = '' 

            if keywords_window:            
                keywords_val = ' '.join(keywords_window)
            else:
                keywords_val = ''

            if format=='csv':
                    fwrite.writerow({'Device ID':session_device.id,
                            'Device Name':session_device.name,
                            'Time Range (s)': str(start)+'-'+str(end),
                            'Transcript':transcript_val,
                            'Keywords': keywords_val,
                            'Keywords Detected': keywords_detected_val,
                            'Similarity': similarity_val,
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
            else:   
                    accumulated_metrics.append([session_device.id,session_device.name,[start,end],transcript_val,
                                                keywords_val,keywords_detected_val,similarity_val,analytic_thinking_val,
                                                authenticity_val,certainty_val,clout_val,emotional_tone_val,participation_score_val,
                                                internal_cohesion_val,responsivity_val,social_impact_val,newness_val,communication_density_val,
                                                word_count_val,t.speaker_tag,int(t.speaker_id),int(t.topic_id)])
                

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

    if format!='csv':
        return accumulated_metrics          

def batch_transcript_video_metrics(transcriptSpeakerMetric,videoMetrics,windowsize,fwrite,speaker,session_device,keywords,format='csv'):
    """
    Accumulate both transcript and video metrics over specified window size.
    """
    accumulated_metrics = []
    batch_transcript_speaker_metrics = batch_transcript_metrics(transcriptSpeakerMetric,windowsize,fwrite,speaker,session_device,keywords,format='list')
    batch_video_speaker_metrics = batch_video_metrics(videoMetrics,windowsize,fwrite,speaker,session_device,format='list')
    vidLen = len(batch_video_speaker_metrics)
    transLen = len(batch_transcript_speaker_metrics)
    lv,lt = 0,0
    while lv < vidLen and lt < transLen:
        v_metrics = batch_video_speaker_metrics[lv]
        t_metrics = batch_transcript_speaker_metrics[lt]
        # Align by time range
        if v_metrics[2][1] <= t_metrics[2][0]:
            value = [v_metrics[0],v_metrics[1],str(v_metrics[2][0])+'-'+str(v_metrics[2][1]),'','','',
                     '',0,0,0,0,0,0,0,0,0,0,0,0,v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[7],-1]
            lv += 1
        elif t_metrics[2][1] <= v_metrics[2][0]:
            value = [t_metrics[0],t_metrics[1],str(t_metrics[2][0])+'-'+str(t_metrics[2][1]),t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                     t_metrics[15],t_metrics[16],t_metrics[17],t_metrics[18],0,0,0,t_metrics[19],t_metrics[20],t_metrics[21]]
            lt += 1
        else:
            # Write combined metrics to CSV or return as list 
            st = min(v_metrics[2][0],t_metrics[2][0])
            en = max(v_metrics[2][1],t_metrics[2][1])
            value = [t_metrics[0],t_metrics[1],str(st)+'-'+str(en),t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                     t_metrics[15],t_metrics[16],t_metrics[17],t_metrics[18],v_metrics[3],v_metrics[4],v_metrics[5],t_metrics[19],t_metrics[20],t_metrics[21]]
            # Overlapping ranges, process both
            lv += 1
            lt += 1
                  
        write_or_append_metrics(value,fwrite,accumulated_metrics,format=format)
    
    while lv < vidLen:
        v_metrics = batch_video_speaker_metrics[lv]
        value = [v_metrics[0],v_metrics[1],str(v_metrics[2][0])+'-'+str(v_metrics[2][1]),'','','',
                 '',0,0,0,0,0,0,0,0,0,0,0,0,v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[7],-1]
        write_or_append_metrics(value,fwrite,accumulated_metrics,format=format)
        lv += 1

    while lt < transLen:
        t_metrics = batch_transcript_speaker_metrics[lt]
        value = [t_metrics[0],t_metrics[1],str(t_metrics[2][0])+'-'+str(t_metrics[2][1]),t_metrics[3],t_metrics[4],t_metrics[5],
                 t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                 t_metrics[15],t_metrics[16],t_metrics[17],t_metrics[18],0,0,0,t_metrics[19],t_metrics[20],t_metrics[21]]
        write_or_append_metrics(value,fwrite,accumulated_metrics,format=format)
        lt += 1    
    
    if format!='csv':
        return accumulated_metrics
def write_or_append_metrics(metrics, fwrite,accumulator, format='csv'):
    """
    Write or append metrics to CSV or return as list.
    """
    if format=='csv':
        fwrite.writerow({'Device ID':metrics[0],
                            'Device Name': metrics[1],
                            'Time Range (s)': metrics[2],
                            'Transcript': metrics[3],
                            'Keywords': metrics[4],
                            'Keywords Detected': metrics[5],
                            'Similarity': metrics[6],
                            'Analytic Thinking': metrics[7],
                            'Authenticity': metrics[8],
                            'Certainty': metrics[9],
                            'Clout': metrics[10],
                            'Emotional Tone': metrics[11],
                            'participation_score': metrics[12],
                            'internal_cohesion':  metrics[13],
                            'responsivity':  metrics[14],
                            'social_impact':  metrics[15],
                            'newness':  metrics[16], 
                            'communication_density': metrics[17],
                            'Word Count': metrics[18],
                            'Facial Emotion': metrics[19],
                            'Object Focus On': metrics[20],
                            'Attention Level': metrics[21],
                            'Speaker Tag': metrics[22],
                            'Speaker ID': metrics[23],
                            'Topic ID': metrics[24]
                            })
    else:
        accumulator.append(metrics)      
