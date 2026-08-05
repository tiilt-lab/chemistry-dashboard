import eventlet

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, make_response, jsonify, request
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

eventlet.patcher.monkey_patch(select=True, socket=True)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
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
r = redis.Redis(host='127.0.0.1', port=6379, db=0)

# Set API Limiter (Flask-Limiter 3.x compatible)
limiter = Limiter(key_func=get_remote_address, app=app)

redis_loc = "redis://127.0.0.1:6379"

# Create SocketIO app (engineio_logger=True for advance debug)
# Allow all origins for production deployment (can restrict later with domain)
socketio = SocketIO(app, log=logger, cors_allowed_origins="*", manage_session=False, message_queue=redis_loc)

# Create database
DATABASE_SERVER = "127.0.0.1" #"blinc.c2tdsnprd97b.us-east-2.rds.amazonaws.com"
DATABASE_FILE = os.path.dirname(os.path.abspath(__file__)) + '/discussion_capture.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://{0}@{1}/discussion_capture'.format(cf.database_user(), DATABASE_SERVER)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
import database
migrate = Migrate(app, db)

# ---------------------------------------------------------------------------
# Study mode: per-participant database isolation
# ---------------------------------------------------------------------------
from flask import session as flask_session, g
from sqlalchemy import event, text

@event.listens_for(db.engine, "checkout")
def _on_checkout(dbapi_conn, conn_record, conn_proxy):
    """Reset connection to correct DB when checked out from pool.
    If we're inside a study-user request, switch to their DB;
    otherwise default to discussion_capture (safety net)."""
    from flask import has_request_context
    target_db = 'discussion_capture'
    if has_request_context():
        study_db = getattr(g, 'study_db', None)
        if study_db:
            target_db = study_db
    cursor = dbapi_conn.cursor()
    cursor.execute(f"USE {target_db}")
    cursor.close()

@app.before_request
def _switch_study_db():
    """If the logged-in user is a study participant (role='study'), route all DB
    and ChromaDB access to their isolated copies."""
    # Skip DB switch for auth routes — they query main DB tables (user, api_client)
    from flask import request
    _MAIN_DB_ROUTES = ('/api/v1/login', '/api/v1/logout', '/api/v1/me',
                       '/api/v1/password', '/api/v1/token')
    if request.path in _MAIN_DB_ROUTES:
        return

    user = flask_session.get('user') or {}
    if user.get('role') == 'study':
        email = user.get('email', '')
        study_db = f'study_{email}'
        g.study_db = study_db
        g.study_user_id = email
        g.chroma_path = f'./chroma_db_{email}'
        db.session.execute(text(f'USE {study_db}'))


# Add with other imports
from llm_routes import llm_bp
from concept_routes import concept_bp
from websocket_handler import init_concept_websocket
from rag_routes import rag_api
from seven_cs_routes import seven_cs_bp
from discussion_pulse_routes import discussion_pulse_bp
from agent_routes import agent_bp
from agent_v2.routes import agent_v2_bp
from agent_v3.routes import agent_v3_bp
from agent_v7.routes_v2 import agent_v7_bp  # Simplified 5-tool architecture
from agent_baseline.routes import agent_baseline_bp  # Transcript-only baseline
from expert_annotation_routes import expert_annotation_bp  # Expert 7C annotations for research
from expert_agent_rating_routes import expert_agent_rating_bp  # Expert blind agent evaluation
from expert_concept_map_rating_routes import expert_concept_map_rating_bp  # Expert concept map ratings
from dimension_schema_routes import dimension_schema_bp  # Dimension schema CRUD

# Register LLM routes
app.register_blueprint(llm_bp)
app.register_blueprint(concept_bp)
app.register_blueprint(rag_api)
app.register_blueprint(seven_cs_bp)
app.register_blueprint(discussion_pulse_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(agent_v2_bp)  # LangGraph agent v2
app.register_blueprint(agent_v3_bp)  # Ultra Agent v3 - intelligent reasoning
app.register_blueprint(agent_v7_bp)  # Full context agent v7 - no truncation limits
app.register_blueprint(agent_baseline_bp)  # Transcript-only baseline
app.register_blueprint(expert_annotation_bp)  # Expert 7C annotations
app.register_blueprint(expert_agent_rating_bp)  # Expert blind agent evaluation
app.register_blueprint(expert_concept_map_rating_bp)  # Expert concept map ratings
app.register_blueprint(dimension_schema_bp)  # Dimension schema CRUD

init_concept_websocket(socketio)

# Add CORS headers for regular HTTP requests

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    domain = cf.domain()
    allowed_origins = [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://127.0.0.1',
        domain,
        'http://' + domain,
        'https://' + domain
    ]
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    elif origin:
        # Allow any origin that matches the configured domain
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

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