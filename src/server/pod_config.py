"""Pod setup for a session: how a breakout group is composed and which
device records what. Set once by the session starter (create-session form),
stored as JSON on session.pod_config, read by the join page (which slot a
device occupies), by pod creation (which team names are legal, how many
speaker slots to pre-create) and by negotiation coding (team names, and
whether the two pods of a group are coded together).

    {
      "group_size": 6,                       # people per breakout group
      "teams": [{"name": "Buyer", "size": 3},  # 0 or 1 entries = no team split
                {"name": "Seller", "size": 3}],
      "devices_per_group": "team" | "group", # one laptop per team, or per group
      "groups": ["Table 1", ..., "Table 10"] # preset labels; [] = free text
    }

Pure functions only (no Flask, no DB) so the rules are unit-testable and
usable from the tables module.
"""
import json
import re

MAX_GROUPS = 200
MAX_TEAMS = 8
MAX_GROUP_SIZE = 64
NAME_MAX = 16          # team name (fits session_device.negotiation_side)
LABEL_MAX = 32         # group label (fits session_device.negotiation_group)
_NAME_RE = re.compile(r"^[a-zA-Z0-9' ]+$")
DEVICES = ("group", "team")
# Placeholder names for a session whose setup names no teams (nothing in the
# code knows any particular case's sides; a class names its own).
DEFAULT_TEAMS = ("Team A", "Team B")


def _clean(text, limit, what):
    if text is None:
        return None, "%s is missing." % what
    if not isinstance(text, str):
        return None, "%s must be text." % what
    text = " ".join(text.split())
    if not text:
        return None, "%s is empty." % what
    if len(text) > limit:
        return None, "%s must not exceed %d characters." % (what, limit)
    if not _NAME_RE.match(text):
        return None, "%s may only use letters, digits, spaces and apostrophes." % what
    return text, None


def _int(value, lo, hi, what):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None, "%s must be a whole number." % what
    if n < lo or n > hi:
        return None, "%s must be between %d and %d." % (what, lo, hi)
    return n, None


def normalize(raw):
    """(config, error): the stored shape for a form/API value, or (None,
    None) when nothing was set (null, {} or a disabled setup)."""
    if raw in (None, "", {}, False):
        return None, None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None, "Pod setup is not valid JSON."
    if not isinstance(raw, dict):
        return None, "Pod setup must be an object."
    if raw.get("enabled") is False:
        return None, None

    teams = []
    seen = set()
    for i, entry in enumerate(raw.get("teams") or []):
        if not isinstance(entry, dict):
            return None, "Each team must be an object with a name and a size."
        name, err = _clean(entry.get("name"), NAME_MAX, "Team %d name" % (i + 1))
        if err:
            return None, err
        if name.lower() in seen:
            return None, "Team names must be different (%s appears twice)." % name
        seen.add(name.lower())
        size, err = _int(entry.get("size", 1), 1, MAX_GROUP_SIZE, "Team %s size" % name)
        if err:
            return None, err
        teams.append({"name": name, "size": size})
    if len(teams) > MAX_TEAMS:
        return None, "At most %d teams per group." % MAX_TEAMS

    if teams:
        group_size = sum(t["size"] for t in teams)
        if group_size > MAX_GROUP_SIZE:
            return None, "A group may hold at most %d people." % MAX_GROUP_SIZE
    else:
        group_size, err = _int(raw.get("group_size", 4), 1, MAX_GROUP_SIZE, "Group size")
        if err:
            return None, err

    devices = raw.get("devices_per_group") or "group"
    if devices not in DEVICES:
        return None, "devices_per_group must be 'group' or 'team'."
    if devices == "team" and len(teams) != 2:
        return None, "One laptop per team needs exactly two teams (one device records each side)."

    groups = []
    raw_groups = raw.get("groups")
    if raw_groups in (None, ""):
        count = raw.get("group_count")
        if count not in (None, "", 0, "0"):
            count, err = _int(count, 1, MAX_GROUPS, "Number of groups")
            if err:
                return None, err
            prefix, err = _clean(raw.get("group_prefix") or "Group", LABEL_MAX - 4, "Group label")
            if err:
                return None, err
            groups = ["%s %d" % (prefix, i + 1) for i in range(count)]
    elif isinstance(raw_groups, list):
        seen = set()
        for i, label in enumerate(raw_groups):
            label, err = _clean(label, LABEL_MAX, "Group label %d" % (i + 1))
            if err:
                return None, err
            if label.lower() in seen:
                return None, "Group labels must be different (%s appears twice)." % label
            seen.add(label.lower())
            groups.append(label)
        if len(groups) > MAX_GROUPS:
            return None, "At most %d groups." % MAX_GROUPS
    else:
        return None, "groups must be a list of labels."

    return {"group_size": group_size, "teams": teams, "devices_per_group": devices, "groups": groups}, None


def team_names(config):
    """The team names a device may record for; the placeholder pair when the
    session has no setup or no team split."""
    teams = (config or {}).get("teams") or []
    if len(teams) >= 2:
        return tuple(t["name"] for t in teams)
    return DEFAULT_TEAMS


def match_team(config, side):
    """The canonical team name for a join's side value (case-insensitive),
    or None when it is not one of the session's teams."""
    if side in (None, ""):
        return None
    wanted = " ".join(str(side).split()).lower()
    for name in team_names(config):
        if name.lower() == wanted:
            return name
    return None


def paired(config):
    """True when each team records from its own device (two pods per group
    are coded as one conversation)."""
    return bool(config) and config.get("devices_per_group") == "team" and len(config.get("teams") or []) == 2


def slots(config):
    """What a joining device can occupy: [{group, team, size, label}], one
    per (group, team) when each team has a device, else one per group.
    Without preset groups the group is None (the join page asks for it)."""
    if not config:
        return []
    groups = config.get("groups") or [None]
    out = []
    if paired(config):
        for g in groups:
            for t in config["teams"]:
                out.append({"group": g, "team": t["name"], "size": t["size"],
                            "label": " · ".join(p for p in (g, "%s's team" % t["name"]) if p)})
    else:
        for g in groups:
            out.append({"group": g, "team": None, "size": config["group_size"], "label": g or ""})
    return out


def speaker_slots(config, team=None):
    """How many speaker cards a device pre-creates: its team's size when it
    records one team, else the group size; 0 without a setup (the roster is
    sized on the speaker page, as before)."""
    if not config:
        return 0
    if team:
        for t in config.get("teams") or []:
            if t["name"] == team:
                return t["size"]
    return config.get("group_size") or 0


def dumps(config):
    return json.dumps(config) if config else None


def loads(raw):
    if not raw:
        return None
    try:
        config = json.loads(raw)
    except ValueError:
        return None
    return config if isinstance(config, dict) else None
