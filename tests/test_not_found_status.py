"""A "not found" response must be 404, not 400.

The route files disagreed: ~18 endpoints returned 404 for a missing entity and
~18 returned 400 for the same outcome (the message literally said "not found").
404 is correct; the 400s are the drift. This bans the "not found ... 400"
combination in the route files. (Flask routes don't run in CI -> source check.)
"""
import os
import re

ROUTES = os.path.join(os.path.dirname(__file__), "..", "src", "server", "routes")


def test_no_route_returns_400_for_a_not_found_message():
    offenders = []
    for name in os.listdir(ROUTES):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(ROUTES, name)) as f:
            for i, line in enumerate(f, 1):
                if re.search(r"not found", line, re.I) and re.search(r",\s*400\)", line):
                    offenders.append(f"{name}:{i}")
    assert not offenders, "a 'not found' response must be 404, not 400: " + ", ".join(offenders)
