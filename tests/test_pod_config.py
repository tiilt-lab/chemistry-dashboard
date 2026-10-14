"""The session starter's pod setup (src/server/pod_config.py): what the
create-session form may send, what is stored, and what the join page and
pod creation derive from it (slots, team names, roster size)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))
import pod_config as pc  # noqa: E402

VIKING = {"group_size": 6, "teams": [{"name": "Pat", "size": 3}, {"name": "Sandy", "size": 3}],
          "devices_per_group": "team", "group_count": 10, "group_prefix": "Table"}


def test_nothing_set_means_no_setup():
    for raw in (None, "", {}, False, {"enabled": False, "teams": [{"name": "X"}]}):
        assert pc.normalize(raw) == (None, None)
    assert pc.loads(None) is None and pc.loads("not json") is None and pc.loads("[1]") is None
    assert pc.dumps(None) is None
    assert pc.slots(None) == [] and pc.speaker_slots(None) == 0 and pc.team_names(None) == ("Team A", "Team B")
    assert pc.paired(None) is False


def test_viking_setup_normalizes_and_generates_group_labels():
    config, err = pc.normalize(VIKING)
    assert err is None
    assert config == {"group_size": 6, "teams": [{"name": "Pat", "size": 3}, {"name": "Sandy", "size": 3}],
                      "devices_per_group": "team", "groups": ["Table %d" % i for i in range(1, 11)]}
    assert pc.paired(config) and pc.team_names(config) == ("Pat", "Sandy")
    assert pc.match_team(config, " sandy ") == "Sandy" and pc.match_team(config, "Coach") is None
    assert pc.speaker_slots(config, "Pat") == 3 and pc.speaker_slots(config, None) == 6
    s = pc.slots(config)
    assert len(s) == 20 and s[0] == {"group": "Table 1", "team": "Pat", "size": 3, "label": "Table 1 · Pat's team"}
    assert s[1]["team"] == "Sandy" and s[-1]["group"] == "Table 10"
    assert pc.loads(pc.dumps(config)) == config
    # JSON text is accepted too (a stored value fed back)
    assert pc.normalize(pc.dumps(config)) == (config, None)


def test_one_device_per_group_with_free_text_groups():
    config, err = pc.normalize({"group_size": "4"})
    assert err is None and config == {"group_size": 4, "teams": [], "devices_per_group": "group", "groups": []}
    assert pc.slots(config) == [{"group": None, "team": None, "size": 4, "label": ""}]
    assert pc.team_names(config) == ("Team A", "Team B") and not pc.paired(config)   # no teams: placeholders
    config, _ = pc.normalize({"teams": [{"name": "A", "size": 2}, {"name": "B", "size": 4}], "groups": ["Left", "Right"]})
    assert config["group_size"] == 6 and config["devices_per_group"] == "group"
    assert [x["label"] for x in pc.slots(config)] == ["Left", "Right"] and pc.slots(config)[0]["size"] == 6
    assert pc.speaker_slots(config, "B") == 4


@pytest.mark.parametrize("raw, message", [
    ("[", "Pod setup is not valid JSON."),
    ([1], "Pod setup must be an object."),
    ({"teams": [1]}, "Each team must be an object with a name and a size."),
    ({"teams": [{"name": ""}]}, "Team 1 name is empty."),
    ({"teams": [{"name": "x" * 17}]}, "Team 1 name must not exceed 16 characters."),
    ({"teams": [{"name": "A<b>"}]}, "Team 1 name may only use letters, digits, spaces and apostrophes."),
    ({"teams": [{"name": "Pat"}, {"name": "pat"}]}, "Team names must be different (pat appears twice)."),
    ({"teams": [{"name": "Pat", "size": 0}]}, "Team Pat size must be between 1 and 64."),
    ({"teams": [{"name": "T%d" % i} for i in range(9)]}, "At most 8 teams per group."),
    ({"teams": [{"name": "A", "size": 40}, {"name": "B", "size": 40}]}, "A group may hold at most 64 people."),
    ({"group_size": "many"}, "Group size must be a whole number."),
    ({"devices_per_group": "laptop"}, "devices_per_group must be 'group' or 'team'."),
    ({"devices_per_group": "team", "teams": [{"name": "Solo"}]},
     "One laptop per team needs exactly two teams (one device records each side)."),
    ({"group_count": 0.5}, "Number of groups must be between 1 and 200."),
    ({"group_count": 201}, "Number of groups must be between 1 and 200."),
    ({"group_count": 2, "group_prefix": "<x>"}, "Group label may only use letters, digits, spaces and apostrophes."),
    ({"groups": "Table 1"}, "groups must be a list of labels."),
    ({"groups": ["A", "a"]}, "Group labels must be different (a appears twice)."),
    ({"groups": ["x" * 33]}, "Group label 1 must not exceed 32 characters."),
    ({"groups": ["G%d" % i for i in range(201)]}, "At most 200 groups."),
])
def test_bad_setups_are_refused_with_a_reason(raw, message):
    assert pc.normalize(raw) == (None, message)
