"""Promote reviewed voice-print v2 profiles from staging into production.

Deliberate and reversible: dry-run by default, requires an explicit --approve
alias list (or --approve-all), and backs up every replaced print to a
timestamped .bak before overwriting. Only touches audiobiometrics/<alias>.emb.npy
(the ECAPA cache the overlap / enrollment-quality / cluster-reconcile paths
read) — no database writes; transcript re-attribution is a separate step
(reattribute_pod.py).

Usage:
  # see what would change
  ../venv-unified/bin/python3 reattribution/promote_profiles.py \
      --staging <dir> --approve cloud matthewxu didiermun
  # actually do it
  ... --approve cloud matthewxu --execute --stamp 20260720
"""
import argparse
import glob
import json
import os
import shutil

BIOMETRICS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audiobiometrics")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", required=True)
    ap.add_argument("--approve", nargs="*", default=[],
                    help="aliases to promote")
    ap.add_argument("--approve-all", action="store_true")
    ap.add_argument("--execute", action="store_true",
                    help="without this, dry-run only")
    ap.add_argument("--stamp", default=None,
                    help="backup suffix, e.g. a date (required with --execute)")
    args = ap.parse_args()

    staged = {os.path.basename(p)[: -len(".emb.npy")]: p
              for p in glob.glob(os.path.join(args.staging, "*.emb.npy"))}
    manifest = {}
    mpath = os.path.join(args.staging, "manifest.json")
    if os.path.isfile(mpath):
        manifest = {m["alias"]: m for m in json.load(open(mpath)).get("profiles", [])}

    approve = set(staged) if args.approve_all else set(args.approve)
    unknown = approve - set(staged)
    if unknown:
        print("WARNING: no staged profile for:", sorted(unknown))
    approve &= set(staged)
    if not approve:
        print("nothing approved. Staged profiles:", sorted(staged))
        return

    if args.execute and not args.stamp:
        print("refusing to --execute without --stamp (backup suffix).")
        return

    print("%-14s %-9s %-18s %s" % ("alias", "seconds", "anchor", "action"))
    for alias in sorted(approve):
        m = manifest.get(alias, {})
        dst = os.path.join(BIOMETRICS, alias + ".emb.npy")
        has_old = os.path.isfile(dst)
        action = ("overwrite (backup)" if has_old else "new") if args.execute \
            else ("would overwrite" if has_old else "would create")
        print("%-14s %-9s %-18s %s" %
              (alias, m.get("seconds", "?"), m.get("anchor", "?"), action))
        if args.execute:
            if has_old:
                shutil.copy2(dst, dst + ".bak-" + args.stamp)  # keep original mtime
            # copy (NOT copy2): the promoted .emb.npy must get a FRESH mtime,
            # newer than the enrollment .wav — else _cached_embedding sees a
            # stale cache and regenerates from the old recording, silently
            # undoing the promotion.
            shutil.copy(staged[alias], dst)
            os.utime(dst, None)

    if args.execute:
        print("\npromoted %d profiles into %s (backups: *.emb.npy.bak-%s)"
              % (len(approve), BIOMETRICS, args.stamp))
        print("next: re-run enrollment survey to refresh .check.json quality, "
              "and reattribute_pod.py to push corrected transcript labels.")
    else:
        print("\nDRY RUN — re-run with --execute --stamp <date> to apply.")


if __name__ == "__main__":
    main()
