"""The spaCy loader + gensim bigram builder + base stop words are shared.

Both topic-modeling modules (audio per-utterance inference, server training)
kept identical copies of _get_nlp / generate_bigram / BASE_STOP_WORDS. They now
import them from common. (These modules pull in spaCy/gensim, absent in CI, so
this is a source-level contract; the real import is exercised when each service
starts.)
"""
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def _read(*p):
    with open(os.path.join(SRC, *p)) as f:
        return f.read()


def test_common_defines_the_shared_helpers():
    c = _read("common", "topic_modeling_common.py")
    assert "def _get_nlp():" in c and "def generate_bigram(" in c
    assert "BASE_STOP_WORDS = ('from', 'subject', 're', 'edu', 'use')" in c


def test_both_modules_import_from_common_and_dont_redefine():
    for parts in (("audio_processing", "topic_modeling", "topic_modeling.py"),
                  ("server", "topic_modeling", "topicmodeling.py")):
        s = _read(*parts)
        name = "/".join(parts)
        assert "from topic_modeling_common import" in s, f"{name}: must import shared helpers"
        assert "def _get_nlp(" not in s, f"{name}: _get_nlp must be inherited"
        assert "def generate_bigram(" not in s, f"{name}: generate_bigram must be inherited"
