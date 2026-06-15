from collections import Counter,defaultdict
import numpy as np
from scipy.stats import median_abs_deviation
import statistics
import logging
from utility import compute_median_and_mad,get_progression,get_class,convert_attention_to_class_fuse_back_to_accumulator,normalized_value_to_percentage \
    ,convert_to_participation_share,get_last_metric_value,compute_average,compute_base_collaboration_metric,compute_slope,normalize_slope,label_trajectory,clean_metric_history

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
        if(v.time_stamp >= start and v.time_stamp >= end) or l == n:
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
        if(t.start_time >= start and t.start_time >= end) or l == n:
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
            keywords_window = []
            keywords_detected_window = []
            similarity_window = []
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


def extract_videometrics_within_window(videoMetrics,speakers,speakers_obj, window_start, window_end, index):
    metric_len = len(videoMetrics)
    metrics = defaultdict(dict)
    while index < metric_len: 
        if videoMetrics[index].time_stamp >= window_start and videoMetrics[index].time_stamp < window_end:
            v = videoMetrics[index]
            speaker_id = speakers_obj[v.student_username]
            if  speaker_id not in metrics:
                if speaker_id not in speakers:
                    speakers[speaker_id] = v.student_username
                metrics[speaker_id]={'facial_emotion':[str(v.facial_emotion)],'object_on_focus':[str(v.object_on_focus)],'attention_level':[int(v.attention_level)]}
            else:
                metrics[speaker_id]['facial_emotion'].append(str(v.facial_emotion)) 
                metrics[speaker_id]['object_on_focus'].append(str(v.object_on_focus)) 
                metrics[speaker_id]['attention_level'].append(int(v.attention_level)) 
        else:
            break    
        index += 1
    return metrics, index

def extract_transcriptmetrics_within_window(transcriptSpeakerMetric,all_participants_transcript,speakers, keywords,window_start, window_end, index):
    metric_len = len(transcriptSpeakerMetric)
    metrics = defaultdict(dict)
    prev_trans_id = None
    trans_id = None
    while index < metric_len: 
        t = transcriptSpeakerMetric[index]['transcript']

        if int(t.speaker_id) == -1:
            index += 1
            continue
        
        speakerMetrics = transcriptSpeakerMetric[index]['speaker_metrics']
        if t.start_time >= window_start and t.start_time < window_end:
            trans_id = t.id
            transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
            keyword_similarity_score = [round((1-keyword.similarity)*100,3) for keyword in transcript_keywords]  
            if  t.speaker_id not in metrics:
                if t.speaker_id not in speakers:
                    speakers[t.speaker_id] = t.speaker_tag
                prev_trans_id = t.id
                metrics[t.speaker_id]={'analytic':[int(t.analytic_thinking_value)],
                                        'authenticity':[int(t.authenticity_value)],
                                        'certainty':[int(t.certainty_value)],
                                        'clout':[int(t.clout_value)],
                                        'emotionaL_tone':[int(t.emotional_tone_value)],
                                        'participation_score':[],
                                        'internal_cohesion':[],
                                        'responsivity':[],
                                        'social_impact':[],
                                        'newness':[],
                                        'word_count':[int(t.word_count)],
                                        'words_per_window':[str(t.transcript)],
                                        'keywords':[', '.join([keyword.keyword for keyword in transcript_keywords])],
                                        'keyword_similarity_score':[compute_average(keyword_similarity_score)]}
                for sm in speakerMetrics:
                    #newness is strictly based on the actual verbal contributions by the participants
                    # if t.speaker_id == sm.speaker_id:
                    #     metrics[sm.speaker_id]['newness'].append(float(sm.newness))
                    if sm.speaker_id not in metrics:
                        metrics[sm.speaker_id]={'analytic':[],
                                        'authenticity':[],
                                        'certainty':[],
                                        'clout':[],
                                        'emotionaL_tone':[],
                                        'participation_score':[float(sm.participation_score)],
                                        'internal_cohesion':[float(sm.internal_cohesion)],
                                        'responsivity':[float(sm.responsivity)],
                                        'social_impact':[float(sm.social_impact)],
                                        'newness':[float(sm.newness)],
                                        'word_count':[],
                                        'words_per_window':[],
                                        'keywords':[],
                                        'keyword_similarity_score':[]}

                    else:
                        metrics[sm.speaker_id]['participation_score'].append(float(sm.participation_score))  
                        metrics[sm.speaker_id]['internal_cohesion'].append(float(sm.internal_cohesion))
                        metrics[sm.speaker_id]['responsivity'].append(float(sm.responsivity))
                        metrics[sm.speaker_id]['social_impact'].append(float(sm.social_impact))  
                        metrics[sm.speaker_id]['newness'].append(float(sm.newness)) 
                
            else:
                metrics[t.speaker_id]['analytic'].append(int(t.analytic_thinking_value))
                metrics[t.speaker_id]['authenticity'].append(int(t.authenticity_value))
                metrics[t.speaker_id]['certainty'].append(int(t.certainty_value))  
                metrics[t.speaker_id]['clout'].append(int(t.clout_value))
                metrics[t.speaker_id]['emotionaL_tone'].append(int(t.emotional_tone_value))
                metrics[t.speaker_id]['word_count'].append(int(t.word_count)),
                metrics[t.speaker_id]['words_per_window'].append(str(t.transcript))
                metrics[t.speaker_id]['keywords'].append(', '.join([keyword.keyword for keyword in transcript_keywords]))
                metrics[t.speaker_id]['keyword_similarity_score'].append(compute_average(keyword_similarity_score))

                for sm in speakerMetrics:
                    # if t.speaker_id == sm.speaker_id:
                    #     metrics[sm.speaker_id]['newness'].append(float(sm.newness))
                    if sm.speaker_id not in metrics:
                        metrics[sm.speaker_id]={'analytic':[],
                                        'authenticity':[],
                                        'certainty':[],
                                        'clout':[],
                                        'emotionaL_tone':[],
                                        'participation_score':[float(sm.participation_score)],
                                        'internal_cohesion':[float(sm.internal_cohesion)],
                                        'responsivity':[float(sm.responsivity)],
                                        'social_impact':[float(sm.social_impact)],
                                        'newness':[float(sm.newness)],
                                        'word_count':[],
                                        'words_per_window':[],
                                        'keywords':[],
                                        'keyword_similarity_score':[]}

                    else:
                        metrics[sm.speaker_id]['participation_score'].append(float(sm.participation_score))  
                        metrics[sm.speaker_id]['internal_cohesion'].append(float(sm.internal_cohesion))
                        metrics[sm.speaker_id]['responsivity'].append(float(sm.responsivity))
                        metrics[sm.speaker_id]['social_impact'].append(float(sm.social_impact))  
                        metrics[sm.speaker_id]['newness'].append(float(sm.newness))

            all_participants_transcript.append([str(window_start)+"-"+str(window_end),t.speaker_tag,str(t.transcript)])
                
        else:
            break    
        index += 1  
    return metrics, index

def aggregate_video_metric_per_window(videoMetrics_per_window,windowsize,window_count,prev_metric):
    facial_emotion = videoMetrics_per_window['facial_emotion']
    object_on_focus = videoMetrics_per_window['object_on_focus']
    attention_level = videoMetrics_per_window['attention_level']
    
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
        avg_attention = 0
        attention_rate = 0
    prev_attention_rate = prev_metric[20]
    trend_direction = get_progression(prev_attention_rate, attention_rate,"numerical")
    gazeontask =  1 if trend_direction >= 0 else 0
    return [most_common_emotion,most_common_object,avg_attention,attention_rate,'focus_level',trend_direction,gazeontask]

def aggregate_transcript_metric_per_window(transcriptMetrics_per_window,prev_metric,noofspeakers):
    val = []
    analytic = transcriptMetrics_per_window['analytic']
    authenticity = transcriptMetrics_per_window['authenticity']
    certainty = transcriptMetrics_per_window['certainty'] 
    clout = transcriptMetrics_per_window['clout']
    emotionaL_tone = transcriptMetrics_per_window['emotionaL_tone']
    participation_score = transcriptMetrics_per_window['participation_score']
    internal_cohesion = transcriptMetrics_per_window['internal_cohesion']
    responsivity = transcriptMetrics_per_window['responsivity']
    social_impact = transcriptMetrics_per_window['social_impact']
    newness = transcriptMetrics_per_window['newness']
    word_count = transcriptMetrics_per_window['word_count']
    words_per_window = transcriptMetrics_per_window['words_per_window']
    keywords = transcriptMetrics_per_window['keywords']
    keyword_similarity_score = transcriptMetrics_per_window['keyword_similarity_score']
    trend_direction = []
    
    _,_,_,_,_,_,prev_keyword_similarity_score_val, prev_analytic_thinking_val, prev_authenticity_val, prev_certainty_val, prev_clout_val, prev_emotional_tone_val, \
    prev_participation_score_val, prev_internal_cohesion_val,prev_responsivity_val,prev_social_impact_val,prev_newness_val,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_ = prev_metric
    # Accumulate metrics for the window
    if analytic:
        val = compute_average(analytic)
        analytic_thinking_val = val
        trend_direction.append(get_progression(prev_analytic_thinking_val, val,"numerical"))
    else:
        analytic_thinking_val = 0
    if authenticity:
        val = compute_average(authenticity)
        authenticity_val = val
        trend_direction.append(get_progression(prev_authenticity_val, val,"numerical"))
    else:
        authenticity_val = 0   
    if certainty:
        val = compute_average(certainty)
        certainty_val = val
        trend_direction.append(get_progression(prev_certainty_val, val,"numerical"))
    else:
        certainty_val = 0
    if clout:
        val = compute_average(clout)
        clout_val = val
        trend_direction.append(get_progression(prev_clout_val, val,"numerical"))
    else:
        clout_val = 0
    if emotionaL_tone: 
        val = compute_average(emotionaL_tone)
        emotional_tone_val = val
        trend_direction.append(get_progression(prev_emotional_tone_val, val,"numerical"))
    else:
        emotional_tone_val = 0
    if participation_score:
        particpation_shares = convert_to_participation_share(participation_score,noofspeakers)
        participation_score_val = particpation_shares
        trend_direction.append(get_progression(prev_participation_score_val, participation_score_val,"numerical"))
    else:
        participation_score_val = 0
    if internal_cohesion:
        val = get_last_metric_value(internal_cohesion)
        internal_cohesion_val = val*100
        trend_direction.append(get_progression(prev_internal_cohesion_val, val,"numerical"))
    else:
        internal_cohesion_val = 0
    if responsivity:
        val = get_last_metric_value(responsivity)
        responsivity_val = val*100
        trend_direction.append(get_progression(prev_responsivity_val, val,"numerical")) 
    else:
        responsivity_val = 0
    if social_impact:
        val = get_last_metric_value(social_impact)
        social_impact_val = val*100
        trend_direction.append(get_progression(prev_social_impact_val, val,"numerical"))
    else:
        social_impact_val = 0
    if newness:
        val = get_last_metric_value(newness) #compute_average(newness)
        newness_val = val*100
        trend_direction.append(get_progression(prev_newness_val, val,"numerical"))
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
    if keywords:
        keywords_val = ' '.join(keywords)
    else:
        keywords_val = ''

    if keyword_similarity_score:
        val = round(compute_average(keyword_similarity_score), 2)
        keyword_similarity_score_val = val
        trend_direction.append(get_progression(prev_keyword_similarity_score_val, val,"numerical"))
    else:
        keyword_similarity_score_val = 0


    return [transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val,certainty_val,clout_val,
            emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val,trend_direction]
        
def combine_transcript_video_metrics(video_metrics, transcript_metrics,window_id,window_start,window_end):
    # Align video and transcript metrics by time ranges and combine them
    if video_metrics and transcript_metrics:
        most_common_emotion,most_common_object,avg_attention,attention_rate,focus_level,v_trend_direction,gazeontask = video_metrics
        transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val,certainty_val,clout_val, \
            emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val,t_trend_direction = transcript_metrics
        
        t_trend_direction.append(v_trend_direction)
        most_common_trend_direction = Counter(t_trend_direction).most_common(1)[0][0]
        
        return [window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val,
                certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val,
                most_common_emotion,most_common_object,avg_attention,attention_rate,gazeontask,'focusscore[-1]','enagementscore[-1]','reasoningscore[-1]',
                'leadershipscore[-1]','initiativescore[-1]','ideacontributionscore[-1]',most_common_trend_direction,'momentum_val','verbalshare_val','turnshare_val']
    
    elif transcript_metrics:
        most_common_emotion = 'None'
        most_common_object = "None"
        avg_attention = 0
        attention_rate = 0
        gazeontask = 0
        transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val,certainty_val,clout_val, \
            emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val,trend_direction = transcript_metrics
        
        most_common_trend_direction = Counter(trend_direction).most_common(1)[0][0]
        return [window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val,
                certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val,
                most_common_emotion,most_common_object,avg_attention,attention_rate,gazeontask,'focusscore[-1]','enagementscore[-1]','reasoningscore[-1]',
                'leadershipscore[-1]','initiativescore[-1]','ideacontributionscore[-1]',most_common_trend_direction,'momentum_val','verbalshare_val','turnshare_val']
    
    elif video_metrics:
        most_common_emotion,most_common_object,avg_attention,attention_rate,focus_level,trend_direction,gazeontask = video_metrics

        return [window_id,window_start,window_end,'no speech',0,'no keywords',0,0,0,0,0,0,0,0,0,0,0,
                    most_common_emotion,most_common_object,avg_attention,attention_rate,gazeontask,'focusscore[-1]','enagementscore[-1]',
                    'reasoningscore[-1]','leadershipscore[-1]','initiativescore[-1]','ideacontributionscore[-1]',trend_direction,'momentum_val','verbalshare_val','turnshare_val']
    else:
        return None   

def get_total_verbal_turn_contribution_by_all_person_in_window(wind_metric_acc,persons):
    total_verbal_contributions = 0
    total_turn = 0
    for p in persons:
        total_verbal_contributions += wind_metric_acc[p][4]
        total_turn += 1 if wind_metric_acc[p][4] > 0 else 0

    return total_verbal_contributions,total_turn

def get_shared_focus_in_window(wind_metric_acc,persons,objectFocus):
    if objectFocus == "None":
        return 0
    overlapfocus = 0
    for p in persons:
        if objectFocus == wind_metric_acc[p][18]:
            overlapfocus += 1
    return  overlapfocus/len(persons) if len(persons) > 0 else 0     

def compute_collaboration_trajectory(social_impact_history,responsivity_history,participation_share_history,percent_scale=True,remove_missing_zeros=True):
    """
    Computes BLINC collaboration trajectory.

    Combines:
    - overall performance across the session
    - direction/rate of change across windows

    Returns a value between 0 and 1.
    """
    si = clean_metric_history(social_impact_history, percent_scale, remove_missing_zeros)
    rp = clean_metric_history(responsivity_history, percent_scale, remove_missing_zeros)
    ps = clean_metric_history(participation_share_history, percent_scale, remove_missing_zeros)

    min_len = min(len(si),len(rp),len(ps))

    if min_len < 2:
        return {
            "trajectory_score": 0.25,
            "auc_score": 0.0,
            "raw_slope": 0.0,
            "normalized_slope": 0.25,
            "label": "Insufficient data"
        }


    si = si[-min_len:]
    rp = rp[-min_len:]
    ps = ps[-min_len:]

    base_metric_history = compute_base_collaboration_metric(si,rp, ps)

    auc_score = float(np.mean(base_metric_history))

    slope = compute_slope(base_metric_history)

    normalized_slope = normalize_slope(slope=slope,n_windows=len(base_metric_history))
    trajectory_score = (0.6 * auc_score + 0.4 * normalized_slope)

    return {"trajectory_score": float(np.clip(trajectory_score, 0, 1)),
            "auc_score": auc_score,
            "raw_slope": slope,
            "normalized_slope": normalized_slope,
            "base_metric_history": base_metric_history.tolist(),
            "label": label_trajectory(trajectory_score)
            }

def compute_derived_metric_and_update(metric_acc_per_window,all_windows,speakerDetail,total_windows,total_verbal_turn_acc,speakeralias,median_x,mad,Combined_object,group_level_metric_acc,total_speaker_detected,object_of_interest_focus,no_of_participants):
    speaker_window_metrics = None
    analyticthinking = []
    authenticity = []
    certainty = []
    clout = []
    session_internalcohesion = 0
    session_socialimpact = 0
    participation_share=[]
    responsivity=[]
    social_impact = []
    internal_cohesion=[]
    newness = []
    session_particpantion_score = 0
    session_responsivity=0
    session_newness=0
    focusscore=[]
    enagementscore=[]
    reasoningscore=[]
    leadershipscore=[]
    initiativescore=[]
    ideacontributionscore=[]
    session_trend = []
    speakingalignmentscore = []
    momentum = []
    turnshare = []
    verbalshare = []
    speaking_word_count = []
    shared_task_focus = []
    focused_gazeOn_task = 0
    
    # logging.info("object of interest focus: {0}".format(object_of_interest_focus))

    facial_expression = {'serious':0.9,'neutral':0.8,'surprise':0.7,'happy':0.6,'sad':0.4,'fear':0.3,'disgust':0.2}

    
    metric_heading = ['windowid','starttime','endtime','transcript','wordcount','keywords','speaking_alignment','analyticthinking','authenticity','certainty','clout',
               'emotionaltone','participationscore','internalcohesion','responsivityscore','socialimpact','newness','facialemotion','objectfocuson','rawfocusscore',
               'rawfocusrate','gazeontask',"focusscore",'engagementscore','reasoningscore','leadershipscore', 'initiativescore','ideacontributionscore','trenddirection','momentum','verbalshare','turntaking']
    
    previous_trend = None
    ## FOR COMPUTING METRIC VALUE ACROSS THE WINDOWS
    # for window_id in all_windows:
    #     if window_id in speakerDetail:
    #         window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
    #         certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
    #         most_common_emotion,most_common_object,avg_attention,attention_rate,gazeontask,_,_,_,_,_,_,most_common_trend_direction,_,_,_ = speakerDetail[window_id]

    #         analyticthinking.append(analytic_thinking_val)
    #         authenticity.append(authenticity_val)
    #         certainty.append(certainty_val)
    #         clout.append(clout_val)
    #         internalcohesion.append(internal_cohesion_val)
    #         socialimpact.append(social_impact_val)
    #         newness.append(newness_val)

    #         focus_level = 0
    #         if mad != 0 and most_common_object != "None":
    #             robust_z = (attention_rate - median_x) / mad 
    #             focus_level = normalized_value_to_percentage(robust_z)

    #         focused_gazeOn_task = 1 if object_of_interest_focus and most_common_object in object_of_interest_focus else 0
    #         speaking = 1 if word_count_val > 0 else 0
    #         speaking_slience_focus = focused_gazeOn_task*50+ speaking*50
    #         facial_emotion = most_common_emotion
            
        
    #         stf = gazeontask/total_speaker_detected if total_speaker_detected > 0 else 0
    #         shared_task_focus.append(stf)
    #         focus = speaking_slience_focus if (focused_gazeOn_task > 0 and speaking > 0 ) else focused_gazeOn_task*100 if focused_gazeOn_task > 0 else speaking*100 if speaking > 0 else 0
    #         focusscore.append(focus)
    #         speakingalignmentscore.append(keyword_similarity_score_val)
    #         participationscore.append(participation_score_val)
    #         responsivityscore.append(responsivity_val)

    #         total_verbal_contri, total_turn  = get_total_verbal_turn_contribution_by_all_person_in_window(metric_acc_per_window[window_id],metric_acc_per_window[window_id]['persons'])
    #         comp_verbal_share = word_count_val/total_verbal_contri if total_verbal_contri > 0 else 0
    #         verbalshare.append(round((comp_verbal_share)*100,2))
    #         turn = 1 if word_count_val > 0 else 0
    #         comp_turn = turn/total_turn if total_turn > 0 else 0
    #         turnshare.append(round((comp_turn)*100,2))

    #         eng_score = round((focusscore[-1]+participation_score_val+turnshare[-1]+ verbalshare[-1])/4,2) if word_count_val > 0 and facial_emotion != "None" \
    #             else  round((focus_level),2)  if facial_emotion != "None" else round((participation_score_val+verbalshare[-1])/(2),2)

    #         # eng_score = round((focusscore[-1]+participation_score_val+emotional_tone_val+facial_expression[facial_emotion]+ speaking_slience_focus)/5,2) if word_count_val > 0 and facial_emotion != "None" \
    #         #     else  round((focus_level+facial_expression[facial_emotion]+ gazeontask*100)/3,2)  if facial_emotion != "None" else round((participation_score_val+emotional_tone_val+speaking*100)/3,2)
    #         enagementscore.append(eng_score)

    #         reason_score = 0 if word_count_val <= 0  else  round((analytic_thinking_val+certainty_val+internal_cohesion_val)/3,2)
    #         reasoningscore.append(reason_score)
            
    #         idea_score = 0 if word_count_val <= 0  else round((analytic_thinking_val+authenticity_val+newness_val)/3,2)
    #         ideacontributionscore.append(idea_score)

    #         initia_score = 0 if word_count_val <= 0  else round((certainty_val+participation_score_val+ideacontributionscore[-1])/3,2)
    #         initiativescore.append(initia_score)

    #         lead_score = 0 if word_count_val <= 0  else round((clout_val+initiativescore[-1])/2,2)
    #         leadershipscore.append(lead_score)

    #         momentum.append(round((focusscore[-1]+participation_score_val+verbalshare[-1])/3,2))

    #         avg_derivative_metric_val = round((participationscore[-1]+focusscore[-1]+enagementscore[-1]+reasoningscore[-1]+ideacontributionscore[-1]+initiativescore[-1]+leadershipscore[-1]+momentum[-1])/8,2)
    #         window_trend_dir = 1 if enagementscore[-1] >= 70 and focusscore[-1] >= 70 else 0 if  enagementscore[-1] >= 50 or focusscore[-1] >= 50 else -1 #    get_progression(previous_trend, avg_derivative_metric_val,"numerical")
    #         # previous_trend = avg_derivative_metric_val
    #         session_trend.append(window_trend_dir)

    #         if word_count_val > 0:
    #             speaking_word_count.append(word_count_val)

    #         speaker_window_metrics =[window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
    #         certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
    #         most_common_emotion,most_common_object,avg_attention,attention_rate,focused_gazeOn_task,focusscore[-1],enagementscore[-1],reasoningscore[-1],leadershipscore[-1], \
    #             initiativescore[-1],ideacontributionscore[-1],window_trend_dir,momentum[-1],verbalshare[-1],turnshare[-1]]
    #     else:
    #         analyticthinking.append(0)
    #         authenticity.append(0)
    #         certainty.append(0)
    #         clout.append(0)
    #         internalcohesion.append(0)
    #         socialimpact.append(0)
    #         newness.append(0)

    #         window_range = window_id.split('_')
    #         focusscore.append(0)
    #         enagementscore.append(0)
    #         reasoningscore.append(0)
    #         leadershipscore.append(0)
    #         initiativescore.append(0)
    #         ideacontributionscore.append(0)
    #         window_trend_dir = -1
    #         momentum.append(0)
    #         verbalshare.append(0)
    #         turnshare.append(0)
    #         speaker_window_metrics =[window_id,window_range[1], window_range[2], 'no speech',0,'no keywords', 0, 0, 0,  0, 0, 0, 0, 0, 0,0,0, 'None', 'None', 0, 0, 0,0,0,0,  0,0,0,-1,0,0,0]

    #     #update the derived value
    #     if window_id not in metric_acc_per_window and speakeralias not in metric_acc_per_window[window_id]:
    #         metric_acc_per_window[window_id][speakeralias][22] = focusscore[-1]
    #         metric_acc_per_window[window_id][speakeralias][23] = enagementscore[-1]
    #         metric_acc_per_window[window_id][speakeralias][24] = reasoningscore[-1]
    #         metric_acc_per_window[window_id][speakeralias][25] = leadershipscore[-1]
    #         metric_acc_per_window[window_id][speakeralias][26] = initiativescore[-1]
    #         metric_acc_per_window[window_id][speakeralias][27] = ideacontributionscore[-1]
    #         metric_acc_per_window[window_id][speakeralias][28] = window_trend_dir
    #         metric_acc_per_window[window_id][speakeralias][29] = momentum[-1]
    #         metric_acc_per_window[window_id][speakeralias][30] = verbalshare[-1]
    #         metric_acc_per_window[window_id][speakeralias][31] = turnshare[-1]

    #     if window_id not in Combined_object['window_level']:
    #         Combined_object['window_level'][window_id] = {speakeralias : dict(zip(metric_heading,speaker_window_metrics))}
    #     else:
    #         Combined_object['window_level'][window_id][speakeralias] = dict(zip(metric_heading,speaker_window_metrics))


    #     if speakeralias not in Combined_object['participants_level']:
    #         Combined_object['participants_level'][speakeralias] = [dict(zip(metric_heading,speaker_window_metrics))]
    #     else:
    #         Combined_object['participants_level'][speakeralias].append(dict(zip(metric_heading,speaker_window_metrics)))
    
    ## FOR COMPUTING METRIC VALUE BASED ON EXPLICITLY WHAT THE SPEAKER ACCUMULATED
    for i , data in enumerate(speakerDetail):
        
        window_id,_,_,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
        certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
        most_common_emotion,most_common_object,_,attention_rate,gazeontask,_,_,_,_,_,_,most_common_trend_direction,_,_,_ = data

        analyticthinking.append(analytic_thinking_val)
        authenticity.append(authenticity_val)
        certainty.append(certainty_val)
        clout.append(clout_val)
        participation_share.append(participation_score_val)
        responsivity.append(responsivity_val)
        social_impact.append(social_impact_val)
        internal_cohesion.append(internal_cohesion_val)
        newness.append(newness_val)

        session_particpantion_score = participation_score_val if participation_score_val > 0 else session_particpantion_score
        session_internalcohesion =  internal_cohesion_val if internal_cohesion_val > 0 else session_internalcohesion 
        session_socialimpact =  social_impact_val if social_impact_val > 0 else session_socialimpact 
        session_responsivity =  responsivity_val if responsivity_val > 0 else session_responsivity 
        session_newness = newness_val if newness_val > 0 else session_newness
        
        focus_level = 0
        if mad != 0 and most_common_object != "None":
           robust_z = (attention_rate - median_x) / mad 
           focus_level = normalized_value_to_percentage(robust_z)

        focused_gazeOn_task = 1 if object_of_interest_focus and most_common_object in object_of_interest_focus else 0
        speaking = 1 if word_count_val > 0 else 0
        speaking_slience_focus = focused_gazeOn_task*50+ speaking*50
        facial_emotion = most_common_emotion
        
       
        stf = get_shared_focus_in_window(metric_acc_per_window[window_id],metric_acc_per_window[window_id]['persons'],most_common_object) # gazeontask/total_speaker_detected if total_speaker_detected > 0 else 0
        shared_task_focus.append(stf)
       
        speakingalignmentscore.append(keyword_similarity_score_val)
       

        total_verbal_contri, total_turn  = get_total_verbal_turn_contribution_by_all_person_in_window(metric_acc_per_window[window_id],metric_acc_per_window[window_id]['persons'])
        comp_verbal_share = word_count_val/total_verbal_contri if total_verbal_contri > 0 else 0
        verbalshare.append(comp_verbal_share*100)
        turn = 1 if word_count_val > 0 else 0
        comp_turn = turn/total_turn if total_turn > 0 else 0
        turnshare.append(comp_turn*100)

        focus = focus_level #(focus_level+participation_score_val)/2 if (focus_level > 0 and speaking > 0 ) else focus_level if focus_level > 0 else verbalshare[-1]  if speaking > 0 else 0
        focusscore.append(focus)

        # eng_score = (focusscore[-1]+participation_score_val+turnshare[-1]+ verbalshare[-1])/4 if word_count_val > 0 and facial_emotion != "None" \
        #     else  (focus_level)  if facial_emotion != "None" else (participation_score_val+verbalshare[-1])/(2)
        eng_score = (0.4*focusscore[-1])+(0.3*participation_score_val)+(0.3*responsivity_val)

        # eng_score = round((focusscore[-1]+participation_score_val+emotional_tone_val+facial_expression[facial_emotion]+ speaking_slience_focus)/5,2) if word_count_val > 0 and facial_emotion != "None" \
        #     else  round((focus_level+facial_expression[facial_emotion]+ gazeontask*100)/3,2)  if facial_emotion != "None" else round((participation_score_val+emotional_tone_val+speaking*100)/3,2)
        enagementscore.append(eng_score)

        reason_score = 0 if word_count_val <= 0  else  (analytic_thinking_val+certainty_val+internal_cohesion_val)/3
        reasoningscore.append(reason_score)
        
        idea_score = ((newness_val*0.3)+(social_impact_val*0.7))#0 if word_count_val <= 0  else (analytic_thinking_val+authenticity_val+newness_val)/3
        ideacontributionscore.append(idea_score)

        initia_score = 0 if word_count_val <= 0  else (certainty_val+participation_score_val+idea_score)/3
        initiativescore.append(initia_score)

        lead_score = (0.2*participation_score_val)+(0.5*social_impact_val)+(0.3*responsivity_val)  #0 if word_count_val <= 0  else (clout_val+initiativescore[-1])/2
        leadershipscore.append(lead_score)

        momentum.append((focusscore[-1]+participation_score_val)/2)

        avg_derivative_metric_val = round((participation_score_val+focusscore[-1]+enagementscore[-1]+reasoningscore[-1]+ideacontributionscore[-1]+initiativescore[-1]+leadershipscore[-1]+momentum[-1])/8,2)
        window_trend_dir = 1 if enagementscore[-1] >= 70 and focusscore[-1] >= 70 else 0 if  enagementscore[-1] >= 50 or focusscore[-1] >= 50 else -1 #    get_progression(previous_trend, avg_derivative_metric_val,"numerical")
        # previous_trend = avg_derivative_metric_val
        session_trend.append(window_trend_dir)

        if word_count_val > 0:
            speaking_word_count.append(word_count_val)

        #update the derived value
        speakerDetail[i][22] = round(focusscore[-1],2)
        metric_acc_per_window[window_id][speakeralias][22] = round(focusscore[-1],2)
        speakerDetail[i][23] = round(enagementscore[-1],2)
        metric_acc_per_window[window_id][speakeralias][23] = round(enagementscore[-1],2)
        speakerDetail[i][24] = round(reasoningscore[-1],2)
        metric_acc_per_window[window_id][speakeralias][24] = round(reasoningscore[-1],2)
        speakerDetail[i][25] = round(leadershipscore[-1],2)
        metric_acc_per_window[window_id][speakeralias][25] = round(leadershipscore[-1],2)
        speakerDetail[i][26] = round(initiativescore[-1],2)
        metric_acc_per_window[window_id][speakeralias][26] = round(initiativescore[-1],2)
        speakerDetail[i][27] = round(ideacontributionscore[-1],2)
        metric_acc_per_window[window_id][speakeralias][27] = round(ideacontributionscore[-1],2)
        speakerDetail[i][28] = window_trend_dir
        metric_acc_per_window[window_id][speakeralias][28] = window_trend_dir
        speakerDetail[i][29] = round(momentum[-1],2)
        metric_acc_per_window[window_id][speakeralias][29] = round(momentum[-1],2)
        speakerDetail[i][30] = round(verbalshare[-1],2)
        metric_acc_per_window[window_id][speakeralias][30] = round(verbalshare[-1],2)
        speakerDetail[i][31] = round(turnshare[-1],2)
        metric_acc_per_window[window_id][speakeralias][31] = round(turnshare[-1],2)

        if window_id not in Combined_object['window_level']:
            Combined_object['window_level'][window_id] = {speakeralias : dict(zip(metric_heading,speakerDetail[i]))}
        else:
            Combined_object['window_level'][window_id][speakeralias] = dict(zip(metric_heading,speakerDetail[i]))


        if speakeralias not in Combined_object['participants_level']:
            Combined_object['participants_level'][speakeralias] = [dict(zip(metric_heading,speakerDetail[i]))]
        else:
            Combined_object['participants_level'][speakeralias].append(dict(zip(metric_heading,speakerDetail[i])))

 

    len_session_trend = len(session_trend) 
    session_most_common_trend = Counter(session_trend).most_common(1)[0][0] if session_trend else -1
    early_trend = Counter(session_trend[0:len_session_trend//3]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    mid_trend = Counter(session_trend[len_session_trend//3 : (len_session_trend//3)*2]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    late_trend = Counter(session_trend[(len_session_trend//3)*2 : len_session_trend ]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    session_metrics=[]
    session_all_metrics = []

    trajectory = compute_collaboration_trajectory(social_impact,responsivity,participation_share)
    # logging.info("trajectory : {0}".format(trajectory))
    if total_windows > 0:
        session_metrics.append(round(sum(focusscore)/total_windows,2))
        session_all_metrics.append(round(compute_average(focusscore, exclude_zeros=True),2))
        session_metrics.append(round(session_particpantion_score,2))
        session_all_metrics.append(round(session_particpantion_score,2))
        session_metrics.append(round(session_responsivity,2))
        session_all_metrics.append(round(session_responsivity,2))
        session_metrics.append(round(sum(enagementscore)/total_windows,2))           
        session_all_metrics.append(round(get_last_metric_value(enagementscore),2))
        session_metrics.append(round(sum(reasoningscore)/total_windows,2))
        session_all_metrics.append(round(compute_average(reasoningscore, exclude_zeros=True),2))
        session_metrics.append(round(sum(leadershipscore)/total_windows,2))
        session_all_metrics.append(round(get_last_metric_value(leadershipscore),2))
        session_metrics.append(round(sum(initiativescore)/total_windows,2))
        session_all_metrics.append(round(compute_average(initiativescore, exclude_zeros=True),2))
        session_metrics.append(round(sum(ideacontributionscore)/total_windows,2))
        session_all_metrics.append(round(get_last_metric_value(ideacontributionscore),2))
        session_metrics.append(round(sum(speakingalignmentscore)/total_windows,2))
        session_all_metrics.append(round(compute_average(speakingalignmentscore, exclude_zeros=True),2))
        session_metrics.append(round(trajectory['trajectory_score']*100,2))
        session_all_metrics.append(round(trajectory['trajectory_score']*100,2))
        session_metrics.append(round((sum(shared_task_focus)/total_windows)*100,2))
        session_all_metrics.append(round((compute_average(shared_task_focus, exclude_zeros=True))*100,2))

        session_all_metrics.append(round(compute_average(analyticthinking, exclude_zeros=True),2))
        session_all_metrics.append(round(compute_average(authenticity, exclude_zeros=True),2))
        session_all_metrics.append(round(compute_average(certainty, exclude_zeros=True),2))
        session_all_metrics.append(round(compute_average(clout, exclude_zeros=True),2))
        session_all_metrics.append(round(session_internalcohesion,2))
        session_all_metrics.append(round(session_socialimpact,2))
        session_all_metrics.append(round(session_newness,2))
        # session_all_metrics.append(round(compute_average(newness,exclude_zeros=True),2))

        # logging.info("participationscore accumulated {0}".format(participationscore))
        # logging.info("responsivityscore accumulated {0}, average_by_all: {1}, average_by_val: {2}, sum: {3}, total windows : {4}".format(responsivityscore,round(sum(responsivityscore)/total_windows,2),round(compute_average(responsivityscore, exclude_zeros=True),2),sum(responsivityscore),total_windows))
        # logging.info("internalcohesion accumulated {0}, average_by_all: {1}, average_by_val: {2}, sum: {3}, total windows : {4}".format(internalcohesion,round(sum(internalcohesion)/total_windows,2),round(compute_average(internalcohesion, exclude_zeros=True),2),sum(internalcohesion),total_windows))
        # logging.info("socialimpact accumulated {0}, average_by_all: {1}, average_by_val: {2}, sum: {3}, total windows : {4}".format(socialimpact,round(sum(socialimpact)/total_windows,2),round(compute_average(socialimpact, exclude_zeros=True),2),sum(socialimpact),total_windows))
        # logging.info("newness accumulated {0}, average_by_all: {1}, average_by_val: {2}, sum: {3}, total windows : {4}".format(newness,round(sum(newness)/total_windows,2),round(compute_average(newness, exclude_zeros=True),2),sum(newness),total_windows))
        # logging.info("ideacontributionscore accumulated {0}, average_by_all: {1}, average_by_val: {2}, sum: {3}, total windows : {4}".format(ideacontributionscore,round(sum(ideacontributionscore)/total_windows,2),round(compute_average(ideacontributionscore, exclude_zeros=True),2),sum(ideacontributionscore),total_windows))
        

    else:
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0) 
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0) 
        session_all_metrics.append(0)

        session_all_metrics.append(0)
        session_all_metrics.append(0)
        session_all_metrics.append(0)
        session_all_metrics.append(0)
        session_all_metrics.append(0)
        session_all_metrics.append(0)
        session_all_metrics.append(0)
    
    share_portion = round(100/no_of_participants, 2) if no_of_participants > 0 else 0
    if len(total_verbal_turn_acc) > 0:     
        session_metrics.append(round((((sum(speaking_word_count)/sum(total_verbal_turn_acc)) *100)/share_portion)*100,2))
        session_all_metrics.append(round((((sum(speaking_word_count)/sum(total_verbal_turn_acc)) *100)/share_portion)*100,2))
        session_metrics.append(round((sum(speaking_word_count)/sum(total_verbal_turn_acc))*100,2))
        session_all_metrics.append(round((sum(speaking_word_count)/sum(total_verbal_turn_acc))*100,2))
        session_metrics.append(round((((len(speaking_word_count)/len(total_verbal_turn_acc))*100)/share_portion)*100,2))
        session_all_metrics.append(round((((len(speaking_word_count)/len(total_verbal_turn_acc)) *100)/share_portion)*100,2))
        session_metrics.append(round(((len(speaking_word_count)/len(total_verbal_turn_acc))*100),2))
        session_all_metrics.append(round(((len(speaking_word_count)/len(total_verbal_turn_acc))*100),2))
        
    else:
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)  
        session_all_metrics.append(0)
        session_metrics.append(0)
        session_all_metrics.append(0)
        session_metrics.append(0)  
        session_all_metrics.append(0)

    session_all_metrics.append(sum(speaking_word_count))

    session_metrics.append(session_most_common_trend)
    session_all_metrics.append(session_most_common_trend)
    session_metrics.append(early_trend)
    session_all_metrics.append(early_trend)
    session_metrics.append(mid_trend)
    session_all_metrics.append(mid_trend)
    session_metrics.append(late_trend)
    session_all_metrics.append(late_trend)

    dominance= -1
    undercontribution = -1 
    if share_portion > 0:
         
        relative_contribution = session_particpantion_score/share_portion
        if relative_contribution > 1:
            overcontribution = max(0,relative_contribution - 1)
            overcontribution = min(1,overcontribution) #cap any particpation share above 1 to 1. so that value range between 0 and 1
            final_responsivity = session_all_metrics[2]
            dominance = overcontribution * (1- (final_responsivity/100))
        else: 
            final_soc_impt = session_all_metrics[16]
            undercontribution = (1-relative_contribution)*(1-(final_soc_impt/100)) 

    session_all_metrics.append(round(dominance,2))
    session_all_metrics.append(round(undercontribution,2)) 
  

    

    group_level_metric_acc['focusscore'].append(session_all_metrics[0]/100)
    group_level_metric_acc['participationscore'].append(session_all_metrics[1]/100)
    group_level_metric_acc['responsivity'].append(session_all_metrics[2]/100)
    group_level_metric_acc['engagementscore'].append(session_all_metrics[3]/100)
    group_level_metric_acc['reasoningscore'].append(session_all_metrics[4]/100)
    group_level_metric_acc['leadershipscore'].append(session_all_metrics[5]/100)
    group_level_metric_acc['initiativescore'].append(session_all_metrics[6]/100)
    group_level_metric_acc['ideacontributionscore'].append(session_all_metrics[7]/100)
    group_level_metric_acc['speakingalignmentscore'].append(session_all_metrics[8]/100)
    group_level_metric_acc['momentum'].append(session_all_metrics[9]/100)
    group_level_metric_acc['sharedtaskfocus'].append(session_all_metrics[10])
    group_level_metric_acc['verbalshare'].append(session_all_metrics[19]/100)
    group_level_metric_acc['turntaking'].append(session_all_metrics[21]/100)
    group_level_metric_acc['trenddirection'].append(session_all_metrics[15])
    group_level_metric_acc['earlytrenddirection'].append(session_all_metrics[16])
    group_level_metric_acc['midtrenddirection'].append(session_all_metrics[17])
    group_level_metric_acc['latetrenddirection'].append(session_all_metrics[18])
    


    
    session_data_heading = ['avg_focusscore','avg_participationscore','avg_responsivity','avg_engagementscore','avg_reasoningscore','avg_leadershipscore', 'avg_initiativescore','avg_ideacontributionscore',
                            'avg_speakingalignmentscore','avg_momentum','sharedtaskfocus','avg_verbalshare_bal','avg_verbalshare','avg_turntaking_bal','avg_turntaking','avg_trenddirection','earlytrenddirection','midtrenddirection','latetrenddirection'] 
    
    session_all_data_heading = ['avg_focusscore','avg_participationscore','avg_responsivity','avg_engagementscore','avg_reasoningscore','avg_leadershipscore', 'avg_initiativescore','avg_ideacontributionscore',
                            'avg_speakingalignmentscore','avg_momentum','sharedtaskfocus','avg_analyticthinking','avg_authenticity','avg_certainty','avg_clout','avg_internalcohesion','avg_socialimpact','avg_newness',
                            'avg_verbalshare_bal','avg_verbalshare','avg_turntaking_bal','avg_turntaking','wordcount','avg_trenddirection','earlytrenddirection','midtrenddirection','latetrenddirection','Dominance','undercontribution'] 
    Combined_object['session_level'][speakeralias] = dict(zip(session_data_heading,session_metrics))
    Combined_object['session_all_metrics'][speakeralias] = dict(zip(session_all_data_heading,session_all_metrics))
   
def synthesized_transcript_video_metrics_by_window(transcriptSpeakerMetric,videoMetrics,session_device,keywords,speakers_obj,windowsize=10): #speakers,

    v_index = t_index = 0
    attention_rate_acc_per_speaker = defaultdict(list)
    metric_acc_per_speaker_list = defaultdict(list)
    metric_acc_per_speaker_obj = defaultdict(dict)
    metric_acc_per_window = defaultdict(dict)
    group_level_metric_acc = defaultdict(list)
    all_participants_transcript = []
    total_verbal_turn_acc = []
    speakers = {}
    Combined_object = {'group_id': session_device.id, 'group_name': session_device.name, 'window_level':{}, 'participants_level':{}, 'session_level':{}, 'session_all_metrics':{},'transcript':{},'group_level':{}}
    min_start = min(videoMetrics[0].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[0]['transcript'].start_time if transcriptSpeakerMetric else 0)
    max_end = max(videoMetrics[-1].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[-1]['transcript'].start_time if transcriptSpeakerMetric else 0)
    window_start = min_start
    window_end = min_start+windowsize
    window_count = 0
    total_speaker_detected = 0
    while window_start <= max_end:
        window_id = f"w_{window_start}_{window_end}"
        window_video_metrics, v_index = extract_videometrics_within_window(videoMetrics,speakers,speakers_obj, window_start, window_end, v_index)
        window_transcript_metrics, t_index = extract_transcriptmetrics_within_window(transcriptSpeakerMetric,all_participants_transcript,speakers,keywords, window_start, window_end, t_index)

        #combine transcrit and video metrics for this window
        for speaker_id,speaker_alias in speakers.items():
            w_video_meteic = window_video_metrics.get(speaker_id,[])
            w_transcript_metric = window_transcript_metrics.get(speaker_id,[])
            prev_metric = metric_acc_per_speaker_list[speaker_id][-1] if metric_acc_per_speaker_list.get(speaker_id,None) else [None]*32
            aggregated_video_metrics = aggregate_video_metric_per_window(w_video_meteic,windowsize,window_count,prev_metric) if w_video_meteic else []
            aggregated_transcript_metrics = aggregate_transcript_metric_per_window(w_transcript_metric,prev_metric,len(speakers)) if w_transcript_metric else []
            
            #accumulate the attention rate for each speaker if there is video metrics. this will be used to compute the robust_z value
            if aggregated_video_metrics:
                attention_rate_acc_per_speaker[speaker_id].append(aggregated_video_metrics[3]) 

            combine_metrics = combine_transcript_video_metrics(aggregated_video_metrics,aggregated_transcript_metrics,window_id,window_start,window_end)

            if combine_metrics:
                metric_acc_per_speaker_list[speaker_id].append(combine_metrics)
                metric_acc_per_speaker_obj[speaker_id][window_id] = combine_metrics
                metric_acc_per_window[window_id][speaker_alias]=combine_metrics

                #keep track of all the speaking turns
                if combine_metrics[4] > 0:
                    total_verbal_turn_acc.append(combine_metrics[4])

                if 'persons' not in metric_acc_per_window[window_id]:
                    metric_acc_per_window[window_id]['persons'] = [speaker_alias]
                else:
                    metric_acc_per_window[window_id]['persons'].append(speaker_alias)


        window_start = window_end
        window_end += windowsize
        window_count += 1

    # add transcript to combine_object
    Combined_object['transcript']= all_participants_transcript

    total_speaker_detected = len(metric_acc_per_speaker_list)
    # so now we begin to compute the derived metrics for each speakers and update the record accordingly
    total_windows = len(metric_acc_per_window)
    object_of_interest_focus = ['laptop','book','paper','person','mouse','whiteboard']
    object_of_interest_focus.extend(list(speakers.values()))
    all_windows = list(metric_acc_per_window.keys())
    for speaker, speakerDetail in  metric_acc_per_speaker_list.items():
    # for speaker, speakerDetail in  metric_acc_per_speaker_obj.items():
        attention_rates = attention_rate_acc_per_speaker.get(speaker,None)
        # logging.info("computing derived metrics for speaker: {0}: {1}".format(speaker, attention_rates))
        median_x,mad = compute_median_and_mad(np.array(attention_rates)) if attention_rates else [0,0]
        compute_derived_metric_and_update(metric_acc_per_window,all_windows,speakerDetail,total_windows,total_verbal_turn_acc,speakers[speaker],median_x,mad,Combined_object,group_level_metric_acc,total_speaker_detected,object_of_interest_focus,len(speakers)) 
        # session_metric_per_speaker[speaker.alias] = session_metrics  

    if total_speaker_detected > 1:
        #compute group level metric using the accumulated group data data 
        Combined_object['group_level']['verbalparticipationbalance'] = round((1 - statistics.stdev(group_level_metric_acc['verbalshare']))*100,2) 
        Combined_object['group_level']['turntakingbalance'] = round((1 - statistics.stdev(group_level_metric_acc['turntaking'])) * 100,2)
        Combined_object['group_level']['Sharedtaskfocus'] = round(sum(group_level_metric_acc['sharedtaskfocus'])/total_speaker_detected,2)
        Combined_object['group_level']['responsivity'] = round((sum(group_level_metric_acc['responsivity'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['ideacontribution'] = round((sum(group_level_metric_acc['ideacontributionscore'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['momentum'] = round((sum(group_level_metric_acc['momentum'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['participation'] = round((sum(group_level_metric_acc['participationscore'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['engagement'] = round((sum(group_level_metric_acc['engagementscore'])/total_speaker_detected)*100,2) 
        Combined_object['group_level']['focusscore'] = round((sum(group_level_metric_acc['focusscore'])/total_speaker_detected)*100,2) 
        
    
    return Combined_object