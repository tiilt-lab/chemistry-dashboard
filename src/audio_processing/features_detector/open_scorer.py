"""Fully open-source Expression & Thinking Style scorer.

Selected with ``scorer=open`` in config.ini. Uses ONLY the Harvard General
Inquirer lexicon (public/academic, bundled in dictionaries/) and NLTK
(Apache-2.0) — no proprietary LIWC dictionary, no cloud API. This gives a
zero-license, offline scoring path to pair with the open Whisper ASR.

Produces the same five *_value keys as the LIWC scorer. The psycholinguistic
mapping differs from the proprietary LIWC constructs (it is built from open HGI
categories), so absolute values are not directly comparable to LIWC output —
they are an open approximation of the same five dimensions.
"""
import logging

from .respeaker_hi_liwc import populate_dictionary_index_hi, process_text

# HGI categories used (all present in inquirerbasicttabsclean.txt).
_CATEGORIES = [
    "Positiv",
    "Negativ",
    "Causal",
    "Know",
    "Strong",
    "Weak",
    "SureLw",
    "Ovrst",
    "Undrst",
    "Self",
]

_hgi_dictionary = None


def initialize():
    global _hgi_dictionary
    print("Initializing open (Harvard General Inquirer) feature scorer...")
    _, _hgi_dictionary = populate_dictionary_index_hi()
    print("Open feature scorer ready.")


def _ratio(a, b):
    # 0-100 where 50 is neutral; a is the "positive pole" count.
    total = a + b
    if total <= 0:
        return 50.0
    return 100.0 * a / total


def _proportion(count, total):
    if total <= 0:
        return 0.0
    return min(100.0, 100.0 * count / total)


def detect_features(transcript):
    if _hgi_dictionary is None or not transcript or not transcript.strip():
        return _zero()

    word_count, counts = process_text(transcript, _hgi_dictionary, _CATEGORIES)
    if word_count <= 0:
        return _zero()

    def c(name):
        return counts.get(name, 0)

    return {
        # Positive vs. negative affect.
        "emotional_tone_value": _ratio(c("Positiv"), c("Negativ")),
        # Causal / knowledge language ~ analytic reasoning.
        "analytic_thinking_value": _proportion(c("Causal") + c("Know"), word_count),
        # Strong vs. weak language ~ confidence / clout.
        "clout_value": _ratio(c("Strong"), c("Weak")),
        # First-person self-reference ~ authenticity proxy.
        "authenticity_value": _proportion(c("Self"), word_count),
        # Overstated vs. understated ~ certainty.
        "certainty_value": _ratio(c("Ovrst") + c("SureLw"), c("Undrst")),
    }


def _zero():
    return {
        "analytic_thinking_value": 0.0,
        "authenticity_value": 0.0,
        "certainty_value": 0.0,
        "clout_value": 0.0,
        "emotional_tone_value": 0.0,
    }
