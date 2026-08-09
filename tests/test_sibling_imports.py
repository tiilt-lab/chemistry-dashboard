"""Guard against the bare-sibling-import bug that took the video services down.

Modules in a package directory (one containing __init__.py) are loaded as
`package.module` submodules, so the package's OWN directory is NOT on sys.path.
A bare `import sibling` / `from sibling import X` of a same-directory module
then raises ModuleNotFoundError at service start — and CI misses it, because the
test runner puts those dirs on sys.path directly. (This is exactly how #8's
metric_post_policy and #11's frame_payload crash-looped the video services.)

A package module may import a same-dir sibling only via a relative import
(`from .sibling import X`) OR after inserting its own directory onto sys.path
(`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`). This test
enforces that across the first-party tree.
"""
import ast
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src")

# Vendored / generated code (mirrors the ruff excludes in pyproject.toml).
EXCLUDE = ("/venv-", "/yolo_head/", "/asd/", "/attention_tracking/",
           "/video_cartoonizer/model/", "/emotion_detector/models/",
           "/migrations/versions/", "/__pycache__/", "/site-packages/")


def _self_dir_bootstrapped(text):
    # A line that puts THIS file's own directory on sys.path.
    return re.search(r"path\.insert\([^)]*dirname\([^)]*abspath\(__file__\)", text) is not None


def test_no_bare_sibling_imports_in_package_dirs():
    violations = []
    for root, _dirs, files in os.walk(SRC):
        if any(x in (root + "/") for x in EXCLUDE):
            continue
        if "__init__.py" not in files:
            continue  # only real package dirs load as submodules
        siblings = {f[:-3] for f in files if f.endswith(".py") and f != "__init__.py"}
        for f in files:
            if not f.endswith(".py") or f == "__init__.py":
                continue
            path = os.path.join(root, f)
            if any(x in "/" + path for x in EXCLUDE):
                continue
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            boot = _self_dir_bootstrapped(text)
            if boot:
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for n in names:
                    if n in siblings:
                        rel = os.path.relpath(path, REPO)
                        violations.append(f"{rel}:{node.lineno} bare-imports same-dir sibling '{n}'")

    assert not violations, (
        "package modules must import same-dir siblings via a relative import or "
        "after a self-dir sys.path insert:\n  " + "\n  ".join(violations))
