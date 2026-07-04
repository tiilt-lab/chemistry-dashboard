"""Expression & Thinking Style scorer factory.

Selects the scoring backend by name (defaulting to the ``scorer`` config key
via config.py ``scorer()``). Each scorer exposes ``initialize()`` and
``detect_features(transcript) -> dict`` with the five *_value keys.

- ``liwc`` (default): the LIWC / Harvard General Inquirer lexicon counter in
  features_detector.py (the module itself satisfies the scorer interface).
- ``open``: Harvard General Inquirer only (no licensed lexicon).
- ``llm``: Google Gemini rates the dimensions from context (llm_scorer.py).
"""
import logging

# One initialized instance per backend, so a long-lived server (e.g. the
# post-hoc processor, where each run may choose a different scorer) can serve
# any of them; each is initialized exactly once, on first use.
_instances = {}


def get_scorer(name=None):
    key = (name or "liwc").strip().lower()
    if key not in ("liwc", "open", "llm"):
        logging.warning("Unknown scorer '%s'; falling back to LIWC", name)
        key = "liwc"
    if key in _instances:
        return _instances[key]

    if key == "open":
        from . import open_scorer

        logging.info("Feature scorer: open (Harvard General Inquirer)")
        instance = open_scorer  # module implements initialize() + detect_features()
    elif key == "llm":
        from .llm_scorer import LlmScorer

        logging.info("Feature scorer: LLM (Gemini)")
        instance = LlmScorer()
    else:
        from . import features_detector as liwc

        logging.info("Feature scorer: LIWC / Harvard General Inquirer")
        instance = liwc  # module implements initialize() + detect_features()
    instance.initialize()
    _instances[key] = instance
    return instance
