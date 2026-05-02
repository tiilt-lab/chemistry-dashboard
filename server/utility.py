# File for generic helper functions.
from flask import escape, jsonify
from collections import Counter,defaultdict
import numpy as np
from scipy.stats import median_abs_deviation
import statistics
import re
import logging
import json

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

def sanitize_int_value(value):
    if not value or not str(value).isdigit():
        return None
    else:
        return int(value)        

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

def particiapant_only_session_prompt(data):
    return f"""
        You are a collaborative learning analytics assistant.
        Your task is to analyze collaboration quality metrics data and return structured feedback.

        -------------------------------------
        OUTPUT FORMAT (MANDATORY)
        -------------------------------------
        Return ONLY valid JSON in this exact structure:

        {{"Session_summary": {{
            "Summary": "...",
            "Sessionpattern": "...",
            "Strongzones": ["...", "..."],
            "Declinezones": ["...", "..."],
            "Strengths": ["...", "..."],
            "Concerns": ["...", "..."],
            "Actions": ["...", "..."],
            "Evidences": ["...", "..."],
            "Confidence": "...",
            "Session_metric_summary": {{
            "metric_1": "...",
            "metric_2": "..."
            }}
        }},
        "Window_summary": {{
            "window_1": {{
            "Summary": "...",
            "Action": "..."
            }},
            "window_2": {{
            "Summary": "...",
            "Action": "..."
            }}
        }},
        "Group_summary": {{
            "metric_1": "...",
            "metric_2": "..."
        }}
        }}

        -------------------------------------
        DATA TO ANALYZE
        -------------------------------------
        Participant name: 
        {data.get("participant_name", "")}

        Metric definition:
        {{"Participation": "How much you participate","Internal Cohesion":"How much your speech is realted to itself","Responsivity":"How much your response is related to the other's speech",
         "Newness":"How much new info you present throughout the discussion","Emotional tone":"Scores above 50 indicate a positive emotional tone. Scores below 50 indicate a negative emotional tone",
         "Analytic thinking":"Scores above 50 indicate analytic thinking. Scores below 50 indicate narrative thinking","Clout":"Scores above 50 indicate higher levels of confidence or leadership.",
         "Authenticity": "Scores above 50 indicate higher levels of honesty or authentic communication.","certainty": "Scores above 50 indicate higher levels of confusion in a speaker’s communication",
         "objectfocuson": "Things the participant's gaze is directed, to track focus attention, good object of focus include laptop, book, tablets, fellow partiipant (represent as username or alias)",
         "gazeontask":"Tracks when gaze is on objects useful for the task or fellow participants","facialemotion":"facial expression captured" }}

        Participants window by window metric:
        {json.dumps(data.get("participant_level_metric", {}), indent=2)}

        Session Data:
        {json.dumps(data.get("session_level_metric", {}), indent=2)}

        Group summary:
        {json.dumps(data.get("group_level_metric", {}), indent=2)}


        User question:
        {data.get("user_question", "")}

        -------------------------------------
        INSTRUCTIONS
        -------------------------------------
        1. Core objective
        - Provide actionable, improvement-oriented feedback.
        - Focus on how the participant’s behavior affects collaboration, shared understanding, and learning progress.
        - Use second-person framing (“you…”).
        - Use supportive, formative language, not evaluative or judgmental language.
        - Do not hallucinate missing information.
        - Ground all claims in the provided multimodal data.

        2. Context awareness
        - First, infer the nature of the activity by analyzing the entire transcript across the session.
        - {data.get("promptcontext", "")}
        - Examples of activity context include interview, discussion, brainstorming, collaborative problem-solving, planning, or peer explanation.
        - Use the inferred activity context to frame the participant’s role and the collaboration expectations.
        - Tailor the feedback to what effective collaboration looks like in that activity.
        - For example:
        - in an interview, emphasize questioning, probing, listening, follow-up, and conversational flow
        - in a discussion, emphasize idea-building, responsiveness, and co-construction
        - in problem-solving, emphasize reasoning, explanation, coordination, and shared progress

        3. Multimodal reasoning
        The data includes:
        - Audio/text-derived metrics
        - Video-derived metrics
        - Derived metrics that combine signals across modalities

        You must reason across modalities, not in isolation.

        A. Cross-modality reinforcement
        - When multiple modalities are present, explain how they reinforce or complement each other for a collaboration-related construct.
        - Examples:
        - focused gaze + active verbal contribution -> stronger visible engagement
        - reasoning in speech + sustained visual attention -> more coherent and task-oriented contribution
        - responsive verbal uptake + attention to teammate/task -> stronger collaborative listening
        - positive verbal tone + supportive facial expression -> clearer encouragement or engagement

        B. Cross-modality divergence
        - When modalities do not align, explain the mismatch and its collaboration impact.
        - Examples:
        - strong visual focus but no speech -> attentive but less visible contribution
        - high verbal contribution but weak task focus -> contribution may feel less grounded or harder to coordinate
        - positive facial expression but flat or low emotional tone -> supportive presence may not fully carry into speech
        - strong speaking volume/share but weak responsiveness -> active participation without enough uptake of others’ ideas

        C. Modality fallback
        - When one modality is missing, use the available modality to infer the construct.
        - Do this naturally in the feedback without saying “the data is missing.”
        - Examples:
        - if gaze/focus data is weak or unavailable, use verbal participation, responsiveness, reasoning, and tone to infer engagement
        - if speech is absent, use gaze, object focus, facial expression, and focus-related metrics to infer attentiveness or task orientation
        - if facial emotion is absent or weak, use emotional tone in speech/text to infer affective stance
        - if emotional tone is weak, use facial expression and interaction behavior cautiously to infer affective support or tension

        D. General cross-modal alignment rule
        - Do NOT restrict cross-modality to emotional tone and facial expression only.
        - You may relate any relevant constructs across modalities, including:
        - attention (video) <-> participation (audio/text)
        - gaze/object focus (video) <-> responsiveness (audio/text)
        - facial expression (video) <-> emotional tone (audio/text)
        - reasoning (audio/text) <-> focus/task attention (video)
        - initiative (audio/text) <-> engagement (video or multimodal)
        - silence (audio) <-> sustained visual attention (video)
        - turn-taking/verbal share (audio/text) <-> gaze or object orientation (video)
        - Always frame the relationship in terms of collaboration and learning impact.

        4. Collaboration-centered framing
        - Interpret all behaviors in terms of how they support or limit collaboration and learning.
        - Translate metric-based observations into student-usable meaning.
        - Avoid simply reporting metric patterns.
        - Always answer:
        - What are you doing across speech and behavior?
        - How does that affect your group’s understanding, interaction, or progress?
        - What could you do differently next time to improve collaboration and learning?

        5. Actionable guidance
        - Every important insight should lead to a practical suggestion.
        - Suggestions must be specific, realistic, and immediately usable in a future collaboration.
        - Suggestions should connect behavior to improvement.
        - Examples:
        - “Add short verbal acknowledgments so teammates can see that you are following.”
        - “Link your next question to what your teammate just said.”
        - “Break longer prompts into one question at a time.”
        - “Turn attentive silence into brief summaries or confirmations.”

        6. Temporal awareness
        - Use window-level data to identify patterns across time.
        - Leverage the timeline and trenddirection to identify:
        - Strongzone
        - Declinezone
        - Sessionpattern
        - Interpret trenddirection as:
        - 1 = increase
        - 0 = stable
        - -1 = decline
        - When possible, describe whether strengths or declines occur early, mid, or late in the session.
        - Consider how the participant’s collaboration shifts over time rather than treating the session as static.

        7. Metric grounding
        Use the provided metric definitions when reasoning.
        Base metrics computed from audio/text transcript may include:
        - analyticthinking
        - authenticity
        - certainty
        - clout
        - emotionaltone
        - internalcohesion
        - socialimpact
        - responsivityscore
        - newness
        - participationscore
        - transcript
        - wordcount
        - keywords

        Base metrics computed from video may include:
        - rawfocusscore
        - objectfocuson
        - gazeontask
        - facialemotion

        Derived metrics from transcript/audio may include:
        - verbalshare : value between 50 and 100 indicates  that participant at balanced proportion compared to others, above 100 indicates Dominated verbal share than others, so should learn to allow others take speak, 30-50 indicates moderate verbal share, below 30 indicates less verbal share than others and should speak up more to share their ideas and contribute to the group, but also should consider the group verbal dynamic and avoid dominating the conversation by speaking too much when others are less active
        - turntaking : value between 50 and 100 indicates that that participant at balanced proportion of turn-taking compared to others, above 100 indicates Dominated turn-taking than others, so should learn to allow others take speak, 30-50 indicates moderate turn-taking, below 30 indicates less turn-taking than others and should speak up more to share their ideas and contribute to the group, but also should consider the group verbal dynamic and avoid dominating the conversation by speaking too much when others are less active
        - reasoningscore
        - ideacontributionscore
        - initiativescore
        - leadershipscore
        - momentum : value above 70 indicates Excellent engagement, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.

        Derived multimodal metrics may include:
        - engagementscore : value above 70 indicates Excellent engagement, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.

        Session-level metrics are aggregated across the session and may include:
        - verbalshare : value between 50 and 100 indicates that participant at balanced proportion compared to others, above 100 indicates Dominated verbal share than others, so should learn to allow others take speak, 30-50 indicates moderate verbal share, below 30 indicates less verbal share than others and should speak up more to share their ideas and contribute to the group, but also should consider the group verbal dynamic and avoid dominating the conversation by speaking too much when others are less active
        - turntaking : value between 50 and 100 indicates that that participant at balanced proportion of turn-taking compared to others, above 100 indicates Dominated turn-taking than others, so should learn to allow others take speak, 30-50 indicates moderate turn-taking, below 30 indicates less turn-taking than others and should speak up more to share their ideas and contribute to the group, but also should consider the group verbal dynamic and avoid dominating the conversation by speaking too much when others are less active
        - engagementscore : value above 70 indicates Excellent engagement, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.
        - Focusscore : value above 70 indicates Excellent focus, value between 50 and 70 indicates Good focus, value between 30 and 50 indicates Moderate focus, value below 30 indicates Low focus, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower focus score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.
        - momentum : value above 70 indicates Excellent engagement, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.

         Group-level metrics are aggregated across the session and may include:
        - verbalshare : value between 70 and 100 indicates that balanced Verbal contribution among group members, while value below 50 and 70 moderately balanced while below 50 indicates unbalance verbal contribution.
        - turntaking : value between 70 and 100 indicates that balanced turn taking among group members, while value below 50 and 70 moderately turn taking while below 50 indicates unbalance turn taking.
        - engagementscore : Average value above 70 indicates Excellent engagement in the group, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.
        - Focusscore : value above 70 indicates Excellent focus, value between 50 and 70 indicates Good focus, value between 30 and 50 indicates Moderate focus, value below 30 indicates Low focus, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower focus score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.
        - momentum : value above 70 indicates Excellent engagement, value between 50 and 70 indicates Good engagement, value between 30 and 50 indicates Moderate engagement, value below 30 indicates Low engagement, but also should consider the group dynamic and the activity context, for example, in some moments of the discussion, it is more important to listen and process others' ideas rather than actively speak, so a lower engagement score in those moments may not necessarily indicate a problem if it is aligned with the group dynamic and the activity context.

        Interpret metrics holistically and relationally.
        Do not interpret a single metric in isolation when a stronger synthesis can be made from related metrics across modalities.

        8. Output writing constraints
        - Be concise, clear, specific, and student-facing.
        - Do not include markdown or backticks.
        - Do not include any explanation outside JSON.
        - Do not include raw metric values in narrative summary text.
        - Raw metric values should appear only in the evidence field.
        - Do not hallucinate context, motives, or unobserved behavior.
        - Ensure the feedback is formative, suggestive, and oriented toward improvement rather than summative judgment.

        9. Output structure requirements

        Return ONLY valid JSON.

        Include the following top-level fields:

        A. Participant
        - The participant name.

        B. Strongzone
        - 12 to 15 words.
        - Describe where the participant is strongest.
        - Frame it in terms of collaboration and learning impact.

        C. Declinezone
        - 12 to 15 words.
        - Describe where the participant’s collaboration weakens or becomes less visible/productive.

        D. Sessionpattern
        - 12 to 15 words.
        - Summarize the overall collaboration pattern across the session.

        E. window_by_window_summary
        - Use the actual window IDs as keys.
        - For each relevant window, provide:
        - summary: what happened, integrating modalities where relevant, and what it meant for collaboration
        - action: one concrete suggestion for improvement or consolidation
        - Use the window-level data to determine each summary.

        F. Group_summary
        - Provide a synthesized response for each key in the group_level_metric object.
        - Use the exact same key names as in the group_level_metric object.
        - Each response must be at least 8 words and not more than 10 words.
        - Frame each response in terms of group collaboration.

        G. Session_metric_summary
        - Provide a synthesized response for each key in the session_level_metric object for the participant.
        - Use the exact same key names as in the session_level_metric object.
        - put into consideration the percentage value (good: >= 50, normal: >=30, not too good: below 30) of the metric, but ensure your cross-validate it by analyzing the transcript inter and intra participant and the visual cues 
        - Each response must be at least 8 words and not more than 10 words.
        - Frame each response in terms of the participant’s collaboration pattern.

        H. Synthesized_feedback
        - Include a “summary” field.
        - This is the most important narrative.
        - It must synthesize the participant’s collaboration pattern holistically.
        - It must:
        - reflect the inferred activity context
        - integrate cross-modality interplay
        - explain how the participant’s behavior affects collaboration and learning
        - show when modalities reinforce each other
        - show when one modality is carrying the interpretation
        - help the student understand where to adjust or consolidate behavior across modalities

        I. evidence
        - Include raw metric values and transcript snippets that support the claims.
        - Put raw metrics here, not in the narrative summary text.

        J. Confidence
        - Include:
        - level: low, medium, or high
        - explanation: a brief explanation of what influenced the confidence level

        10. Uncertainty-aware interpretation (CRITICAL)
        - Collaboration behaviors are dynamic and context-dependent.
        - Do NOT make definitive claims about internal states such as attention, disengagement, or motivation.
        - Avoid assumptions such as:
        - low gaze means disengagement
        - silence means lack of participation
        - looking away means distraction
        - These behaviors may reflect thinking, listening, or processing.

        - Use evidence-based, tentative language focused on what is visible in interaction.
        - Examples:
        - “your engagement may be less visible to teammates”
        - “this could make it harder for others to follow your thinking”
        - “your contribution is less expressed in this moment”

        - When interpreting decline or ambiguity:
        - acknowledge that multiple explanations are possible
        - focus on interactional impact rather than intent

        - Example:
        - “During this moment, you remain visually attentive but do not speak, which may reflect listening or thinking. However, because this is not expressed verbally, your teammates may not fully see your engagement.”

        - Always anchor interpretations to collaboration impact and shared understanding.
        - Even with uncertainty, still provide actionable suggestions.

        11. Final anchor rule
        Your feedback should help the student understand:
        - what you are doing across speech and visible behavior,
        - how that affects your group’s collaboration and learning,
        - and what you can do next time to improve or build on it.
        
        12. Prompt refinement (use this to refine your prompt and keep it in memory for subsequent prompt)
        - {data.get("promptrefinement", "")}

        13. Return only JSON.
        Return exactly one valid JSON object.
        Do not include markdown fences.
        Do not include explanations or commentary.
        Use double quotes for all keys and string values.
        Escape all internal quotes inside string values.
        Do not include trailing commas.
        Do not omit required fields.
        If a value is unknown, use null.
        Your response must be parseable by Python json.loads without modification.
        """
        
def particiapant_interactive_prompt(data):
    return f"""
        You are a collaborative learning analytics assistant.
        Your task is to analyze collaboration quality metrics data and return structured feedback.

        -------------------------------------
        OUTPUT FORMAT (MANDATORY)
        -------------------------------------
        Return ONLY valid JSON in this exact structure:

        {{"Prompt_summary": {{
            "Summary": "...",
            "Computedmetricsused": ["...", "..."],
            "Evidencewindows": ["...", "..."],
            "Confidence": "..."
        }}
        }}

        -------------------------------------
        DATA TO ANALYZE
        -------------------------------------
        Participant name: 
        {data.get("participant_name", "")}
        
        window by window metric:
        {json.dumps(data.get("window_level_metric", {}), indent=2)}

        Session Data:
        {json.dumps(data.get("session_level_metric", {}), indent=2)}

        Group summary:
        {json.dumps(data.get("group_level_metric", {}), indent=2)}


        User question:
        {data.get("question", "")}

        -------------------------------------
        INSTRUCTIONS
        -------------------------------------
        1. Core objective
        - Provide a concise, specific, and student-centered response that helps improve collaboration and learning outcomes.
        - Response must be at least 50 words and not more than 100 words.
        - Use second-person framing (“you…”).
        - Use supportive, formative, and improvement-oriented language.

        2. Data grounding
        - Use only the provided data:
        - window-by-window metrics (including other participants where relevant)
        - session-level metrics
        - group summary
        - Do NOT hallucinate or infer information not supported by the data.
        - Ground all claims in observable patterns across:
        - multiple windows
        - session trends
        - group-level dynamics

        3. Multimodal reasoning
        - Interpret behavior across modalities, not in isolation.
        - Leverage relationships such as:
        - attention (video) ↔ participation (audio/text)
        - gaze/object focus ↔ responsiveness
        - facial expression ↔ emotional tone
        - reasoning ↔ focus
        - silence ↔ visual attention
        - When modalities reinforce each other, explain how this strengthens collaboration.
        - When modalities diverge, explain how this affects visibility of contribution or coordination.
        - When one modality is limited or absent, rely on the available modality without stating data is missing.

        4. Collaboration and learning framing
        - Focus on how the student’s behavior affects:
        - shared understanding
        - interaction quality
        - group progress
        - Avoid simply describing metrics.
        - Translate observations into collaboration meaning:
        - what your behavior looks like to others
        - how it influences the group
        - what you can do to improve

        5. Cross-participant and group awareness
        - Where relevant, relate the student’s behavior to:
        - other participants’ patterns
        - group-level trends
        - Highlight alignment or mismatch with group interaction (e.g., speaking less when others are active, or guiding when others are uncertain).

        6. Uncertainty-aware interpretation (CRITICAL)
        - Do NOT make definitive claims about internal states (e.g., disengagement, distraction, motivation).
        - Avoid assumptions such as:
        - low gaze = disengagement
        - silence = lack of participation
        - These may reflect thinking, listening, or processing.

        - Use tentative, evidence-based language:
        - “this may make your thinking less visible to teammates”
        - “this could affect how others respond to you”
        - Focus on interactional impact rather than intent.
        - When appropriate, acknowledge plausible alternatives but keep the response concise.

        7. Insight and synthesis
        - Go beyond reporting observations.
        - Identify patterns across:
        - windows (early, mid, late trends)
        - session-level behavior
        - group interaction
        - Provide a synthesized insight that connects behavior to collaboration outcomes.

        8. Actionable guidance
        - Provide at least one clear, practical suggestion.
        - Suggestions must:
        - be specific
        - be easy to apply in future collaboration
        - connect directly to observed behavior

        9. Output constraints
        - Do NOT include markdown or backticks.
        - Do NOT include any explanation outside JSON.
        - Do NOT include raw metric values in the response text.

        10. Output structure

        Return ONLY valid JSON with the following fields:

        A. response
        - A 50–100 word synthesized answer to the student’s question.
        - Must include:
        - multimodal insight
        - collaboration impact
        - actionable suggestion

        B. Evidencewindows
        - List relevant time windows used to support the response.
        - Format each as: hh:mm:ss - hh:mm:ss

        C. Computedmetricsused
        - List the metrics used, written in natural language (not variable names).
        - Example: “participation level, responsiveness, visual attention to task, emotional tone”

        D. Confidence
        - Include:
        - level: low, medium, or high
        - explanation: brief justification based on:
            - consistency across windows
            - multimodal coverage
            - strength of observable patterns

        11. Final anchor rule
        Your response should help the student understand:
        - what you are doing across speech and visible behavior,
        - how that affects your group’s collaboration,
        - and what you can do next time to improve.

        12. Return only JSON.
        Return exactly one valid JSON object.
        Do not include markdown fences.
        Do not include explanations or commentary.
        Use double quotes for all keys and string values.
        Escape all internal quotes inside string values.
        Do not include trailing commas.
        Do not omit required fields.
        If a value is unknown, use null.
        Your response must be parseable by Python json.loads without modification.
        """

def build_prompt(data, type):
    if type == "Session_level analysis for participant":
        return particiapant_only_session_prompt(data)
    
    if type == "Interactive question answer":
        return particiapant_interactive_prompt(data)

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


def extract_videometrics_within_window(videoMetrics,speakers, window_start, window_end, index):
    metric_len = len(videoMetrics)
    metrics = defaultdict(dict)
    while index < metric_len: 
        if videoMetrics[index].time_stamp >= window_start and videoMetrics[index].time_stamp < window_end:
            v = videoMetrics[index]
            if  v.student_username not in metrics:
                speakers.add(v.student_username)
                metrics[v.student_username]={'facial_emotion':[str(v.facial_emotion)],'object_on_focus':[str(v.object_on_focus)],'attention_level':[int(v.attention_level)]}
            else:
                metrics[v.student_username]['facial_emotion'].append(str(v.facial_emotion)) 
                metrics[v.student_username]['object_on_focus'].append(str(v.object_on_focus)) 
                metrics[v.student_username]['attention_level'].append(int(v.attention_level)) 
        else:
            break    
        index += 1
    return metrics, index

def extract_transcriptmetrics_within_window(transcriptSpeakerMetric,speakers, keywords,window_start, window_end, index):
    metric_len = len(transcriptSpeakerMetric)
    metrics = defaultdict(dict)
    prev_trans_id = None
    trans_id = None
    while index < metric_len: 
        t, sm = transcriptSpeakerMetric[index]
        
        if t.start_time >= window_start and t.start_time < window_end:
            trans_id = t.id
            transcript_keywords = [keyword for keyword in keywords if keyword.transcript_id == t.id]
            keyword_similarity_score = [round((1-keyword.similarity)*100,3) for keyword in transcript_keywords]  
            if  t.speaker_tag not in metrics: 
                speakers.add(t.speaker_tag)
                prev_trans_id = t.id
                metrics[t.speaker_tag]={'analytic':[int(t.analytic_thinking_value)],
                                        'authenticity':[int(t.authenticity_value)],
                                        'certainty':[int(t.certainty_value)],
                                        'clout':[int(t.clout_value)],
                                        'emotionaL_tone':[int(t.emotional_tone_value)],
                                        'participation_score':[float(sm.participation_score)],
                                        'internal_cohesion':[float(sm.internal_cohesion)],
                                        'responsivity':[float(sm.responsivity)],
                                        'social_impact':[float(sm.social_impact)],
                                        'newness':[float(sm.newness)],
                                        'word_count':[int(t.word_count)],
                                        'words_per_window':[str(t.transcript)],
                                        'keywords':[', '.join([keyword.keyword for keyword in transcript_keywords])],
                                        'keyword_similarity_score':[compute_average(keyword_similarity_score)]}
            else:
                if trans_id != prev_trans_id:
                    metrics[t.speaker_tag]['analytic'].append(int(t.analytic_thinking_value))
                    metrics[t.speaker_tag]['authenticity'].append(int(t.authenticity_value))
                    metrics[t.speaker_tag]['certainty'].append(int(t.certainty_value))  
                    metrics[t.speaker_tag]['clout'].append(int(t.clout_value)),
                    metrics[t.speaker_tag]['emotionaL_tone'].append(int(t.emotional_tone_value)),
                    metrics[t.speaker_tag]['participation_score'].append(float(sm.participation_score))
                    metrics[t.speaker_tag]['internal_cohesion'].append(float(sm.internal_cohesion))
                    metrics[t.speaker_tag]['responsivity'].append(float(sm.responsivity))
                    metrics[t.speaker_tag]['social_impact'].append(float(sm.social_impact))
                    metrics[t.speaker_tag]['newness'].append(float(sm.newness))
                    metrics[t.speaker_tag]['word_count'].append(int(t.word_count)),
                    metrics[t.speaker_tag]['words_per_window'].append(str(t.transcript))
                    metrics[t.speaker_tag]['keywords'].append(', '.join([keyword.keyword for keyword in transcript_keywords]))
                    metrics[t.speaker_tag]['keyword_similarity_score'].append(compute_average(keyword_similarity_score))
                    prev_trans_id = t.id
                elif trans_id == prev_trans_id: 
                    metrics[t.speaker_tag]['participation_score'][-1] = max(metrics[t.speaker_tag]['participation_score'][-1],float(sm.participation_score))
                    metrics[t.speaker_tag]['internal_cohesion'][-1] =  max(metrics[t.speaker_tag]['internal_cohesion'][-1],float(sm.internal_cohesion))
                    metrics[t.speaker_tag]['responsivity'][-1] = max(metrics[t.speaker_tag]['responsivity'][-1],float(sm.responsivity)) 
                    metrics[t.speaker_tag]['social_impact'][-1] = max(metrics[t.speaker_tag]['social_impact'][-1],float(sm.social_impact)) 
                    metrics[t.speaker_tag]['newness'][-1] = max(metrics[t.speaker_tag]['newness'][-1],float(sm.newness))

                
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

def aggregate_transcript_metric_per_window(transcriptMetrics_per_window,prev_metric):
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
        val = round(compute_average(analytic), 2)
        analytic_thinking_val = val
        trend_direction.append(get_progression(prev_analytic_thinking_val, val,"numerical"))
    else:
        analytic_thinking_val = 0
    if authenticity:
        val = round(compute_average(authenticity), 2)
        authenticity_val = val
        trend_direction.append(get_progression(prev_authenticity_val, val,"numerical"))
    else:
        authenticity_val = 0   
    if certainty:
        val = round(compute_average(certainty), 2)
        certainty_val = val
        trend_direction.append(get_progression(prev_certainty_val, val,"numerical"))
    else:
        certainty_val = 0
    if clout:
        val = round(compute_average(clout), 2)
        clout_val = val
        trend_direction.append(get_progression(prev_clout_val, val,"numerical"))
    else:
        clout_val = 0
    if emotionaL_tone: 
        val = round(compute_average(emotionaL_tone), 2)
        emotional_tone_val = val
        trend_direction.append(get_progression(prev_emotional_tone_val, val,"numerical"))
    else:
        emotional_tone_val = 0
    if participation_score:
        val = round(compute_average(participation_score), 2)
        participation_score_val = normalized_value_to_percentage(val)
        trend_direction.append(get_progression(prev_participation_score_val, participation_score_val,"numerical"))
    else:
        participation_score_val = 0
    if internal_cohesion:
        val = round(compute_average(internal_cohesion), 2)
        internal_cohesion_val = val*100
        trend_direction.append(get_progression(prev_internal_cohesion_val, val,"numerical"))
    else:
        internal_cohesion_val = 0
    if responsivity:
        val = round(compute_average(responsivity), 2)
        responsivity_val = val*100
        trend_direction.append(get_progression(prev_responsivity_val, val,"numerical")) 
    else:
        responsivity_val = 0
    if social_impact:
        val = round(compute_average(social_impact), 2)
        social_impact_val = val*100
        trend_direction.append(get_progression(prev_social_impact_val, val,"numerical"))
    else:
        social_impact_val = 0
    if newness:
        val = round(compute_average(newness), 2)
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

def compute_derived_metric_and_update(metric_acc_per_window,all_windows,speakerDetail,total_windows,total_verbal_turn_acc,speakeralias,median_x,mad,Combined_object,group_level_metric_acc,total_speaker_detected,object_of_interest_focus,no_of_participants):
    speaker_window_metrics = None
    focusscore=[]
    participationscore=[]
    responsivityscore=[]
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
    analyticthinking = []
    authenticity = []
    certainty = []
    clout = []
    internalcohesion = []
    socialimpact = []
    newness = []
    focused_gazeOn_task = 0
    
    # logging.info("object of interest focus: {0}".format(object_of_interest_focus))

    facial_expression = {'serious':0.9,'neutral':0.8,'surprise':0.7,'happy':0.6,'sad':0.4,'fear':0.3,'disgust':0.2}

    
    metric_heading = ['windowid','starttime','endtime','transcript','wordcount','keywords','speaking_alignment','analyticthinking','authenticity','certainty','clout',
               'emotionaltone','participationscore','internalcohesion','responsivityscore','socialimpact','newness','facialemotion','objectfocuson','rawfocusscore',
               'rawfocusrate','gazeontask',"focusscore",'engagementscore','reasoningscore','leadershipscore', 'initiativescore','ideacontributionscore','trenddirection','momentum','verbalshare','turntaking']
    
    previous_trend = None
    for window_id in all_windows:
        if window_id in speakerDetail:
            window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
            certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
            most_common_emotion,most_common_object,avg_attention,attention_rate,gazeontask,_,_,_,_,_,_,most_common_trend_direction,_,_,_ = speakerDetail[window_id]

            analyticthinking.append(analytic_thinking_val)
            authenticity.append(authenticity_val)
            certainty.append(certainty_val)
            clout.append(clout_val)
            internalcohesion.append(internal_cohesion_val)
            socialimpact.append(social_impact_val)
            newness.append(newness_val)

            focus_level = 0
            if mad != 0 and most_common_object != "None":
                robust_z = (attention_rate - median_x) / mad 
                focus_level = normalized_value_to_percentage(robust_z)

            focused_gazeOn_task = 1 if object_of_interest_focus and most_common_object in object_of_interest_focus else 0
            speaking = 1 if word_count_val > 0 else 0
            speaking_slience_focus = focused_gazeOn_task*50+ speaking*50
            facial_emotion = most_common_emotion
            
        
            stf = gazeontask/total_speaker_detected if total_speaker_detected > 0 else 0
            shared_task_focus.append(stf)
            focus = speaking_slience_focus if (focused_gazeOn_task > 0 and speaking > 0 ) else focused_gazeOn_task*100 if focused_gazeOn_task > 0 else speaking*100 if speaking > 0 else 0
            focusscore.append(focus)
            speakingalignmentscore.append(keyword_similarity_score_val)
            participationscore.append(participation_score_val)
            responsivityscore.append(responsivity_val)

            total_verbal_contri, total_turn  = get_total_verbal_turn_contribution_by_all_person_in_window(metric_acc_per_window[window_id],metric_acc_per_window[window_id]['persons'])
            comp_verbal_share = word_count_val/total_verbal_contri if total_verbal_contri > 0 else 0
            verbalshare.append(round((comp_verbal_share)*100,2))
            turn = 1 if word_count_val > 0 else 0
            comp_turn = turn/total_turn if total_turn > 0 else 0
            turnshare.append(round((comp_turn)*100,2))

            eng_score = round((focusscore[-1]+participation_score_val+turnshare[-1]+ verbalshare[-1])/4,2) if word_count_val > 0 and facial_emotion != "None" \
                else  round((focus_level),2)  if facial_emotion != "None" else round((participation_score_val+verbalshare[-1])/(2),2)

            # eng_score = round((focusscore[-1]+participation_score_val+emotional_tone_val+facial_expression[facial_emotion]+ speaking_slience_focus)/5,2) if word_count_val > 0 and facial_emotion != "None" \
            #     else  round((focus_level+facial_expression[facial_emotion]+ gazeontask*100)/3,2)  if facial_emotion != "None" else round((participation_score_val+emotional_tone_val+speaking*100)/3,2)
            enagementscore.append(eng_score)

            reason_score = 0 if word_count_val <= 0  else  round((analytic_thinking_val+certainty_val+internal_cohesion_val)/3,2)
            reasoningscore.append(reason_score)
            
            idea_score = 0 if word_count_val <= 0  else round((analytic_thinking_val+authenticity_val+newness_val)/3,2)
            ideacontributionscore.append(idea_score)

            initia_score = 0 if word_count_val <= 0  else round((certainty_val+participation_score_val+ideacontributionscore[-1])/3,2)
            initiativescore.append(initia_score)

            lead_score = 0 if word_count_val <= 0  else round((clout_val+initiativescore[-1])/2,2)
            leadershipscore.append(lead_score)

            momentum.append(round((focusscore[-1]+participation_score_val+verbalshare[-1])/3,2))

            avg_derivative_metric_val = round((participationscore[-1]+focusscore[-1]+enagementscore[-1]+reasoningscore[-1]+ideacontributionscore[-1]+initiativescore[-1]+leadershipscore[-1]+momentum[-1])/8,2)
            window_trend_dir = 1 if enagementscore[-1] >= 70 and focusscore[-1] >= 70 else 0 if  enagementscore[-1] >= 50 or focusscore[-1] >= 50 else -1 #    get_progression(previous_trend, avg_derivative_metric_val,"numerical")
            # previous_trend = avg_derivative_metric_val
            session_trend.append(window_trend_dir)

            if word_count_val > 0:
                speaking_word_count.append(word_count_val)

            speaker_window_metrics =[window_id,window_start,window_end,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
            certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
            most_common_emotion,most_common_object,avg_attention,attention_rate,focused_gazeOn_task,focusscore[-1],enagementscore[-1],reasoningscore[-1],leadershipscore[-1], \
                initiativescore[-1],ideacontributionscore[-1],window_trend_dir,momentum[-1],verbalshare[-1],turnshare[-1]]
        else:
            analyticthinking.append(0)
            authenticity.append(0)
            certainty.append(0)
            clout.append(0)
            internalcohesion.append(0)
            socialimpact.append(0)
            newness.append(0)

            window_range = window_id.split('_')
            focusscore.append(0)
            enagementscore.append(0)
            reasoningscore.append(0)
            leadershipscore.append(0)
            initiativescore.append(0)
            ideacontributionscore.append(0)
            window_trend_dir = -1
            momentum.append(0)
            verbalshare.append(0)
            turnshare.append(0)
            speaker_window_metrics =[window_id,window_range[1], window_range[2], 'no speech',0,'no keywords', 0, 0, 0,  0, 0, 0, 0, 0, 0,0,0, 'None', 'None', 0, 0, 0,0,0,0,  0,0,0,-1,0,0,0]

        #update the derived value
        if window_id not in metric_acc_per_window and speakeralias not in metric_acc_per_window[window_id]:
            metric_acc_per_window[window_id][speakeralias][22] = focusscore[-1]
            metric_acc_per_window[window_id][speakeralias][23] = enagementscore[-1]
            metric_acc_per_window[window_id][speakeralias][24] = reasoningscore[-1]
            metric_acc_per_window[window_id][speakeralias][25] = leadershipscore[-1]
            metric_acc_per_window[window_id][speakeralias][26] = initiativescore[-1]
            metric_acc_per_window[window_id][speakeralias][27] = ideacontributionscore[-1]
            metric_acc_per_window[window_id][speakeralias][28] = window_trend_dir
            metric_acc_per_window[window_id][speakeralias][29] = momentum[-1]
            metric_acc_per_window[window_id][speakeralias][30] = verbalshare[-1]
            metric_acc_per_window[window_id][speakeralias][31] = turnshare[-1]

        if window_id not in Combined_object['window_level']:
            Combined_object['window_level'][window_id] = {speakeralias : dict(zip(metric_heading,speaker_window_metrics))}
        else:
            Combined_object['window_level'][window_id][speakeralias] = dict(zip(metric_heading,speaker_window_metrics))


        if speakeralias not in Combined_object['participants_level']:
            Combined_object['participants_level'][speakeralias] = [dict(zip(metric_heading,speaker_window_metrics))]
        else:
            Combined_object['participants_level'][speakeralias].append(dict(zip(metric_heading,speaker_window_metrics)))
    
    # for i , data in enumerate(speakerDetail):
    #     window_id,_,_,transcript_val,word_count_val,keywords_val,keyword_similarity_score_val,analytic_thinking_val,authenticity_val, \
    #     certainty_val,clout_val,emotional_tone_val,participation_score_val, internal_cohesion_val,responsivity_val,social_impact_val,newness_val, \
    #     most_common_emotion,most_common_object,_,attention_rate,gazeontask,_,_,_,_,_,_,most_common_trend_direction,_,_,_ = data

    #     focus_level = 0
    #     if mad != 0 and most_common_object != "None":
    #        robust_z = (attention_rate - median_x) / mad 
    #        focus_level = normalized_value_to_percentage(robust_z)

    #     focused_gazeOn_task = 1 if object_of_interest_focus and most_common_object in object_of_interest_focus else 0
    #     speaking = 1 if word_count_val > 0 else 0
    #     speaking_slience_focus = focused_gazeOn_task*50+ speaking*50
    #     facial_emotion = most_common_emotion
        
       
    #     stf = gazeontask/total_speaker_detected if total_speaker_detected > 0 else 0
    #     shared_task_focus.append(stf)
    #     focus = speaking_slience_focus if (focused_gazeOn_task > 0 and speaking > 0 ) else focused_gazeOn_task*100 if focused_gazeOn_task > 0 else speaking*100 if speaking > 0 else 0
    #     focusscore.append(focus)
    #     speakingalignmentscore.append(keyword_similarity_score_val)
    #     participationscore.append(participation_score_val)
    #     responsivityscore.append(responsivity_val)

    #     total_verbal_contri, total_turn  = get_total_verbal_turn_contribution_by_all_person_in_window(metric_acc_per_window[window_id],metric_acc_per_window[window_id]['persons'])
    #     comp_verbal_share = word_count_val/total_verbal_contri if total_verbal_contri > 0 else 0
    #     verbalshare.append(round((comp_verbal_share)*100,2))
    #     turn = 1 if word_count_val > 0 else 0
    #     comp_turn = turn/total_turn if total_turn > 0 else 0
    #     turnshare.append(round((comp_turn)*100,2))

    #     eng_score = round((focusscore[-1]+participation_score_val+turnshare[-1]+ verbalshare[-1])/4,2) if word_count_val > 0 and facial_emotion != "None" \
    #         else  round((focus_level),2)  if facial_emotion != "None" else round((participation_score_val+verbalshare[-1])/(2),2)

    #     # eng_score = round((focusscore[-1]+participation_score_val+emotional_tone_val+facial_expression[facial_emotion]+ speaking_slience_focus)/5,2) if word_count_val > 0 and facial_emotion != "None" \
    #     #     else  round((focus_level+facial_expression[facial_emotion]+ gazeontask*100)/3,2)  if facial_emotion != "None" else round((participation_score_val+emotional_tone_val+speaking*100)/3,2)
    #     enagementscore.append(eng_score)

    #     reason_score = 0 if word_count_val <= 0  else  round((analytic_thinking_val+certainty_val+internal_cohesion_val)/3,2)
    #     reasoningscore.append(reason_score)
        
    #     idea_score = 0 if word_count_val <= 0  else round((analytic_thinking_val+authenticity_val+newness_val)/3,2)
    #     ideacontributionscore.append(idea_score)

    #     initia_score = 0 if word_count_val <= 0  else round((certainty_val+participation_score_val+ideacontributionscore[-1])/3,2)
    #     initiativescore.append(initia_score)

    #     lead_score = 0 if word_count_val <= 0  else round((clout_val+initiativescore[-1])/2,2)
    #     leadershipscore.append(lead_score)

    #     momentum.append(round((focusscore[-1]+participation_score_val+verbalshare[-1])/3,2))

    #     avg_derivative_metric_val = round((participationscore[-1]+focusscore[-1]+enagementscore[-1]+reasoningscore[-1]+ideacontributionscore[-1]+initiativescore[-1]+leadershipscore[-1]+momentum[-1])/8,2)
    #     window_trend_dir = 1 if enagementscore[-1] >= 70 and focusscore[-1] >= 70 else 0 if  enagementscore[-1] >= 50 or focusscore[-1] >= 50 else -1 #    get_progression(previous_trend, avg_derivative_metric_val,"numerical")
    #     # previous_trend = avg_derivative_metric_val
    #     session_trend.append(window_trend_dir)

    #     if word_count_val > 0:
    #         speaking_word_count.append(word_count_val)

    #     #update the derived value
    #     speakerDetail[i][22] = focusscore[-1]
    #     metric_acc_per_window[window_id][speakeralias][22] = focusscore[-1]
    #     speakerDetail[i][23] = enagementscore[-1]
    #     metric_acc_per_window[window_id][speakeralias][23] = enagementscore[-1]
    #     speakerDetail[i][24] = reasoningscore[-1]
    #     metric_acc_per_window[window_id][speakeralias][24] = reasoningscore[-1]
    #     speakerDetail[i][25] = leadershipscore[-1]
    #     metric_acc_per_window[window_id][speakeralias][25] = leadershipscore[-1]
    #     speakerDetail[i][26] = initiativescore[-1]
    #     metric_acc_per_window[window_id][speakeralias][26] = initiativescore[-1]
    #     speakerDetail[i][27] = ideacontributionscore[-1]
    #     metric_acc_per_window[window_id][speakeralias][27] = ideacontributionscore[-1]
    #     speakerDetail[i][28] = window_trend_dir
    #     metric_acc_per_window[window_id][speakeralias][28] = window_trend_dir
    #     speakerDetail[i][29] = momentum[-1]
    #     metric_acc_per_window[window_id][speakeralias][29] = momentum[-1]
    #     speakerDetail[i][30] = verbalshare[-1]
    #     metric_acc_per_window[window_id][speakeralias][30] = verbalshare[-1]
    #     speakerDetail[i][31] = turnshare[-1]
    #     metric_acc_per_window[window_id][speakeralias][31] = turnshare[-1]

    #     if window_id not in Combined_object['window_level']:
    #         Combined_object['window_level'][window_id] = {speakeralias : dict(zip(metric_heading,speakerDetail[i]))}
    #     else:
    #         Combined_object['window_level'][window_id][speakeralias] = dict(zip(metric_heading,speakerDetail[i]))


    #     if speakeralias not in Combined_object['participants_level']:
    #         Combined_object['participants_level'][speakeralias] = [dict(zip(metric_heading,speakerDetail[i]))]
    #     else:
    #         Combined_object['participants_level'][speakeralias].append(dict(zip(metric_heading,speakerDetail[i])))

 

    len_session_trend = len(session_trend) 
    session_most_common_trend = Counter(session_trend).most_common(1)[0][0] if session_trend else -1
    early_trend = Counter(session_trend[0:len_session_trend//3]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    mid_trend = Counter(session_trend[len_session_trend//3 : (len_session_trend//3)*2]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    late_trend = Counter(session_trend[(len_session_trend//3)*2 : len_session_trend ]).most_common(1)[0][0] if session_trend and len_session_trend >= 3 else -1
    session_metrics=[]
    session_all_metrics = []
    if total_windows > 0:
        session_metrics.append(round(sum(focusscore)/total_windows,2))
        session_all_metrics.append(round(sum(focusscore)/total_windows,2))
        session_metrics.append(round(sum(participationscore)/total_windows,2))
        session_all_metrics.append(round(sum(participationscore)/total_windows,2))
        session_metrics.append(round(sum(responsivityscore)/total_windows,2))
        session_all_metrics.append(round(sum(responsivityscore)/total_windows,2))
        session_metrics.append(round(sum(enagementscore)/total_windows,2))           
        session_all_metrics.append(round(sum(enagementscore)/total_windows,2))
        session_metrics.append(round(sum(reasoningscore)/total_windows,2))
        session_all_metrics.append(round(sum(reasoningscore)/total_windows,2))
        session_metrics.append(round(sum(leadershipscore)/total_windows,2))
        session_all_metrics.append(round(sum(leadershipscore)/total_windows,2))
        session_metrics.append(round(sum(initiativescore)/total_windows,2))
        session_all_metrics.append(round(sum(initiativescore)/total_windows,2))
        session_metrics.append(round(sum(ideacontributionscore)/total_windows,2))
        session_all_metrics.append(round(sum(ideacontributionscore)/total_windows,2))
        session_metrics.append(round(sum(speakingalignmentscore)/total_windows,2))
        session_all_metrics.append(round(sum(speakingalignmentscore)/total_windows,2))
        session_metrics.append(round(sum(momentum)/total_windows,2))
        session_all_metrics.append(round(sum(momentum)/total_windows,2))
        session_metrics.append(round(sum(shared_task_focus)/total_windows,2))
        session_all_metrics.append(round((sum(shared_task_focus)/total_windows)*100,2))

        session_all_metrics.append(round(sum(analyticthinking)/total_windows,2))
        session_all_metrics.append(round(sum(authenticity)/total_windows,2))
        session_all_metrics.append(round(sum(certainty)/total_windows,2))
        session_all_metrics.append(round(sum(clout)/total_windows,2))
        session_all_metrics.append(round(sum(internalcohesion)/total_windows,2))
        session_all_metrics.append(round(sum(socialimpact)/total_windows,2))
        session_all_metrics.append(round(sum(newness)/total_windows,2))

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

    if len(total_verbal_turn_acc) > 0:   
        share_portion = round(100/no_of_participants, 2)
        session_metrics.append(round((((sum(speaking_word_count)/sum(total_verbal_turn_acc)) *100)/share_portion)*100,2))
        session_all_metrics.append(round((((sum(speaking_word_count)/sum(total_verbal_turn_acc)) *100)/share_portion)*100,2))
        session_metrics.append(round((((len(speaking_word_count)/len(total_verbal_turn_acc))*100)/share_portion)*100,2))
        session_all_metrics.append(round((((sum(speaking_word_count)/sum(total_verbal_turn_acc)) *100)/share_portion)*100,2))
    else:
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
    

    group_level_metric_acc['focusscore'].append(session_metrics[0]/100)
    group_level_metric_acc['participationscore'].append(session_metrics[1]/100)
    group_level_metric_acc['responsivity'].append(session_metrics[2]/100)
    group_level_metric_acc['engagementscore'].append(session_metrics[3]/100)
    group_level_metric_acc['reasoningscore'].append(session_metrics[4]/100)
    group_level_metric_acc['leadershipscore'].append(session_metrics[5]/100)
    group_level_metric_acc['initiativescore'].append(session_metrics[6]/100)
    group_level_metric_acc['ideacontributionscore'].append(session_metrics[7]/100)
    group_level_metric_acc['speakingalignmentscore'].append(session_metrics[8]/100)
    group_level_metric_acc['momentum'].append(session_metrics[9]/100)
    group_level_metric_acc['sharedtaskfocus'].append(session_metrics[10])
    group_level_metric_acc['verbalshare'].append(session_metrics[11]/100)
    group_level_metric_acc['turntaking'].append(session_metrics[12]/100)
    group_level_metric_acc['trenddirection'].append(session_metrics[13])
    group_level_metric_acc['earlytrenddirection'].append(session_metrics[14])
    group_level_metric_acc['midtrenddirection'].append(session_metrics[15])
    group_level_metric_acc['latetrenddirection'].append(session_metrics[16])
    


    
    session_data_heading = ['avg_focusscore','avg_participationscore','avg_responsivity','avg_engagementscore','avg_reasoningscore','avg_leadershipscore', 'avg_initiativescore','avg_ideacontributionscore',
                            'avg_speakingalignmentscore','avg_momentum','sharedtaskfocus','avg_verbalshare','avg_turntaking','avg_trenddirection','earlytrenddirection','midtrenddirection','latetrenddirection'] 
    
    session_all_data_heading = ['avg_focusscore','avg_participationscore','avg_responsivity','avg_engagementscore','avg_reasoningscore','avg_leadershipscore', 'avg_initiativescore','avg_ideacontributionscore',
                            'avg_speakingalignmentscore','avg_momentum','sharedtaskfocus','avg_analyticthinking','avg_authenticity','avg_certainty','avg_clout','avg_internalcohesion','avg_socialimpact','avg_newness',
                            'avg_verbalshare','avg_turntaking','wordcount','avg_trenddirection','earlytrenddirection','midtrenddirection','latetrenddirection'] 
    Combined_object['session_level'][speakeralias] = dict(zip(session_data_heading,session_metrics))
    Combined_object['session_all_metrics'][speakeralias] = dict(zip(session_all_data_heading,session_all_metrics))
   
def synthesized_transcript_video_metrics_by_window(transcriptSpeakerMetric,videoMetrics,session_device,keywords,windowsize=10): #speakers,
    v_index = t_index = 0
    attention_rate_acc_per_speaker = defaultdict(list)
    metric_acc_per_speaker_list = defaultdict(list)
    metric_acc_per_speaker_obj = defaultdict(dict)
    metric_acc_per_window = defaultdict(dict)
    group_level_metric_acc = defaultdict(list)
    total_verbal_turn_acc = []
    speakers = set()
    Combined_object = {'group_id': session_device.id, 'group_name': session_device.name, 'window_level':{}, 'participants_level':{}, 'session_level':{}, 'session_all_metrics':{},'group_level':{}}
    min_start = min(videoMetrics[0].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[0][0].start_time if transcriptSpeakerMetric else 0)
    max_end = max(videoMetrics[-1].time_stamp if videoMetrics else 0, transcriptSpeakerMetric[-1][0].start_time if transcriptSpeakerMetric else 0)
    window_start = min_start
    window_end = min_start+windowsize
    window_count = 0
    total_speaker_detected = 0
    while window_start <= max_end:
        window_id = f"w_{window_start}_{window_end}"
        window_video_metrics, v_index = extract_videometrics_within_window(videoMetrics,speakers, window_start, window_end, v_index)
        window_transcript_metrics, t_index = extract_transcriptmetrics_within_window(transcriptSpeakerMetric,speakers,keywords, window_start, window_end, t_index)

        #combine transcrit and video metrics for this window
        for speaker in speakers:
            w_video_meteic = window_video_metrics.get(speaker,[])
            w_transcript_metric = window_transcript_metrics.get(speaker,[])
            prev_metric = metric_acc_per_speaker_list[speaker][-1] if metric_acc_per_speaker_list.get(speaker,None) else [None]*32
            aggregated_video_metrics = aggregate_video_metric_per_window(w_video_meteic,windowsize,window_count,prev_metric) if w_video_meteic else []
            aggregated_transcript_metrics = aggregate_transcript_metric_per_window(w_transcript_metric,prev_metric) if w_transcript_metric else []
            
            #accumulate the attention rate for each speaker if there is video metrics. this will be used to compute the robust_z value
            if aggregated_video_metrics:
                attention_rate_acc_per_speaker[speaker].append(aggregated_video_metrics[3]) 

            combine_metrics = combine_transcript_video_metrics(aggregated_video_metrics,aggregated_transcript_metrics,window_id,window_start,window_end)

            if combine_metrics:
                metric_acc_per_speaker_list[speaker].append(combine_metrics)
                metric_acc_per_speaker_obj[speaker][window_id] = combine_metrics
                metric_acc_per_window[window_id][speaker]=combine_metrics

                #keep track of all the speaking turns
                if combine_metrics[4] > 0:
                    total_verbal_turn_acc.append(combine_metrics[4])

                if 'persons' not in metric_acc_per_window[window_id]:
                    metric_acc_per_window[window_id]['persons'] = [speaker]
                else:
                    metric_acc_per_window[window_id]['persons'].append(speaker)


        window_start = window_end
        window_end += windowsize
        window_count += 1

    total_speaker_detected = len(metric_acc_per_speaker_list)
    # so now we begin to compute the derived metrics for each speakers and update the record accordingly
    total_windows = len(metric_acc_per_window)
    object_of_interest_focus = ['laptop','book','paper','whiteboard']
    object_of_interest_focus.extend(list(speakers))
    all_windows = list(metric_acc_per_window.keys())
    for speaker, speakerDetail in  metric_acc_per_speaker_obj.items():
        attention_rates = attention_rate_acc_per_speaker.get(speaker,None)
        median_x,mad = compute_median_and_mad(np.array(attention_rates)) if attention_rates else [0,0]
        compute_derived_metric_and_update(metric_acc_per_window,all_windows,speakerDetail,total_windows,total_verbal_turn_acc,speaker,median_x,mad,Combined_object,group_level_metric_acc,total_speaker_detected,object_of_interest_focus,len(speakers)) 
        # session_metric_per_speaker[speaker.alias] = session_metrics  

    if total_speaker_detected > 1:
        #compute group level metric using the accumulated group data data 
        Combined_object['group_level']['verbalparticipationbalance'] = round((1 - statistics.stdev(group_level_metric_acc['verbalshare']))*100,2) 
        Combined_object['group_level']['turntakingbalance'] = round((1 - statistics.stdev(group_level_metric_acc['turntaking'])) * 100,2)
        Combined_object['group_level']['Sharedtaskfocus'] = round(sum(group_level_metric_acc['sharedtaskfocus']),2)
        Combined_object['group_level']['responsivity'] = round((sum(group_level_metric_acc['responsivity'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['ideacontribution'] = round((sum(group_level_metric_acc['ideacontributionscore'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['momentum'] = round((sum(group_level_metric_acc['momentum'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['participation'] = round((sum(group_level_metric_acc['participationscore'])/total_speaker_detected)*100,2)
        Combined_object['group_level']['engagement'] = round((sum(group_level_metric_acc['engagementscore'])/total_speaker_detected)*100,2) 
        Combined_object['group_level']['focusscore'] = round((sum(group_level_metric_acc['focusscore'])/total_speaker_detected)*100,2) 
        
    
    return Combined_object