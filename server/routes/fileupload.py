from flask import Blueprint, Response, jsonify, request, abort, session
from utility import sanitize, json_response
from werkzeug.utils import secure_filename
import topic_modeling.topicmodeling as topicmodeling
import logging
import database
import wrappers
import os


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
    response = [topic[1] for topic in topicModel.print_topics()]
    logging.info(response)
    return json_response(response)
