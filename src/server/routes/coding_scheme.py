"""Coding schemes in the Library (coding_schemes.py): the built-in ones and the
caller's own, with create / update / delete for the latter. Admins and supers
see and may edit everyone's. The create-session form lists them; a session
stores the chosen one's ref.
"""
from flask import Blueprint, request
from utility import json_response
import coding_schemes as cs
import database
import wrappers

api_routes = Blueprint('coding_scheme', __name__)


def _may_edit(scheme, user):
    return scheme.owner_id == user['id'] or user.get('role') in wrappers.ADMIN_ROLES


@api_routes.route('/api/v1/coding_schemes', methods=['GET'])
@wrappers.verify_login(public=True)
def list_coding_schemes(user, **kwargs):
    # Built-ins first, then the caller's (everyone's for admins), by name.
    mine = database.get_coding_schemes(owner_id=None if user.get('role') in wrappers.ADMIN_ROLES else user['id'])
    result = [dict(s, owner_id=None, dimension_count=len(s['dimensions']),
                   context=s['context'], dimensions=s['dimensions']) for s in cs.builtin_schemes()]
    result += [dict(s.json(full=False), owned=s.owner_id == user['id']) for s in sorted(mine, key=lambda s: s.name.lower())]
    return json_response(result)


@api_routes.route('/api/v1/coding_schemes', methods=['POST'])
@wrappers.verify_login(public=True)
def create_coding_scheme(user, **kwargs):
    scheme, error = cs.normalize(request.get_json(silent=True))
    if error:
        return json_response({'message': error}, 400)
    stored = database.create_coding_scheme(user['id'], scheme)
    return json_response(stored.json())


@api_routes.route('/api/v1/coding_schemes/<path:ref>', methods=['GET'])
@wrappers.verify_login(public=True)
def get_coding_scheme(user, ref, **kwargs):
    # "builtin:<key>", "scheme:<id>" or a bare id.
    if ref.isdigit():
        ref = cs.SCHEME_PREFIX + ref
    if ref.startswith(cs.BUILTIN_PREFIX):
        scheme = cs.builtin_scheme(ref[len(cs.BUILTIN_PREFIX):])
        if scheme is None:
            return json_response({'message': 'Coding scheme not found.'}, 404)
        return json_response(dict(scheme, owner_id=None, dimension_count=len(scheme['dimensions'])))
    stored = database.get_coding_schemes(id=int(ref[len(cs.SCHEME_PREFIX):])) if ref.startswith(cs.SCHEME_PREFIX) and ref[len(cs.SCHEME_PREFIX):].isdigit() else None
    if stored is None or not _may_edit(stored, user):
        return json_response({'message': 'Coding scheme not found.'}, 404)
    return json_response(dict(stored.json(), owned=stored.owner_id == user['id']))


@api_routes.route('/api/v1/coding_schemes/<int:scheme_id>', methods=['PUT'])
@wrappers.verify_login(public=True)
def update_coding_scheme(user, scheme_id, **kwargs):
    stored = database.get_coding_schemes(id=scheme_id)
    if stored is None or not _may_edit(stored, user):
        return json_response({'message': 'Coding scheme not found.'}, 404)
    scheme, error = cs.normalize(request.get_json(silent=True))
    if error:
        return json_response({'message': error}, 400)
    stored = database.update_coding_scheme(scheme_id, scheme)
    return json_response(stored.json())


@api_routes.route('/api/v1/coding_schemes/<int:scheme_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
def delete_coding_scheme(user, scheme_id, **kwargs):
    stored = database.get_coding_schemes(id=scheme_id)
    if stored is None or not _may_edit(stored, user):
        return json_response({'message': 'Coding scheme not found.'}, 404)
    # Sessions that used it keep their coded results (the run stores its
    # own copy of the codebook's shape in the codes); new runs would fall
    # back to the built-in negotiation scheme.
    database.delete_coding_scheme(scheme_id)
    return json_response()


@api_routes.route('/api/v1/coding_schemes/validate', methods=['POST'])
@wrappers.verify_login(public=True)
def validate_coding_scheme(user, **kwargs):
    scheme, error = cs.normalize(request.get_json(silent=True))
    if error:
        return json_response({'ok': False, 'message': error}, 200)
    return json_response({'ok': True, 'scheme': scheme})
