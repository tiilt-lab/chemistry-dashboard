#!/usr/bin/env bash
# Dependency hygiene for src/ (CI job "deptry"): what the code imports must be
# what src/requirements-direct.txt lists, and the lock must pin every name
# there. Config in pyproject.toml [tool.deptry].
set -euo pipefail
cd "$(dirname "$0")/../.."

# The services put their own directories on sys.path and import by bare name
# (import callbacks, import database), so every module and package under
# src/* is first party, not a missing dependency.
mapfile -t names < <(find src -maxdepth 3 \( -path 'src/venv-*' -o -name node_modules -o -name __pycache__ \) -prune -o \( -name '*.py' -o -type d \) -print \
    | sed -E 's#.*/##; s#\.py$##' | grep -vE '^(src|)$' | sort -u)
args=()
for n in "${names[@]}"; do args+=(--known-first-party "$n"); done
deptry src "${args[@]}"

python3 - <<'EOF'
import re
def names(path):
    out = set()
    for line in open(path):
        line = line.strip()
        if line and not line.startswith(("#", "-")):
            out.add(re.split(r"[=<>!@ ;\[]", line, 1)[0].lower().replace("_", "-"))
    return out
direct = names("src/requirements-direct.txt")
lock = names("src/requirements-unified.txt")
try:
    lock |= names("src/requirements-unified-nodeps.txt")
except FileNotFoundError:
    pass
missing = sorted(direct - lock)
if missing:
    raise SystemExit("direct dependencies not pinned in the lock: " + ", ".join(missing))
print("lock covers all %d direct dependencies" % len(direct))
EOF
