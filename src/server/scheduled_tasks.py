from apscheduler.schedulers.background import BackgroundScheduler
from handlers import session_handler
import database
import requests
import datetime
import logging
import watchers

TIMEOUT = 10 * 60 # Time in seconds without transcripts before timeout occurs
WATCH_TIMEOUT = 5 * 60 # Dashboard poll recency that still counts as "watched"

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

# Verifies if session is still active.
def check_transcripts():
	# Flask-SQLAlchemy 3: background jobs need an app context for db access.
	from app import app
	with app.app_context():
		_check_transcripts()


def _check_transcripts():
	try:
		active_sessions = database.get_sessions(active=True)
		for session in active_sessions:
			devices = database.get_session_devices(session_id=session.id)
			# Lobby: joining is open and nobody has joined yet — an
			# instructor may have set up ahead of class; wait indefinitely.
			if session.passcode is not None and len(devices) == 0:
				continue
			# A connected group is activity, speaking or not.
			if any(device.connected for device in devices):
				continue
			# Someone has the session dashboard open (it polls every 2s).
			if watchers.watched_within(session.id, WATCH_TIMEOUT):
				continue
			length = session.get_length()
			if length > TIMEOUT:
				transcripts = database.get_transcripts(session_id=session.id, start_time=max(length - TIMEOUT, 0), end_time=-1)
				if len(transcripts) == 0:
					logging.info('Session {0}: no transcripts, no connected devices, and unwatched for {1} minutes - stopping.'.format(session.id, int(TIMEOUT / 60)))
					session_handler.end_session(session.id)
	except Exception as ex:
		logging.info('Session timeout scheduled task has failed: {0}'.format(ex))
	finally:
		database.close_session()
