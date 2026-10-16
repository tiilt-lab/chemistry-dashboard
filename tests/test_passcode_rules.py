"""src/server/passcode_rules.py: a chosen join code."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import passcode_rules  # noqa: E402


def test_blank_means_draw_a_random_word():
    for raw in (None, "", "   "):
        assert passcode_rules.normalize(raw) == (None, None)


def test_codes_are_trimmed_and_upper_cased():
    assert passcode_rules.normalize(" moon ") == ("MOON", None)
    assert passcode_rules.normalize("Table7") == ("TABLE7", None)


def test_length_limits_match_the_join_page():
    assert passcode_rules.normalize("AB")[0] is None
    assert passcode_rules.normalize("A" * 17)[0] is None
    assert passcode_rules.normalize("A" * 16) == ("A" * 16, None)
    assert passcode_rules.normalize("ABC") == ("ABC", None)


def test_only_letters_and_digits():
    for raw in ("MO ON", "MOON!", "MO-ON", "MOON/", "月月月"):
        code, err = passcode_rules.normalize(raw)
        assert code is None
        assert "letters and digits" in err
    code, err = passcode_rules.normalize(3)
    assert code is None and "text" in err


def test_in_use_message_names_the_session():
    msg = passcode_rules.in_use_message("MOON", "Viking Oct 16")
    assert "MOON" in msg and "Viking Oct 16" in msg and "End that session" in msg
