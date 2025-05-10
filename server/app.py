import eventlet
eventlet.monkey_patch()

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import os
import shutil
import socket
import time
import redis
from datetime import timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import config as cf

# Initialize config file
cf.initialize()
base_dir = os.path.dirname(os.path.abspath(__file__))

# Create logger
log_format = logging.Formatter('%(asctime)s - %(name)s(%(levelname)s): %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('apscheduler.executors.default').setLevel(logging.CRITICAL) # Suppresses output from APScheduler
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('socketio.server').setLevel(logging.WARNING)
logging.getLogger('engineio.server').setLevel(logging.WARNING)
dir_path = os.path.dirname(os.path.realpath(__file__))
log_file = logging.FileHandler(os.path.join(dir_path, 'discussion_capture_server.log'))
log_file.setFormatter(log_format)
logger.addHandler(log_file)
log_console = logging.StreamHandler()
log_console.setFormatter(log_format)
logger.addHandler(log_console)

# Create app
app = Flask(__name__)
app.config['SECRET_KEY'] = '\xf9\xc5_!\x9c^t\x80\xce\xee\xbc\x8c_\xd2\xd6\xf3\x92C\x9e\xcb\x88\xc7\xa9('
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = cf.https()
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_NAME'] = 'DCSession'
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# this proxyfix will allow remote_addr to be correct based on the number of proxies in the chain
# when running behind an AWS load balancer, that counts as 1. Nginx counts as another.
# For now, determine if behind AWS based on the https setting.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2 if cf.cloud() else 1, x_proto=1)

# Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Set API Limiter
limiter = Limiter(app, key_func=get_remote_address)

# Create SocketIO app (engineio_logger=True for advance debug)
if cf.cloud():
	socketio = SocketIO(app, log=logger, cors_allowed_origins=[cf.domain(),"127.0.0.1:5000","localhost"], manage_session=False, message_queue="redis://")
else:
	socketio = SocketIO(app, log=logger, cors_allowed_origins=[cf.domain(),"127.0.0.1:5000","localhost"],manage_session=False, message_queue="redis://")

# Create database
DATABASE_FILE = os.path.dirname(os.path.abspath(__file__)) + '/discussion_capture.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://{0}@localhost:3306/discussion_capture'.format(cf.database_user())
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Scheduled tasks
TIMEOUT = 10 * 60 # Time in seconds without transcripts before timeout occurs

# Create scheduler
scheduler = BackgroundScheduler({
	'apscheduler.jobstores.default': {
		'type': 'memory',
	},
	'apscheduler.executors.default': {
		'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
		'max_workers': '20'
	},
	'apscheduler.executors.processpool': {
		'type': 'processpool',
		'max_workers': '5'
	},
	'apscheduler.job_defaults.coalesce': 'false',
	'apscheduler.job_defaults.max_instances': '3',
	'apscheduler.timezone': 'UTC',
})
scheduler.start()
