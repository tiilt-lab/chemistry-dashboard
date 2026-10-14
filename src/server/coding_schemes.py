"""Coding schemes: what the utterance coder codes for. A scheme is data, not
code: a name, a description, optional context lines the coder is shown so
references in the transcript resolve, and dimensions, each with its codes
(one code per utterance, or any number). The negotiation scheme built for
the Kellogg Viking case ships as a built-in (src/server/
negotiation_codebook.json); instructors make their own in the Library
(tables/coding_scheme.py, routes/coding_scheme.py) and a session picks one
(session.coding_scheme = "builtin:<key>" | "scheme:<id>"). Named in the
plural because routes/ and tables/ each have a coding_scheme module.

Two shapes. The EDITOR shape (what the API takes and returns) keeps
dimensions and codes as ordered lists with labels; the ENGINE shape
(negotiation_coding.py) keys them by slug. ``to_codebook`` converts.
Pure functions only; the DB lookup for "scheme:<id>" is passed in.
"""
import json
import os
import re

NAME_MAX = 64
DESCRIPTION_MAX = 500
CONTEXT_MAX_ITEMS, CONTEXT_ITEM_MAX = 30, 300
DIMENSIONS_MAX = 8
LABEL_MAX, SLUG_MAX = 40, 24
GUIDANCE_MAX = 2500
CODES_MAX = 24
DEFINITION_MAX = 400
EXAMPLES_MAX, EXAMPLE_MAX = 6, 200
CONVENTIONS_MAX, CONVENTION_MAX = 12, 300
_SLUG_RE = re.compile(r"^[a-z0-9_]+$")
_NAME_RE = re.compile(r"^[a-zA-Z0-9' :,./()\-]+$")

BUILTIN_PREFIX, SCHEME_PREFIX = "builtin:", "scheme:"
BUILTIN_NEGOTIATION = "negotiation"
_BUILTIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "negotiation_codebook.json")
# Display labels for the built-in scheme (its JSON predates labels).
_BUILTIN_LABELS = {
    "emotion": ("Emotion", {"escalating": "Escalating", "defusing": "Defusing", "neutral": "Neutral"}),
    "rip": ("Interests, rights, power", {"interest": "Interest", "right": "Right", "power": "Power", "none": "None"}),
    "frame": ("Frame", {"past_blame": "Past / blame", "future_problem_solving": "Future / problem-solving", "none": "None"}),
    "listening": ("Listening", {"open_question": "Open question", "closed_question": "Closed question",
                                "paraphrase": "Paraphrase", "summarize": "Summarize", "acknowledge": "Acknowledge",
                                "check_understanding": "Check understanding", "ask_why": "Ask why",
                                "ask_priority": "Ask priority", "ask_constraint": "Ask constraint",
                                "interrupt": "Interrupt"}),
}


def slugify(text, limit=SLUG_MAX):
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return s[:limit].rstrip("_")


def titleize(slug):
    return (slug or "").replace("_", " ").strip().capitalize()


# ------------------------------------------------------------ built-ins

def _builtin_negotiation():
    with open(_BUILTIN_FILE, encoding="utf-8") as f:
        book = json.load(f)
    dims = []
    for key, spec in book["dimensions"].items():
        label, code_labels = _BUILTIN_LABELS.get(key, (titleize(key), {}))
        dims.append({
            "key": key, "label": label, "multi": bool(spec.get("multi")),
            "guidance": spec.get("guidance") or "",
            "default": spec.get("default") if not spec.get("multi") else None,
            "codes": [{"code": c, "label": code_labels.get(c, titleize(c)),
                       "definition": e.get("definition") or "", "examples": list(e.get("examples") or [])}
                      for c, e in spec["codes"].items()],
            "conventions": list(spec.get("conventions") or []),
            "notes": spec.get("notes") or None,
        })
    return {
        "ref": BUILTIN_PREFIX + BUILTIN_NEGOTIATION,
        "name": "Negotiation: emotion, interests/rights/power, frame, listening",
        "description": "Built for the Kellogg Viking Investments case: every utterance coded for "
                       "escalation, the interests/rights/power move, past-blame vs future "
                       "problem-solving framing, and listening moves; with a de-escalation timeline "
                       "and per-team opening moves. The context lines describe the Viking case.",
        "context": list(book.get("case_facts") or []),
        "dimensions": dims,
        "builtin": True,
        "version": book.get("version"),
    }


def builtin_schemes():
    return [_builtin_negotiation()]


def builtin_scheme(key):
    for scheme in builtin_schemes():
        if scheme["ref"] == BUILTIN_PREFIX + key:
            return scheme
    return None


# ----------------------------------------------------------- validation

def _text(value, limit, what, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        return None, "%s must be text." % what
    value = " ".join(value.split()) if "\n" not in value else "\n".join(" ".join(l.split()) for l in value.splitlines()).strip()
    if required and not value:
        return None, "%s is missing." % what
    if len(value) > limit:
        return None, "%s must not exceed %d characters." % (what, limit)
    return value, None


def _lines(value, max_items, item_max, what):
    if value in (None, ""):
        return [], None
    if isinstance(value, str):
        value = [l for l in value.splitlines()]
    if not isinstance(value, list):
        return None, "%s must be a list of lines." % what
    out = []
    for i, item in enumerate(value):
        item, err = _text(item, item_max, "%s line %d" % (what, i + 1))
        if err:
            return None, err
        if item:
            out.append(item)
    if len(out) > max_items:
        return None, "At most %d %s lines." % (max_items, what.lower())
    return out, None


def normalize(raw):
    """(scheme in the editor shape, error) for a form/API value."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None, "Coding scheme is not valid JSON."
    if not isinstance(raw, dict):
        return None, "Coding scheme must be an object."
    name, err = _text(raw.get("name"), NAME_MAX, "Scheme name", required=True)
    if err:
        return None, err
    if not _NAME_RE.match(name):
        return None, "Scheme name may only use letters, digits, spaces and basic punctuation."
    description, err = _text(raw.get("description"), DESCRIPTION_MAX, "Description")
    if err:
        return None, err
    context, err = _lines(raw.get("context"), CONTEXT_MAX_ITEMS, CONTEXT_ITEM_MAX, "Context")
    if err:
        return None, err
    raw_dims = raw.get("dimensions")
    if not isinstance(raw_dims, list) or not raw_dims:
        return None, "A scheme needs at least one dimension."
    if len(raw_dims) > DIMENSIONS_MAX:
        return None, "At most %d dimensions." % DIMENSIONS_MAX
    dims, seen = [], set()
    for i, d in enumerate(raw_dims):
        if not isinstance(d, dict):
            return None, "Dimension %d must be an object." % (i + 1)
        label, err = _text(d.get("label"), LABEL_MAX, "Dimension %d label" % (i + 1), required=True)
        if err:
            return None, err
        key = slugify(d.get("key") or label)
        if not key or not _SLUG_RE.match(key):
            return None, "Dimension '%s' needs a key of letters, digits and underscores." % label
        if key in seen:
            return None, "Two dimensions share the key '%s'." % key
        seen.add(key)
        multi = d.get("multi") is True
        guidance, err = _text(d.get("guidance"), GUIDANCE_MAX, "'%s' guidance" % label)
        if err:
            return None, err
        raw_codes = d.get("codes")
        if not isinstance(raw_codes, list) or not raw_codes:
            return None, "Dimension '%s' needs at least one code." % label
        if len(raw_codes) > CODES_MAX:
            return None, "Dimension '%s': at most %d codes." % (label, CODES_MAX)
        codes, code_keys = [], set()
        for j, c in enumerate(raw_codes):
            if isinstance(c, str):
                c = {"code": c}
            if not isinstance(c, dict):
                return None, "'%s' code %d must be an object." % (label, j + 1)
            clabel, err = _text(c.get("label"), LABEL_MAX, "'%s' code %d label" % (label, j + 1))
            if err:
                return None, err
            code = slugify(c.get("code") or clabel)
            if not code or not _SLUG_RE.match(code):
                return None, "'%s' code %d needs a code of letters, digits and underscores." % (label, j + 1)
            if code in code_keys:
                return None, "Dimension '%s' lists the code '%s' twice." % (label, code)
            code_keys.add(code)
            definition, err = _text(c.get("definition"), DEFINITION_MAX, "'%s' definition" % code)
            if err:
                return None, err
            examples, err = _lines(c.get("examples"), EXAMPLES_MAX, EXAMPLE_MAX, "'%s' examples" % code)
            if err:
                return None, err
            codes.append({"code": code, "label": clabel or titleize(code), "definition": definition, "examples": examples})
        conventions, err = _lines(d.get("conventions"), CONVENTIONS_MAX, CONVENTION_MAX, "'%s' conventions" % label)
        if err:
            return None, err
        default = None
        if not multi:
            wanted = slugify(d.get("default") or "")
            if wanted and wanted not in code_keys:
                return None, "Dimension '%s': the default '%s' is not one of its codes." % (label, wanted)
            default = wanted or next((c for c in ("none", "neutral", "other") if c in code_keys), codes[-1]["code"])
        dims.append({"key": key, "label": label, "multi": multi, "guidance": guidance,
                     "default": default, "codes": codes, "conventions": conventions})
    return {"name": name, "description": description, "context": context, "dimensions": dims}, None


# ---------------------------------------------------------- conversions

def to_codebook(scheme, ref=None):
    """The engine's shape for a scheme: dimensions keyed by slug."""
    dims = {}
    for d in scheme["dimensions"]:
        spec = {"multi": bool(d.get("multi")), "label": d.get("label") or titleize(d["key"]),
                "default": [] if d.get("multi") else d.get("default"),
                "guidance": d.get("guidance") or "",
                "codes": {c["code"]: {"label": c.get("label") or titleize(c["code"]),
                                      "definition": c.get("definition") or "",
                                      "examples": list(c.get("examples") or [])} for c in d["codes"]}}
        if d.get("conventions"):
            spec["conventions"] = list(d["conventions"])
        if d.get("notes"):
            spec["notes"] = d["notes"]
        dims[d["key"]] = spec
    return {"version": scheme.get("version") or scheme["name"], "ref": ref or scheme.get("ref"),
            "name": scheme["name"], "description": scheme.get("description") or "",
            "case_facts": list(scheme.get("context") or []), "dimensions": dims}


def panel_json(codebook):
    """What the pod page needs to render a run: dimensions, codes and labels
    in order, plus which codebook-specific analytics apply."""
    dims = []
    for key, spec in codebook["dimensions"].items():
        dims.append({"key": key, "label": spec.get("label") or titleize(key), "multi": bool(spec.get("multi")),
                     "default": spec.get("default"),
                     "codes": [{"code": c, "label": e.get("label") or titleize(c)} for c, e in spec["codes"].items()]})
    return {"ref": codebook.get("ref"), "name": codebook.get("name") or codebook.get("version"),
            "dimensions": dims, "analytics": analytics(codebook)}


def analytics(codebook):
    """Which of the negotiation-specific analytics the scheme supports: the
    de-escalation timeline needs an 'emotion' dimension with 'escalating';
    the per-team dynamics need 'rip' with interest/right/power."""
    dims = codebook.get("dimensions") or {}
    emotion = (dims.get("emotion") or {}).get("codes") or {}
    rip = (dims.get("rip") or {}).get("codes") or {}
    frame = (dims.get("frame") or {}).get("codes") or {}
    return {"timeline": "escalating" in emotion,
            "future_move": "future_problem_solving" in frame,
            "dynamics": all(c in rip for c in ("interest", "right", "power"))}


def resolve(ref, lookup=None):
    """The scheme (editor shape) a session ref points at, or None. ``lookup``
    maps a numeric id to a stored scheme dict for "scheme:<id>"."""
    if not ref or not isinstance(ref, str):
        return None
    if ref.startswith(BUILTIN_PREFIX):
        return builtin_scheme(ref[len(BUILTIN_PREFIX):])
    if ref.startswith(SCHEME_PREFIX) and lookup is not None:
        try:
            scheme_id = int(ref[len(SCHEME_PREFIX):])
        except ValueError:
            return None
        stored = lookup(scheme_id)
        return dict(stored, ref=ref) if stored else None
    return None


def loads(raw):
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None
