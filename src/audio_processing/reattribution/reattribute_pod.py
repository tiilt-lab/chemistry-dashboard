"""Push confirmed cluster -> name corrections into the transcript, via the
sanctioned reassign endpoint (never direct DB), and report how attribution
moves. The batch form of the transcript UI's "apply to all N" button.

Input mapping (JSON): {"<device_id>": {"<old_tag>": "<name>", ...}, ...}
  — e.g. {"923": {"SPEAKER_00": "Fengli"}} confirms that pod 923's
  SPEAKER_00 diarization cluster is really Fengli. Sources: the tagging UI,
  a resolved cross-session chain, or a fused audio+video verdict. Only names
  in the pod roster are accepted (the endpoint enforces this).

Dry-run by default: shows before/after speaking-seconds per speaker without
writing. --execute applies via POST /transcripts/<id>/reassign?apply_to_tag.

Usage:
  BLINC_EMAIL=.. BLINC_PASSWORD=.. ../venv-unified/bin/python3 \
     reattribution/reattribute_pod.py --session 292 --map map.json [--execute]
"""
import argparse
import json
import os
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", type=int, required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--base-url", default="https://nublinc.com")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    import requests
    s = requests.Session()
    s.post(args.base_url + "/api/v1/login", json={
        "email": os.environ["BLINC_EMAIL"],
        "password": os.environ["BLINC_PASSWORD"]}, timeout=30).raise_for_status()

    mapping = json.load(open(args.map))
    for did, tagmap in mapping.items():
        did = int(did)
        rows = s.get(args.base_url + "/api/v1/sessions/%d/devices/%d/transcripts"
                     % (args.session, did), timeout=60).json()
        before = defaultdict(float)
        for r in rows:
            before[r.get("speaker_tag") or "(none)"] += r["length"]

        # simulate the relabel to show the after-picture
        after = defaultdict(float)
        changed_rows = 0
        for r in rows:
            new = tagmap.get(r.get("speaker_tag"))
            tag = new or (r.get("speaker_tag") or "(none)")
            after[tag] += r["length"]
            if new and new != r.get("speaker_tag"):
                changed_rows += 1

        print("\n=== pod %d — %d rows, %d would change ===" % (did, len(rows), changed_rows))
        print("  before: %s" % {k: round(v) for k, v in sorted(before.items(), key=lambda x: -x[1])})
        print("  after : %s" % {k: round(v) for k, v in sorted(after.items(), key=lambda x: -x[1])})

        if not args.execute:
            continue
        # apply: one call per (old_tag -> name) with apply_to_tag, using any
        # row that currently carries old_tag as the handle.
        for old_tag, name in tagmap.items():
            handle = next((r["id"] for r in rows if r.get("speaker_tag") == old_tag), None)
            if handle is None:
                continue
            resp = s.post(args.base_url + "/api/v1/transcripts/%d/reassign" % handle,
                          json={"alias": name, "apply_to_tag": True}, timeout=30)
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            print("  %s -> %s : %s" % (old_tag, name,
                                       body.get("reassigned", body.get("message", resp.status_code))))
    if not args.execute:
        print("\nDRY RUN — add --execute to write via the reassign endpoint.")


if __name__ == "__main__":
    main()
