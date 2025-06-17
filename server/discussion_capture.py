from app import app, db, DATABASE_FILE, socketio, scheduler
from routes import socket
from tables import folder, device, session_device, session, transcript, keyword, keyword_usage, keyword_list, keyword_list_item, user
import scheduled_tasks
import config as cf
import device_websockets
import os
import logging
import database

from routes.auth import api_routes as auth_api
from routes.session import api_routes as session_api
from routes.device import api_routes as device_api
from routes.keyword import api_routes as keyword_api
from routes.callback import api_routes as callback_api
from routes.admin import api_routes as admin_api
from routes.folder import api_routes as folder_api
from routes.topic_model import api_routes as topicmodel_api
from routes.speaker import api_routes as speaker_api

app.register_blueprint(admin_api)
app.register_blueprint(auth_api)
app.register_blueprint(session_api)
app.register_blueprint(device_api)
app.register_blueprint(keyword_api)
app.register_blueprint(callback_api)
app.register_blueprint(folder_api)
app.register_blueprint(topicmodel_api)
app.register_blueprint(speaker_api)



def main():
    
	# Set device connection status to false
	devices = database.get_devices(connected=True)
	for device in devices:
		device.connected = False
	database.save_changes()

	# Schedule tasks
	scheduler.add_job(scheduled_tasks.check_transcripts, 'interval', seconds=60)

	device_websockets.run_server()
	logging.info('Discussion Capture Server running...')
	socketio.run(app, debug=cf.debug(), host="0.0.0.0", use_reloader=False)
	scheduler.shutdown(wait=False)

if __name__ == '__main__':
    main()
