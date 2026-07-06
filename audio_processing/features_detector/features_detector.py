import json
import os
import re
from .respeaker_hi_liwc import populate_dictionary_index_hi, populate_dictionary_index_liwc, process_text,extract_liwc_categories,balance_index,COMPOSITE_LIWC_INDICES,mean_liwc_index,weighted_average

def initialize():
    print('Unpacking features model...')
    global hgi_emots, hgi_dictionary, liwc_emots, liwc_dictionary
    hgi_emots, hgi_dictionary = populate_dictionary_index_hi()
    liwc_emots, liwc_dictionary = populate_dictionary_index_liwc()
    print('Model unpacked.')

def detect_features(transcript):
    hgi_emots = ['Positiv','Know', 'Causal','SureLw']
    liwc_emots = ['CogMech', 'Assent', 'Conj', 'Insight', 'Certain','I']
    hgi_count, hgi_emot_dict = process_text(transcript, hgi_dictionary, hgi_emots)
    liwc_count, liwc_emot_dict = process_text(transcript, liwc_dictionary, liwc_emots)
    emotion_val = 0.0
    analytic_val = 0.0
    collab_quality_val = 0.0
    certainty_val = 0.0
    authenticity_val = 0.0
    if liwc_count > 0:
        emotion_val = 100.0 * max([hgi_emot_dict['Positiv']])/float(liwc_count)
        analytic_val = 100.0 * max([hgi_emot_dict['Causal'], liwc_emot_dict['CogMech'], liwc_emot_dict['Insight']])/float(liwc_count)
        collab_quality_val = 100.0 * max([liwc_emot_dict['Conj'], liwc_emot_dict['Assent']])/float(liwc_count)
        certainty_val = 100.0 * max([hgi_emot_dict['SureLw'],liwc_emot_dict['Certain']])/float(liwc_count)
        authenticity_val = 100.0 * liwc_emot_dict['I']/float(liwc_count)

    return {
        'analytic_thinking_value': analytic_val,
        'authenticity_value': authenticity_val,
        'certainty_value':certainty_val,
        'clout_value': collab_quality_val,
        'emotional_tone_value': emotion_val
    }

def detect_LIWC_Indices(transcript):
    results = {}
    liwc_emots, liwc_dictionary = populate_dictionary_index_liwc()
    liwc_features = extract_liwc_categories(transcript, liwc_dictionary, liwc_emots)
    for summary_name, weights in COMPOSITE_LIWC_INDICES.items():
        raw_score = mean_liwc_index(liwc_features, weights)
        results[f"{summary_name}"] = round(raw_score, 3)
    
    return {
        'analytic_thinking_value':  results["analytical_thinking"], #balance_index(results["analytical_thinking"],results["Narrative_thinking"]),
        'Narrative_thinking': results["Narrative_thinking"],
        'composite_analytical_thinking': balance_index(results["analytical_thinking"],results["Narrative_thinking"]),
        'authenticity_value': results["authenticity"],
        'certainty': results["certainty"],
        'uncertainty': results["uncertainty"],
        'certainty_value': balance_index(results["certainty"],results["uncertainty"]), #results["certainty"],
        'clout': results["clout"],
        'no_clout': results["no_clout"],
        'clout_value': balance_index(results["clout"],results["no_clout"]) ,#results["clout"],
        'positive_climate':results["positive_climate"],
        'negative_conflict_climate': results["negative_conflict_climate"],
        'emotional_tone_value': balance_index(results["positive_climate"],results["negative_conflict_climate"]) #max(0.0, min(1, round((results["positive_climate"] - results["negative_conflict_climate"]+1)/2,2)))
    }
        
    
def detect_LIWC_features(transcript):
    results = {}
    liwc_emots, liwc_dictionary = populate_dictionary_index_liwc()
    liwc_features = extract_liwc_categories(transcript, liwc_dictionary, liwc_emots)
    return liwc_features
           

# The question detector may eventually need it's own folder/module.
# Due to its limited implementation, it can stay here for now.
def detect_questions(transcript):
    # Find all instances of text ending with a '?' and starting with punctuation (and spaces).
    questions = re.findall(r'(?:[.!]\s+|\A).*?[?]', transcript)

    # Remove extra spaces and beginning punctuation.
    result = []
    for question in questions:
        result.append(re.sub(r'\A[.,!]?\s+', '', question))
    return result

if __name__ == '__main__':
    initialize()
    result = detect_features('It is a strong belief of mine that the Earth is spherical in nature.')
    print(result)

    result = detect_questions('What is your favorite color?')
    print(result)

    result = detect_questions("My favorite color is orange.")
    print(result)

    result = detect_questions("   What is your favorite color?  My favorite color is orange.  Another question?????? Random words... Do you work for the C.I.A?")
    print(result)
