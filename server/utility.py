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

def get_progression(previous, current,type="categorical"):
    if type == "categorical":
        if previous is None:
            return "stable"
        elif current == previous:
            return "stable"
        elif current > previous:
            return "increasing"
        elif current < previous:
            return "decreasing"
    else:
        if previous is None:
            return 0 
        elif current == previous:
            return 0
        elif current > previous:
            return 1
        elif current < previous:
            return -1

def get_class(value, thresholds, classes):
    for i, threshold in enumerate(thresholds):
        if value < threshold:
            return classes[i]
    return  classes[-1]

def convert_attention_to_class_fuse_back_to_accumulator(accumulated_metrics,attention_rates,type="categorical"):
    
    len_attention_rates = len(attention_rates)

    if type == "categorical":
        if len_attention_rates > 0 and len_attention_rates  == 1:
            attention_class = 'low'
            accumulated_metrics[0][7] = "low"
            return accumulated_metrics
        elif len_attention_rates > 0:
            previous_robust_z = None
            median_x,mad = compute_median_and_mad(np.array(attention_rates))

            if attention_rates[0] <= 0:
                accumulated_metrics[0][7] = "low"
            else:
                robust_z = (attention_rates[0] - median_x) / mad
                accumulated_metrics[0][7] = get_class(robust_z, [-1, 1], ["low", "medium", "high"])+" and "+get_progression(None, robust_z)
                previous_robust_z = robust_z
            for i in range(1, len(attention_rates)):
                x = attention_rates[i]

                if x <= 0:
                    accumulated_metrics[i][7] = "low"
                    continue    

                robust_z = (x - median_x) / mad
                accumulated_metrics[i][7] = get_class(robust_z, [-1, 1], ["low", "medium", "high"])+" and "+get_progression(previous_robust_z, robust_z)
                previous_robust_z = robust_z
    else:
        if len_attention_rates > 0 and len_attention_rates  == 1:
            accumulated_metrics[0][7] = [normalized_value_to_percentage(0), 0]
            return accumulated_metrics
        elif len_attention_rates > 0:
            previous_robust_z = None
            median_x,mad = compute_median_and_mad(np.array(attention_rates))
            if attention_rates[0] <= 0:
                accumulated_metrics[0][7] = [0, 0]
            else:    
                robust_z = (attention_rates[0] - median_x) / mad
                accumulated_metrics[0][7] = [normalized_value_to_percentage(robust_z), get_progression(None, robust_z,"numerical")]
                previous_robust_z = robust_z
            for i in range(1, len(attention_rates)):
                x = attention_rates[i]
                if x <= 0:
                    accumulated_metrics[i][7] = [0, 0]
                    continue  
                robust_z = (x - median_x) / mad
                accumulated_metrics[i][7] = [normalized_value_to_percentage(robust_z), get_progression(previous_robust_z, robust_z,"numerical")]
                previous_robust_z = robust_z            
    return accumulated_metrics

def normalized_value_to_percentage(x):

    # clip first
    x = max(-2, min(2, x))

    if x < -0.5:
        # low: [-2, -0.5] -> [0, 33]
        return ((x - (-2)) / (-0.5 - (-2))) * 33
    elif x <= 0.5:
        # medium: [-0.5, 0.5] -> [34, 66]
        return ((x - (-0.5)) / (0.5 - (-0.5))) * (66 - 34) + 34
    else:
        # high: [0.5, 2] -> [67, 100]
        return ((x - 0.5) / (2 - 0.5)) * (100 - 67) + 67  
    
def compute_average(list_of_values):
    if not list_of_values:
        return 0
    return sum(list_of_values) / len(list_of_values)

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
            fwrite.writerow({'Group ID':metrics[0],
                            'Group Name':metrics[1],
                            'Time Range (s)':str(metrics[2][0])+'-'+str(metrics[2][1]),
                            'Facial Emotion': metrics[3],
                            'Object Focus On': metrics[4],
                            'Attention Level': metrics[5],
                            'Attention Rate': metrics[6],
                            "Attention Class":metrics[7],
                            'Speaker Tag': metrics[8],
                            })  

def synthesized_video_metrics(videoMetrics, speaker, session_device,windowsize=10):
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
    focus_level = 0
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
                                        most_common_object,avg_attention,attention_rate,focus_level,speaker.alias])
            # Reset for next window
            facial_emotion = []
            object_on_focus = []
            attention_level = []
            newwindowstarted = False
            window_count += 1 
    accumulated_metrics_final = convert_attention_to_class_fuse_back_to_accumulator(accumulated_metrics,attention_rate_acc,type="numerical") 
    
    return accumulated_metrics_final

            
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
    prev_participation_score_value = prev_internal_cohesion_value = prev_responsivity_value = prev_social_impact_value = prev_newness_value = None
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
                val = round(compute_average(analytic), 2)
                analytic_thinking_val = get_class(val, [50, 51], ["Narrative thinking", "Balanced thinking", "Analytical thinking"])  + " and " + get_progression(prev_analytic_value, val)
                prev_analytic_value = val 
            else:
                analytic_thinking_val = 'None'
            if authenticity:
                val = round(compute_average(authenticity), 2)
                authenticity_val = get_class(val, [50, 51], ["Low", "Balanced", "High"]) + " and " + get_progression(prev_authenticity_value, val)
                prev_authenticity_value = val 
            else:
                authenticity_val = 'None'   
            if certainty:
                val = round(compute_average(certainty), 2)
                certainty_val = get_class(val, [50, 51], ["Low", "Medium", "High"]) + " and " + get_progression(prev_certainty_value, val)
                prev_certainty_value = val 
            else:
                certainty_val = 'None'
            if clout:
                val = round(compute_average(clout), 2)
                clout_val = get_class(val, [50, 51], ["Low", "Medium", "High"]) + " and " + get_progression(prev_clout_value, val)
                prev_clout_value = val
            else:
                clout_val = 'None'
            if emotionaL_tone: 
                val = round(compute_average(emotionaL_tone), 2)
                emotional_tone_val = get_class(val, [50, 51], ["Negative", "Neutral", "Positive"]) + " and " + get_progression(prev_emotional_tone_value, val)
                prev_emotional_tone_value = val
            else:
                emotional_tone_val = 'None'
            if participation_score:
                val = round(compute_average(participation_score), 2)
                participation_score_val = get_class(val, [-0.75, -0.25,0.5,1.5], ["Minimal participation" ,"Low participation" , "Balanced participation", "High participation","Dominant participation"]) + " and " + get_progression(prev_participation_score_value, val)
                prev_participation_score_value = val
            else:
                participation_score_val = 'None'
            if internal_cohesion:
                val = round(compute_average(internal_cohesion), 2)
                internal_cohesion_val = get_class(val, [0.2, 0.5], ["Low", "Medium", "High"]) + " and " + get_progression(prev_internal_cohesion_value, val)
                prev_internal_cohesion_value = val
            else:
                internal_cohesion_val = 'None'
            if responsivity:
                val = round(compute_average(responsivity), 2)
                responsivity_val = get_class(val, [0.2, 0.5], ["Low", "Medium", "High"]) + " and " + get_progression(prev_responsivity_value, val)
                prev_responsivity_value = val
            else:
                responsivity_val = 'None'
            if social_impact:
                val = round(compute_average(social_impact), 2)
                social_impact_val = get_class(val, [0.2, 0.5], ["Low", "Medium", "High"]) + " and " + get_progression(prev_social_impact_value, val)
                prev_social_impact_value = val
            else:
                social_impact_val = 'None'
            if newness:
                val = round(compute_average(newness), 2)
                newness_val = get_class(val, [0.2, 0.5], ["Low", "Medium", "High"]) + " and " + get_progression(prev_newness_value, val)
                prev_newness_value = val
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
                    fwrite.writerow({'Group ID':session_device.id,
                            'Group Name':session_device.name,
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

def synthesized_transcript_metrics(transcriptSpeakerMetric, speaker, session_device,keywords,windowsize=10):
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
    prev_participation_score_value = prev_internal_cohesion_value = prev_responsivity_value = prev_social_impact_value = prev_newness_value = None
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
                val = round(compute_average(analytic), 2)
                analytic_thinking_val = [val, get_progression(prev_analytic_value, val,"numerical")]
                prev_analytic_value = val 
            else:
                analytic_thinking_val = 0
            if authenticity:
                val = round(compute_average(authenticity), 2)
                authenticity_val = [val, get_progression(prev_authenticity_value, val,"numerical")]
                prev_authenticity_value = val 
            else:
                authenticity_val = 0   
            if certainty:
                val = round(compute_average(certainty), 2)
                certainty_val = [val, get_progression(prev_certainty_value, val,"numerical")]
                prev_certainty_value = val 
            else:
                certainty_val = 0
            if clout:
                val = round(compute_average(clout), 2)
                clout_val = [val, get_progression(prev_clout_value, val,"numerical")]
                prev_clout_value = val
            else:
                clout_val = 0
            if emotionaL_tone: 
                val = round(compute_average(emotionaL_tone), 2)
                emotional_tone_val = [val, get_progression(prev_emotional_tone_value, val,"numerical")]
                prev_emotional_tone_value = val
            else:
                emotional_tone_val = 0
            if participation_score:
                val = round(compute_average(participation_score), 2)
                participation_score_val = [normalized_value_to_percentage(val), get_progression(prev_participation_score_value, val,"numerical")]
                prev_participation_score_value = val
            else:
                participation_score_val = 0
            if internal_cohesion:
                val = round(compute_average(internal_cohesion), 2)
                internal_cohesion_val = [val*100, get_progression(prev_internal_cohesion_value, val,"numerical")]
                prev_internal_cohesion_value = val
            else:
                internal_cohesion_val = 0
            if responsivity:
                val = round(compute_average(responsivity), 2)
                responsivity_val = [val*100, get_progression(prev_responsivity_value, val,"numerical")]
                prev_responsivity_value = val
            else:
                responsivity_val = 0
            if social_impact:
                val = round(compute_average(social_impact), 2)
                social_impact_val = [val*100, get_progression(prev_social_impact_value, val,"numerical")]
                prev_social_impact_value = val
            else:
                social_impact_val = 0
            if newness:
                val = round(compute_average(newness), 2)
                newness_val = [val*100, get_progression(prev_newness_value, val,"numerical")]
                prev_newness_value = val
            else:
                newness_val = 0
            
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
    

            if keywords_window:            
                keywords_val = ' '.join(keywords_window)
            else:
                keywords_val = ''

            accumulated_metrics.append([session_device.id,session_device.name,[start,end],transcript_val,
                                        keywords_val,keywords_detected_val,analytic_thinking_val,
                                        authenticity_val,certainty_val,clout_val,emotional_tone_val,participation_score_val,
                                        internal_cohesion_val,responsivity_val,social_impact_val,newness_val,
                                        word_count_val,t.speaker_tag])
                

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
        fwrite.writerow({'Group ID':metrics[0],
                            'Group Name': metrics[1],
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

def extract_videometrics_within_window(videoMetrics, window_start, window_end, index):
    metric_len = len(videoMetrics)
    metrics = []
    while index < metric_len: 
        if videoMetrics[index].time_stamp >= window_start and videoMetrics[index].time_stamp < window_end:
            metrics.append(videoMetrics[index])
        else:
            break    
        index += 1
    return metrics, index

def extract_transcriptmetrics_within_window(transcriptMetrics, window_start, window_end, index):
    metric_len = len(transcriptMetrics)
    metrics = []
    while index < metric_len: 
        if transcriptMetrics[index].start_time >= window_start and transcriptMetrics[index].start_time < window_end:
            metrics.append(transcriptMetrics[index])
        else:
            break    
        index += 1
    return metrics, index

def synthesized_transcript_video_metrics_by_window(transcriptSpeakerMetric,videoMetrics,speaker,session_device,keywords,windowsize=10):
    v_index = t_index = 0
    min_start = min(videoMetrics[0].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[0][0].start_time if transcriptSpeakerMetric else 0)
    max_end = max(videoMetrics[-1].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[-1][0].start_time if transcriptSpeakerMetric else 0)
    window_start = min_start
    window_end = min_start+windowsize
    while window_end < max_end:
        window_video_metrics, v_index = extract_videometrics_within_window(videoMetrics, window_start, window_end, v_index)
        window_transcript_metrics, t_index = extract_transcriptmetrics_within_window(transcriptSpeakerMetric, window_start, window_end, t_index)

        # align transcript and video metrics within the window so that transcript and video metrics with same time ranges are combined
        aligned_combined_metrics = align_and_combine_metrics(window_video_metrics, window_transcript_metrics)

        window_start = window_end
        window_end += windowsize

def align_and_combine_metrics(video_metrics, transcript_metrics):
    # Align video and transcript metrics by time ranges and combine them
    aligned_metrics = []
    vidLen = len(video_metrics)
    transLen = len(transcript_metrics)
    lv,lt = 0,0
    while lv < vidLen and lt < transLen:
        v_metrics = video_metrics[lv]
        t_metrics = transcript_metrics[lt]
    return aligned_metrics

def synthesized_transcript_video_metrics(transcriptSpeakerMetric,videoMetrics,speaker,session_device,keywords,windowsize=10):
    """
    Accumulate both transcript and video metrics over specified window size.
    """
    accumulated_metrics = []
    facial_expression = {'serious':0.9,'neutral':0.8,'surprise':0.7,'happy':0.6,'sad':0.4,'fear':0.3,'disgust':0.2}
    transcript_metrics = synthesized_transcript_metrics(transcriptSpeakerMetric,speaker,session_device,keywords,windowsize=windowsize)
    video_metrics = synthesized_video_metrics(videoMetrics,speaker,session_device,windowsize=windowsize)
    vidLen = len(video_metrics)
    transLen = len(transcript_metrics)
    lv,lt = 0,0
    window_id = ""
    focusscore=[]
    participationscore=[]
    responsivityscore=[]
    enagementscore=[]
    reasoningscore=[]
    leadershipscore=[]
    initiativescore=[]
    ideacontributionscore=[]
    heading = ['windowid','groupid','groupname','starttime','endtime','transcript','keywords','keywordsdetected','analyticthinking','authenticity','certainty','clout',
               'emotionaltone','internalcohesion','socialimpact','newness','wordcount','facialemotion','objectfocuson','rawfocusscore',
               'rawfocusrate','speakertag','silence',"focusscore",'participationscore','responsivity','engagementscore','reasoningscore','leadershipscore', 'initiativescore','ideacontributionscore']
    while lv < vidLen and lt < transLen:
        v_metrics = video_metrics[lv]
        t_metrics = transcript_metrics[lt]
        # Align by time range
        if v_metrics[2][1] <= t_metrics[2][0]:
            attention_level = v_metrics[7][0]
            facial_emotion = v_metrics[3]
            focusscore.append(attention_level)
            participationscore.append(0)
            responsivityscore.append(0)
            enagementscore.append(round((attention_level+facial_expression[facial_emotion])/2,2))
            reasoningscore.append(0)
            leadershipscore.append(0)
            initiativescore.append(0)
            ideacontributionscore.append(0)

            window_id = f"w_{v_metrics[2][0]}_{v_metrics[2][1]}_{v_metrics[-1]}"
            value = [window_id,v_metrics[0],v_metrics[1],v_metrics[2][0],v_metrics[2][1],'no speech','no keywords','no keyword detected',0,0,0,0,0,0,0,0,0,
                    v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[8],1,focusscore[-1],participationscore[-1],responsivityscore[-1],enagementscore[-1],
                    reasoningscore[-1],leadershipscore[-1],initiativescore[-1],ideacontributionscore[-1]]
            lv += 1
        elif t_metrics[2][1] <= v_metrics[2][0]:
            attention_level = 0
            facial_emotion = 0
            participation_level = t_metrics[11][0]
            analytic_thinking_level = t_metrics[6][0]
            authenticity_level = t_metrics[7][0]
            certainty_level = t_metrics[8][0]
            clout_level = t_metrics[9][0]
            internal_cohesion_level = t_metrics[12][0]
            emotional_tone_level = t_metrics[10][0]
            newness_level = t_metrics[15][0]
            focusscore.append(attention_level)
            participationscore.append(participation_level)
            responsivityscore.append(t_metrics[13][0])
            enagementscore.append(round((participation_level+emotional_tone_level)/2,2))
            reasoningscore.append(round((analytic_thinking_level+certainty_level+internal_cohesion_level)/3,2))
            ideacontributionscore.append(round((analytic_thinking_level+authenticity_level+newness_level)/3,2))
            initiativescore.append(round((certainty_level+participation_level+ideacontributionscore[-1])/3,2))
            leadershipscore.append(round((clout_level+initiativescore[-1])/2,2))

            window_id = f"w_{t_metrics[2][0]}_{t_metrics[2][1]}_{t_metrics[-1]}"

            value = [window_id,t_metrics[0],t_metrics[1],t_metrics[2][0],t_metrics[2][1],t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6][0],t_metrics[7][0],t_metrics[8][0],t_metrics[9][0],t_metrics[10][0],t_metrics[12][0],t_metrics[14][0],
                     t_metrics[15][0],t_metrics[16],"None","None",0,0,t_metrics[17],0,focusscore[-1],participationscore[-1],responsivityscore[-1],enagementscore[-1],
                    reasoningscore[-1],leadershipscore[-1],initiativescore[-1],ideacontributionscore[-1]]
            lt += 1
            
        else:
            attention_level = 0
            facial_emotion = v_metrics[3]
            participation_level = t_metrics[11][0]
            analytic_thinking_level = t_metrics[6][0]
            authenticity_level = t_metrics[7][0]
            certainty_level = t_metrics[8][0]
            clout_level = t_metrics[9][0]
            internal_cohesion_level = t_metrics[12][0]
            emotional_tone_level = t_metrics[10][0]
            newness_level = t_metrics[15][0]
            focusscore.append(attention_level)
            participationscore.append(participation_level)
            responsivityscore.append(t_metrics[13][0])
            enagementscore.append(round((focusscore[-1]+participation_level+emotional_tone_level+facial_expression[facial_emotion])/4,2))
            reasoningscore.append(round((analytic_thinking_level+certainty_level+internal_cohesion_level)/3,2))
            ideacontributionscore.append(round((analytic_thinking_level+authenticity_level+newness_level)/3,2))
            initiativescore.append(round((certainty_level+participation_level+ideacontributionscore[-1])/3,2))
            leadershipscore.append(round((clout_level+initiativescore[-1])/2,2))
            
            # Write combined metrics to CSV or return as list 
            st = min(v_metrics[2][0],t_metrics[2][0])
            en = max(v_metrics[2][1],t_metrics[2][1])

            window_id = f"w_{st}_{en}_{t_metrics[-1]}"
            value = [window_id,t_metrics[0],t_metrics[1],st,en,t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6][0],t_metrics[7][0],t_metrics[8][0],t_metrics[9][0],t_metrics[10][0],t_metrics[12][0],t_metrics[14][0],
                     t_metrics[15][0],t_metrics[16],"None","None",0,0,t_metrics[17],0,focusscore[-1],participationscore[-1],responsivityscore[-1],enagementscore[-1],
                    reasoningscore[-1],leadershipscore[-1],initiativescore[-1],ideacontributionscore[-1]]
            # Overlapping ranges, process both
            lv += 1
            lt += 1

        accumulated_metrics.append(value)          
        
    
    while lv < vidLen:
        v_metrics = video_metrics[lv]

        attention_level = v_metrics[7][0]
        facial_emotion = v_metrics[3]
        focusscore.append(attention_level)
        participationscore.append(0)
        responsivityscore.append(0)
        enagementscore.append(round((attention_level+facial_expression[facial_emotion])/2,2))
        reasoningscore.append(0)
        leadershipscore.append(0)
        initiativescore.append(0)
        ideacontributionscore.append(0)
        window_id = f"w_{v_metrics[2][0]}_{v_metrics[2][1]}_{v_metrics[-1]}"
        value = [window_id,v_metrics[0],v_metrics[1],v_metrics[2][0],v_metrics[2][1],'no speech','no keywords','no keyword detected',0,0,0,0,0,0,0,0,0,
                    v_metrics[3],v_metrics[4],v_metrics[5],v_metrics[6],v_metrics[8],1,focusscore[-1],participationscore[-1],responsivityscore[-1],enagementscore[-1],
                    reasoningscore[-1],leadershipscore[-1],initiativescore[-1],ideacontributionscore[-1]]
        
        accumulated_metrics.append(value)
        lv += 1

    while lt < transLen:
        t_metrics = transcript_metrics[lt]

        attention_level = 0
        facial_emotion = 0
        participation_level = t_metrics[11][0]
        analytic_thinking_level = t_metrics[6][0]
        authenticity_level = t_metrics[7][0]
        certainty_level = t_metrics[8][0]
        clout_level = t_metrics[9][0]
        internal_cohesion_level = t_metrics[12][0]
        emotional_tone_level = t_metrics[10][0]
        newness_level = t_metrics[15][0]
        focusscore.append(attention_level)
        participationscore.append(participation_level)
        responsivityscore.append(t_metrics[13][0])
        enagementscore.append(round((participation_level+emotional_tone_level)/2,2))
        reasoningscore.append(round((analytic_thinking_level+certainty_level+internal_cohesion_level)/3,2))
        ideacontributionscore.append(round((analytic_thinking_level+authenticity_level+newness_level)/3,2))
        initiativescore.append(round((certainty_level+participation_level+ideacontributionscore[-1])/3,2))
        leadershipscore.append(round((clout_level+initiativescore[-1])/2,2))

        window_id = f"w_{t_metrics[2][0]}_{t_metrics[2][1]}_{t_metrics[-1]}"
        
        value = [window_id,t_metrics[0],t_metrics[1],t_metrics[2][0],t_metrics[2][1],t_metrics[3],t_metrics[4],t_metrics[5],
                     t_metrics[6][0],t_metrics[7][0],t_metrics[8][0],t_metrics[9][0],t_metrics[10][0],t_metrics[12][0],t_metrics[14][0],
                     t_metrics[15][0],t_metrics[16],"None","None",0,0,t_metrics[17],0,focusscore[-1],participationscore[-1],responsivityscore[-1],enagementscore[-1],
                    reasoningscore[-1],leadershipscore[-1],initiativescore[-1],ideacontributionscore[-1]]
        
        accumulated_metrics.append(value)
        lt += 1    
    
    
    #computer session level metrics
    session_metrics=[]
    session_metrics_label = ['avg_focusscore','avg_participationscore','avg_responsivity','avg_engagementscore','avg_reasoningscore','avg_leadershipscore', 'avg_initiativescore','avg_ideacontributionscore']
    session_metrics.append(round(compute_average(focusscore),2))
    session_metrics.append(round(compute_average(participationscore),2))
    session_metrics.append(round(compute_average(responsivityscore),2))
    session_metrics.append(round(compute_average(enagementscore),2))           
    session_metrics.append(round(compute_average(reasoningscore),2))
    session_metrics.append(round(compute_average(leadershipscore),2))
    session_metrics.append(round(compute_average(initiativescore),2))
    session_metrics.append(round(compute_average(ideacontributionscore),2))

    window_metrics_dict = [dict(zip(heading, row)) for row in accumulated_metrics] 
    session_metrics_dict = dict(zip(session_metrics_label,session_metrics))
    return { "window_metrics": window_metrics_dict, "session_metrics": session_metrics_dict}
