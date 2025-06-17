from flask import Blueprint, Response, jsonify, request, abort, session
from utility import sanitize, json_response
from tables.keyword_list import KeywordList
from tables.keyword_list_item import KeywordListItem
import topic_modeling.topicmodeling as topicmodeling
import logging
import database
import wrappers
import os

api_routes = Blueprint('keyword', __name__)


@api_routes.route('/api/v1/keyword_lists', methods=['GET'])
@wrappers.verify_login(public=True)
def get_keyword_lists(user, **kwargs):
    return json_response([keyword_list.json() for keyword_list in database.get_keyword_lists(owner_id=user['id'])])


# @api_routes.route('/api/v1/topics', methods=['GET'])
# @wrappers.verify_login(public=True)
# def get_topics(user, **kwargs):
#     id2word, texts, corpus = topicmodeling.generate_corpus(
#         "/vagrant/uploads/{}".format(user['id']), [""])
#     topicModel = topicmodeling.generate_topic_model(id2word, texts, corpus, 5)
#     response = [topic[1] for topic in topicModel.print_topics()]
#     return json_response(response)


@api_routes.route('/api/v1/keyword_lists', methods=['POST'])
@wrappers.verify_login(public=True)
def add_keyword_list(user, **kwargs):
    new_name = request.json.get('name', None)
    new_keywords = request.json.get('keywords', None)
    valid, message = KeywordList.verify_fields(
        name=new_name, keywords=new_keywords)
    if not valid:
        return json_response({'message': message}, 400)
    if new_name != None or new_keywords != None:
        new_keyword_list = database.add_keyword_list(user['id'])
        new_keyword_list = database.update_keyword_list(
            new_keyword_list.id, new_name, new_keywords)
        return json_response(new_keyword_list.json())
    else:
        return json_response({'message': 'Must provide both "name" and "keywords".'}, status=400)


@api_routes.route('/api/v1/keyword_lists/<int:keyword_list_id>', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_keyword_list_access
def get_keyword_list(keyword_list_id, **kwargs):
    keyword_list = database.get_keyword_lists(id=keyword_list_id)
    if keyword_list:
        return json_response(keyword_list.json())
    else:
        return json_response({'message': 'Keyword list not found'}, 400)


@api_routes.route('/api/v1/keyword_lists/<int:keyword_list_id>', methods=['PUT'])
@wrappers.verify_login(public=True)
@wrappers.verify_keyword_list_access
def update_keyword_list(keyword_list_id, **kwargs):
    new_name = request.json.get('name', None)
    new_keywords = request.json.get('keywords', None)
    valid, message = KeywordList.verify_fields(
        name=new_name, keywords=new_keywords)
    if not valid:
        return json_response({'message': message}, 400)
    if new_name != None or new_keywords != None:
        keyword_list = database.update_keyword_list(
            keyword_list_id, new_name, new_keywords)
        return json_response(keyword_list.json())
    return json_response({'message': 'Keyword list not found'}, 400)


@api_routes.route('/api/v1/keyword_lists/<int:keyword_list_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_keyword_list_access
def delete_keyword_list(keyword_list_id, **kwargs):
    success = database.delete_keyword_list(keyword_list_id)
    if success:
        return json_response()
    else:
        return json_response('Failed to delete keyword list.', 400)


@api_routes.route('/api/v1/keyword_lists/<int:keyword_list_id>/keywords', methods=['GET'])
@wrappers.verify_login(public=True)
@wrappers.verify_keyword_list_access
def get_keyword_list_items(keyword_list_id, **kwargs):
    keywords = database.get_keyword_list_items(keyword_list_id)
    return json_response([keyword.json() for keyword in keywords])
