# File for generic helper functions.
from flask import escape, jsonify
from collections import Counter
import numpy as np
from scipy.stats import median_abs_deviation
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

def compute_median_and_mad(values):
    median = np.median(values)
    mad = median_abs_deviation(values,scale='normal')
    return median, mad

def get_progression(previous, current):
    if previous is None:
        return "stable"
    elif current > previous:
        return "increasing"
    elif current < previous:
        return "decreasing"
    else:
        return "stable"

def convert_attention_to_class_fuse_back_to_accumulator(accumulated_metrics,attention_rates):
    # attention_rates = sorted(attention_rates,key=lambda x: x[1])
    # len_attention_rates = len(attention_rates)

    # for i in range(len_attention_rates):
    #     percentile = round((i / (len_attention_rates - 1)), 2)
    #     if percentile <= 0.25:
    #         attention_class = 'low'
    #     elif percentile <= 0.75:
    #         attention_class = 'medium'
    #     else:            
    #         attention_class = 'high'
    len_attention_rates = len(attention_rates)
    if len_attention_rates > 0 and len_attention_rates  == 1:
        attention_class = 'low'
        accumulated_metrics[0][7] = "low"
        return accumulated_metrics
    elif len_attention_rates > 0:
        median_x,mad = compute_median_and_mad(np.array(attention_rates))

        robust_z = (attention_rates[0] - median_x) / mad
        attention_class = "low" if robust_z < -1 else "medium" if -1 < robust_z < 1 else "high"
        accumulated_metrics[0][7] = attention_class+" and "+get_progression(None, robust_z)
        previous_robust_z = robust_z
        for i in range(1, len(attention_rates)):
            x = attention_rates[i]
            robust_z = (x - median_x) / mad
            attention_class = "low" if robust_z < -1 else "medium" if -1 < robust_z < 1 else "high"
            accumulated_metrics[i][7] = attention_class+" and "+get_progression(previous_robust_z, robust_z)
            previous_robust_z = robust_z
    return accumulated_metrics

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
    attention_rate_acc = [] 
    l = 0
    window_count = 0
    attention_class = "No Attention"
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
                attention_rate = avg_attention / (windowsize * (window_count+1)) 
            else:
                avg_attention = None
                attention_rate = 0
            
            # attention_rate_acc.append([window_count, attention_rate])
            attention_rate_acc.append(attention_rate)
        
            accumulated_metrics.append([session_device.id,session_device.name,[start,end],most_common_emotion,
                                        most_common_object,avg_attention,attention_rate,attention_class,speaker.alias,speaker.id])
            # Reset for next window
            facial_emotion = []
            object_on_focus = []
            attention_level = []
            newwindowstarted = False
            window_count += 1 
    accumulated_metrics_final = convert_attention_to_class_fuse_back_to_accumulator(accumulated_metrics,attention_rate_acc) 
    if format!='csv':
        return accumulated_metrics_final
    else:
        for metrics in accumulated_metrics_final:
            fwrite.writerow({'Device ID':metrics[0],
                            'Device Name':metrics[1],
                            'Time Range (s)':str(metrics[2][0])+'-'+str(metrics[2][1]),
                            'Facial Emotion': metrics[3],
                            'Object Focus On': metrics[4],
                            'Attention Level': metrics[5],
                            'Attention Rate': metrics[6],
                            "Attention Class":metrics[7],
                            'Speaker Tag': metrics[8],
                            })  

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
    prev_analytic_value= prev_authenticity_value=prev_certainty_value=prev_clout_value=prev_emotional_tone_value= None
    prev_participation_score_val = prev_internal_cohesion_val = prev_responsivity_val = prev_social_impact_val = prev_newness_val = None
    # communication_density = []
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
            participation_score.append(float(sm.participation_score)),
            internal_cohesion.append(float(sm.internal_cohesion)),
            responsivity.append(float(sm.responsivity)),
            social_impact.append(float(sm.social_impact)),
            newness.append(float(sm.newness)), 
            # communication_density.append(float(sm.communication_density)),
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
                val = sum(analytic)//len(analytic)
                analytic_thinking_val = "Analytical thinking" if val > 50 else "Narrative thinking" if val < 50 else "Balanced thinking"
            else:
                analytic_thinking_val = 'None'
            if authenticity:
                val = sum(authenticity)//len(authenticity)
                authenticity_val = "High" if val > 50 else "Low" if val < 50 else "Balanced"
            else:
                authenticity_val = 'None'   
            if certainty:
                val = sum(certainty)//len(certainty)
                certainty_val = "High" if val > 50 else "Low" if val < 50 else "Medium"
            else:
                certainty_val = 'None'
            if clout:
                val = sum(clout)//len(clout)
                clout_val = "High" if val > 50 else "Low" if val < 50 else "Medium"
            else:
                clout_val = 'None'
            if emotionaL_tone: 
                val = sum(emotionaL_tone)//len(emotionaL_tone) 
                emotional_tone_val = "Positive" if val > 50 else "Negative" if val < 50 else "Neutral"
            else:
                emotional_tone_val = 'None'
            if participation_score:
                val = sum(participation_score)//len(participation_score)
                if val > 1.5:
                    participation_score_val = "Dominant participation"
                elif 0.5<val < 1:
                    participation_score_val = "High participation"
                elif -0.25<val < 0.5:
                    participation_score_val = "Balanced participation"  
                elif -0.75 < val < -0.25:
                    participation_score_val = "Low participation"   
                else:
                    participation_score_val = "Minimal participation" 
            else:
                participation_score_val = 'None'
            if internal_cohesion:
                val = sum(internal_cohesion)//len(internal_cohesion)
                internal_cohesion_val = "High" if val > 0.5 else "Low" if val < 0.20 else "Medium"
            else:
                internal_cohesion_val = 'None'
            if responsivity:
                val = sum(responsivity)//len(responsivity)
                responsivity_val = "High" if val > 0.5 else "Low" if val < 0.20 else "Medium"
            else:
                responsivity_val = 'None'
            if social_impact:
                val = sum(social_impact)//len(social_impact)
                social_impact_val = "High" if val > 0.5 else "Low" if val < 0.20 else "Medium"
            else:
                social_impact_val = 'None'
            if newness:
                val = sum(newness)//len(newness)
                newness_val = "High" if val > 0.67 else "Low" if val < 0.33 else "Medium"
            else:
                newness_val = 'None'
            # if communication_density:
            #     val = sum(communication_density)//len(communication_density)
            #     communication_density_val = "High" if val > 0.67 else "Low" if val < 0.33 else "Medium"
            # else:
            #     communication_density_val = 'None'
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
                            # 'communication_density': communication_density_val,
                            'Word Count': word_count_val,
                            'Speaker Tag': t.speaker_tag,
                            'Speaker ID': int(t.speaker_id),
                            'Topic ID': int(t.topic_id)
                            })
            else:   
                    accumulated_metrics.append([session_device.id,session_device.name,[start,end],transcript_val,
                                                keywords_val,keywords_detected_val,similarity_val,analytic_thinking_val,
                                                authenticity_val,certainty_val,clout_val,emotional_tone_val,participation_score_val,
                                                internal_cohesion_val,responsivity_val,social_impact_val,newness_val,
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
            # communication_density = []
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
                     '',"None","None","None","None","None","None","None","None","None","None",0,v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[7],v_metrics[8],v_metrics[9],-1]
            lv += 1
        elif t_metrics[2][1] <= v_metrics[2][0]:
            value = [t_metrics[0],t_metrics[1],str(t_metrics[2][0])+'-'+str(t_metrics[2][1]),t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                     t_metrics[15],t_metrics[16],t_metrics[17],"None","None",0,0,"No Attention",t_metrics[18],t_metrics[19],t_metrics[20]]
            lt += 1
        else:
            # Write combined metrics to CSV or return as list 
            st = min(v_metrics[2][0],t_metrics[2][0])
            en = max(v_metrics[2][1],t_metrics[2][1])
            value = [t_metrics[0],t_metrics[1],str(st)+'-'+str(en),t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                     t_metrics[15],t_metrics[16],t_metrics[17],v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[7],t_metrics[18],t_metrics[19],t_metrics[20]]
            # Overlapping ranges, process both
            lv += 1
            lt += 1
                  
        write_or_append_metrics(value,fwrite,accumulated_metrics,format=format)
    
    while lv < vidLen:
        v_metrics = batch_video_speaker_metrics[lv]
        value = [v_metrics[0],v_metrics[1],str(v_metrics[2][0])+'-'+str(v_metrics[2][1]),'','','',
                 '',"None","None","None","None","None","None","None","None","None","None",0,v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[7],v_metrics[8],v_metrics[9],-1]
        write_or_append_metrics(value,fwrite,accumulated_metrics,format=format)
        lv += 1

    while lt < transLen:
        t_metrics = batch_transcript_speaker_metrics[lt]
        value = [t_metrics[0],t_metrics[1],str(t_metrics[2][0])+'-'+str(t_metrics[2][1]),t_metrics[3],t_metrics[4],t_metrics[5],
                 t_metrics[6],t_metrics[7],t_metrics[8],t_metrics[9],t_metrics[10],t_metrics[11],t_metrics[12],t_metrics[13],t_metrics[14],
                 t_metrics[15],t_metrics[16],t_metrics[17],"None","None",0,0,"No Attention",t_metrics[18],t_metrics[19],t_metrics[20]]
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
                            # 'communication_density': metrics[17],
                            'Word Count': metrics[17],
                            'Facial Emotion': metrics[18],
                            'Object Focus On': metrics[19],
                            'Attention Level': metrics[20],
                            'Attention Rate': metrics[21] ,
                            "Attention Class":metrics[22],
                            'Speaker Tag': metrics[23],
                            'Speaker ID': metrics[24],
                            'Topic ID': metrics[25]
                            })
    else:
        accumulator.append(metrics)      
