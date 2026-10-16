"""Enrollment asks for a username, group and team, not a first and last
name: the sign-up form, the Students page and the student routes agree,
and the old name-based records still display."""
import ast
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return f.read()


def test_signup_form_asks_for_username_group_and_team_only():
    page = _read("frontend", "src", "profile-creation", "html-pages.jsx")
    for field in ('id="username"', 'id="group"', 'id="team"'):
        assert field in page
    for gone in ('id="firstname"', 'id="lastname"', "First name", "Last name"):
        assert gone not in page
    comp = _read("frontend", "src", "profile-creation", "profile-creation-component.jsx")
    assert "const verifyUserProfileInput = (username, group, team, voiceOnlyChoice = false) => {" in comp
    assert "createStudentProfile({ username, group, team }," in comp
    assert "{ group: studentObject.group_name, team: studentObject.team_name }," in comp
    svc = _read("frontend", "src", "services", "auth-service.js")
    assert "group: profile.group || \"\"," in svc and "team: profile.team || \"\"," in svc
    assert "firstname" not in svc and "lastname" not in svc


def test_students_page_shows_name_group_and_team_and_edits_the_labels():
    page = _read("frontend", "src", "students", "students-component.jsx")
    assert "firstname" not in page and "lastname" not in page
    assert 'id="stuUsername"' in page and 'id="stuGroup"' in page and 'id="stuTeam"' in page
    assert 'id="editGroup"' in page and 'id="editTeam"' in page
    assert "{ username, group, team }," in page
    assert '"Name,Username,Group,Team,Voice,Face,Sessions,Last active,Created"' in page
    profile = _read("frontend", "src", "student-profile", "student-profile-component.jsx")
    assert "firstname" not in profile and "{student.name}" in profile
    model = _read("frontend", "src", "models", "student.js")
    assert "model.group_name = json['group_name'] || null" in model
    assert "model.name = json['name'] || json['username']" in model


def test_routes_take_group_and_team_and_prove_reenrollment_with_them():
    s = _read("src", "server", "routes", "student.py")
    tree = ast.parse(s)
    add = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "add_students")
    src = ast.unparse(add)
    assert "group_name, team_name = _labels(content)" in src
    assert "database.add_student(username, group_name=group_name, team_name=team_name)" in src
    assert "name_matches = student.identity_matches(group_name, team_name)" in src
    assert "Must provide Last name" not in s and "Must provide First name" not in s
    upd = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "update_students")
    src = ast.unparse(upd)
    assert "student.identity_matches(typed_group, typed_team)" in src
    assert "edits = {}" in src  # non-admins never edit the labels


def test_half_finished_signup_is_reclaimable_and_the_page_only_proceeds_with_a_token():
    # A student whose recording never uploaded (biometric_captured stays
    # "no") retried with a differently typed group, got "Username already
    # exists" without a token, and the page still sent them on to the
    # recorder, where the socket refused them: a dead end (2026-10-16).
    s = _read("src", "server", "routes", "student.py")
    add = next(n for n in ast.walk(ast.parse(s)) if isinstance(n, ast.FunctionDef) and n.name == "add_students")
    src = ast.unparse(add)
    assert "unclaimed = student.biometric_captured != 'yes'" in src
    claim = s[s.index("if unclaimed and not name_matches:"):s.index("body = {'message': \"Username already exists.\"")]
    assert 'database.update_student(student.id, group_name=group_name or "", team_name=team_name or "")' in claim
    assert "name_matches = True" in claim
    svc = _read("frontend", "src", "services", "auth-service.js")
    assert 'if (err["reenroll_allowed"] && student.enrollment_token){' in svc
    assert 'student.biometric_captured !== "yes"' not in svc
    page = _read("frontend", "src", "profile-creation", "html-pages.jsx")
    assert "maxLength={20}" in page and "maxLength={10}" not in page, "username box must take the 20-char limit"
    assert "5–20 letters and numbers" in page


def test_migration_adds_the_labels_and_relaxes_the_names():
    m = _read("src", "server", "migrations", "versions", "9a1b2c3d4e5f_student_group_team.py")
    assert "revision = '9a1b2c3d4e5f'" in m and "down_revision = '809102132435'" in m
    assert "LABELS = ('group_name', 'team_name')" in m
    assert "batch.alter_column(col, existing_type=sa.String(length=50), nullable=True)" in m
    t = _read("src", "server", "tables", "student.py")
    assert "lastname = db.Column(db.String(50), nullable=True)" in t
    assert "firstname = db.Column(db.String(50), nullable=True)" in t
    assert "group_name = db.Column(db.String(64), nullable=True)" in t
