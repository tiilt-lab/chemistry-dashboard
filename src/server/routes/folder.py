from flask import Blueprint, request
import logging
import database
import json
from utility import json_response
import wrappers
from tables.folder import Folder

api_routes = Blueprint('folder', __name__)

@api_routes.route('/api/folders', methods=['GET'])
@wrappers.verify_login()
def get_folders(user, **kwargs):
    # Folders follow sessions: admins and supers see every account's, so a
    # session an admin is allowed to read is not hidden by a folder they cannot
    # see. Without this the sessions list returned another owner's sessions but
    # the page filed them under a folder it had never heard of, and they simply
    # never appeared. Writes stay owner-or-super via verify_folder_access.
    sees_all = user.get('role') in ['admin', 'super']
    folders = database.get_folders(owner_id=None if sees_all else user['id'])
    owner_emails = database.get_user_emails() if sees_all else {}
    result = []
    for folder in folders:
        data = folder.json()
        data['owned'] = folder.owner_id == user['id']
        if sees_all:
            data['owner'] = owner_emails.get(folder.owner_id)
        result.append(data)
    return json_response(result)

@api_routes.route('/api/folder', methods=['POST'])
@wrappers.verify_login()
def add_folder(user, **kwargs):
    owner_id = user['id']
    name = request.json.get('name', 'Folder')
    parent = request.json.get('parent', None)
    if parent == -1:
        parent = None
    valid, message = Folder.verify_fields(name=name)
    if not valid:
        return json_response({'message': message}, 400)
    if parent:
        owned_folder = database.get_folders(id=parent, owner_id=owner_id, first=True)
        if not owned_folder:
            return json_response({'message': 'Folder does not exist.'}, 404)
    folder = database.add_folder(owner_id=owner_id, name=name, parent=parent)
    return json_response(folder.json())

@api_routes.route('/api/folders/<int:folder_id>', methods=['POST'])
@wrappers.verify_login()
@wrappers.verify_folder_access
def update_folder(folder_id, user, **kwargs):
    parent = request.json.get('parent', None)
    name = request.json.get('name', None)
    if name:
        valid, message = Folder.verify_fields(name=name)
        if not valid:
            return json_response({'message': message}, 400)
    if parent:
        if database.is_child_folder(folder_id, parent) or folder_id == parent:
            return json_response({'message':'Invalid location.'}, 400)
    if parent != -1:
        owned_folder = database.get_folders(id=parent, owner_id=user['id'], first=True)
        if not owned_folder:
            return json_response({'message': 'Folder does not exist.'}, 404)
    folder = database.update_folder(folder_id, name, parent)
    return json_response(folder.json())

@api_routes.route('/api/folders/<int:folder_id>', methods=['DELETE'])
@wrappers.verify_login()
@wrappers.verify_folder_access
def delete_folder(folder_id, **kwargs):
    success, message = database.delete_folder(folder_id)
    return json_response({'message': message}, 200 if success else 400)