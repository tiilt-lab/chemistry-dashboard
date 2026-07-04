"""LLM-based Expression & Thinking Style scorer (Google Gemini).

A modern alternative to the LIWC / Harvard General Inquirer lexicon counting in
features_detector.py. Selected with ``scorer=llm`` in config.ini. Instead of
dictionary word-counts, it asks an LLM to rate the five dimensions 0-100 from
the utterance text, which handles context, negation, and paraphrase that a
bag-of-words lexicon cannot.

Reuses the same google-genai client the server already uses for the Reflection
Dashboard. Requires GOOGLE_API_KEY in the environment (or [llm] api_key config).

Returns the identical dict shape as the LIWC scorer so it is a drop-in swap.
"""
import os
import json
import logging

DIMENSIONS = [
    ("emotional_tone_value", "emotional tone (0 very negative, 100 very positive)"),
    ("analytic_thinking_value", "analytic vs. narrative thinking (100 = highly analytic)"),
    ("clout_value", "clout / confidence / leadership (100 = high)"),
    ("authenticity_value", "authenticity / honesty (100 = high)"),
    ("certainty_value", "certainty / conviction (100 = high)"),
]

_ZERO = {key: 0.0 for key, _ in DIMENSIONS}


class LlmScorer:
    def __init__(self):
        self._client = None
        self._model = None

    def initialize(self):
        print("Initializing LLM feature scorer...")
        from google import genai  # lazy import

        api_key = os.getenv("GOOGLE_API_KEY")
        self._model = os.getenv("LLM_SCORER_MODEL", "gemini-2.5-flash-lite")
        if not api_key:
            logging.warning(
                "GOOGLE_API_KEY not set; LLM scorer will return zeros. "
                "Set it or use scorer=liwc."
            )
            return
        self._client = genai.Client(api_key=api_key)
        print("LLM feature scorer ready ({}).".format(self._model))

    def detect_features(self, transcript):
        if not self._client or not transcript or not transcript.strip():
            return dict(_ZERO)

        rubric = "; ".join("{} = {}".format(k, d) for k, d in DIMENSIONS)
        prompt = (
            "Rate the following utterance on each dimension from 0 to 100. "
            "Respond with ONLY a compact JSON object using these exact keys: "
            + ", ".join(k for k, _ in DIMENSIONS)
            + ". Dimensions: " + rubric
            + '.\nUtterance: "' + transcript.strip() + '"'
        )
        try:
            resp = self._client.models.generate_content(
                model=self._model, contents=prompt
            )
            data = _parse_json(resp.text)
            return {
                key: _clamp(data.get(key)) for key, _ in DIMENSIONS
            }
        except Exception as e:
            logging.warning("LLM scorer failed; returning zeros: %s", e)
            return dict(_ZERO)


def _parse_json(text):
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {}
    return json.loads(text[start : end + 1])


def _clamp(value):
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
