from flask import Blueprint, Response, jsonify, request, abort, session
from tables.topic_model import TopicModel
from utility import sanitize, json_response
from werkzeug.utils import secure_filename
import topic_modeling.topicmodeling as topicmodeling
import logging
import database
import wrappers
import os
from joblib import dump, load


api_routes = Blueprint('fileupload', __name__)


@api_routes.route('/api/v1/uploads/<int:user_id>', methods=['POST'])
@wrappers.verify_login()
def post_file(user_id, **kwargs):
    logging.info("Upload a file.")
    if request.method == 'POST':
        logging.info("This is a post")
        # fileUploaded = request.files['fileUpload']
        filesUploaded = request.files.getlist("fileUpload[]")
        logging.info(filesUploaded)
        for fileUploaded in filesUploaded:
            filename = secure_filename(fileUploaded.filename)
            logging.info("fileName: ")
            logging.info(filename)
            if filename != '':
                logging.info("This file has file name")
                if not os.path.exists("uploads"):
                    os.makedirs("uploads/")
                if not os.path.exists("uploads/{}".format(user_id)):
                    os.makedirs("uploads/{}".format(user_id))
                fileUploaded.save(os.path.join(
                    "uploads/{}".format(user_id), filename))
    return json_response()


@api_routes.route('/api/v1/topics', methods=['GET'])
@wrappers.verify_login(public=True)

def get_topics(user, **kwargs):
    id2word, texts, corpus = topicmodeling.generate_corpus(
        "uploads/{}".format(user['id']), [""])
    topicModel = topicmodeling.generate_topic_model(id2word, texts, corpus, 5)

    if not os.path.exists("topicModels"):
      os.makedirs("topicModels")
    dump(topicModel, os.path.join("topicModels", "tempModel"))

    response = [topic[1] for topic in topicModel.print_topics()]
    logging.info(response)
    return json_response(response)


@api_routes.route('/api/v1/topics', methods=['POST'])
@wrappers.verify_login(public=True)

def save_topic_model(user, **kwargs):
  new_name = request.json.get('name', None)
  summary = request.json.get('summary', None)

  valid, message = TopicModel.verify_fields(
    name=new_name)
  if not valid:
    return json_response({'message': message}, 400)
  if new_name != None:
    new_topic_model = database.add_topic_model(user['id'], new_name, summary)
    file_name = "{}_{}".format(new_topic_model.owner_id, new_topic_model.id)
    os.rename(os.path.join("topicModels", "tempModel"), os.path.join("topicModels", file_name))
    return json_response(new_topic_model.json())
  else:
    return json_response({'message': 'Must provide "name".'}, status=400)

@api_routes.route('/api/v1/topic_models', methods=['GET'])
@wrappers.verify_login(public=True)

def get_topic_models(user, **kwargs):
  return json_response([topic_model.json() for topic_model in database.get_topic_models(owner_id=user['id'])])

@api_routes.route('/api/v1/topic_models/<int:topic_model_id>', methods=['DELETE'])
@wrappers.verify_login(public=True)
@wrappers.verify_topic_model_access

def deleteTopicModel(topic_model_id, **kwargs):
  topic_model = database.get_topic_models(id=topic_model_id)
  file_name = "{}_{}".format(topic_model.owner_id, topic_model.id)
  success = database.delete_topic_model(topic_model_id)
  if success:
    os.remove(os.path.join("topicModels", file_name))
    return json_response()
  else:
    return json_response('Failed to delete topic model.', 400)

