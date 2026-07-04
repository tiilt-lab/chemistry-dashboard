"""Expression & Thinking Style scorer factory.

Selects the scoring backend from the ``scorer`` config key (config.py
``scorer()``). Each scorer exposes ``initialize()`` and
``detect_features(transcript) -> dict`` with the five *_value keys.

- ``liwc`` (default): the LIWC / Harvard General Inquirer lexicon counter in
  features_detector.py (the module itself satisfies the scorer interface).
- ``llm``: Google Gemini rates the dimensions from context (llm_scorer.py).

A process-wide singleton so the server (initialize) and processor
(detect_features) share one instance.
"""
import logging

_active = None


def get_scorer(name=None):
    global _active
    if _active is not None:
        return _active

    key = (name or "liwc").strip().lower()
    if key == "open":
        from . import open_scorer

        logging.info("Feature scorer: open (Harvard General Inquirer)")
        _active = open_scorer  # module implements initialize() + detect_features()
    elif key == "llm":
        from .llm_scorer import LlmScorer

        logging.info("Feature scorer: LLM (Gemini)")
        _active = LlmScorer()
    else:
        if key not in ("liwc", ""):
            logging.warning("Unknown scorer '%s'; falling back to LIWC", name)
        from . import features_detector as liwc

        logging.info("Feature scorer: LIWC / Harvard General Inquirer")
        _active = liwc  # module implements initialize() + detect_features()
    return _active
