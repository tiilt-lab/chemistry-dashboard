"""Composite LIWC indices used by the post-hoc P&I / E&T style re-computation.

Ported verbatim from the videodev checkout's respeaker_hi_liwc.py so the
transcript-only re-scoring (SpeakerMetricProcessor) can run without disturbing
the live scoring path in respeaker_hi_liwc.py / features_detector.detect_features.
"""

from collections import Counter
from .respeaker_hi_liwc import process_text

COMPOSITE_LIWC_INDICES = {
    "analytical_thinking": ["Article", "Prep", "CogMech", "Insight", "Cause", "Certain"],
    "Narrative_thinking": ["I", "Ppron", "AuxVb", "Adverbs", "Conj", "Negate"],
    "clout": ["Certain", "Assent", "Achiev", "We"],
    "no_clout": ["Tentat", "Anx"],
    "authenticity": ["I", "Ppron", "Affect", "Negemo", "Anx", "Sad"],
    "positive_climate": ["Posemo", "Assent", "Affect"],
    "negative_conflict_climate": ["Negemo", "Anger", "Sad", "Anx", "Negate"],
    "collaborative_coordination": ["Social", "We", "Assent"],
    "social_attention": ["You", "They", "SheHe"],
    "disfluency_signal": ["Nonflu", "Filler"],
    "task_focus": ["Work", "Achiev", "CogMech", "Cause", "Insight"],
    "certainty": ["Certain", "Assent"],
    "uncertainty": ["Tentat", "Discrep", "Negate"],
}


def weighted_average(features, weights):
    numerator = 0.0
    denominator = 0.0
    for category, weight in weights.items():
        value = features.get(category, 0.0)
        if value > 0:
            numerator += value * weight
            denominator += weight
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 2)


def mean_liwc_index(features, categories, decimals=2):
    values = [float(features.get(cat, 0.0)) for cat in categories]
    if not values:
        return 0.0
    return round(sum(values) / len(values), decimals)


def balance_index(positive, negative):
    total = positive + negative
    if total == 0:
        return 0.5  # no evidence either way
    return positive / total


def extract_liwc_categories(text, liwc_dictionary, liwc_emots):
    """Extract LIWC category percentages from text."""
    detected_category_counts = Counter()
    liwc_emot_feature = {}
    total_words_count, liwc_emot = process_text(text, liwc_dictionary, liwc_emots)
    for category, cat_count in liwc_emot.items():
        if cat_count > 0:
            detected_category_counts[category] = cat_count
            liwc_emot_feature[category] = (cat_count / total_words_count) * 100
        else:
            liwc_emot_feature[category] = 0.0
    liwc_emot_feature["word_count"] = total_words_count
    liwc_emot_feature["dictionary_coverage"] = (
        sum(detected_category_counts.values()) / total_words_count
        if total_words_count > 0
        else 0.0
    )
    return liwc_emot_feature
