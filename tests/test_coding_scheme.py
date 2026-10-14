"""Coding schemes as data (src/server/coding_schemes.py): the built-in
negotiation scheme, validation of an instructor's own, and the conversions
the engine and the pod page use."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))
import coding_schemes as cs  # noqa: E402


def test_the_builtin_negotiation_scheme_comes_from_the_viking_codebook():
    schemes = cs.builtin_schemes()
    assert [s["ref"] for s in schemes] == ["builtin:negotiation"]
    s = schemes[0]
    assert s["builtin"] is True and s["version"] == "viking-v2" and len(s["context"]) == 6
    assert [d["key"] for d in s["dimensions"]] == ["emotion", "rip", "frame", "listening"]
    assert [d["label"] for d in s["dimensions"]][1] == "Interests, rights, power"
    assert s["dimensions"][3]["multi"] is True and s["dimensions"][3]["default"] is None
    assert s["dimensions"][0]["default"] == "neutral"
    assert {c["code"]: c["label"] for c in s["dimensions"][2]["codes"]} == {
        "past_blame": "Past / blame", "future_problem_solving": "Future / problem-solving", "none": "None"}
    assert s["dimensions"][3]["conventions"] and s["dimensions"][3]["notes"]
    assert cs.builtin_scheme("nope") is None
    # a built-in round-trips through the validator unchanged in substance
    clean, err = cs.normalize({k: v for k, v in s.items() if k in ("name", "description", "context", "dimensions")})
    assert err is None and [d["key"] for d in clean["dimensions"]] == ["emotion", "rip", "frame", "listening"]


def test_normalize_slugs_labels_defaults_and_trims():
    raw = {"name": "  Turn taking  ", "description": "x",
           "context": "Line one\n\n  line two  ",
           "dimensions": [{"label": "Speech act", "codes": ["Question", {"code": "Answer "}, {"label": "Side remark"}]},
                          {"label": "Tone", "multi": True, "codes": [{"code": "warm", "examples": "a\nb"}], "default": "ignored"}]}
    scheme, err = cs.normalize(raw)
    assert err is None
    assert scheme["name"] == "Turn taking" and scheme["context"] == ["Line one", "line two"]
    d0, d1 = scheme["dimensions"]
    assert d0["key"] == "speech_act" and d0["multi"] is False and d0["default"] == "side_remark"
    assert [c["code"] for c in d0["codes"]] == ["question", "answer", "side_remark"]
    assert [c["label"] for c in d0["codes"]] == ["Question", "Answer", "Side remark"]
    assert d1["key"] == "tone" and d1["multi"] is True and d1["default"] is None
    assert d1["codes"][0]["examples"] == ["a", "b"]
    # a 'none' code becomes the single-choice default when none is named
    scheme, _ = cs.normalize({"name": "n", "dimensions": [{"label": "D", "codes": ["a", "none", "b"]}]})
    assert scheme["dimensions"][0]["default"] == "none"
    scheme, _ = cs.normalize({"name": "n", "dimensions": [{"label": "D", "codes": ["a", "b"], "default": "A"}]})
    assert scheme["dimensions"][0]["default"] == "a"
    assert cs.normalize('{"name": "j", "dimensions": [{"label": "D", "codes": ["a"]}]}')[1] is None


@pytest.mark.parametrize("raw, message", [
    ("{", "Coding scheme is not valid JSON."),
    ([], "Coding scheme must be an object."),
    ({"dimensions": [{"label": "D", "codes": ["a"]}]}, "Scheme name is missing."),
    ({"name": "x" * 65, "dimensions": []}, "Scheme name must not exceed 64 characters."),
    ({"name": "<b>", "dimensions": []}, "Scheme name may only use letters, digits, spaces and basic punctuation."),
    ({"name": "n"}, "A scheme needs at least one dimension."),
    ({"name": "n", "dimensions": [{"label": "D%d" % i, "codes": ["a"]} for i in range(9)]}, "At most 8 dimensions."),
    ({"name": "n", "dimensions": ["D"]}, "Dimension 1 must be an object."),
    ({"name": "n", "dimensions": [{"codes": ["a"]}]}, "Dimension 1 label is missing."),
    ({"name": "n", "dimensions": [{"label": "D", "key": "!!", "codes": ["a"]}]}, "Dimension 'D' needs a key of letters, digits and underscores."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": ["a"]}, {"label": "d", "codes": ["a"]}]}, "Two dimensions share the key 'd'."),
    ({"name": "n", "dimensions": [{"label": "D"}]}, "Dimension 'D' needs at least one code."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": ["c%d" % i for i in range(25)]}]}, "Dimension 'D': at most 24 codes."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": [1]}]}, "'D' code 1 must be an object."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": [{"definition": "x"}]}]}, "'D' code 1 needs a code of letters, digits and underscores."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": ["a", "A"]}]}, "Dimension 'D' lists the code 'a' twice."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": ["a"], "default": "zzz"}]}, "Dimension 'D': the default 'zzz' is not one of its codes."),
    ({"name": "n", "context": ["x" * 301], "dimensions": [{"label": "D", "codes": ["a"]}]}, "Context line 1 must not exceed 300 characters."),
    ({"name": "n", "dimensions": [{"label": "D", "codes": [{"code": "a", "definition": "x" * 401}]}]}, "'a' definition must not exceed 400 characters."),
])
def test_bad_schemes_are_refused_with_a_reason(raw, message):
    assert cs.normalize(raw) == (None, message)


def test_codebook_panel_and_analytics_conversions():
    scheme, _ = cs.normalize({"name": "Tiny", "description": "d", "context": ["c"],
                              "dimensions": [{"label": "Move", "codes": [{"code": "a", "label": "Aa", "definition": "x", "examples": ["e"]}, "none"],
                                              "conventions": ["rule"]}]})
    book = cs.to_codebook(scheme, "scheme:7")
    assert book["ref"] == "scheme:7" and book["version"] == "Tiny" and book["case_facts"] == ["c"]
    assert book["dimensions"]["move"] == {"multi": False, "label": "Move", "default": "none", "guidance": "",
                                          "codes": {"a": {"label": "Aa", "definition": "x", "examples": ["e"]},
                                                    "none": {"label": "None", "definition": "", "examples": []}},
                                          "conventions": ["rule"]}
    panel = cs.panel_json(book)
    assert panel == {"ref": "scheme:7", "name": "Tiny",
                     "dimensions": [{"key": "move", "label": "Move", "multi": False, "default": "none",
                                     "codes": [{"code": "a", "label": "Aa"}, {"code": "none", "label": "None"}]}],
                     "analytics": {"timeline": False, "future_move": False, "dynamics": False}}
    viking = cs.to_codebook(cs.builtin_scheme("negotiation"))
    assert cs.analytics(viking) == {"timeline": True, "future_move": True, "dynamics": True}
    assert cs.resolve("builtin:negotiation")["name"] == "Viking"
    assert cs.resolve("scheme:3", lambda i: {"name": "S%d" % i, "dimensions": []}) == {"name": "S3", "dimensions": [], "ref": "scheme:3"}
    assert cs.resolve("scheme:3", lambda i: None) is None and cs.resolve("scheme:x", lambda i: {}) is None
    assert cs.resolve("bogus:1") is None and cs.resolve(None) is None and cs.resolve("scheme:3") is None
    assert cs.slugify("Past / blame!!") == "past_blame" and cs.titleize("future_problem_solving") == "Future problem solving"
