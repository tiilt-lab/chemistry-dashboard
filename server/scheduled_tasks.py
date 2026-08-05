from apscheduler.schedulers.background import BackgroundScheduler
from handlers import session_handler
import database
import requests
import datetime
import logging

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

# Verifies if session is still active.
def check_transcripts():
	try:
		active_sessions = database.get_sessions(active=True)
		for session in active_sessions:
			length = session.get_length()
			if length > TIMEOUT:
				transcripts = database.get_transcripts(session_id=session.id, start_time=max(length - TIMEOUT, 0), end_time=-1)
				if len(transcripts) == 0:
					logging.info('No transcripts received in last {0} minutes, stopping session'.format(int(TIMEOUT / 60)))
					session_handler.end_session(session.id)
	except Exception as ex:
		logging.info('Session timeout scheduled task has failed: {0}'.format(ex))
	finally:
		database.close_session()
