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
    return json_response([folder.json() for folder in database.get_folders(owner_id=user['id'])])

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